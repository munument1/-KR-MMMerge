#!/usr/bin/env python3
"""One-way migration of hard-coded GlobalTxt Korean wording out of Lua.

The late-reapply behavior is preserved by adding every affected GlobalTxt id to
config/runtime_override_keys.tsv.  tools/rebuild_runtime_overrides.py then
copies wording from canonical KO_GlobalTxt.txt.  This script removes only the
now-redundant Lua wording tables/functions, not unrelated stats/skills or UI
runtime mechanics.

Legacy Korean Lua sources are a mixture of UTF-8 and CP949.  Their original
encoding is preserved byte-for-byte apart from the intended textual edit.
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


def read_preserving_encoding(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def write_preserving_encoding(path: Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def extract_numeric_ids(body: str) -> set[int]:
    return {int(value) for value in re.findall(r"\[(\d+)\]\s*=", body)}


def migrate_stats(text: str) -> tuple[str, set[int]]:
    pattern = re.compile(
        r"\t-- 6\. Game\.GlobalTxt UI 레이블 정밀 매핑 \(Global\.TXT 전용 인덱스\)\r?\n"
        r"\tlocal globalTxts = \{(?P<body>.*?)\r?\n\t\}\r?\n"
        r"\tfor i, v in pairs\(globalTxts\) do\r?\n"
        r"\t\tif Game\.GlobalTxt and Game\.GlobalTxt\[i\] then\r?\n"
        r"\t\t\tGame\.GlobalTxt\[i\] = enc\(v\)\r?\n"
        r"\t\tend\r?\n"
        r"\tend\r?\n",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        if "globalTxts" not in text:
            return text, set()
        raise RuntimeError("could not isolate KoreanStatsAndSkills.globalTxts block")
    ids = extract_numeric_ids(match.group("body"))
    if not ids:
        raise RuntimeError("globalTxts block contained no numeric ids")
    newline = "\r\n" if "\r\n" in match.group(0) else "\n"
    replacement = (
        "\t-- 6. GlobalTxt wording is owned by KO_GlobalTxt/PO." + newline
        + "\t-- Required late-reapply ids are generated into KO_RuntimeOverrides.txt." + newline
    )
    return text[: match.start()] + replacement + text[match.end() :], ids


def migrate_reported(text: str) -> tuple[str, set[int]]:
    pattern = re.compile(
        r"-- Experience right-click uses a mixture of stats\.txt and GlobalTxt strings\.\r?\n"
        r"-- Reapply the dynamic labels/formats as known-good EUC-KR bytes so UTF-8 Lua\r?\n"
        r"-- source bytes cannot reach the native DBCS drawing/wrapping paths\.\r?\n"
        r"local EXPERIENCE_TEXT = \{(?P<body>.*?)\r?\n\}\r?\n\r?\n"
        r"local function applyExperienceTextSafety\(\)\r?\n"
        r".*?\r?\nend\r?\n\r?\n",
        re.S,
    )
    match = pattern.search(text)
    if match:
        ids = extract_numeric_ids(match.group("body"))
        if not ids:
            raise RuntimeError("EXPERIENCE_TEXT block contained no ids")
        newline = "\r\n" if "\r\n" in match.group(0) else "\n"
        replacement = (
            "-- Experience/GlobalTxt wording is owned by KO_GlobalTxt/PO and is" + newline
            + "-- re-applied through generated KO_RuntimeOverrides.txt." + newline + newline
        )
        text = text[: match.start()] + replacement + text[match.end() :]
    else:
        if "EXPERIENCE_TEXT" in text or "applyExperienceTextSafety" in text:
            raise RuntimeError("could not isolate EXPERIENCE_TEXT runtime block")
        ids = set()

    text = re.sub(r"^[ \t]*applyExperienceTextSafety\(\)[ \t]*\r?\n", "", text, flags=re.M)
    text = re.sub(
        r"^KoreanReportedLocalization\.ApplyExperienceTextSafety\s*=\s*applyExperienceTextSafety\s*\r?\n",
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
    MANIFEST.write_text(out.getvalue(), encoding="utf-8", newline="")
    return added


def main() -> int:
    stats_before, stats_encoding = read_preserving_encoding(STATS_LUA)
    reported_before, reported_encoding = read_preserving_encoding(REPORTED_LUA)

    stats_after, stats_ids = migrate_stats(stats_before)
    reported_after, reported_ids = migrate_reported(reported_before)
    all_ids = stats_ids | reported_ids

    write_preserving_encoding(STATS_LUA, stats_after, stats_encoding)
    write_preserving_encoding(REPORTED_LUA, reported_after, reported_encoding)
    added = update_manifest(all_ids)

    print("GlobalTxt Lua ownership migration")
    print(f"  KoreanStatsAndSkills encoding:      {stats_encoding}")
    print(f"  ReportedLocalization encoding:      {reported_encoding}")
    print(f"  ids from KoreanStatsAndSkills:      {len(stats_ids)}")
    print(f"  ids from ReportedLocalization:      {len(reported_ids)}")
    print(f"  unique GlobalTxt late-reapply ids:  {len(all_ids)}")
    print(f"  newly added manifest keys:          {added}")
    print("  Lua wording blocks removed:         OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
