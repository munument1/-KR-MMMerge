#!/usr/bin/env python3
"""Build a context-stable Korean PO from this patch's localization sources.

English msgids come from a pinned mm678-i18n source/en/mmmerge snapshot.
Korean msgstr values come only from this repository.  The importer deliberately
does not use mm678-i18n's Korean catalog.

Long overlay tables are parsed with Merge's actual continuation-line semantics:
only a line with a numeric Id starts a new record; all other non-empty physical
lines continue the previous text field.  This is required for NPCText,
NPCTopic, greetings, scrolls and class descriptions, which contain legacy
unquoted multiline text.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import polib
except ImportError as exc:
    raise SystemExit("polib is required: python -m pip install polib") from exc


LONG_HEADER = ("table (of game struct)", "id", "field", "new text")


@dataclass(frozen=True)
class Cell:
    context: str
    msgid: str
    msgstr: str
    source_file: str
    korean_file: str


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def norm(value: str) -> str:
    return value.strip().casefold()


def decode_field(raw: str) -> str:
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('""', '"')
    return raw


def is_long(path: Path) -> bool:
    first = read_text(path).splitlines()
    if not first:
        return False
    cells = first[0].split("\t")
    return len(cells) >= 4 and tuple(norm(x) for x in cells[:4]) == LONG_HEADER


def parse_long(path: Path):
    """Parse Merge overlay tables without treating continuation text as columns."""
    lines = read_text(path).splitlines()
    if not lines:
        raise ValueError(f"{path}: empty overlay")
    header = lines[0].split("\t")
    if len(header) < 4 or tuple(norm(x) for x in header[:4]) != LONG_HEADER:
        raise ValueError(f"{path}: unexpected long-overlay header")

    current_table = ""
    current_key = None
    order = []
    values = {}

    for line_no, line in enumerate(lines[1:], 2):
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            if parts[0].strip():
                current_table = parts[0].strip()
            if not current_table:
                raise ValueError(f"{path}:{line_no}: record has no table name")
            key = (current_table, parts[1].strip(), parts[2].strip())
            if key in values:
                raise ValueError(f"{path}:{line_no}: duplicate structural key {key!r}")
            values[key] = decode_field(parts[3])
            order.append(key)
            current_key = key
            continue

        if not line.strip():
            continue
        if current_key is None:
            raise ValueError(f"{path}:{line_no}: orphan continuation line")
        values[current_key] += "\n" + line

    return order, values


def read_wide(path: Path):
    return list(
        csv.reader(
            io.StringIO(read_text(path), newline=""),
            delimiter="\t",
            quotechar='"',
            doublequote=True,
        )
    )


def parse_wide(path: Path):
    rows = read_wide(path)
    if not rows:
        raise ValueError(f"{path}: empty TSV")
    header = [x.strip() for x in rows[0]]
    if len(header) < 2:
        raise ValueError(f"{path}: expected key + text columns")

    order = []
    values = {}
    for row_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, len(header) - len(row))
        key = row[0].strip()
        if not key and not any(row[1:]):
            continue
        if not key:
            raise ValueError(f"{path}:{row_no}: data row has no key")
        if key in values:
            raise ValueError(f"{path}:{row_no}: duplicate key {key!r}")
        values[key] = row[: len(header)]
        order.append(key)
    return header, order, values


def pair_long(source: Path, korean: Path, source_label: str, korean_label: str):
    source_order, source_map = parse_long(source)
    _, korean_map = parse_long(korean)
    cells = []
    missing = []

    for key in source_order:
        english = source_map[key]
        korean_text = korean_map.get(key, "")
        if key not in korean_map and english:
            missing.append(f"{key[0]}:{key[1]}:{key[2] or '<default>'}")
        if not english and not korean_text:
            continue
        if not english and korean_text:
            raise ValueError(f"{korean}: Korean text exists for empty English record {key!r}")
        table, record_id, field = key
        context = (
            f"mmmerge/Text localization/{source.name}"
            f"|table={table}|id={record_id}|field={field or '<default>'}"
        )
        cells.append(Cell(context, english, korean_text, source_label, korean_label))

    korean_only = sorted(
        f"{t}:{i}:{f or '<default>'}"
        for (t, i, f) in (set(korean_map) - set(source_map))
        if korean_map[(t, i, f)]
    )
    return cells, {
        "format": "long",
        "source_records": len(source_map),
        "korean_records": len(korean_map),
        "missing_korean": missing,
        "korean_only": korean_only,
    }


def pair_wide(source: Path, korean: Path, source_label: str, korean_label: str):
    source_header, source_order, source_map = parse_wide(source)
    korean_header, _, korean_map = parse_wide(korean)
    if [norm(x) for x in source_header] != [norm(x) for x in korean_header]:
        raise ValueError(
            f"header mismatch: {source.name} {source_header!r} != "
            f"{korean.name} {korean_header!r}"
        )

    cells = []
    missing = []
    for record_id in source_order:
        source_row = source_map[record_id]
        korean_row = korean_map.get(record_id)
        for column in range(1, len(source_header)):
            english = source_row[column] if column < len(source_row) else ""
            korean_text = korean_row[column] if korean_row and column < len(korean_row) else ""
            if korean_row is None and english:
                missing.append(f"{record_id}:{source_header[column] or f'column-{column}'}")
            if not english and not korean_text:
                continue
            if not english and korean_text:
                raise ValueError(
                    f"{korean}: Korean text exists at id={record_id}, "
                    f"field={source_header[column]!r} but English is empty"
                )
            field = source_header[column].strip() or f"column-{column}"
            context = f"mmmerge/Text localization/{source.name}|id={record_id}|field={field}"
            cells.append(Cell(context, english, korean_text, source_label, korean_label))

    korean_only = sorted(
        key for key in (set(korean_map) - set(source_map))
        if any(korean_map[key][1:])
    )
    return cells, {
        "format": "wide",
        "source_records": len(source_map),
        "korean_records": len(korean_map),
        "missing_korean": missing,
        "korean_only": korean_only,
    }


def source_lookup(folder: Path):
    return {p.name.casefold(): p for p in folder.iterdir() if p.is_file()}


def pair_map_strings(korean_path: Path, source_str_dir: Path):
    sources = source_lookup(source_str_dir)
    rows = read_wide(korean_path)
    if not rows or [norm(x) for x in rows[0][:3]] != ["mapfile", "stringid", "text"]:
        raise ValueError(f"{korean_path}: unexpected MapStrings header")

    cache = {}
    cells = []
    missing_files = []
    missing_indexes = []
    seen = set()

    for row_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, 3 - len(row))
        file_name, index_text, korean_text = row[:3]
        file_name = file_name.strip()
        index_text = index_text.strip()
        if not file_name and not index_text and not korean_text:
            continue
        if not index_text.isdigit():
            raise ValueError(f"{korean_path}:{row_no}: invalid string id {index_text!r}")
        index = int(index_text)
        identity = (file_name.casefold(), index)
        if identity in seen:
            raise ValueError(f"{korean_path}:{row_no}: duplicate map string {file_name}:{index}")
        seen.add(identity)

        source = sources.get(file_name.casefold())
        if source is None:
            missing_files.append(file_name)
            continue
        lines = cache.setdefault(file_name.casefold(), read_text(source).splitlines())
        if index >= len(lines):
            missing_indexes.append(f"{file_name}:{index}")
            continue
        english = lines[index]
        if not english and korean_text:
            raise ValueError(f"{korean_path}:{row_no}: Korean text maps to empty English STR")
        if not english and not korean_text:
            continue
        cells.append(
            Cell(
                f"mmmerge/10LocLANG.T/{source.name}|string={index}",
                english,
                korean_text,
                f"source/en/mmmerge/Data/10LocLANG.T/{source.name}",
                f"Data/Text localization/{korean_path.name}",
            )
        )

    return cells, {
        "format": "map-str",
        "mapped": len(cells),
        "missing_files": sorted(set(missing_files), key=str.casefold),
        "missing_indexes": sorted(set(missing_indexes), key=str.casefold),
    }


def build_catalog(cells: Iterable[Cell], revision: str):
    po = polib.POFile(wrapwidth=0)
    po.metadata = {
        "Project-Id-Version": "MMMerge Korean patch",
        "Language": "ko",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": "nplurals=1; plural=0;",
        "X-Generator": "tools/bootstrap_po_from_utf8.py",
        "X-English-Source": "might-and-magic/mm678-i18n",
        "X-English-Source-Revision": revision,
        "X-Korean-Source": "munument1/-KR-MMMerge Data/Text localization",
    }
    by_context = {}
    for cell in cells:
        old = by_context.get(cell.context)
        if old and (old.msgid != cell.msgid or old.msgstr != cell.msgstr):
            raise ValueError(f"context collision: {cell.context}")
        by_context[cell.context] = cell

    for context in sorted(by_context, key=str.casefold):
        cell = by_context[context]
        entry = polib.POEntry(msgctxt=context, msgid=cell.msgid, msgstr=cell.msgstr)
        entry.comment = f"EN: {cell.source_file}\nKO: {cell.korean_file}"
        po.append(entry)
    return po


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--korean-dir", type=Path, required=True)
    p.add_argument("--english-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--source-revision", required=True)
    args = p.parse_args()

    korean_dir = args.korean_dir.resolve()
    english_root = args.english_root.resolve()
    source_text_dir = english_root / "Data" / "Text localization"
    source_str_dir = english_root / "Data" / "10LocLANG.T"
    for required in (korean_dir, source_text_dir, source_str_dir):
        if not required.is_dir():
            raise SystemExit(f"missing directory: {required}")

    all_cells = []
    file_reports = {}
    paired_korean = set()
    source_only_files = []

    for source in sorted(source_text_dir.glob("LANG_*.txt"), key=lambda x: x.name.casefold()):
        suffix = source.name[len("LANG_"):]
        korean = korean_dir / f"KO_{suffix}"
        if not korean.is_file():
            source_only_files.append(source.name)
            continue
        paired_korean.add(korean.name.casefold())
        source_label = f"source/en/mmmerge/Data/Text localization/{source.name}"
        korean_label = f"Data/Text localization/{korean.name}"

        source_long = is_long(source)
        korean_long = is_long(korean)
        if source_long != korean_long:
            raise ValueError(f"format mismatch: {source.name} vs {korean.name}")
        if source_long:
            cells, details = pair_long(source, korean, source_label, korean_label)
        else:
            cells, details = pair_wide(source, korean, source_label, korean_label)
        all_cells.extend(cells)
        details["entries"] = len(cells)
        file_reports[korean.name] = details

    map_strings = korean_dir / "KO_MapStrings.txt"
    if map_strings.is_file():
        cells, details = pair_map_strings(map_strings, source_str_dir)
        all_cells.extend(cells)
        file_reports[map_strings.name] = details
        paired_korean.add(map_strings.name.casefold())

    korean_candidates = sorted(
        [*korean_dir.glob("KO_*.txt"), *korean_dir.glob("KO_*.tsv")],
        key=lambda x: x.name.casefold(),
    )
    unmapped = [p.name for p in korean_candidates if p.name.casefold() not in paired_korean]

    po = build_catalog(all_cells, args.source_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(args.output))

    translated = sum(1 for e in po if e.msgstr)
    untranslated = sum(1 for e in po if not e.msgstr)
    missing = sum(len(d.get("missing_korean", [])) for d in file_reports.values())
    ko_only = sum(len(d.get("korean_only", [])) for d in file_reports.values())
    map_missing = sum(
        len(d.get("missing_files", [])) + len(d.get("missing_indexes", []))
        for d in file_reports.values()
    )
    report = {
        "schema": 2,
        "source_revision": args.source_revision,
        "entries": len(po),
        "translated": translated,
        "untranslated": untranslated,
        "paired_files": len(file_reports),
        "source_only_files": source_only_files,
        "unmapped_korean_files": unmapped,
        "missing_korean_records": missing,
        "korean_only_records": ko_only,
        "map_source_misses": map_missing,
        "files": file_reports,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("PO bootstrap from text sources")
    print(f"  paired files:           {report['paired_files']}")
    print(f"  PO entries:             {report['entries']}")
    print(f"  translated:             {report['translated']}")
    print(f"  untranslated:           {report['untranslated']}")
    print(f"  missing Korean records: {report['missing_korean_records']}")
    print(f"  Korean-only records:    {report['korean_only_records']}")
    print(f"  map source misses:      {report['map_source_misses']}")
    if unmapped:
        print("  not yet mapped:         " + ", ".join(unmapped))
    if source_only_files:
        print("  source-only files:      " + ", ".join(source_only_files))

    if ko_only or map_missing:
        print("bootstrap has unsafe unmapped Korean/source records; see report", file=sys.stderr)
        return 1
    if len(po) < 1000:
        print(f"bootstrap produced implausibly few entries: {len(po)}", file=sys.stderr)
        return 1
    print("text-source bootstrap: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
