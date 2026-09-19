#!/usr/bin/env python3
"""Apply high-confidence terminology consistency fixes found by PO audit.

Only exact msgctxt entries are touched.  This deliberately avoids broad
replacement of ambiguous words such as 지팡이, 행운, 도적, or 마을.
"""
from __future__ import annotations

import pathlib
import sys

import polib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
PO = ROOT / "translations" / "ko" / "mmmerge.po"

FIXES: list[tuple[str, str, str]] = [
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=595|field=<default>",
     "지팡이", "마법봉"),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=454|field=<default>",
     "낙하 감쇠", "깃털 낙하"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=440|field=<default>",
     "용맹", "영웅심"),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=10|field=<default>",
     "마을 포털", "도시 귀환"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=421|field=<default>",
     "타운 포털", "도시 귀환"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=574|field=<default>",
     "타운 포털", "도시 귀환"),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=608|field=<default>",
     "광분", "광폭화"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=218|field=<default>",
     "제물", "화염의 장막"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=853|field=<default>",
     "강력한 치료", "대치유"),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=546|field=<default>",
     "뉴 소피갈", "뉴 소르피갈"),

    ("mmmerge/Text localization/LANG_StdItemsTxtStats.txt|table=StdItemsTxt|id=6|field=BonusStat",
     "행운", "운"),
    ("mmmerge/Text localization/LANG_StdItemsTxtStats.txt|table=StdItemsTxt|id=9|field=BonusStat",
     "방어도", "방어력"),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=677|field=<default>",
     "네크로맨서", "강령술사"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=114|field=<default>",
     "도적", "로그"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=3|field=<default>",
     "스파이", "첩자"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=679|field=<default>",
     "클레릭", "성직자"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=681|field=<default>",
     "나이트", "기사"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=686|field=<default>",
     "미노타우로스 로드", "미노타우로스 군주"),
]

for item_id in (733, 734, 735, 736, 737, 738, 739, 740, 743):
    FIXES.append((
        f"mmmerge/Text localization/LANG_ItemsTxt.txt|id={item_id}|field=NotIdentifiedName",
        "일지 조각",
        "일기 조각",
    ))


def main() -> None:
    if len(FIXES) != 27:
        raise SystemExit(f"internal error: expected 27 fixes, got {len(FIXES)}")

    po = polib.pofile(str(PO), encoding="utf-8")
    by_context: dict[str, list[polib.POEntry]] = {}
    for entry in po:
        if entry.msgctxt:
            by_context.setdefault(entry.msgctxt, []).append(entry)

    changed = 0
    for ctx, old, new in FIXES:
        matches = by_context.get(ctx, [])
        if len(matches) != 1:
            raise SystemExit(f"{ctx}: expected one PO entry, found {len(matches)}")
        entry = matches[0]
        if entry.msgstr == old:
            entry.msgstr = new
            changed += 1
        elif entry.msgstr == new:
            pass
        else:
            raise SystemExit(
                f"{ctx}: expected {old!r} or {new!r}, found {entry.msgstr!r}"
            )

    for ctx, _old, new in FIXES:
        entry = by_context[ctx][0]
        if entry.msgstr != new:
            raise SystemExit(f"verification failed for {ctx}: {entry.msgstr!r}")

    po.save(str(PO))
    print(f"terminology audit pass 2: {changed} corrections")


if __name__ == "__main__":
    main()
