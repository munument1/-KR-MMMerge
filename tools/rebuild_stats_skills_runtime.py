#!/usr/bin/env python3
"""Move Stats/Skills wording out of runtime Lua and generate its late projection.

Canonical ownership:
  * stat names: KO_GlobalTxt.txt (MM8 Global ids)
  * stat descriptions: KO_StatsDescriptions.tsv
  * skill names/descriptions/mastery text: KO_Skilldes.txt

KO_StatsSkillsRuntime.txt is generated EUC-KR runtime data consumed by
LocalizeTables.lua.  KoreanStatsAndSkills.lua becomes an inert compatibility
stub so no independent wording remains in Lua.

MMExtension exposes Game.StatsDescriptions as an array of exactly seven
primary-stat pointers.  The canonical TSV may keep additional reference/help
wording, but runtime projection must never write indexes 7+ into that engine
array.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data" / "Text localization"
LUA = ROOT / "Scripts" / "General" / "KoreanStatsAndSkills.lua"
LOCALIZE = ROOT / "Scripts" / "General" / "LocalizeTables.lua"
SKILL_SOURCE = DATA / "KO_Skilldes.txt"
RUNTIME = DATA / "KO_StatsSkillsRuntime.txt"
GLOBAL = DATA / "KO_GlobalTxt.txt"
STATS = DATA / "KO_StatsDescriptions.tsv"

STAT_GLOBAL_IDS = [144, 116, 163, 75, 1, 211, 136]
RUNTIME_STAT_DESCRIPTION_COUNT = 7
MAPS = {
    "statsNames": 7,
    "statsDescs": 7,
    "skillNames": 39,
    "skillDescs": 39,
    "desNormal": 39,
    "desExpert": 39,
    "desMaster": 39,
    "desGM": 39,
}

STUB = """-- Korean Stats/Skills wording is no longer maintained in Lua.\n-- Canonical sources:\n--   Data/Text localization/KO_GlobalTxt.txt\n--   Data/Text localization/KO_StatsDescriptions.tsv\n--   Data/Text localization/KO_Skilldes.txt\n-- Runtime projection:\n--   Data/Text localization/KO_StatsSkillsRuntime.txt\n-- LocalizeTables.lua applies the generated projection during initialization\n-- and TxtFilesReloaded, preserving the late-reapply behavior without duplicate\n-- translation ownership.\n"""


def read_any(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def unescape_lua(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(value):
            out.append("\\")
            break
        esc = value[i]
        if esc in {'\\', '"', "'"}:
            out.append(esc)
            i += 1
        elif esc == "n":
            out.append("\n")
            i += 1
        elif esc == "r":
            out.append("\r")
            i += 1
        elif esc == "t":
            out.append("\t")
            i += 1
        elif esc.isdigit():
            j = i
            while j < len(value) and j < i + 3 and value[j].isdigit():
                j += 1
            out.append(chr(int(value[i:j], 10)))
            i = j
        else:
            out.append(esc)
            i += 1
    return "".join(out)


def extract_literal_map(text: str, variable: str, expected: int) -> dict[int, str]:
    match = re.search(
        rf"(?:local\s+)?{re.escape(variable)}\s*=\s*\{{(?P<body>.*?)\n\s*\}}",
        text,
        flags=re.S,
    )
    if not match:
        raise ValueError(f"could not find Lua literal map {variable}")
    pairs = re.findall(
        r'\[(\d+)\]\s*=\s*"((?:\\.|[^"\\])*)"',
        match.group("body"),
    )
    result = {int(index): unescape_lua(value) for index, value in pairs}
    if sorted(result) != list(range(expected)):
        raise ValueError(
            f"{variable}: expected ids 0..{expected - 1}, got {sorted(result)}"
        )
    return result


def extract_skill_source_from_lua() -> tuple[dict[str, dict[int, str]], str]:
    lua_text, encoding = read_any(LUA)
    maps = {name: extract_literal_map(lua_text, name, count) for name, count in MAPS.items()}
    return maps, encoding


def write_skill_source(maps: dict[str, dict[int, str]]) -> None:
    out = io.StringIO(newline="")
    writer = csv.writer(
        out,
        delimiter="\t",
        quotechar='"',
        doublequote=True,
        lineterminator="\n",
    )
    writer.writerow(["Index", "Name", "Description", "Normal", "Expert", "Master", "GrandMaster"])
    for i in range(39):
        writer.writerow([
            i,
            maps["skillNames"][i],
            maps["skillDescs"][i],
            maps["desNormal"][i],
            maps["desExpert"][i],
            maps["desMaster"][i],
            maps["desGM"][i],
        ])
    SKILL_SOURCE.write_text(out.getvalue(), encoding="utf-8", newline="")


def read_skill_source() -> dict[int, list[str]]:
    text, _ = read_any(SKILL_SOURCE)
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter="\t", quotechar='"', doublequote=True))
    expected = ["Index", "Name", "Description", "Normal", "Expert", "Master", "GrandMaster"]
    if not rows or rows[0][:7] != expected:
        raise ValueError(f"unexpected KO_Skilldes header: {rows[0] if rows else None!r}")
    result: dict[int, list[str]] = {}
    for row_no, row in enumerate(rows[1:], 2):
        row = row + [""] * max(0, 7 - len(row))
        if not row[0].strip():
            continue
        if not row[0].strip().isdigit():
            raise ValueError(f"KO_Skilldes:{row_no}: invalid index {row[0]!r}")
        index = int(row[0].strip())
        result[index] = row[1:7]
    if sorted(result) != list(range(39)):
        raise ValueError(f"KO_Skilldes must contain indexes 0..38; got {sorted(result)}")
    for index, values in result.items():
        if any(value == "" for value in values):
            raise ValueError(f"KO_Skilldes index {index} contains an empty canonical field")
    return result


def read_global_values() -> dict[int, str]:
    text, _ = read_any(GLOBAL)
    values: dict[int, str] = {}
    current_table = ""
    for line_no, line in enumerate(text.splitlines()[1:], 2):
        parts = line.split("\t", 3)
        if len(parts) < 4 or not parts[1].strip().isdigit():
            continue
        if parts[0].strip():
            current_table = parts[0].strip()
        if current_table != "GlobalTxt":
            continue
        values[int(parts[1].strip())] = parts[3]
    missing = [index for index in STAT_GLOBAL_IDS if not values.get(index)]
    if missing:
        raise ValueError(f"KO_GlobalTxt missing stat-name source ids: {missing}")
    return values


def read_stats_descriptions() -> dict[int, str]:
    text, _ = read_any(STATS)
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter="\t", quotechar='"', doublequote=True))
    if not rows or [x.strip() for x in rows[0][:2]] != ["Index", "Description"]:
        raise ValueError("unexpected KO_StatsDescriptions header")
    result: dict[int, str] = {}
    for row in rows[1:]:
        if len(row) >= 2 and row[0].strip().isdigit():
            result[int(row[0].strip())] = row[1]
    if sorted(result) != list(range(26)):
        raise ValueError(f"KO_StatsDescriptions must contain indexes 0..25; got {sorted(result)}")
    if any(not result[i] for i in range(26)):
        raise ValueError("KO_StatsDescriptions contains empty canonical text")
    return result


def runtime_text() -> str:
    global_values = read_global_values()
    stats = read_stats_descriptions()
    skills = read_skill_source()

    tables: list[tuple[str, list[str]]] = []
    tables.append(("StatsNames", [global_values[source_id] for source_id in STAT_GLOBAL_IDS]))
    tables.append(("StatsDescriptions", [stats[i] for i in range(RUNTIME_STAT_DESCRIPTION_COUNT)]))
    tables.append(("SkillNames", [skills[i][0] for i in range(39)]))
    tables.append(("SkillDescriptions", [skills[i][1] for i in range(39)]))
    tables.append(("SkillDesNormal", [skills[i][2] for i in range(39)]))
    tables.append(("SkillDesExpert", [skills[i][3] for i in range(39)]))
    tables.append(("SkillDesMaster", [skills[i][4] for i in range(39)]))
    tables.append(("SkillDesGM", [skills[i][5] for i in range(39)]))

    lines = ["Table (of Game struct)\tId\tField\tNew text"]
    for table_name, values in tables:
        for index, value in enumerate(values):
            prefix = table_name if index == 0 else ""
            # Canonical fields are single-line by construction.  A tab/newline
            # here would corrupt the generic LocalizeTables long-overlay parser.
            if "\t" in value or "\n" in value or "\r" in value:
                raise ValueError(f"{table_name}[{index}] contains a tab/newline")
            lines.append(f"{prefix}\t{index}\t\t{value}")
    return "\r\n".join(lines) + "\r\n"


def ensure_localize_whitelist(write: bool) -> bool:
    text, encoding = read_any(LOCALIZE)
    marker = '["ko_statsskillsruntime.txt"] = true'
    if marker in text:
        return False
    needle = '\t["ko_runtimeoverrides.txt"] = true\n}'
    replacement = '\t["ko_runtimeoverrides.txt"] = true,\n\t["ko_statsskillsruntime.txt"] = true\n}'
    if needle not in text:
        raise ValueError("could not locate RuntimeKOFiles tail in LocalizeTables.lua")
    if write:
        updated = text.replace(needle, replacement, 1)
        LOCALIZE.write_bytes(updated.encode("utf-8" if encoding == "utf-8" else "cp949"))
    return True


def migrate_lua_if_needed(maps: dict[str, dict[int, str]] | None, write: bool) -> dict[str, int]:
    text, _ = read_any(LUA)
    still_owned = [name for name in MAPS if re.search(rf"\b{re.escape(name)}\s*=\s*\{{", text)]
    if not still_owned:
        return {"literal_maps_removed": 0, "old_stat_name_differences": 0, "old_stat_description_differences": 0}
    if maps is None:
        raise ValueError("Lua still owns wording but its maps were not extracted")

    global_values = read_global_values()
    canonical_names = [global_values[source_id] for source_id in STAT_GLOBAL_IDS]
    stats = read_stats_descriptions()
    old_name_diff = sum(maps["statsNames"][i] != canonical_names[i] for i in range(7))
    old_desc_diff = sum(maps["statsDescs"][i] != stats[i] for i in range(7))

    if write:
        LUA.write_text(STUB, encoding="ascii", newline="")
    return {
        "literal_maps_removed": len(still_owned),
        "old_stat_name_differences": old_name_diff,
        "old_stat_description_differences": old_desc_diff,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--migrate-lua", action="store_true")
    args = parser.parse_args()
    if not args.write and not args.check:
        parser.error("choose --write and/or --check")

    maps = None
    lua_text, lua_encoding = read_any(LUA)
    has_old_maps = any(re.search(rf"\b{re.escape(name)}\s*=\s*\{{", lua_text) for name in MAPS)

    if not SKILL_SOURCE.is_file():
        if not has_old_maps:
            raise SystemExit("KO_Skilldes.txt is missing and Lua no longer contains source maps")
        maps, _ = extract_skill_source_from_lua()
        if args.write:
            write_skill_source(maps)
            print("created canonical source: Data/Text localization/KO_Skilldes.txt")
    elif has_old_maps:
        maps, _ = extract_skill_source_from_lua()
        # Refuse to erase Lua unless the canonical source is byte-for-byte equal
        # in meaning to the six skill maps being removed.
        canonical = read_skill_source()
        for i in range(39):
            expected = [
                maps["skillNames"][i], maps["skillDescs"][i], maps["desNormal"][i],
                maps["desExpert"][i], maps["desMaster"][i], maps["desGM"][i],
            ]
            if canonical[i] != expected:
                raise SystemExit(f"KO_Skilldes differs from Lua at index {i}; refusing migration")

    if not SKILL_SOURCE.is_file():
        raise SystemExit("KO_Skilldes.txt was not created")

    expected_runtime = runtime_text()
    expected_bytes = expected_runtime.encode("euc_kr")

    changed_runtime = not RUNTIME.is_file() or RUNTIME.read_bytes() != expected_bytes
    if args.write and changed_runtime:
        RUNTIME.write_bytes(expected_bytes)
        print("wrote generated runtime projection: Data/Text localization/KO_StatsSkillsRuntime.txt")

    whitelist_needed = ensure_localize_whitelist(args.write)
    migration = {"literal_maps_removed": 0, "old_stat_name_differences": 0, "old_stat_description_differences": 0}
    if args.migrate_lua:
        migration = migrate_lua_if_needed(maps, args.write)

    if args.check:
        problems = []
        if not RUNTIME.is_file() or RUNTIME.read_bytes() != expected_bytes:
            problems.append("KO_StatsSkillsRuntime.txt is not synchronized with canonical sources")
        localize_text, _ = read_any(LOCALIZE)
        if '["ko_statsskillsruntime.txt"] = true' not in localize_text:
            problems.append("LocalizeTables.lua does not whitelist KO_StatsSkillsRuntime.txt")
        current_lua, _ = read_any(LUA)
        remaining = [name for name in MAPS if re.search(rf"\b{re.escape(name)}\s*=\s*\{{", current_lua)]
        if remaining:
            problems.append("KoreanStatsAndSkills.lua still owns literal maps: " + ", ".join(remaining))
        if problems:
            print("Stats/skills runtime ownership check failed:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1

    print("Stats/skills canonical ownership")
    print(f"  original Lua encoding:          {lua_encoding}")
    print("  canonical skill rows:           39")
    print("  runtime StatsNames:             7")
    print(f"  runtime StatsDescriptions:      {RUNTIME_STAT_DESCRIPTION_COUNT}")
    print("  runtime skill fields:           234")
    print(f"  generated runtime entries:      {7 + RUNTIME_STAT_DESCRIPTION_COUNT + 234}")
    if args.migrate_lua:
        print(f"  Lua literal maps removed:       {migration['literal_maps_removed']}")
        print(f"  stale stat-name values replaced:{migration['old_stat_name_differences']}")
        print(f"  stale stat-desc values replaced:{migration['old_stat_description_differences']}")
    print(f"  runtime projection changed:     {changed_runtime}")
    print(f"  whitelist change needed:        {whitelist_needed}")
    if args.check:
        print("stats/skills ownership check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())