#!/usr/bin/env python3
"""Run report 65949 source corrections in a safe, deterministic order."""
from __future__ import annotations

import pathlib
import sys

import apply_report_65949_fixes as fixes

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"

EXTRA_ITEM_FIXES = [
    ("기벳", "교수대"),
    ("건설된 샤렐는", "제작된 샤렐은"),
    (
        "이 성은 서기 590년 하렉 1세가 독살당한 후 혼란기에 레그나의 유일한 에라티아 전초기지에 남겨졌습니다.",
        "이 창은 서기 590년 하렉 1세가 독살당한 후 혼란기에 레그나의 유일한 에라시아 전초기지에 남겨졌습니다.",
    ),
]


def main() -> None:
    total = 0

    # Repair unambiguous terminology/corruption first across localization data.
    for path in sorted(loc.glob("KO_*.txt")):
        total += fixes.rewrite(path, fixes.SAFE_ALL)

    # Exact artifact/relic/reagent corrections must run before mechanical
    # normalization. Several source strings contain "행운 +", "속도 +",
    # "지력 +" etc.; normalizing those first would make the exact fixes miss.
    for path in [loc / "KO_ItemsTxt.txt", loc / "KO_RuntimeOverrides.txt"]:
        total += fixes.rewrite(path, fixes.ITEM_FIXES + EXTRA_ITEM_FIXES)

    # Normalize only mechanical stat notation, not ordinary Korean prose.
    for path in [
        loc / "KO_ItemsTxt.txt",
        loc / "KO_RuntimeOverrides.txt",
        loc / "KO_SpcItemsTxtStats.txt",
        loc / "KO_StdItemsTxtStats.txt",
    ]:
        total += fixes.rewrite(path, fixes.MECHANICAL)

    total += fixes.rewrite(loc / "KO_GlobalTxt.txt", fixes.GLOBAL_FIXES)
    total += fixes.rewrite(loc / "KO_StatsDescriptions.tsv", fixes.STATS_FIXES)

    # GrayFace/MMExtension reads this beside MM8.exe. Keep a UTF-8 source in
    # Data/Text localization, but ship the runtime file as CP949/EUC-KR bytes.
    template = loc / "KO_mm8lang.ini.utf8"
    output = root / "mm8lang.ini"
    lang = template.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    wanted = lang.replace("\n", "\r\n").encode("cp949")
    if not output.exists() or output.read_bytes() != wanted:
        output.write_bytes(wanted)
        total += 1
        print("mm8lang.ini: regenerated as CP949")

    print(f"report 65949 source fixes: {total} changes")


if __name__ == "__main__":
    main()
