#!/usr/bin/env python3
"""Append canonical Korean skill text to the MMMerge PO.

KO_Skilldes.txt is a Korean-owned source extracted from the former runtime Lua
literal maps.  English msgids come from the pinned MM8 Skilldes.txt because
MMMerge inherits these Game.Skill* tables from MM8.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

import polib


FIELDS = (
    ("Name", 0, "SkillNames"),
    ("Description", 1, "SkillDescriptions"),
    ("Normal", 2, "SkillDesNormal"),
    ("Expert", 3, "SkillDesExpert"),
    ("Master", 4, "SkillDesMaster"),
    ("GrandMaster", 5, "SkillDesGM"),
)


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp949")


def read_rows(path: Path):
    return list(
        csv.reader(
            io.StringIO(read_text(path), newline=""),
            delimiter="\t",
            quotechar='"',
            doublequote=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--korean", type=Path, required=True)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--po", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    # The bootstrap workflow is installed before the one-time Lua migration.
    # Until KO_Skilldes.txt exists, keep the existing catalog valid.
    if not args.korean.is_file():
        print("KO_Skilldes.txt not created yet; skill-source augmentation skipped")
        return 0

    korean_rows = read_rows(args.korean)
    if not korean_rows:
        raise SystemExit("KO_Skilldes.txt is empty")
    expected_header = ["Index", "Name", "Description", "Normal", "Expert", "Master", "GrandMaster"]
    if korean_rows[0][:7] != expected_header:
        raise SystemExit(f"unexpected KO_Skilldes header: {korean_rows[0]!r}")

    korean = {}
    for row_no, row in enumerate(korean_rows[1:], 2):
        row = row + [""] * max(0, 7 - len(row))
        if not row[0].strip():
            continue
        if not row[0].strip().isdigit():
            raise SystemExit(f"KO_Skilldes.txt:{row_no}: non-numeric Index {row[0]!r}")
        idx = int(row[0].strip())
        if idx in korean:
            raise SystemExit(f"KO_Skilldes.txt:{row_no}: duplicate Index {idx}")
        korean[idx] = row[1:7]

    english_rows = []
    for row in read_rows(args.english)[1:]:
        if row and row[0].strip():
            english_rows.append((row + [""] * 6)[:6])

    if sorted(korean) != list(range(39)):
        raise SystemExit(f"KO_Skilldes indexes must be 0..38; got {sorted(korean)}")
    if len(english_rows) != 39:
        raise SystemExit(f"MM8 Skilldes must contain exactly 39 usable rows; got {len(english_rows)}")

    po = polib.pofile(str(args.po))
    seen = {entry.msgctxt or "" for entry in po if not entry.obsolete}
    added = 0
    untranslated = []

    for idx in range(39):
        ko_fields = korean[idx]
        en_fields = english_rows[idx]
        for ko_col, (field_name, en_col, game_table) in enumerate(FIELDS):
            msgid = en_fields[en_col]
            msgstr = ko_fields[ko_col]
            context = (
                "mmmerge/inherited/mm8/Skilldes.txt"
                f"|table={game_table}|id={idx}|field=<default>"
            )
            if not msgid and not msgstr:
                continue
            if not msgid and msgstr:
                raise SystemExit(f"Korean skill text maps to empty English source: {idx}:{field_name}")
            if msgid and not msgstr:
                untranslated.append(f"{idx}:{field_name}")
            if context in seen:
                raise SystemExit(f"duplicate PO context: {context}")
            entry = polib.POEntry(msgctxt=context, msgid=msgid, msgstr=msgstr)
            entry.comment = (
                "EN: source/en/mm8/Data/10LocLANG.EnglishT/Skilldes.txt\n"
                "KO: Data/Text localization/KO_Skilldes.txt"
            )
            po.append(entry)
            seen.add(context)
            added += 1

    if untranslated:
        raise SystemExit(
            f"KO_Skilldes contains {len(untranslated)} untranslated cells; first={untranslated[:10]}"
        )
    if added != 39 * len(FIELDS):
        raise SystemExit(f"expected 234 skill PO entries, added {added}")

    po.sort(key=lambda e: ((e.msgctxt or "").casefold(), e.msgid.casefold()))
    po.save(str(args.po))

    report = json.loads(args.report.read_text(encoding="utf-8"))
    report.setdefault("files", {})["KO_Skilldes.txt"] = {
        "format": "inherited-base-game",
        "entries": added,
        "missing_files": [],
        "missing_indexes": [],
        "missing_korean": [],
        "korean_only": [],
    }
    mapped = set(report.get("special_mapped_files", []))
    mapped.add("KO_Skilldes.txt")
    report["special_mapped_files"] = sorted(mapped, key=str.casefold)
    generated = set(report.get("generated_korean_files", []))
    generated.add("KO_StatsSkillsRuntime.txt")
    report["generated_korean_files"] = sorted(generated, key=str.casefold)
    report["special_entries_added"] = int(report.get("special_entries_added", 0)) + added

    active = [entry for entry in po if not entry.obsolete]
    report["entries"] = len(active)
    report["translated"] = sum(1 for entry in active if entry.msgstr)
    report["untranslated"] = sum(1 for entry in active if not entry.msgstr)
    report["paired_files"] = len(report.get("files", {}))
    report["schema"] = max(int(report.get("schema", 0)), 4)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Canonical skill source augmentation")
    print(f"  skill rows:       {len(korean)}")
    print(f"  entries added:    {added}")
    print(f"  PO total:         {len(active)}")
    print(f"  translated:       {report['translated']}")
    print(f"  untranslated:     {report['untranslated']}")
    print("skill source mapping: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
