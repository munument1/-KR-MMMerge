#!/usr/bin/env python3
"""Build a context-stable Korean PO from this patch's text sources.

English comes from a pinned mm678-i18n `source/en/mmmerge` snapshot. Korean
comes only from this repository's `Data/Text localization` files. The script
never imports another project's Korean msgstr values and never decodes the
packaged LOD to recover translations.

Two source layouts are supported:

* long overlay tables: Table / Id / Field / New text
* wide text tables: Id / <one or more translatable columns>

`KO_MapStrings.txt` is paired with the English STR files by filename and exact
zero-based string index.
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
except ImportError as exc:  # pragma: no cover - dependency error is user-facing
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
        # The pinned English source can contain legacy CP1252 punctuation.
        return data.decode("cp1252")


def read_tsv(path: Path) -> list[list[str]]:
    text = read_text(path)
    return list(csv.reader(io.StringIO(text, newline=""), delimiter="\t", quotechar='"', doublequote=True))


def norm(value: str) -> str:
    return value.strip().casefold()


def ensure_unique(mapping: dict, key, *, path: Path) -> None:
    if key in mapping:
        raise ValueError(f"{path}: duplicate structural key {key!r}")


def parse_long(rows: list[list[str]], path: Path) -> tuple[list[tuple[tuple[str, str, str], str]], dict]:
    """Return ordered ((table,id,field), text) records from a long overlay."""
    result: list[tuple[tuple[str, str, str], str]] = []
    seen: dict[tuple[str, str, str], str] = {}
    current_table = ""
    for row_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, 4 - len(row))
        if row[0].strip():
            current_table = row[0].strip()
        record_id = row[1].strip()
        field = row[2].strip()
        text = row[3]
        if not record_id and not field and not text:
            continue
        if not current_table:
            raise ValueError(f"{path}:{row_no}: row has no table name")
        if not record_id:
            raise ValueError(f"{path}:{row_no}: row has no id")
        key = (current_table, record_id, field)
        ensure_unique(seen, key, path=path)
        seen[key] = text
        result.append((key, text))
    return result, seen


def parse_wide(rows: list[list[str]], path: Path) -> tuple[list[str], list[tuple[str, list[str]]], dict[str, list[str]]]:
    if not rows:
        raise ValueError(f"{path}: empty TSV")
    header = [cell.strip() for cell in rows[0]]
    if len(header) < 2:
        raise ValueError(f"{path}: expected an id column and at least one text column")

    ordered: list[tuple[str, list[str]]] = []
    mapping: dict[str, list[str]] = {}
    for row_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, len(header) - len(row))
        key = row[0].strip()
        if not key and not any(row[1:]):
            continue
        if not key:
            raise ValueError(f"{path}:{row_no}: data row has no id/key")
        if key in mapping:
            raise ValueError(f"{path}:{row_no}: duplicate id/key {key!r}")
        values = row[: len(header)]
        mapping[key] = values
        ordered.append((key, values))
    return header, ordered, mapping


def is_long(rows: list[list[str]]) -> bool:
    if not rows or len(rows[0]) < 4:
        return False
    return tuple(norm(cell) for cell in rows[0][:4]) == LONG_HEADER


def pair_long(source: Path, korean: Path, source_label: str, korean_label: str) -> tuple[list[Cell], dict]:
    source_rows = read_tsv(source)
    korean_rows = read_tsv(korean)
    if not is_long(source_rows) or not is_long(korean_rows):
        raise ValueError(f"long/wide format mismatch: {source} vs {korean}")

    source_order, source_map = parse_long(source_rows, source)
    _, korean_map = parse_long(korean_rows, korean)
    cells: list[Cell] = []
    missing_korean: list[str] = []

    for (table, record_id, field), english in source_order:
        key = (table, record_id, field)
        korean_text = korean_map.get(key, "")
        if key not in korean_map and english:
            missing_korean.append(f"{table}:{record_id}:{field or '<default>'}")
        if not english and not korean_text:
            continue
        if not english and korean_text:
            # We cannot create a safe gettext identity without an English msgid.
            raise ValueError(
                f"{korean}: Korean text exists for {key!r} but English msgid is empty"
            )
        context = (
            f"mmmerge/Text localization/{source.name}"
            f"|table={table}|id={record_id}|field={field or '<default>'}"
        )
        cells.append(Cell(context, english, korean_text, source_label, korean_label))

    korean_only = sorted(
        f"{table}:{record_id}:{field or '<default>'}"
        for table, record_id, field in (set(korean_map) - set(source_map))
        if korean_map[(table, record_id, field)]
    )
    return cells, {
        "format": "long",
        "source_records": len(source_map),
        "korean_records": len(korean_map),
        "missing_korean": missing_korean,
        "korean_only": korean_only,
    }


def pair_wide(source: Path, korean: Path, source_label: str, korean_label: str) -> tuple[list[Cell], dict]:
    source_rows = read_tsv(source)
    korean_rows = read_tsv(korean)
    if is_long(source_rows) or is_long(korean_rows):
        raise ValueError(f"long/wide format mismatch: {source} vs {korean}")

    source_header, source_order, source_map = parse_wide(source_rows, source)
    korean_header, _, korean_map = parse_wide(korean_rows, korean)
    if [norm(x) for x in source_header] != [norm(x) for x in korean_header]:
        raise ValueError(
            f"header mismatch: {source.name} {source_header!r} != {korean.name} {korean_header!r}"
        )

    cells: list[Cell] = []
    missing_korean: list[str] = []
    for record_id, source_row in source_order:
        korean_row = korean_map.get(record_id)
        for column in range(1, len(source_header)):
            english = source_row[column] if column < len(source_row) else ""
            korean_text = korean_row[column] if korean_row and column < len(korean_row) else ""
            if korean_row is None and english:
                missing_korean.append(f"{record_id}:{source_header[column] or f'column-{column}'}")
            if not english and not korean_text:
                continue
            if not english and korean_text:
                raise ValueError(
                    f"{korean}: Korean text exists at id={record_id}, "
                    f"field={source_header[column]!r} but English msgid is empty"
                )
            field = source_header[column].strip() or f"column-{column}"
            context = f"mmmerge/Text localization/{source.name}|id={record_id}|field={field}"
            cells.append(Cell(context, english, korean_text, source_label, korean_label))

    korean_only = sorted(key for key in (set(korean_map) - set(source_map)) if any(korean_map[key][1:]))
    return cells, {
        "format": "wide",
        "source_records": len(source_map),
        "korean_records": len(korean_map),
        "missing_korean": missing_korean,
        "korean_only": korean_only,
    }


def source_lookup(folder: Path) -> dict[str, Path]:
    return {path.name.casefold(): path for path in folder.iterdir() if path.is_file()}


def pair_map_strings(korean_path: Path, source_str_dir: Path) -> tuple[list[Cell], dict]:
    sources = source_lookup(source_str_dir)
    rows = read_tsv(korean_path)
    if not rows or [norm(x) for x in rows[0][:3]] != ["mapfile", "stringid", "text"]:
        raise ValueError(f"{korean_path}: unexpected MapStrings header")

    cache: dict[str, list[str]] = {}
    cells: list[Cell] = []
    missing_files: list[str] = []
    missing_indexes: list[str] = []
    seen: set[tuple[str, int]] = set()

    for row_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, 3 - len(row))
        file_name = row[0].strip()
        index_text = row[1].strip()
        korean_text = row[2]
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
        if file_name.casefold() not in cache:
            cache[file_name.casefold()] = read_text(source).splitlines()
        lines = cache[file_name.casefold()]
        if index < 0 or index >= len(lines):
            missing_indexes.append(f"{file_name}:{index}")
            continue
        english = lines[index]
        if not english and korean_text:
            raise ValueError(f"{korean_path}:{row_no}: Korean text maps to an empty English STR line")
        if not english and not korean_text:
            continue
        context = f"mmmerge/10LocLANG.T/{source.name}|string={index}"
        cells.append(
            Cell(
                context,
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


def build_catalog(cells: Iterable[Cell], source_revision: str) -> polib.POFile:
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
        "X-English-Source-Revision": source_revision,
        "X-Korean-Source": "munument1/-KR-MMMerge Data/Text localization",
    }

    by_context: dict[str, Cell] = {}
    for cell in cells:
        old = by_context.get(cell.context)
        if old is not None and (old.msgid != cell.msgid or old.msgstr != cell.msgstr):
            raise ValueError(f"context collision: {cell.context}")
        by_context[cell.context] = cell

    for context in sorted(by_context, key=str.casefold):
        cell = by_context[context]
        entry = polib.POEntry(msgctxt=context, msgid=cell.msgid, msgstr=cell.msgstr)
        entry.comment = f"EN: {cell.source_file}\nKO: {cell.korean_file}"
        po.append(entry)
    return po


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--korean-dir", type=Path, required=True)
    parser.add_argument("--english-root", type=Path, required=True, help="pinned source/en/mmmerge directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()

    korean_dir = args.korean_dir.resolve()
    english_root = args.english_root.resolve()
    source_text_dir = english_root / "Data" / "Text localization"
    source_str_dir = english_root / "Data" / "10LocLANG.T"
    for required in (korean_dir, source_text_dir, source_str_dir):
        if not required.is_dir():
            raise SystemExit(f"missing directory: {required}")

    all_cells: list[Cell] = []
    file_reports: dict[str, dict] = {}
    paired_korean: set[str] = set()
    source_files = sorted(source_text_dir.glob("LANG_*.txt"), key=lambda p: p.name.casefold())
    source_only_files: list[str] = []

    for source in source_files:
        suffix = source.name[len("LANG_"):]
        korean = korean_dir / f"KO_{suffix}"
        if not korean.is_file():
            source_only_files.append(source.name)
            continue
        paired_korean.add(korean.name.casefold())
        source_label = f"source/en/mmmerge/Data/Text localization/{source.name}"
        korean_label = f"Data/Text localization/{korean.name}"
        source_rows = read_tsv(source)
        korean_rows = read_tsv(korean)
        if is_long(source_rows) != is_long(korean_rows):
            raise ValueError(f"format mismatch: {source.name} vs {korean.name}")
        if is_long(source_rows):
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
        key=lambda p: p.name.casefold(),
    )
    unmapped_korean_files = [
        path.name for path in korean_candidates if path.name.casefold() not in paired_korean
    ]

    po = build_catalog(all_cells, args.source_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(args.output))

    translated = sum(1 for entry in po if entry.msgstr)
    untranslated = sum(1 for entry in po if not entry.msgstr)
    missing_korean = sum(len(details.get("missing_korean", [])) for details in file_reports.values())
    korean_only = sum(len(details.get("korean_only", [])) for details in file_reports.values())
    map_missing = sum(
        len(details.get("missing_files", [])) + len(details.get("missing_indexes", []))
        for details in file_reports.values()
    )
    report = {
        "schema": 1,
        "source_revision": args.source_revision,
        "entries": len(po),
        "translated": translated,
        "untranslated": untranslated,
        "paired_files": len(file_reports),
        "source_only_files": source_only_files,
        "unmapped_korean_files": unmapped_korean_files,
        "missing_korean_records": missing_korean,
        "korean_only_records": korean_only,
        "map_source_misses": map_missing,
        "files": file_reports,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("PO bootstrap from text sources")
    print(f"  paired files:          {report['paired_files']}")
    print(f"  PO entries:            {report['entries']}")
    print(f"  translated:            {report['translated']}")
    print(f"  untranslated:          {report['untranslated']}")
    print(f"  missing Korean records:{report['missing_korean_records']}")
    print(f"  Korean-only records:   {report['korean_only_records']}")
    print(f"  map source misses:     {report['map_source_misses']}")
    if unmapped_korean_files:
        print("  not yet mapped:        " + ", ".join(unmapped_korean_files))
    if source_only_files:
        print("  source-only files:     " + ", ".join(source_only_files))

    # Hard safety: never silently drop Korean records inside a file we claim to pair.
    if korean_only or map_missing:
        print("bootstrap has unsafe unmapped Korean/source records; see report", file=sys.stderr)
        return 1
    if len(po) < 1000:
        print(f"bootstrap produced implausibly few entries: {len(po)}", file=sys.stderr)
        return 1
    print("text-source bootstrap: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
