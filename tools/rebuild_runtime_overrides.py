#!/usr/bin/env python3
"""Generate KO_RuntimeOverrides.txt from canonical Korean translation tables.

The manifest says *which* values must be re-applied late at runtime.  It does
not duplicate their wording.  For every key that exists in a normal KO table,
this generator copies the current canonical Korean text.  Only genuinely
runtime-only keys may carry literal text in the manifest.

This keeps Merge's late-reapply behavior while preventing an old runtime
translation from overwriting a newer PO/static translation.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from pathlib import Path


LONG_HEADER = ("table (of game struct)", "id", "field", "new text")


@dataclass(frozen=True)
class Record:
    table: str
    record_id: str
    field: str
    text: str

    @property
    def key(self):
        return (self.table, self.record_id, self.field)


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp949")


def norm(value: str) -> str:
    return value.strip().casefold()


def decode_field(raw: str) -> str:
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('""', '"')
    return raw


def encode_field(value: str) -> str:
    if any(ch in value for ch in ('\t', '\r', '\n', '"')):
        return '"' + value.replace('"', '""') + '"'
    return value


def is_long(path: Path) -> bool:
    lines = read_text(path).splitlines()
    if not lines:
        return False
    head = lines[0].split("\t")
    return len(head) >= 4 and tuple(norm(x) for x in head[:4]) == LONG_HEADER


def parse_long(path: Path) -> list[Record]:
    lines = read_text(path).splitlines()
    current_table = ""
    current: Record | None = None
    records: list[Record] = []

    for line_no, line in enumerate(lines[1:], 2):
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            if parts[0].strip():
                current_table = parts[0].strip()
            if not current_table:
                raise ValueError(f"{path}:{line_no}: missing table name")
            current = Record(
                current_table,
                parts[1].strip(),
                parts[2].strip(),
                decode_field(parts[3]),
            )
            records.append(current)
            continue
        if not line.strip():
            continue
        if current is None:
            raise ValueError(f"{path}:{line_no}: orphan continuation line")
        current = Record(
            current.table,
            current.record_id,
            current.field,
            current.text + "\n" + line,
        )
        records[-1] = current
    return records


def infer_wide_table(path: Path) -> str:
    stem = path.stem
    if stem.startswith("KO_"):
        stem = stem[3:]
    # Current wide tables use their Game table name in the filename.
    return stem


def parse_wide(path: Path) -> list[Record]:
    rows = list(
        csv.reader(
            io.StringIO(read_text(path), newline=""),
            delimiter="\t",
            quotechar='"',
            doublequote=True,
        )
    )
    if not rows or len(rows[0]) < 2:
        return []
    header = [x.strip() for x in rows[0]]
    table = infer_wide_table(path)
    records: list[Record] = []
    for row in rows[1:]:
        row = row + [""] * max(0, len(header) - len(row))
        record_id = row[0].strip()
        if not record_id.isdigit():
            continue
        for column in range(1, len(header)):
            text = row[column] if column < len(row) else ""
            if not text:
                continue
            records.append(
                Record(table, record_id, header[column] or f"column-{column}", text)
            )
    return records


def canonical_index(folder: Path):
    index: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    for path in sorted([*folder.glob("KO_*.txt"), *folder.glob("KO_*.tsv")], key=lambda p: p.name.casefold()):
        if path.name in {"KO_RuntimeOverrides.txt", "KO_MapStrings.txt"}:
            continue
        records = parse_long(path) if is_long(path) else parse_wide(path)
        for record in records:
            index.setdefault(record.key, []).append((path.name, record.text))
    return index


def read_manifest(path: Path):
    rows = list(csv.reader(io.StringIO(read_text(path)), delimiter="\t"))
    if not rows or [norm(x) for x in rows[0][:4]] != ["table", "id", "field", "runtimeonlytext"]:
        raise ValueError(f"{path}: unexpected manifest header")
    result = []
    seen = set()
    for line_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, 4 - len(row))
        table, record_id, field, fallback = row[:4]
        table = table.strip()
        record_id = record_id.strip()
        field = field.strip()
        if not table and not record_id and not field and not fallback:
            continue
        if not table or not record_id.isdigit():
            raise ValueError(f"{path}:{line_no}: invalid key")
        key = (table, record_id, field)
        if key in seen:
            raise ValueError(f"{path}:{line_no}: duplicate key {key!r}")
        seen.add(key)
        result.append((key, fallback))
    return result


def resolve(manifest, canonical):
    output = []
    runtime_only = []
    for key, fallback in manifest:
        candidates = canonical.get(key, [])
        if candidates:
            texts = {text for _, text in candidates}
            if len(texts) != 1:
                raise ValueError(
                    f"canonical conflict for {key!r}: "
                    + ", ".join(f"{name}={text!r}" for name, text in candidates)
                )
            output.append((key, next(iter(texts)), sorted({name for name, _ in candidates})))
        else:
            if not fallback:
                raise ValueError(f"manifest key {key!r} has no canonical source and no runtime-only text")
            output.append((key, fallback, []))
            runtime_only.append(key)
    return output, runtime_only


def render(resolved) -> str:
    lines = ["Table (of Game struct)\tId\tField\tNew text"]
    previous_table = None
    for (table, record_id, field), text, _sources in resolved:
        table_cell = table if table != previous_table else ""
        lines.append(f"{table_cell}\t{record_id}\t{field}\t{encode_field(text)}")
        previous_table = table
    # Merge's loader splits this file explicitly on CRLF.
    return "\r\n".join(lines) + "\r\n"


def normalized_records(text: str):
    temp_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    current_table = ""
    current = None
    result = []
    for line in temp_lines[1:]:
        if not line:
            continue
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            if parts[0].strip():
                current_table = parts[0].strip()
            current = [current_table, parts[1].strip(), parts[2].strip(), decode_field(parts[3])]
            result.append(current)
        elif current is not None:
            current[3] += "\n" + line
    return [tuple(x) for x in result]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translations", type=Path, default=Path("Data/Text localization"))
    parser.add_argument("--manifest", type=Path, default=Path("config/runtime_override_keys.tsv"))
    parser.add_argument("--output", type=Path, default=Path("Data/Text localization/KO_RuntimeOverrides.txt"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    canonical = canonical_index(args.translations)
    manifest = read_manifest(args.manifest)
    resolved, runtime_only = resolve(manifest, canonical)
    generated = render(resolved)

    print("Runtime override generator")
    print(f"  manifest keys:      {len(manifest)}")
    print(f"  canonical-backed:   {len(manifest) - len(runtime_only)}")
    print(f"  runtime-only:       {len(runtime_only)}")
    for key in runtime_only:
        print(f"    runtime-only: {key[0]}[{key[1]}] {key[2] or '<default>'}")

    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(generated.encode("utf-8"))
        print(f"  wrote:              {args.output}")
        return 0

    if not args.output.is_file():
        print(f"missing generated runtime file: {args.output}", file=sys.stderr)
        return 1
    existing = read_text(args.output)
    if normalized_records(existing) != normalized_records(generated):
        print(
            "KO_RuntimeOverrides.txt has drifted from canonical Korean tables; "
            "run tools/rebuild_runtime_overrides.py --write",
            file=sys.stderr,
        )
        return 1
    print("  drift check:        OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
