#!/usr/bin/env python3
"""Apply terminology consistency fixes from player report 66207.

The canonical Korean catalog (translations/ko/mmmerge.po) owns the player-facing
text.  Every edit here is scoped to one exact PO context so that generic words
such as 용, 체력, 속도, 불, and 공기 are not changed in unrelated prose.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
PO = ROOT / "translations" / "ko" / "mmmerge.po"


def sel(source: str, key: str) -> tuple[str, str]:
    return source, key


FIXES: list[tuple[tuple[str, ...], str, str]] = [
    (sel("Global.txt", "|table=GlobalTxt|id=277|field=<default>"), 'msgstr "메이스"', 'msgstr "철퇴"'),
    (sel("Skilldes.txt", "|table=SkillNames|id=6|field=<default>"), 'msgstr "메이스"', 'msgstr "철퇴"'),
    (sel("Skilldes.txt", "|table=SkillDescriptions|id=6|field=<default>"), 'msgstr "메이스 무기 숙련도입니다."', 'msgstr "철퇴 무기 숙련도입니다."'),

    (sel("LANG_ItemsTxt.txt", "|id=9|field=Notes"), "바로 용을 처치", "바로 드래곤을 처치"),
    (sel("LANG_ItemsTxt.txt", "|id=45|field=Notes"), "가장 오래된 용에게조차", "가장 오래된 드래곤에게조차"),

    (sel("LANG_StdItemsTxtNames.txt", "|id=5|field=NameAdd"), 'msgstr "[속도]"', 'msgstr "[민첩성]"'),
    (sel("LANG_StdItemsTxtStats.txt", "|id=3|field=BonusStat"), 'msgstr "체력"', 'msgstr "인내력"'),
    (sel("LANG_StdItemsTxtStats.txt", "|id=5|field=BonusStat"), 'msgstr "속도"', 'msgstr "민첩성"'),
    (sel("LANG_SpcItemsTxtStats.txt", "|id=42|field=BonusStat"), " 체력, 방어도 및 생명력 +10.", " 인내력, 방어도 및 생명력 +10."),
    (sel("LANG_SpcItemsTxtStats.txt", "|id=44|field=BonusStat"), " 속도와 정확도 +5.", " 민첩성과 정확도 +5."),
    (sel("LANG_SpcItemsTxtStats.txt", "|id=50|field=BonusStat"), " 주문력, 속도 및 지능 +10.", " 주문력, 민첩성 및 지능 +10."),
    (sel("LANG_SpcItemsTxtStats.txt", "|id=51|field=BonusStat"), " 체력과 정확도 +10.", " 인내력과 정확도 +10."),

    (sel("LANG_SpcItemsTxtNames.txt", "|id=29|field=NameAdd"), 'msgstr "[불 마법]"', 'msgstr "[화염 마법]"'),
]

for item_id in range(128, 134):
    FIXES.append((sel("LANG_2DEvents.txt", f"|id={item_id}|field=Name"), "불 마법", "화염 마법"))
for item_id in range(134, 140):
    FIXES.append((sel("LANG_2DEvents.txt", f"|id={item_id}|field=Name"), "공기 마법", "대기 마법"))

for topic_id in (336, 337, 338, 986, 987, 988, 1537, 1538):
    FIXES.append((sel("LANG_NPCTopic.txt", f"|id={topic_id}|field=<default>"), "불 마법", "화염 마법"))
for topic_id in (339, 340, 341, 989, 990, 991, 1539, 1540):
    FIXES.append((sel("LANG_NPCTopic.txt", f"|id={topic_id}|field=<default>"), "공기 마법", "대기 마법"))
for topic_id in (1154, 1704):
    FIXES.append((sel("LANG_NPCTopic.txt", f"|id={topic_id}|field=<default>"), "불 길드 가입", "화염 길드 가입"))
for topic_id in (1152, 1702):
    FIXES.append((sel("LANG_NPCTopic.txt", f"|id={topic_id}|field=<default>"), "공기 길드 가입", "대기 길드 가입"))

FIXES.extend([
    (sel("LANG_ItemsTxt.txt", "|id=1322|field=Notes"), "석화 상태 면역", "석화 면역"),
    (sel("LANG_ItemsTxt.txt", "|id=522|field=Notes"), "모든 마법 저항력 +10", "모든 저항력 +10"),
    (sel("LANG_ItemsTxt.txt", "|id=182|field=Name"), 'msgstr "황옥"', 'msgstr "토파즈"'),
    (sel("LANG_ItemsTxt.txt", "|id=989|field=Name"), 'msgstr "황옥"', 'msgstr "토파즈"'),
    (sel("LANG_ItemsTxt.txt", "|id=996|field=Name"), 'msgstr "노란 황옥"', 'msgstr "노란 토파즈"'),
    (sel("LANG_ItemsTxt.txt", "|id=2058|field=Name"), 'msgstr "황옥"', 'msgstr "토파즈"'),
    (sel("LANG_ItemsTxt.txt", "|id=2062|field=Name"), 'msgstr "보라색 황옥"', 'msgstr "보라색 토파즈"'),
])


def main() -> None:
    if len(FIXES) != 52:
        raise SystemExit(f"internal error: expected 52 scoped fixes, got {len(FIXES)}")

    original = PO.read_text(encoding="utf-8")
    parts = re.split(r"(\n\n+)", original)
    changed = 0

    for selectors, old, new in FIXES:
        matches = [
            i for i in range(0, len(parts), 2)
            if all(marker in parts[i] for marker in selectors)
        ]
        if len(matches) != 1:
            raise SystemExit(
                f"expected one PO block for {selectors!r}, found {len(matches)}"
            )

        idx = matches[0]
        block = parts[idx]
        old_count = block.count(old)
        new_count = block.count(new)

        if old_count == 1:
            parts[idx] = block.replace(old, new, 1)
            changed += 1
        elif old_count == 0 and new_count >= 1:
            # Idempotent: already fixed.
            pass
        else:
            raise SystemExit(
                f"{selectors!r}: expected one old value {old!r}; "
                f"old_count={old_count}, new_count={new_count}"
            )

    updated = "".join(parts)
    if updated != original:
        PO.write_text(updated, encoding="utf-8", newline="")

    # Final verification: every target must contain its corrected wording.
    for selectors, _old, new in FIXES:
        matches = [
            parts[i] for i in range(0, len(parts), 2)
            if all(marker in parts[i] for marker in selectors)
        ]
        if len(matches) != 1 or new not in matches[0]:
            raise SystemExit(f"verification failed for {selectors!r}: {new!r}")

    print(f"report 66207 terminology fixes: {changed} corrections")


if __name__ == "__main__":
    main()
