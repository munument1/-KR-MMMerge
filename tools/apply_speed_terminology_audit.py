#!/usr/bin/env python3
"""Normalize Speed stat terminology without touching literal movement/attack speed prose."""
from __future__ import annotations

import pathlib
import sys
import polib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
PO = ROOT / "translations" / "ko" / "mmmerge.po"

# (msgctxt, expected msgid, old msgstr, new msgstr)
FIXES: list[tuple[str, str, str, str]] = [
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=51|field=<default>",
     "Speed Boost (White) = Orange + Red and Orange Layered",
     "속도 강화 (흰색) = 주황 + 빨강·주황 층상 물약",
     "민첩성 강화 (흰색) = 주황 + 빨강·주황 층상 물약"),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=680|field=<default>",
     "Essence of Speed = Cure Insanity + Harden Item",
     "속도의 정수 = 광기 치료 + 아이템 강화",
     "민첩성의 정수 = 광기 치료 + 아이템 강화"),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=686|field=<default>",
     "Potion of the Gods = Essense of Might + Harden item or Essence of Intellect + Stoneskin or Essence of Personality + Recharge item or Essence of Endurance + Haste or Essence of Accuracy + Shield or Essence of Speed + Heroism.",
     "신들의 물약 = 힘의 정수 + 아이템 강화 또는 지력의 정수 + 돌가죽 또는 인격의 정수 + 아이템 충전 또는 체력의 정수 + 신속 또는 정확도의 정수 + 방패 또는 속도의 정수 + 영웅심.",
     "신들의 물약 = 힘의 정수 + 아이템 강화 또는 지력의 정수 + 돌가죽 또는 인격의 정수 + 아이템 충전 또는 체력의 정수 + 신속 또는 정확도의 정수 + 방패 또는 민첩성의 정수 + 영웅심."),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=80|field=<default>",
     "Pure Speed (Black) = Purple Potion + Speed Boost (White)",
     "순수한 속도 (검은색) = 보라색 물약 + 속도 강화 (흰색)",
     "순수한 민첩성 (검은색) = 보라색 물약 + 민첩성 강화 (흰색)"),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=232|field=<default>",
     "Well on the Island of Regna gives a permanent Speed bonus up to a Speed of 16.",
     "레그나 섬에 있는 우물에서 속도가 16 미만일 때 영구적으로 증가.",
     "레그나 섬에 있는 우물에서 민첩성이 16 미만일 때 영구적으로 증가."),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=283|field=<default>",
     "2 points of permanent Speed from the well in the western section of Tidewater in Tatalia.",
     "타이드워터 · 타탈리아 서부에 있는 우물에서 속도 영구적으로 2 증가.",
     "타이드워터 · 타탈리아 서부에 있는 우물에서 민첩성 영구적으로 2 증가."),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=408|field=<default>",
     "10 Points of temporary speed from the east fountain at Castle Ironfist.",
     "아이언피스트 성 동쪽에 있는 분수에서 일시적으로 속도 10 증가.",
     "아이언피스트 성 동쪽에 있는 분수에서 일시적으로 민첩성 10 증가."),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=416|field=<default>",
     "2 Points of permanent speed from the south fountain west of Silver Cove.",
     "실버 코브 서쪽의 남쪽 분수에서 속도가 영구적으로 2 증가.",
     "실버 코브 서쪽의 남쪽 분수에서 민첩성이 영구적으로 2 증가."),
    ("mmmerge/Text localization/LANG_AutonoteTxt.txt|table=AutonoteTxt|id=420|field=<default>",
     "20 Points of temporary speed and accuracy from the west fountain in Icewind Lake.",
     "아이스윈드 호수 서쪽에 있는 분수에서 일시적으로 속도와 정확도 20 증가.",
     "아이스윈드 호수 서쪽에 있는 분수에서 일시적으로 민첩성과 정확도 20 증가."),

    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1439|field=Notes",
     "(+100 Speed, +50 Accuracy, +50 Air Resistance, Regenerate SP and HP over time, and Feather Falling) Rumored to be the footwear of a god, the winged sandals confer enormous power on the wearer.",
     "(+100 속도, +50 정확도, +50 공기 저항, 시간에 따른 주문력과 생명력 회복, 깃털 낙하) 신의 신발이라는 소문이 있는 이 날개 달린 샌들은 착용자에게 엄청난 힘을 부여합니다.",
     "(민첩성 +100, 정확도 +50, 공기 저항 +50, 시간에 따른 주문력과 생명력 회복, 깃털 낙하) 신의 신발이라는 소문이 있는 이 날개 달린 샌들은 착용자에게 엄청난 힘을 부여합니다."),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1548|field=Name",
     "Pure Speed Recipe", "순수한 속도 제조법", "순수한 민첩성 제조법"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1548|field=NotIdentifiedName",
     "Pure Speed Recipe", "순수한 속도 제조법", "순수한 민첩성 제조법"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1556|field=Name",
     "Speed Boost Recipe", "속도 강화 제조법", "민첩성 강화 제조법"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1556|field=NotIdentifiedName",
     "Speed Boost Recipe", "속도 강화 제조법", "민첩성 강화 제조법"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1785|field=Notes",
     "Once only:  Adds 15 to Personality and subtracts 5 from Speed permanently.  To drink, pick the potion up and right-click over a character's portrait.  To mix, pick the potion up and right-click over another potion.",
     "1회 사용 가능: 인격을 15만큼 증가시키고 속도를 5만큼 영구적으로 감소시킵니다. 마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약을 오른쪽 클릭하십시오.",
     "1회 사용 가능: 인격을 15만큼 증가시키고 민첩성을 5만큼 영구적으로 감소시킵니다. 마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약을 오른쪽 클릭하십시오."),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1788|field=Name",
     "Essence of Speed", "속도의 정수", "민첩성의 정수"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=1788|field=Notes",
     "Once only:  Adds 15 to Speed and subtracts 5 from Personality permanently.  To drink, pick the potion up and right-click over a character's portrait.  To mix, pick the potion up and right-click over another potion.",
     "1회 사용 가능: 이동 속도를 15 증가시키고 인격을 5 감소시킵니다(영구 효과). 마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약을 오른쪽 클릭하십시오.",
     "1회 사용 가능: 민첩성을 15 증가시키고 인격을 5 감소시킵니다(영구 효과). 마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약을 오른쪽 클릭하십시오."),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=244|field=Name",
     "Speed Boost", "속도 강화", "민첩성 강화"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=244|field=Notes",
     "Increases temporary Speed by three times the strength of the potion for 30 minutes per point of strength of the potion.  (To drink, pick the potion up and right-click over a character's portrait.  To mix two potions, pick up one and right-click it over the other.)",
     "물약 효능 1포인트당 30분 동안 물약 효능의 3배만큼 이동 속도를 일시적으로 증가시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 물약 두 개를 섞으려면 물약 하나를 집어 들고 다른 물약 위에 오른쪽 클릭하십시오.)",
     "물약 효능 1포인트당 30분 동안 물약 효능의 3배만큼 민첩성을 일시적으로 증가시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 물약 두 개를 섞으려면 물약 하나를 집어 들고 다른 물약 위에 오른쪽 클릭하십시오.)"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=265|field=Name",
     "Pure Speed", "순수한 속도", "순수한 민첩성"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=265|field=Notes",
     "Adds 50 to permanent Speed.  (To drink, pick the potion up and right-click over a character's portrait.  To mix, pick the potion up and right-click over another potion.)",
     "이동 속도를 영구적으로 50 증가시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약을 오른쪽 클릭하십시오.)",
     "민첩성을 영구적으로 50 증가시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약을 오른쪽 클릭하십시오.)"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=274|field=Notes",
     "Permanently raises Personality by 15 while reducing Speed by 5.  (To drink, pick the potion up and right-click over a character's portrait.  To mix, pick the potion up and right-click over another potion.)",
     "인격 수치를 영구적으로 15만큼 올리고 속도를 5만큼 감소시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약 위에 오른쪽 클릭하십시오.)",
     "인격 수치를 영구적으로 15만큼 올리고 민첩성을 5만큼 감소시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약 위에 오른쪽 클릭하십시오.)"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=277|field=Name",
     "Essence of Speed", "속도의 정수", "민첩성의 정수"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=277|field=Notes",
     "Permanently raises Speed by 15 while reducing Personality by 5.  (To drink, pick the potion up and right-click over a character's portrait.  To mix, pick the potion up and right-click over another potion.)",
     "이동 속도를 15만큼 영구적으로 증가시키고 인격을 5만큼 감소시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약 위에 오른쪽 클릭하십시오.)",
     "민첩성을 15만큼 영구적으로 증가시키고 인격을 5만큼 감소시킵니다. (마시려면 물약을 집어 들고 캐릭터 초상화를 오른쪽 클릭하십시오. 섞으려면 물약을 집어 들고 다른 물약 위에 오른쪽 클릭하십시오.)"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=706|field=Name",
     "Pure Speed Recipe", "순수한 속도 제조법", "순수한 민첩성 제조법"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=714|field=Name",
     "Speed Boost Recipe", "속도 강화 제조법", "민첩성 강화 제조법"),
    ("mmmerge/Text localization/LANG_ItemsTxt.txt|id=768|field=Name",
     "Essence of Speed recipe", "속도의 정수 제조법", "민첩성의 정수 제조법"),

    ("mmmerge/Text localization/LANG_MessageScrolls.txt|table=MessageScrolls|id=128|field=<default>",
     " The Black Potion of Pure Speed could be the answer for a party who just doesn't get the jump on the monsters.  The addition to permanent speed could be just what is needed to allow you recover and act before the monsters do.  You can never be too quick. To mix this potion you need the correct combination of four of any red reagent type plus two of any blue reagent type and one of the yellow reagents.  ",
     " 검은 순수한 속도 물약은 속도를 영구적으로 높여 더 빠르게 회복하고 몬스터보다 먼저 행동할 수 있게 합니다. 이 물약을 조합하려면 빨간색 시약 네 개, 파란색 시약 두 개, 노란색 시약 한 개를 올바르게 조합해야 합니다.  ",
     " 검은 순수한 민첩성 물약은 민첩성을 영구적으로 높여 더 빠르게 회복하고 몬스터보다 먼저 행동할 수 있게 합니다. 이 물약을 조합하려면 빨간색 시약 네 개, 파란색 시약 두 개, 노란색 시약 한 개를 올바르게 조합해야 합니다.  "),
    ("mmmerge/Text localization/LANG_MessageScrolls.txt|table=MessageScrolls|id=136|field=<default>",
     " The White Potion of Speed Boost temporarily boosts your speed just when you need it. To mix this potion you need the correct combination of three of any red reagent type and two of any yellow reagents.",
     " 흰 속도 증폭 물약은 필요할 때 속도를 일시적으로 높여줍니다. 이 물약을 조합하려면 빨간색 시약 세 개와 노란색 시약 두 개가 필요합니다.",
     " 흰 민첩성 강화 물약은 필요할 때 민첩성을 일시적으로 높여줍니다. 이 물약을 조합하려면 빨간색 시약 세 개와 노란색 시약 두 개가 필요합니다."),
    ("mmmerge/Text localization/LANG_MessageScrolls.txt|table=MessageScrolls|id=14|field=<default>",
     " The White Potion of Speed Boost temporarily boosts your speed just when you need it. To mix this potion you need the correct combination of three of any red reagent type and two of any yellow reagents.",
     " 흰 속도 증폭 물약은 필요할 때 속도를 일시적으로 높여줍니다. 이 물약을 조합하려면 빨간색 시약 세 개와 노란색 시약 두 개를 올바르게 조합해야 합니다.",
     " 흰 민첩성 강화 물약은 필요할 때 민첩성을 일시적으로 높여줍니다. 이 물약을 조합하려면 빨간색 시약 세 개와 노란색 시약 두 개를 올바르게 조합해야 합니다."),
    ("mmmerge/Text localization/LANG_MessageScrolls.txt|table=MessageScrolls|id=68|field=<default>",
     "Essence of Speed increases a character’s Speed by 15, while subtracting 5 from his Personality. This potion requires six reagents to mix, four of any one color supplemented by one from each of the remaining colors.",
     "속도의 정수는 캐릭터의 속도를 15 높이는 대신 인격을 5 낮춥니다. 이 물약을 조합하려면 한 색상 시약 네 개와 나머지 두 색상 시약을 각각 한 개씩 넣어 총 여섯 개가 필요합니다.",
     "민첩성의 정수는 캐릭터의 민첩성을 15 높이는 대신 인격을 5 낮춥니다. 이 물약을 조합하려면 한 색상 시약 네 개와 나머지 두 색상 시약을 각각 한 개씩 넣어 총 여섯 개가 필요합니다."),
    ("mmmerge/Text localization/LANG_MessageScrolls.txt|table=MessageScrolls|id=6|field=<default>",
     " The Black Potion of Pure Speed could be the answer for a party who just doesn't get the jump on the monsters.  The addition to permanent speed could be just what is needed to allow you to recover and act before the monsters do.  You can never be too quick. To mix this potion you need the correct combination of four of any red reagent type, plus one of any blue reagent type and two of the yellow reagents.  ",
     " 검은 순수한 속도 물약은 몬스터보다 먼저 행동하지 못하는 일행에게 해답이 될 수 있습니다. 속도를 영구적으로 높이면 더 빠르게 회복하고 몬스터보다 먼저 행동할 수 있습니다. 아무리 빨라도 지나치지 않습니다. 이 물약을 조합하려면 빨간색 시약 네 개, 파란색 시약 한 개, 노란색 시약 두 개를 올바르게 조합해야 합니다.  ",
     " 검은 순수한 민첩성 물약은 몬스터보다 먼저 행동하지 못하는 일행에게 해답이 될 수 있습니다. 민첩성을 영구적으로 높이면 더 빠르게 회복하고 몬스터보다 먼저 행동할 수 있습니다. 아무리 빨라도 지나치지 않습니다. 이 물약을 조합하려면 빨간색 시약 네 개, 파란색 시약 한 개, 노란색 시약 두 개를 올바르게 조합해야 합니다.  "),

    ("mmmerge/Text localization/LANG_NPCText.txt|table=NPCText|id=1492|field=<default>",
     "+2 Speed permanent", "속도 영구 +2", "민첩성 영구 +2"),
    ("mmmerge/Text localization/LANG_NPCText.txt|table=NPCText|id=719|field=<default>",
     "+2 Speed permanent", "속도 영구 +2", "민첩성 영구 +2"),
    ("mmmerge/Text localization/LANG_NPCText.txt|table=NPCText|id=624|field=<default>",
     "Perhaps you can bring me the basic ingredients for a Potion of Pure speed?\nWith them I can make this incredible potion and finish my studies in alchemy!\nI will reward you well for your assistance!",
     "순수한 속도의 물약에 필요한 기본 재료를 가져다주시겠습니까?\n재료만 있으면 이 놀라운 물약을 만들어 연금술 연구를 마칠 수 있습니다!\n도와주시면 후하게 보상하겠습니다!",
     "순수한 민첩성 물약에 필요한 기본 재료를 가져다주시겠습니까?\n재료만 있으면 이 놀라운 물약을 만들어 연금술 연구를 마칠 수 있습니다!\n도와주시면 후하게 보상하겠습니다!"),
    ("mmmerge/Text localization/LANG_NPCTopic.txt|table=NPCTopic|id=179|field=<default>",
     "Potion of Pure Speed", "순수한 속도 물약", "순수한 민첩성 물약"),
    ("mmmerge/Text localization/LANG_QuestsTxt.txt|table=QuestsTxt|id=113|field=<default>",
     "Bring Thistle on the Dagger Wound Islands the basic ingredients for a potion of Pure Speed.",
     "순수한 속도 물약의 기본 재료를 대거 운드 제도의 시슬에게 가져가십시오.",
     "순수한 민첩성 물약의 기본 재료를 대거 운드 제도의 시슬에게 가져가십시오."),
]

def main() -> None:
    if len(FIXES) != 37:
        raise SystemExit(f"internal error: expected 37 fixes, got {len(FIXES)}")

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
            raise SystemExit(f"{ctx}: expected msgid {expected_msgid!r}, found {entry.msgid!r}")
        if entry.msgstr == old:
            entry.msgstr = new
            changed += 1
        elif entry.msgstr == new:
            pass
        else:
            raise SystemExit(f"{ctx}: expected {old!r} or {new!r}, found {entry.msgstr!r}")

    for ctx, expected_msgid, _old, new in FIXES:
        entry = by_context[ctx][0]
        if entry.msgid != expected_msgid or entry.msgstr != new:
            raise SystemExit(f"verification failed for {ctx}: {entry.msgid!r} / {entry.msgstr!r}")

    if changed:
        po.save(str(PO))
    print(f"speed terminology audit: {changed} corrections")

if __name__ == "__main__":
    main()
