#!/usr/bin/env python3
"""Apply high-confidence terminology consistency fixes found by PO-wide audit pass 3.

Only exact msgctxt/msgid pairs are touched. Context-sensitive words, person
names, ambiguous transliterations, and deliberately generic unidentified names
are intentionally excluded.
"""
from __future__ import annotations

import pathlib
import sys

import polib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
PO = ROOT / "translations" / "ko" / "mmmerge.po"

# (msgctxt, expected English msgid, old Korean, canonical Korean)
FIXES: list[tuple[str, str, str, str]] = [
    # Class / creature terminology. These canonical forms already agree across
    # ClassNames, NPCTopic, and/or Monsters; only outliers are changed.
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=119|field=<default>",
     "Master Archer", "궁술 마스터", "명궁"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=254|field=<default>",
     "Cavalier", "기사", "중기병"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=26|field=<default>",
     "Initiate", "수련생", "수련자"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=48|field=<default>",
     "Warlock", "워록", "흑마법사"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=684|field=<default>",
     "War Troll", "워 트롤", "전투 트롤"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=692|field=<default>",
     "Great Wyrm", "그레이트 웜", "고룡"),
    ("mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=2|field=<default>",
     "Black Knight", "블랙 나이트", "흑기사"),
    # ClassNames has Black Knight / Champion translations swapped.
    ("mmmerge/Text localization/LANG_ClassNames.txt|table=ClassNames|id=18|field=<default>",
     "Black Knight", "챔피언", "흑기사"),
    ("mmmerge/Text localization/LANG_ClassNames.txt|table=ClassNames|id=19|field=<default>",
     "Champion", "흑기사", "챔피언"),

    # Spell name: all spell/item name occurrences already use 로이드의 봉화.
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=729|field=<default>",
     "Lloyd's Beacon", "로이드의 표식", "로이드의 봉화"),

    # Named places / businesses.
    ("mmmerge/Text localization/LANG_2DEvents.txt|id=361|field=Name",
     "Dragon Hunter Camp", "드래곤 사냥꾼야영지", "드래곤 사냥꾼 야영지"),
    ("mmmerge/Text localization/LANG_2DEvents.txt|id=325|field=Name",
     "New Sorpigal Temple", "뉴 소르피갈신전", "뉴 소르피갈 신전"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=126|field=<default>",
     "Buccaneers' Lair", "해적의 소굴", "해적단의 소굴"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=151|field=<default>",
     "Buccaneers' Lair", "해적의 소굴", "해적단의 소굴"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=127|field=<default>",
     "Protection Services", "보호 서비스", "방호 서비스"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=152|field=<default>",
     "Protection Services", "보호 서비스", "방호 서비스"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=130|field=<default>",
     "Duelists' Edge", "결투자의 칼끝", "결투자의 칼날"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=155|field=<default>",
     "Duelists' Edge", "결투자의 칼끝", "결투자의 칼날"),
    ("mmmerge/10LocLANG.T/OUT03.STR|string=46",
     "Ogre Raiding Fort", "오우거 요새", "오우거 약탈 요새"),
    ("mmmerge/10LocLANG.T/OUTC2.STR|string=28",
     "Guild of Mind", "정신의 길드", "정신 마법 길드"),
    ("mmmerge/10LocLANG.T/7out05.STR|string=25",
     "Hall of the Pit", "구덩이의 회관", "구덩이의 전당"),
    ("mmmerge/10LocLANG.T/out14.STR|string=27",
     "Hall under the Hill", "언덕 아래의 회관", "언덕 아래 전당"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=382|field=<default>",
     "The Enchanted Hauberk", "마법의 사슬 갑옷", "마법 걸린 호버크"),

    # Exact proper-name reference to an existing named inn.
    ("mmmerge/Text localization/LANG_AwardsTxt.txt|table=AwardsTxt|id=65|field=<default>",
     "Won Arcomage at Kessel's Kantina in Ravenshore.",
     "레이븐쇼어의 '케셀스 칸티나'에서 아르코메이지에 승리함",
     "레이븐쇼어의 '케셀의 칸티나'에서 아르코메이지에 승리함"),

    # Core stat terminology: all other base stats already match GlobalTxt.
    ("mmmerge/Text localization/LANG_StdItemsTxtStats.txt|table=StdItemsTxt|id=1|field=BonusStat",
     "Intellect", "지력", "지능"),

    # One pure spacing mismatch in the same NPC profession term.
    ("mmmerge/inherited/mm6/npcprof.txt|table=NPCProfessions|id=66|field=Name",
     "Trapper", "덫사냥꾼", "덫 사냥꾼"),

    # Quest / item names: use the actual item-table name in matching NPC topics.
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=1387|field=<default>",
     "Memory Crystal", "기억의 수정", "기억 수정"),
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=53|field=<default>",
     "Ebonest", "에보니스트", "에보네스트"),
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=57|field=<default>",
     "Ebonest", "에보니스트", "에보네스트"),
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=190|field=<default>",
     "Anointed Herb Potion", "기름 부은 약초 물약", "축성된 약초 물약"),
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=76|field=<default>",
     "Prophecies of the Sun", "태양의 예언서", "태양의 예언"),
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=80|field=<default>",
     "Prophecies of the Sun", "태양의 예언서", "태양의 예언"),
    ("mmmerge/Text localization/LANG_NPCNewsTopics.txt|table=NPCNewsTopics|id=589|field=<default>",
     "Widoweeps Berries", "위도우윕 열매", "위도우스위프 열매"),

    # Identical recovery-rate text in the same Spells table.
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=41|field=GrandMaster",
     "Faster recovery rate", "더 빠른 회복 속도", "회복 속도 증가"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=42|field=GrandMaster",
     "Faster recovery rate", "더 빠른 회복 속도", "회복 속도 증가"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=52|field=GrandMaster",
     "Faster recovery rate", "더 빠른 회복 속도", "회복 속도 증가"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=65|field=GrandMaster",
     "Faster recovery rate", "더 빠른 회복 속도", "회복 속도 증가"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=76|field=GrandMaster",
     "Faster recovery rate", "더 빠른 회복 속도", "회복 속도 증가"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=84|field=GrandMaster",
     "Faster recovery rate", "더 빠른 회복 속도", "회복 속도 증가"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=87|field=GrandMaster",
     "Moderate recovery rate", "보통의 회복 속도", "보통 회복 속도"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=97|field=GrandMaster",
     "Moderate recovery rate", "보통의 회복 속도", "보통 회복 속도"),
    ("mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=91|field=Master",
     "Fastest recovery rate", "가장 빠른 회복 속도", "회복 속도 매우 증가"),
]


