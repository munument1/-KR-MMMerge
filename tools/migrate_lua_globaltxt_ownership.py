#!/usr/bin/env python3
"""One-way migration of hard-coded GlobalTxt Korean wording out of Lua.

The late-reapply behavior is preserved by adding every affected GlobalTxt id to
config/runtime_override_keys.tsv.  tools/rebuild_runtime_overrides.py then
copies wording from canonical KO_GlobalTxt.txt.  This script removes only the
now-redundant Lua wording tables/functions, not unrelated stats/skills or UI
runtime mechanics.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATS_LUA = ROOT / "Scripts/General/KoreanStatsAndSkills.lua"
REPORTED_LUA = ROOT / "Scripts/General/ZZ_KoreanReportedLocalization.lua"
MANIFEST = ROOT / "config/runtime_override_keys.tsv"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def extract_numeric_ids(body: str) -> set[int]:
    return {int(value) for value in re.findall(r"\[(\d+)\]\s*=", body)}


def migrate_stats(text: str) -> tuple[str, set[int]]:
    pattern = re.compile(
        r"(?P<indent>\t)-- 6\. Game\.GlobalTxt UI 레이블 정밀 매핑 \(Global\.TXT 전용 인덱스\)\n"
        r"\tlocal globalTxts = \{(?P<body>.*?)\n\t\}\n"
        r"\tfor i, v in pairs\(globalTxts\) do\n"
        r"\t\tif Game\.GlobalTxt and Game\.GlobalTxt\[i\] then\n"
        r"\t\t\tGame\.GlobalTxt\[i\] = enc\(v\)\n"
        r"\t\tend\n"
        r"\tend\n",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        # Idempotent rerun after migration.
        if "globalTxts" not in text:
            return text, set()
        raise RuntimeError("could not isolate KoreanStatsAndSkills.globalTxts block")
    ids = extract_numeric_ids(match.group("body"))
    if not ids:
        raise RuntimeError("globalTxts block contained no numeric ids")
    replacement = (
        "\t-- 6. GlobalTxt wording is owned by KO_GlobalTxt/PO.\n"
        "\t-- Required late-reapply ids are generated into KO_RuntimeOverrides.txt.\n"
    )
    return text[: match.start()] + replacement + text[match.end() :], ids


def migrate_reported(text: str) -> tuple[str, set[int]]:
    pattern = re.compile(
        r"-- Experience right-click uses a mixture of stats\.txt and GlobalTxt strings\.\n"
        r"-- Reapply the dynamic labels/formats as known-good EUC-KR bytes so UTF-8 Lua\n"
        r"-- source bytes cannot reach the native DBCS drawing/wrapping paths\.\n"
        r"local EXPERIENCE_TEXT = \{(?P<body>.*?)\n\}\n\n"
        r"local function applyExperienceTextSafety\(\)\n"
        r".*?\nend\n\n",
        re.S,
    )
    match = pattern.search(text)
    if match:
        ids = extract_numeric_ids(match.group("body"))
        if not ids:
            raise RuntimeError("EXPERIENCE_TEXT block contained no ids")
        replacement = (
            "-- Experience/GlobalTxt wording is owned by KO_GlobalTxt/PO and is\n"
            "-- re-applied through generated KO_RuntimeOverrides.txt.\n\n"
        )
        text = text[: match.start()] + replacement + text[match.end() :]
    else:
        if "EXPERIENCE_TEXT" in text or "applyExperienceTextSafety" in text:
            raise RuntimeError("could not isolate EXPERIENCE_TEXT runtime block")
        ids = set()

    text = re.sub(r"^\s*applyExperienceTextSafety\(\)\s*\n", "", text, flags=re.M)
    text = re.sub(
        r"^KoreanReportedLocalization\.ApplyExperienceTextSafety\s*=\s*applyExperienceTextSafety\s*\n",
        "",
        text,
        flags=re.M,
    )
    if "applyExperienceTextSafety" in text or "EXPERIENCE_TEXT" in text:
        raise RuntimeError("experience runtime wording references remain after migration")
    return text, ids


def update_manifest(ids: set[int]) -> int:
    raw = MANIFEST.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(raw), delimiter="\t"))
    if not rows or rows[0][:4] != ["Table", "Id", "Field", "RuntimeOnlyText"]:
        raise RuntimeError("unexpected runtime manifest header")

    existing = {(row[0].strip(), row[1].strip(), row[2].strip()) for row in rows[1:] if len(row) >= 3}
    added = 0
    for record_id in sorted(ids):
        key = ("GlobalTxt", str(record_id), "")
        if key not in existing:
            rows.append(["GlobalTxt", str(record_id), "", ""])
            existing.add(key)
            added += 1

    # Keep the manifest deterministic: runtime-only Houses first, then tables
    # alphabetically, numeric ids numerically, and field last.
    header, data = rows[0], rows[1:]
    data.sort(
        key=lambda row: (
            0 if row[0] == "Houses" and len(row) > 3 and row[3] else 1,
            row[0].casefold(),
            int(row[1]) if len(row) > 1 and row[1].isdigit() else 10**9,
            row[2].casefold() if len(row) > 2 else "",
        )
    )
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerows([header, *data])
    write(MANIFEST, out.getvalue())
    return added


def main() -> int:
    stats_before = read(STATS_LUA)
    reported_before = read(REPORTED_LUA)

    stats_after, stats_ids = migrate_stats(stats_before)
    reported_after, reported_ids = migrate_reported(reported_before)
    all_ids = stats_ids | reported_ids

    write(STATS_LUA, stats_after)
    write(REPORTED_LUA, reported_after)
    added = update_manifest(all_ids)

    print("GlobalTxt Lua ownership migration")
    print(f"  ids from KoreanStatsAndSkills:      {len(stats_ids)}")
    print(f"  ids from ReportedLocalization:      {len(reported_ids)}")
    print(f"  unique GlobalTxt late-reapply ids:  {len(all_ids)}")
    print(f"  newly added manifest keys:          {added}")
    print("  Lua wording blocks removed:         OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
