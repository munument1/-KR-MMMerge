#!/usr/bin/env python3
"""Materialize canonical Korean localization tables from translations/ko/mmmerge.po.

The existing KO files are structural templates only: ids, columns, record order,
legacy line layout, and native file encoding are preserved. Player-facing text
comes from PO msgstr values. Generated runtime projection files are intentionally
excluded; their dedicated generators consume the canonical tables after this
step.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

import polib


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PO = ROOT / "translations/ko/mmmerge.po"
DEFAULT_REPORT = ROOT / "translations/ko/PO_BOOTSTRAP_REPORT.json"
DEFAULT_SOURCE_ROOT = ROOT / "Data/Text localization"

GENERATED = {"KO_RuntimeOverrides.txt", "KO_StatsSkillsRuntime.txt"}
LONG_SPECIAL = {"KO_GlobalTxt.txt", "KO_SpellsTxt.txt"}

STRUCT_RE = re.compile(
    r"\|table=(?P<table>[^|]+)\|id=(?P<id>[^|]+)\|field=(?P<field>[^|]+)$"
)
WIDE_RE = re.compile(r"\|id=(?P<id>[^|]+)\|field=(?P<field>[^|]+)$")
MAP_RE = re.compile(r"/(?P<file>[^/|]+)\|string=(?P<index>\d+)$")

SKILL_TABLE_TO_FIELD = {
    "SkillNames": "Name",
    "SkillDescriptions": "Description",
    "SkillDesNormal": "Normal",
    "SkillDesExpert": "Expert",
    "SkillDesMaster": "Master",
    "SkillDesGM": "GrandMaster",
}


@dataclass
class TextFile:
    text: str
    encoding: str
    bom: bool
    newline: str


def read_preserving(path: Path) -> TextFile:
    data = path.read_bytes()
    bom = data.startswith(b"\xef\xbb\xbf")
    if bom:
        text = data[3:].decode("utf-8")
        encoding = "utf-8"
    else:
        try:
            text = data.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = data.decode("cp949")
            encoding = "cp949"

    crlf = text.count("\r\n")
    bare_lf = text.count("\n") - crlf
    newline = "\r\n" if crlf > bare_lf else "\n"
    return TextFile(text=text, encoding=encoding, bom=bom, newline=newline)


def encode_preserving(doc: TextFile, text: str) -> bytes:
    data = text.encode(doc.encoding)
    if doc.encoding == "utf-8" and doc.bom:
        data = b"\xef\xbb\xbf" + data
    return data


def parse_target_from_comment(entry: polib.POEntry) -> str | None:
    for line in (entry.comment or "").splitlines():
        if line.startswith("KO: Data/Text localization/"):
            return line.rsplit("/", 1)[-1]
    return None


def load_catalog(po_path: Path, expected_files: set[str]):
    po = polib.pofile(str(po_path))
    grouped: dict[str, list[polib.POEntry]] = {name: [] for name in expected_files}
    unexpected = []
    untranslated = []
    duplicate_contexts = []
    seen = set()

    for entry in po:
        if entry.obsolete:
            continue
        context = entry.msgctxt or ""
        if not context:
            raise ValueError("active PO entry has no msgctxt")
        if context in seen:
            duplicate_contexts.append(context)
        seen.add(context)
        if not entry.msgstr:
            untranslated.append(context)

        target = parse_target_from_comment(entry)
        if target is None:
            unexpected.append(f"{context}: no KO target comment")
            continue
        if target in GENERATED:
            unexpected.append(f"{context}: generated file must not own PO text ({target})")
            continue
        if target not in grouped:
            unexpected.append(f"{context}: target {target} is not in bootstrap report")
            continue
        grouped[target].append(entry)

    empty_targets = sorted(name for name, entries in grouped.items() if not entries)
    if duplicate_contexts or untranslated or unexpected or empty_targets:
        parts = []
        if duplicate_contexts:
            parts.append(f"duplicate contexts={duplicate_contexts[:5]}")
        if untranslated:
            parts.append(f"untranslated={untranslated[:5]}")
        if unexpected:
            parts.append(f"unexpected targets={unexpected[:5]}")
        if empty_targets:
            parts.append(f"targets without PO entries={empty_targets}")
        raise ValueError("; ".join(parts))
    return grouped


def parse_long_semantics(text: str):
    lines = text.splitlines()
    if not lines:
        raise ValueError("empty long table")
    current_table = ""
    current_key = None
    order = []
    values = {}
    starts = []

    for idx, line in enumerate(lines[1:], 1):
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            if parts[0].strip():
                current_table = parts[0].strip()
            if not current_table:
                raise ValueError(f"line {idx + 1}: record has no table")
            key = (current_table, parts[1].strip(), parts[2].strip())
            if key in values:
                raise ValueError(f"line {idx + 1}: duplicate key {key}")
            values[key] = parts[3]
            order.append(key)
            starts.append((idx, key, parts[:3]))
            current_key = key
        elif line.strip():
            if current_key is None:
                raise ValueError(f"line {idx + 1}: orphan continuation")
            values[current_key] += "\n" + line
    return lines[0], lines, order, values, starts


def long_po_map(entries: list[polib.POEntry]):
    out = {}
    for entry in entries:
        match = STRUCT_RE.search(entry.msgctxt or "")
        if not match:
            raise ValueError(f"long-table context is not structural: {entry.msgctxt}")
        field = match.group("field")
        if field == "<default>":
            field = ""
        key = (match.group("table"), match.group("id"), field)
        if key in out:
            raise ValueError(f"duplicate long-table structural key {key}")
        out[key] = entry.msgstr
    return out


def build_long(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    header, lines, order, current, starts = parse_long_semantics(doc.text)
    desired = long_po_map(entries)

    missing = sorted(set(desired) - set(current))
    if missing:
        raise ValueError(f"PO contains long-table keys missing from template: {missing[:5]}")

    changes = sum(1 for key, value in desired.items() if current[key] != value)
    if not changes:
        return doc.text, 0

    start_by_index = {idx: (key, prefix) for idx, key, prefix in starts}
    start_indexes = sorted(start_by_index)
    next_start = {
        idx: (start_indexes[pos + 1] if pos + 1 < len(start_indexes) else len(lines))
        for pos, idx in enumerate(start_indexes)
    }

    out = [header]
    i = 1
    while i < len(lines):
        start = start_by_index.get(i)
        if start is None:
            out.append(lines[i])
            i += 1
            continue

        key, prefix = start
        end = next_start[i]
        if key not in desired:
            out.extend(lines[i:end])
            i = end
            continue

        value_lines = desired[key].split("\n")
        first = value_lines[0] if value_lines else ""
        out.append("\t".join([*prefix, first]))
        out.extend(value_lines[1:])

        for old in lines[i + 1:end]:
            if not old.strip():
                out.append(old)
        i = end

    trailing_newline = doc.text.endswith(("\n", "\r"))
    result = doc.newline.join(out)
    if trailing_newline:
        result += doc.newline
    return result, changes


def read_wide(text: str):
    return list(
        csv.reader(
            io.StringIO(text, newline=""),
            delimiter="\t",
            quotechar='"',
            doublequote=True,
        )
    )


def write_wide(rows: list[list[str]], newline: str, trailing_newline: bool) -> str:
    buf = io.StringIO(newline="")
    writer = csv.writer(
        buf,
        delimiter="\t",
        quotechar='"',
        doublequote=True,
        lineterminator=newline,
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerows(rows)
    value = buf.getvalue()
    if not trailing_newline:
        value = value.rstrip("\r\n")
    return value


def parse_generic_wide_entries(entries: list[polib.POEntry]):
    out = {}
    for entry in entries:
        match = WIDE_RE.search(entry.msgctxt or "")
        if not match:
            raise ValueError(f"wide-table context is not structural: {entry.msgctxt}")
        key = (match.group("id"), match.group("field"))
        if key in out:
            raise ValueError(f"duplicate wide structural key {key}")
        out[key] = entry.msgstr
    return out


def build_npc_names(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    rows = read_wide(doc.text)
    if not rows:
        raise ValueError("KO_NPCNames.txt is empty")
    header = rows[0]
    desired = parse_generic_wide_entries(entries)
    field_lookup = {name.strip(): idx for idx, name in enumerate(header)}
    changes = 0
    used = set()

    for row_index, row in enumerate(rows[1:]):
        row += [""] * max(0, len(header) - len(row))
        for field, column in field_lookup.items():
            key = (str(row_index), field)
            if key not in desired:
                continue
            used.add(key)
            if row[column] != desired[key]:
                row[column] = desired[key]
                changes += 1

    missing = sorted(set(desired) - used)
    if missing:
        raise ValueError(f"NPCNames PO keys missing from positional template: {missing[:5]}")
    if not changes:
        return doc.text, 0
    return write_wide(rows, doc.newline, doc.text.endswith(("\n", "\r"))), changes


def build_generic_wide(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    rows = read_wide(doc.text)
    if not rows:
        raise ValueError("empty wide table")
    header = [x.strip() for x in rows[0]]
    if not header:
        raise ValueError("wide table has no header")

    desired = parse_generic_wide_entries(entries)
    field_lookup = {name: idx for idx, name in enumerate(header)}
    row_lookup = {}
    for idx, row in enumerate(rows[1:], 1):
        row += [""] * max(0, len(header) - len(row))
        record_id = row[0].strip()
        if record_id:
            if record_id in row_lookup:
                raise ValueError(f"duplicate wide id {record_id}")
            row_lookup[record_id] = idx

    used = set()
    changes = 0
    for (record_id, field), value in desired.items():
        row_index = row_lookup.get(record_id)
        if row_index is None:
            raise ValueError(f"wide PO id missing from template: {record_id}")
        column = field_lookup.get(field)
        if column is None:
            raise ValueError(f"wide PO field missing from template header: {field!r}")
        used.add((record_id, field))
        if rows[row_index][column] != value:
            rows[row_index][column] = value
            changes += 1

    if len(used) != len(desired):
        raise ValueError("not all wide PO entries were consumed")
    if not changes:
        return doc.text, 0
    return write_wide(rows, doc.newline, doc.text.endswith(("\n", "\r"))), changes


def build_npc_professions(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    rows = read_wide(doc.text)
    if not rows or len(rows[0]) < 2:
        raise ValueError("unexpected NPCProfessions table")
    desired = {}
    for entry in entries:
        match = STRUCT_RE.search(entry.msgctxt or "")
        if not match or match.group("table") != "NPCProfessions":
            raise ValueError(f"unexpected NPCProfessions context: {entry.msgctxt}")
        desired[match.group("id")] = entry.msgstr

    changes = 0
    used = set()
    for row in rows[1:]:
        row += [""] * max(0, 2 - len(row))
        record_id = row[0].strip()
        if record_id in desired:
            used.add(record_id)
            if row[1] != desired[record_id]:
                row[1] = desired[record_id]
                changes += 1
    missing = sorted(set(desired) - used)
    if missing:
        raise ValueError(f"NPCProfessions ids missing from template: {missing[:5]}")
    if not changes:
        return doc.text, 0
    return write_wide(rows, doc.newline, doc.text.endswith(("\n", "\r"))), changes


def build_stats(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    rows = read_wide(doc.text)
    if not rows or len(rows[0]) < 2:
        raise ValueError("unexpected StatsDescriptions table")
    desired = {}
    for entry in entries:
        match = STRUCT_RE.search(entry.msgctxt or "")
        if not match or match.group("table") != "StatsDescriptions":
            raise ValueError(f"unexpected StatsDescriptions context: {entry.msgctxt}")
        desired[match.group("id")] = entry.msgstr

    changes = 0
    used = set()
    for row in rows[1:]:
        row += [""] * max(0, 2 - len(row))
        record_id = row[0].strip()
        if record_id in desired:
            used.add(record_id)
            if row[1] != desired[record_id]:
                row[1] = desired[record_id]
                changes += 1
    missing = sorted(set(desired) - used)
    if missing:
        raise ValueError(f"StatsDescription ids missing from template: {missing[:5]}")
    if not changes:
        return doc.text, 0
    return write_wide(rows, doc.newline, doc.text.endswith(("\n", "\r"))), changes


def build_skilldes(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    rows = read_wide(doc.text)
    if not rows:
        raise ValueError("KO_Skilldes.txt is empty")
    header = [x.strip() for x in rows[0]]
    columns = {name: idx for idx, name in enumerate(header)}
    desired = {}
    for entry in entries:
        match = STRUCT_RE.search(entry.msgctxt or "")
        if not match:
            raise ValueError(f"unexpected Skilldes context: {entry.msgctxt}")
        table = match.group("table")
        field = SKILL_TABLE_TO_FIELD.get(table)
        if field is None:
            raise ValueError(f"unsupported Skilldes table in PO: {table}")
        desired[(match.group("id"), field)] = entry.msgstr

    row_lookup = {}
    for idx, row in enumerate(rows[1:], 1):
        row += [""] * max(0, len(header) - len(row))
        if row[0].strip():
            row_lookup[row[0].strip()] = idx

    changes = 0
    used = set()
    for (record_id, field), value in desired.items():
        row_index = row_lookup.get(record_id)
        column = columns.get(field)
        if row_index is None or column is None:
            raise ValueError(f"Skilldes key missing from template: {record_id}:{field}")
        used.add((record_id, field))
        if rows[row_index][column] != value:
            rows[row_index][column] = value
            changes += 1
    if len(used) != len(desired):
        raise ValueError("not all Skilldes PO entries were consumed")
    if not changes:
        return doc.text, 0
    return write_wide(rows, doc.newline, doc.text.endswith(("\n", "\r"))), changes


def build_map_strings(doc: TextFile, entries: list[polib.POEntry]) -> tuple[str, int]:
    rows = read_wide(doc.text)
    if not rows or [x.strip().casefold() for x in rows[0][:3]] != ["mapfile", "stringid", "text"]:
        raise ValueError("unexpected MapStrings header")

    desired = {}
    for entry in entries:
        match = MAP_RE.search(entry.msgctxt or "")
        if not match:
            raise ValueError(f"unexpected MapStrings context: {entry.msgctxt}")
        key = (match.group("file").casefold(), int(match.group("index")))
        desired[key] = entry.msgstr

    changes = 0
    used = set()
    for row in rows[1:]:
        row += [""] * max(0, 3 - len(row))
        if not row[1].strip().isdigit():
            continue
        key = (row[0].strip().casefold(), int(row[1].strip()))
        if key in desired:
            used.add(key)
            if row[2] != desired[key]:
                row[2] = desired[key]
                changes += 1
    missing = sorted(set(desired) - used)
    if missing:
        raise ValueError(f"MapStrings keys missing from template: {missing[:5]}")
    if not changes:
        return doc.text, 0
    return write_wide(rows, doc.newline, doc.text.endswith(("\n", "\r"))), changes


def materialize_file(name: str, source_path: Path, entries: list[polib.POEntry]) -> tuple[bytes, int]:
    doc = read_preserving(source_path)
    if name == "KO_MapStrings.txt":
        text, changes = build_map_strings(doc, entries)
    elif name == "KO_NPCNames.txt":
        text, changes = build_npc_names(doc, entries)
    elif name in LONG_SPECIAL:
        text, changes = build_long(doc, entries)
    elif name == "KO_NPCProfessions.txt":
        text, changes = build_npc_professions(doc, entries)
    elif name == "KO_StatsDescriptions.tsv":
        text, changes = build_stats(doc, entries)
    elif name == "KO_Skilldes.txt":
        text, changes = build_skilldes(doc, entries)
    else:
        first_lines = doc.text.splitlines()
        first = first_lines[0] if first_lines else ""
        parts = first.split("\t")
        is_long = (
            len(parts) >= 4
            and [x.strip().casefold() for x in parts[:4]]
            == ["table (of game struct)", "id", "field", "new text"]
        )
        if is_long:
            text, changes = build_long(doc, entries)
        else:
            text, changes = build_generic_wide(doc, entries)

    return encode_preserving(doc, text), changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--po", type=Path, default=DEFAULT_PO)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace canonical Data/Text localization files in --source-root",
    )
    parser.add_argument(
        "--require-byte-identical",
        action="store_true",
        help="fail if materializing the current PO would change any canonical file bytes",
    )
    args = parser.parse_args()

    if args.write and args.output_root:
        raise SystemExit("--write and --output-root are mutually exclusive")
    if not args.write and not args.output_root:
        raise SystemExit("provide --output-root for preview or --write for in-place materialization")

    report = json.loads(args.report.read_text(encoding="utf-8"))
    file_specs = report.get("files", {})
    generated = set(report.get("generated_korean_files", [])) | GENERATED
    expected_files = set(file_specs) - generated
    if not expected_files:
        raise SystemExit("bootstrap report contains no canonical Korean files")

    grouped = load_catalog(args.po, expected_files)
    source_root = args.source_root
    changed_files = []
    total_changes = 0
    byte_drift = []

    if args.output_root:
        target_root = args.output_root / "Data/Text localization"
        target_root.mkdir(parents=True, exist_ok=True)
    else:
        target_root = source_root

    for name in sorted(expected_files, key=str.casefold):
        source_path = source_root / name
        if not source_path.is_file():
            raise SystemExit(f"missing canonical template: {source_path}")
        try:
            output_bytes, changes = materialize_file(name, source_path, grouped[name])
        except Exception as exc:
            raise SystemExit(f"{name}: {exc}") from exc

        original = source_path.read_bytes()
        if output_bytes != original:
            byte_drift.append(name)
        if changes:
            changed_files.append(name)
            total_changes += changes

        destination = target_root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if args.write:
            if output_bytes != original:
                destination.write_bytes(output_bytes)
        else:
            destination.write_bytes(output_bytes)

    if args.require_byte_identical and byte_drift:
        raise SystemExit(
            "current PO does not byte-round-trip canonical files: "
            + ", ".join(byte_drift[:20])
        )

    print("PO -> canonical Korean materialization")
    print(f"  canonical files:     {len(expected_files)}")
    print(f"  PO entries applied:  {sum(len(v) for v in grouped.values())}")
    print(f"  text cells changed:  {total_changes}")
    print(f"  files changed:       {len(changed_files)}")
    print(f"  byte-drift files:    {len(byte_drift)}")
    if changed_files:
        print("  changed files:       " + ", ".join(changed_files))
    if byte_drift:
        print("  byte drift:          " + ", ".join(byte_drift))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