def main() -> None:
    if len(FIXES) != 42:
        raise SystemExit(f"internal error: expected 42 fixes, got {len(FIXES)}")

    po = polib.pofile(str(PO), encoding="utf-8")
    by_context: dict[str, list[polib.POEntry]] = {}
    for entry in po:
        if entry.msgctxt:
            by_context.setdefault(entry.msgctxt, []).append(entry)

    changed = 0
    for ctx, expected_msgid, old, new in FIXES:
        matches = by_context.get(ctx, [])
        if len(matches) != 1:
            raise SystemExit(f"{ctx}: expected one PO entry, found {len(matches)}")

        entry = matches[0]
        if entry.msgid != expected_msgid:
            raise SystemExit(
                f"{ctx}: expected msgid {expected_msgid!r}, found {entry.msgid!r}"
            )

        if entry.msgstr == old:
            entry.msgstr = new
            changed += 1
        elif entry.msgstr == new:
            pass
        else:
            raise SystemExit(
                f"{ctx}: expected {old!r} or {new!r}, found {entry.msgstr!r}"
            )

    for ctx, expected_msgid, _old, new in FIXES:
        entry = by_context[ctx][0]
        if entry.msgid != expected_msgid or entry.msgstr != new:
            raise SystemExit(
                f"verification failed for {ctx}: {entry.msgid!r} / {entry.msgstr!r}"
            )

    if changed:
        po.save(str(PO))
    print(f"terminology audit pass 3: {changed} corrections")


if __name__ == "__main__":
    main()
