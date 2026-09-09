#!/usr/bin/env python3
"""Audit Korean translation ownership across static tables and runtime Lua.

The long-term rule is simple:

* PO/static text owns wording whenever the game can load the value normally.
* Runtime Lua may re-apply a value when Merge rebuilds/caches it later, but the
  wording should not be independently maintained in Lua.
* Truly runtime-created UI/history/cache fixes remain explicit exceptions.

This audit is intentionally conservative.  It reports overlaps; it does not
rewrite game files or assume that a late runtime assignment is safe to remove.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path


LONG_HEADER = ("table (of game struct)", "id", "field", "new text")
RUNTIME_OVERRIDE_NAME = "KO_RuntimeOverrides.txt"

# Known Lua literal maps whose numeric keys are later written into Game tables.
# These are the highest-value duplicate-translation risks because wording is
# maintained twice: once in KO/PO data and once inside Lua source.
LUA_LITERAL_MAPS = {
    "globalTxts": "GlobalTxt",
    "EXPERIENCE_TEXT": "GlobalTxt",
    "statsNames": "StatsNames",
    "statsDescs": "StatsDescriptions",
    "skillNames": "SkillNames",
    "skillDescs": "SkillDescriptions",
    "desNormal": "SkillDescriptionsNormal",
    "desExpert": "SkillDescriptionsExpert",
    "desMaster": "SkillDescriptionsMaster",
    "desGM": "SkillDescriptionsGrandMaster",
}

# Runtime mechanics that are expected to remain Lua-owned even after PO is the
# wording source of truth.  They are listed here so the report can distinguish
# structural runtime code from suspicious duplicate translation tables.
RUNTIME_MECHANIC_FILES = {
    "ZZZZ_KoreanRuntimeHotfix.lua",
    "ZZZ_KoreanExtraSettingsOverlay.lua",
    "ZZ_KoreanEmeraldWellTimerFix.lua",
    "ZZ_KoreanReportedLocalization.lua",
    "KoreanHistory.lua",
}


@dataclass(frozen=True)
class Record:
    table: str
    record_id: str
    field: str
    text: str
    source: str

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

    def replace_last(rec: Record) -> None:
        records[-1] = rec

    for line_no, line in enumerate(lines[1:], 2):
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            if parts[0].strip():
                current_table = parts[0].strip()
            if not current_table:
                raise ValueError(f"{path}:{line_no}: record has no table")
            current = Record(
                current_table,
                parts[1].strip(),
                parts[2].strip(),
                decode_field(parts[3]),
                path.name,
            )
            records.append(current)
            continue
        if not line.strip():
            continue
        if current is None:
            raise ValueError(f"{path}:{line_no}: orphan continuation")
        current = Record(
            current.table,
            current.record_id,
            current.field,
            current.text + "\n" + line,
            current.source,
        )
        replace_last(current)
    return records


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
    # Wide source files describe one Game table named after KO_<name>Txt.
    stem = path.stem
    table = stem[3:] if stem.startswith("KO_") else stem
    if table.endswith("Txt"):
        table = table

    result: list[Record] = []
    for row_index, row in enumerate(rows[1:]):
        row = row + [""] * max(0, len(header) - len(row))
        key = row[0].strip()
        # Ordered tables such as NPCNames have no numeric game id in col 0.
        # Use row position only for audit identity; it will not accidentally
        # collide with normal numeric long-overlay records.
        record_id = key if key.isdigit() else f"@row:{row_index}"
        for col in range(1, len(header)):
            text = row[col] if col < len(row) else ""
            if not text:
                continue
            result.append(Record(table, record_id, header[col] or f"column-{col}", text, path.name))
    return result


def load_translation_records(folder: Path):
    by_key: dict[tuple[str, str, str], list[Record]] = defaultdict(list)
    by_source: dict[str, list[Record]] = {}
    for path in sorted([*folder.glob("KO_*.txt"), *folder.glob("KO_*.tsv")], key=lambda p: p.name.casefold()):
        if path.name == "KO_MapStrings.txt":
            continue
        records = parse_long(path) if is_long(path) else parse_wide(path)
        by_source[path.name] = records
        for rec in records:
            by_key[rec.key].append(rec)
    return by_key, by_source


def extract_lua_literal_maps(path: Path):
    text = read_text(path)
    found = []
    for variable, game_table in LUA_LITERAL_MAPS.items():
        # Match a local/non-local table literal conservatively until the first
        # standalone closing brace. Current localization maps use this layout.
        match = re.search(
            rf"(?:local\s+)?{re.escape(variable)}\s*=\s*\{{(?P<body>.*?)\n\s*\}}",
            text,
            flags=re.S,
        )
        if not match:
            continue
        ids = sorted({int(x) for x in re.findall(r"\[(\d+)\]\s*=", match.group("body"))})
        found.append({
            "file": str(path).replace("\\", "/"),
            "variable": variable,
            "game_table": game_table,
            "ids": ids,
        })
    return found


def scan_lua(scripts: Path):
    maps = []
    direct_assignments = []
    for path in sorted(scripts.rglob("*.lua"), key=lambda p: str(p).casefold()):
        maps.extend(extract_lua_literal_maps(path))
        text = read_text(path)
        for table, record_id in re.findall(r"Game\.(\w+)\s*\[\s*(\d+)\s*\]\s*=", text):
            direct_assignments.append({
                "file": str(path).replace("\\", "/"),
                "game_table": table,
                "id": int(record_id),
            })
    return maps, direct_assignments


def static_matches_for_lua(by_key, game_table: str, ids: list[int]):
    result = []
    wanted = {str(i) for i in ids}
    for (table, record_id, field), records in by_key.items():
        if table == game_table and record_id in wanted:
            result.append({
                "table": table,
                "id": int(record_id),
                "field": field,
                "sources": sorted({r.source for r in records}),
            })
    return sorted(result, key=lambda x: (x["id"], x["field"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translations", type=Path, default=Path("Data/Text localization"))
    parser.add_argument("--scripts", type=Path, default=Path("Scripts"))
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    by_key, by_source = load_translation_records(args.translations)
    runtime_records = by_source.get(RUNTIME_OVERRIDE_NAME, [])
    runtime_duplicates = []
    runtime_unique = []

    for runtime in runtime_records:
        peers = [r for r in by_key.get(runtime.key, []) if r.source != RUNTIME_OVERRIDE_NAME]
        item = {
            "table": runtime.table,
            "id": runtime.record_id,
            "field": runtime.field,
            "runtime_text": runtime.text,
            "other_sources": sorted({r.source for r in peers}),
            "same_text": any(r.text == runtime.text for r in peers),
        }
        if peers:
            runtime_duplicates.append(item)
        else:
            runtime_unique.append(item)

    lua_maps, direct_assignments = scan_lua(args.scripts)
    for item in lua_maps:
        item["static_matches"] = static_matches_for_lua(by_key, item["game_table"], item["ids"])
        item["static_overlap_ids"] = sorted({x["id"] for x in item["static_matches"]})

    suspicious_lua_maps = [x for x in lua_maps if x["static_overlap_ids"]]
    report = {
        "schema": 1,
        "policy": {
            "wording_source": "PO/static data whenever possible",
            "runtime_role": "late reapplication/cache/UI mechanics only",
        },
        "translation_files": len(by_source),
        "runtime_override_records": len(runtime_records),
        "runtime_override_duplicate_keys": len(runtime_duplicates),
        "runtime_override_unique_keys": len(runtime_unique),
        "runtime_override_duplicates": runtime_duplicates,
        "lua_literal_maps": lua_maps,
        "lua_literal_maps_with_static_overlap": len(suspicious_lua_maps),
        "direct_game_assignments": direct_assignments,
        "runtime_mechanic_files": sorted(RUNTIME_MECHANIC_FILES),
    }

    print("Korean runtime translation ownership audit")
    print(f"  translation source files:       {report['translation_files']}")
    print(f"  KO_RuntimeOverrides records:    {report['runtime_override_records']}")
    print(f"  duplicate override keys:        {report['runtime_override_duplicate_keys']}")
    print(f"  runtime-only override keys:     {report['runtime_override_unique_keys']}")
    print(f"  Lua literal maps found:         {len(lua_maps)}")
    print(f"  Lua maps overlapping static:    {report['lua_literal_maps_with_static_overlap']}")

    if runtime_duplicates:
        print("\nRuntimeOverrides entries also owned elsewhere:")
        for item in runtime_duplicates:
            print(
                f"  {item['table']}[{item['id']}] {item['field'] or '<default>'}: "
                f"{', '.join(item['other_sources'])} (same_text={item['same_text']})"
            )

    if suspicious_lua_maps:
        print("\nHard-coded Lua maps overlapping static translation data:")
        for item in suspicious_lua_maps:
            print(
                f"  {item['file']}::{item['variable']} -> {item['game_table']}: "
                f"{len(item['static_overlap_ids'])}/{len(item['ids'])} ids overlap"
            )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nJSON report: {args.json}")

    # Audit is informational during migration. CI failure policy is added only
    # after current intentional runtime exceptions have an explicit allowlist.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
