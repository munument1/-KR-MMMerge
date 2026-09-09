#!/usr/bin/env python3
"""Add Korean MMMerge tables whose English source lives outside mmmerge/Text localization.

MMMerge inherits several localized tables directly from the base games.  Their
English text therefore lives in mm678-i18n's MM8/MM6 source snapshots instead
of source/en/mmmerge/Data/Text localization.  This tool appends those entries
to the already-bootstrapped Korean PO while keeping stable structural contexts.

Korean msgstr values always come from this repository.  No Korean text is read
from mm678-i18n.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

import polib

from bootstrap_po_from_utf8 import parse_long, parse_wide, read_text


SPECIAL_FILES = {
    "KO_GlobalTxt.txt",
    "KO_NPCProfessions.txt",
    "KO_SpellsTxt.txt",
    "KO_StatsDescriptions.tsv",
}
GENERATED_FILES = {"KO_RuntimeOverrides.txt"}


def rows(path: Path):
    return list(
        csv.reader(
            io.StringIO(read_text(path), newline=""),
            delimiter="\t",
            quotechar='"',
            doublequote=True,
        )
    )


def add_entry(po: polib.POFile, seen: set[str], *, context: str, msgid: str,
              msgstr: str, source_label: str, korean_label: str) -> None:
    if not msgid and not msgstr:
        return
    if not msgid and msgstr:
        raise ValueError(f"Korean text exists for empty English source: {context}")
    if context in seen:
        raise ValueError(f"duplicate PO context while adding special source: {context}")
    entry = polib.POEntry(msgctxt=context, msgid=msgid, msgstr=msgstr)
    entry.comment = f"EN: {source_label}\nKO: {korean_label}"
    po.append(entry)
    seen.add(context)


def pair_global(po, seen, korean: Path, english: Path):
    order, ko = parse_long(korean)
    en = {}
    for row in rows(english):
        if row and row[0].strip().isdigit():
            en[row[0].strip()] = row[1] if len(row) > 1 else ""

    missing_source = []
    missing_korean = []
    added = 0
    for table, record_id, field in order:
        if table != "GlobalTxt":
            raise ValueError(f"{korean}: unexpected table {table!r}")
        english_text = en.get(record_id)
        korean_text = ko[(table, record_id, field)]
        if english_text is None:
            if korean_text:
                missing_source.append(record_id)
            continue
        if english_text and not korean_text:
            missing_korean.append(record_id)
        before = len(po)
        add_entry(
            po, seen,
            context=f"mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id={record_id}|field=<default>",
            msgid=english_text,
            msgstr=korean_text,
            source_label="source/en/mm8/Data/10LocLANG.EnglishT/Global.txt",
            korean_label=f"Data/Text localization/{korean.name}",
        )
        added += len(po) - before
    return added, missing_source, missing_korean


def pair_spells(po, seen, korean: Path, english: Path):
    order, ko = parse_long(korean)
    field_column = {
        "Name": 2,
        "ShortName": 4,
        "Description": 5,
        "Normal": 6,
        "Expert": 7,
        "Master": 8,
        "GrandMaster": 9,
    }
    en_rows = {}
    for row in rows(english):
        if row and row[0].strip().isdigit():
            en_rows[row[0].strip()] = row

    missing_source = []
    missing_korean = []
    added = 0
    for table, record_id, field in order:
        if table != "SpellsTxt":
            raise ValueError(f"{korean}: unexpected table {table!r}")
        if field not in field_column:
            raise ValueError(f"{korean}: unsupported spell field {field!r}")
        source_row = en_rows.get(record_id)
        if source_row is None:
            if ko[(table, record_id, field)]:
                missing_source.append(f"{record_id}:{field}")
            continue
        column = field_column[field]
        english_text = source_row[column] if column < len(source_row) else ""
        korean_text = ko[(table, record_id, field)]
        if english_text and not korean_text:
            missing_korean.append(f"{record_id}:{field}")
        before = len(po)
        add_entry(
            po, seen,
            context=f"mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id={record_id}|field={field}",
            msgid=english_text,
            msgstr=korean_text,
            source_label="source/en/mm8/Data/10LocLANG.EnglishT/Spells.txt",
            korean_label=f"Data/Text localization/{korean.name}",
        )
        added += len(po) - before
    return added, missing_source, missing_korean


def pair_stats(po, seen, korean: Path, english: Path):
    header, order, ko = parse_wide(korean)
    if [x.strip().casefold() for x in header[:2]] != ["index", "description"]:
        raise ValueError(f"{korean}: unexpected stats header {header!r}")

    source_rows = []
    for row in rows(english)[1:]:
        if len(row) >= 2 and row[0].strip():
            source_rows.append(row)

    missing_source = []
    missing_korean = []
    added = 0
    for record_id in order:
        if not record_id.isdigit():
            raise ValueError(f"{korean}: non-numeric stats index {record_id!r}")
        index = int(record_id)
        korean_text = ko[record_id][1] if len(ko[record_id]) > 1 else ""
        if index >= len(source_rows):
            if korean_text:
                missing_source.append(record_id)
            continue
        source_name = source_rows[index][0]
        english_text = source_rows[index][1]
        if english_text and not korean_text:
            missing_korean.append(record_id)
        before = len(po)
        add_entry(
            po, seen,
            context=f"mmmerge/inherited/mm8/stats.txt|table=StatsDescriptions|id={record_id}|field=Description",
            msgid=english_text,
            msgstr=korean_text,
            source_label=f"source/en/mm8/Data/10LocLANG.EnglishT/stats.txt ({source_name})",
            korean_label=f"Data/Text localization/{korean.name}",
        )
        added += len(po) - before
    return added, missing_source, missing_korean


def pair_npc_professions(po, seen, korean: Path, english: Path):
    header, order, ko = parse_wide(korean)
    if [x.strip().casefold() for x in header[:2]] != ["id", "new text"]:
        raise ValueError(f"{korean}: unexpected profession header {header!r}")

    en = {}
    for row in rows(english):
        if row and row[0].strip().isdigit():
            en[row[0].strip()] = row[1] if len(row) > 1 else ""

    missing_source = []
    missing_korean = []
    added = 0
    for record_id in order:
        korean_text = ko[record_id][1] if len(ko[record_id]) > 1 else ""
        english_text = en.get(record_id)
        if english_text is None:
            if korean_text:
                missing_source.append(record_id)
            continue
        if english_text and not korean_text:
            missing_korean.append(record_id)
        before = len(po)
        add_entry(
            po, seen,
            context=f"mmmerge/inherited/mm6/npcprof.txt|table=NPCProfessions|id={record_id}|field=Name",
            msgid=english_text,
            msgstr=korean_text,
            source_label="source/en/mm6/data/10LocLANG.icons/npcprof.txt",
            korean_label=f"Data/Text localization/{korean.name}",
        )
        added += len(po) - before
    return added, missing_source, missing_korean


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--korean-dir", type=Path, required=True)
    parser.add_argument("--english-en-root", type=Path, required=True)
    parser.add_argument("--po", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    po = polib.pofile(str(args.po))
    seen = {entry.msgctxt or "" for entry in po if not entry.obsolete}
    start_entries = len(po)

    specs = [
        (
            "KO_GlobalTxt.txt",
            pair_global,
            args.english_en_root / "mm8/Data/10LocLANG.EnglishT/Global.txt",
        ),
        (
            "KO_SpellsTxt.txt",
            pair_spells,
            args.english_en_root / "mm8/Data/10LocLANG.EnglishT/Spells.txt",
        ),
        (
            "KO_StatsDescriptions.tsv",
            pair_stats,
            args.english_en_root / "mm8/Data/10LocLANG.EnglishT/stats.txt",
        ),
        (
            "KO_NPCProfessions.txt",
            pair_npc_professions,
            args.english_en_root / "mm6/data/10LocLANG.icons/npcprof.txt",
        ),
    ]

    report = json.loads(args.report.read_text(encoding="utf-8"))
    problems = []
    mapped_names = []

    for korean_name, pairer, english_path in specs:
        korean_path = args.korean_dir / korean_name
        if not korean_path.is_file():
            problems.append(f"missing Korean source: {korean_name}")
            continue
        if not english_path.is_file():
            problems.append(f"missing English source: {english_path}")
            continue
        added, missing_source, missing_korean = pairer(po, seen, korean_path, english_path)
        report.setdefault("files", {})[korean_name] = {
            "format": "inherited-base-game",
            "entries": added,
            "missing_files": [],
            "missing_indexes": missing_source,
            "missing_korean": missing_korean,
            "korean_only": missing_source,
        }
        mapped_names.append(korean_name)
        if missing_source:
            problems.append(
                f"{korean_name}: {len(missing_source)} Korean records have no English source; "
                f"first={missing_source[:10]}"
            )
        if missing_korean:
            problems.append(
                f"{korean_name}: {len(missing_korean)} English records are untranslated; "
                f"first={missing_korean[:10]}"
            )
        print(
            f"special source {korean_name}: entries={added}, "
            f"source_miss={len(missing_source)}, untranslated={len(missing_korean)}"
        )

    po.sort(key=lambda e: ((e.msgctxt or "").casefold(), e.msgid.casefold()))
    po.save(str(args.po))

    active = [entry for entry in po if not entry.obsolete]
    report["entries"] = len(active)
    report["translated"] = sum(1 for entry in active if entry.msgstr)
    report["untranslated"] = sum(1 for entry in active if not entry.msgstr)
    report["paired_files"] = len(report.get("files", {}))
    report["missing_korean_records"] = sum(
        len(details.get("missing_korean", []))
        for details in report.get("files", {}).values()
    )
    report["korean_only_records"] = sum(
        len(details.get("korean_only", []))
        for details in report.get("files", {}).values()
    )

    unmapped = set(report.get("unmapped_korean_files", []))
    unmapped.difference_update(SPECIAL_FILES)
    unmapped.difference_update(GENERATED_FILES)
    report["unmapped_korean_files"] = sorted(unmapped, key=str.casefold)
    report["special_mapped_files"] = sorted(mapped_names, key=str.casefold)
    report["generated_korean_files"] = sorted(GENERATED_FILES, key=str.casefold)
    report["special_entries_added"] = len(active) - start_entries
    report["schema"] = max(int(report.get("schema", 0)), 3)

    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Special inherited source augmentation")
    print(f"  base entries:           {start_entries}")
    print(f"  added entries:          {len(active) - start_entries}")
    print(f"  total entries:          {len(active)}")
    print(f"  translated:             {report['translated']}")
    print(f"  untranslated:           {report['untranslated']}")
    print(f"  unmapped Korean files:  {report['unmapped_korean_files']}")
    print(f"  generated-only files:   {report['generated_korean_files']}")

    if problems:
        print("\nSpecial source mapping failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    if report["unmapped_korean_files"]:
        print("unclassified Korean source files remain", file=sys.stderr)
        return 1
    print("special source mapping: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
