#!/usr/bin/env python3
"""Apply high-confidence terminology consistency fixes found by PO audit.

Only exact msgctxt blocks are touched.  This deliberately avoids broad
replacement of ambiguous words such as 지팡이, 행운, 도적, or 마을.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
PO = ROOT / "translations" / "ko" / "mmmerge.po"

FIXES: list[tuple[str, str, str]] = [
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=595|field=<default>",
     'msgstr "지팡이"', 'msgstr "마법봉"'),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=454|field=<default>",
     'msgstr "낙하 감쇠"', 'msgstr "깃털 낙하"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=440|field=<default>",
     'msgstr "용맹"', 'msgstr "영웅심"'),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=10|field=<default>",
     'msgstr "마을 포털"', 'msgstr "도시 귀환"'),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=421|field=<default>",
     'msgstr "타운 포털"', 'msgstr "도시 귀환"'),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=574|field=<default>",
     'msgstr "타운 포털"', 'msgstr "도시 귀환"'),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=608|field=<default>",
     'msgstr "광분"', 'msgstr "광폭화"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=218|field=<default>",
     'msgstr "제물"', 'msgstr "화염의 장막"'),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=853|field=<default>",
     'msgstr "강력한 치료"', 'msgstr "대치유"'),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=546|field=<default>",
     'msgstr "뉴 소피갈"', 'msgstr "뉴 소르피갈"'),

    ("mmmerge/Text localization/LANG_StdItemsTxtStats.txt|table=StdItemsTxt|id=6|field=BonusStat",
     'msgstr "행운"', 'msgstr "운"'),
    ("mmmerge/Text localization/LANG_StdItemsTxtStats.txt|table=StdItemsTxt|id=9|field=BonusStat",
     'msgstr "방어도"', 'msgstr "방어력"'),

    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=677|field=<default>",
     'msgstr "네크로맨서"', 'msgstr "강령술사"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=114|field=<default>",
     'msgstr "도적"', 'msgstr "로그"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=3|field=<default>",
     'msgstr "스파이"', 'msgstr "첩자"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=679|field=<default>",
     'msgstr "클레릭"', 'msgstr "성직자"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=681|field=<default>",
     'msgstr "나이트"', 'msgstr "기사"'),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=686|field=<default>",
     'msgstr "미노타우로스 로드"', 'msgstr "미노타우로스 군주"'),
]

for item_id in (733, 734, 735, 736, 737, 738, 739, 740, 743):
    FIXES.append((
        f"mmmerge/Text localization/LANG_ItemsTxt.txt|id={item_id}|field=NotIdentifiedName",
        'msgstr "일지 조각"',
        'msgstr "일기 조각"',
    ))


def main() -> None:
    if len(FIXES) != 27:
        raise SystemExit(f"internal error: expected 27 fixes, got {len(FIXES)}")

    original = PO.read_text(encoding="utf-8")
    parts = re.split(r"(\n\n+)", original)
    changed = 0

    for ctx, old, new in FIXES:
        matches = [
            i for i in range(0, len(parts), 2)
            if ctx in parts[i]
        ]
        if len(matches) != 1:
            raise SystemExit(f"{ctx}: expected one PO block, found {len(matches)}")

        idx = matches[0]
        block = parts[idx]
        old_count = block.count(old)
        new_count = block.count(new)

        if old_count == 1:
            parts[idx] = block.replace(old, new, 1)
            changed += 1
        elif old_count == 0 and new_count >= 1:
            pass
        else:
            raise SystemExit(
                f"{ctx}: expected one old value {old!r}; "
                f"old_count={old_count}, new_count={new_count}"
            )

    updated = "".join(parts)
    if updated != original:
        PO.write_text(updated, encoding="utf-8", newline="")

    # Verify all targets.
    for ctx, _old, new in FIXES:
        matches = [parts[i] for i in range(0, len(parts), 2) if ctx in parts[i]]
        if len(matches) != 1 or new not in matches[0]:
            raise SystemExit(f"verification failed for {ctx}: {new}")

    print(f"terminology audit pass 2: {changed} corrections")


if __name__ == "__main__":
    main()
