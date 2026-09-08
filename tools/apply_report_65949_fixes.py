#!/usr/bin/env python3
"""Apply confirmed corrections from player report 65949.

The legacy translation tables are a mix of UTF-8 and CP949 and are marked
binary in git.  This script preserves each source file's encoding and line
endings.  Broad substitutions are intentionally limited to unambiguous game
terms; artifact/relic corrections use exact phrases so we don't repeat the
substring-replacement corruption reported by players.
"""

from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"


def decode_with_encoding(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def rewrite(path: pathlib.Path, replacements: list[tuple[str, str]]) -> int:
    original = path.read_bytes()
    text, encoding = decode_with_encoding(original)
    changed = 0
    for old, new in replacements:
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            changed += count
    if changed:
        path.write_bytes(text.encode(encoding))
        print(f"{path.relative_to(root)}: {changed} replacements ({encoding})")
    return changed


# Safe phrase-level terminology used across localization sources.  Do not add
# short roots such as "운" here: a previous indiscriminate replacement turned
# "날카로운" into "날카로행운" and similar corruptions.
SAFE_ALL = [
    ("신체 마법", "육체 마법"),
    ("신체 피해", "육체 피해"),
    ("신체 저항", "육체 저항"),
    ("대기 마법", "공기 마법"),
    ("흙 마법", "대지 마법"),
    ("일시적 행운", "일시적 운"),
    ("일시적 속도", "일시적 민첩성"),
    ("날카로행운", "날카로운"),
    ("아름다행운", "아름다운"),
    ("가까행운", "가까운"),
    ("갑작스러행운", "갑작스러운"),
    ("기행운", "기운"),
    ("불행운하게", "불운하게"),
    ("불행운의", "불운의"),
]

# Mechanical stat notation.  These are limited to item/stat tables so normal
# prose such as "체력 회복" or "빠른 속도" isn't changed accidentally.
MECHANICAL = [
    ("이동 속도 +", "민첩성 +"),
    ("이동 속도 -", "민첩성 -"),
    ("지력 +", "지능 +"),
    ("지력 -", "지능 -"),
    ("체력 +", "인내력 +"),
    ("체력 -", "인내력 -"),
    ("속도 +", "민첩성 +"),
    ("속도 -", "민첩성 -"),
    ("행운 +", "운 +"),
    ("행운 -", "운 -"),
    ("화염 저항력 +", "화염 저항 +"),
    ("화염 저항력 -", "화염 저항 -"),
    ("공기 저항력 +", "공기 저항 +"),
    ("공기 저항력 -", "공기 저항 -"),
    ("물 저항력 +", "물 저항 +"),
    ("물 저항력 -", "물 저항 -"),
    ("대지 저항력 +", "대지 저항 +"),
    ("대지 저항력 -", "대지 저항 -"),
    ("정신 저항력 +", "정신 저항 +"),
    ("정신 저항력 -", "정신 저항 -"),
    ("육체 저항력 +", "육체 저항 +"),
    ("육체 저항력 -", "육체 저항 -"),
    ("원소 저항력 +", "원소 저항 +"),
    ("원소 저항력 -", "원소 저항 -"),
]

ITEM_FIXES = [
    # Canonical terminology and report-confirmed substring corruption.
    ("파이널리티", "종결"),
    ("구울스베인", "구울베인"),
    ("아이언 페더", "철깃털"),
    ("아르테무스", "아르테미스"),
    ("샤렐레", "샤렐"),
    ("시트린", "황수정"),
    ("타이탄의 벨트", "타이탄의 허리띠"),
    ("마쉬", "매시"),
    ("아먹", "어먹"),
    ("스플리터", "파쇄자"),
    ("울리세스", "율리시스"),
    ("다투라", "흰독말풀"),
    ("데빌 체액 약병", "악마의 피 약병"),
    ("용거북 송곳니", "드래곤 터틀의 송곳니"),

    # Exact item-effect corrections supported by the English Merge source.
    ("(+모든 능력치 +10,", "(모든 능력치 +10,"),
    ("(폭발적인 충격, 화염 저항 +50)", "(명중 시 폭발, 화염 저항 +50)"),
    ("(수중 호흡, +70 물 저항, -70 화염 저항)", "(수중 호흡, 물 저항 +70, 화염 저항 -70)"),
    ("(물의 속성, 연금술 기술 +5, 지력 +40, 체력 -20)", "(물 마법, 연금술 기술 +5, 지능 +40, 인내력 -20)"),
    ("(물 마법 사용 시 속도 +40)", "(민첩성 +40, 물 마법)"),
    ("(정신 마법, 어둠 마법에 관하여)", "(정신 마법, 어둠 마법)"),
    ("(무장 해제 기술 +5, 독 피해 8점", "(함정 해제 기술 +5, 독 피해 8점"),
    ("살을 돌로 변하게 하는 효과 면역, 방패 사용 시 행운 +20, 이동 속도 -20",
     "석화 면역, 원거리 공격 피해 절반, 운 +20, 민첩성 -20"),
    ("(특수 능력: 힘)", "(특수 능력: 명중한 적을 밀쳐냄)"),
    ("(특수 능력: 신속, 학살)", "(특수 능력: 공격 회복 속도 증가, 명중 시 폭발)"),
    ("(특수 능력: 체력 +30, 부상 회복력, 체력 재생)",
     "(특수 능력: 인내력 +30, 피격 회복 속도 증가, 생명력 재생)"),
    ("(특수 능력: 독 피해 +20, 행운 +20, 도둑질 +20, 재생력 +10)",
     "(특수 능력: 독 피해 +20, 운 +20, 도둑질 +20, 생명력 지속 감소)"),
    ("(화염 피해 10-20, 느림, 이동 속도 -20)",
     "(화염 피해 10-20, 공격 회복 속도 감소, 민첩성 -20)"),

    # Swift is an attack-recovery modifier, not movement speed.
    (", 신속,", ", 공격 회복 속도 증가,"),
    ("(신속,", "(공격 회복 속도 증가,"),
    (", 신속)", ", 공격 회복 속도 증가)"),

    # Exact prose corrections from the report / English source.
    ("레그나 \"제국\" 건국 당시 하렉 1세의 명령으로 건설된 샤렐은 그의 아내인 샤렐 왕비의 이름을 따서 명명되었습니다. 이 성은 서기 590년 하렉 1세가 독살당한 후 혼란기에 레그나의 유일한 에라티아 전초기지에 남겨졌습니다.",
     "레그나 \"제국\" 건국 당시 하렉 1세의 명령으로 제작된 샤렐은 그의 아내인 샤렐 왕비의 이름을 따서 명명되었습니다. 이 창은 서기 590년 하렉 1세가 독살당한 후 혼란기에 레그나의 유일한 에라시아 전초기지에 남겨졌습니다."),
    ("이 검은 여전히 마법처럼 날카로운 날과 모든 본래의 힘을 간직하고 있습니다.",
     "이 검의 날은 여전히 마법처럼 날카롭고, 본래의 힘도 모두 간직하고 있습니다."),
    ("전투 중 착용자가 부딪히는 것을 막아줍니다.",
     "전투 중 공격을 받아 휘청이는 시간을 줄여줍니다."),
    ("정령과 연결되어 있어 사용자는 영혼 마법에 취약하지만",
     "원소와 연결되어 있어 사용자는 원소 마법에 취약하지만"),
    ("이 갑옷을 착용하는 동안 얼굴은", "이 목걸이를 착용하는 동안 얼굴은"),
    ("활 숙련도 +5", "활 기술 +5"),
    ("체력을 회복합니다.", "생명력을 회복합니다."),

    # Reagent instruction/style consistency.
    ("(사용하려면, 약초를 줍고 빈 물약 병을 오른쪽 클릭하십시오.)",
     "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"),
    ("(사용하려면 약초를 줍고 빈 물약병 위에 마우스 오른쪽 버튼을 클릭하세요.)",
     "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"),
    ("(사용하려면 약초를 줍고 빈 물약 병 위에 마우스 오른쪽 버튼을 클릭하세요.)",
     "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"),
    ("(사용하려면, 허브를 채취한 후 빈 물약 병 위에 마우스 오른쪽 버튼을 클릭하세요.)",
     "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"),
    ("(사용하려면 송곳니를 주워 빈 물약 병 위에 마우스 오른쪽 버튼을 클릭하세요.)",
     "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"),
    ("\t약초\t", "\t시약\t"),

    # Gem-description tone consistency.
    ("보석으로서의 품질은 좋지만, 마법적인 효능은 없으니 팔아버리는 게 나을지도 몰라요.",
     "보석으로서의 품질은 좋지만 마법적인 효능은 없으니 팔아버리는 편이 좋겠습니다."),
    ("보석으로서의 품질은 좋지만 마법적인 효능은 없으니, 차라리 파시는 게 나을지도 모르겠네요.",
     "보석으로서의 품질은 좋지만 마법적인 효능은 없으니 팔아버리는 편이 좋겠습니다."),
    ("보석으로서의 품질은 좋지만 마법적인 효능은 없으니 팔아버리는 게 나을지도 모릅니다.",
     "보석으로서의 품질은 좋지만 마법적인 효능은 없으니 팔아버리는 편이 좋겠습니다."),
]

# GlobalTxt IDs are player-facing canonical labels.  Exact row fragments avoid
# touching normal prose.
GLOBAL_FIXES = [
    ("\t1\t\t적중률", "\t1\t\t정확도"),
    ("\t75\t\t체력", "\t75\t\t인내력"),
    ("\t211\t\t속도", "\t211\t\t민첩성"),
    ("\t248\t\t일시적 행운", "\t248\t\t일시적 운"),
    ("\t258\t\t일시적 속도", "\t258\t\t일시적 민첩성"),
    ("\t284\t\t대기 마법", "\t284\t\t공기 마법"),
    ("\t291\t\t신체 마법", "\t291\t\t육체 마법"),
]

STATS_FIXES = [
    ("지능은", "지능은"),
    ("체력은 캐릭터의 육체적 강인함과 내구력을 나타냅니다. 체력이 높을수록 생명력이 증가합니다.",
     "인내력은 캐릭터의 육체적 강인함과 내구력을 나타냅니다. 인내력이 높을수록 생명력이 증가합니다."),
    ("적중률은 캐릭터의 정확성과 손과 눈의 협응 능력을 나타냅니다. 적중률이 높을수록 전투에서 몬스터를 더 자주 명중시킵니다.",
     "정확도는 캐릭터의 조준 능력과 손과 눈의 협응 능력을 나타냅니다. 정확도가 높을수록 전투에서 몬스터를 더 자주 명중시킵니다."),
    ("속도는 캐릭터가 얼마나 민첩한지를 나타냅니다. 속도가 높을수록 방어력과 공격 후 회복 속도가 증가합니다.",
     "민첩성은 캐릭터가 얼마나 빠르고 민첩하게 움직이는지를 나타냅니다. 민첩성이 높을수록 방어력과 공격 후 회복 속도가 증가합니다."),
    ("스킬, 주문, 적중률 등", "스킬, 주문, 정확도 등"),
    ("장착한 활로 몬스터를", "장착한 원거리 무기로 몬스터를"),
    ("장착한 활로 가하는", "장착한 원거리 무기로 가하는"),
    ("신체 저항은 신체 계열 공격으로", "육체 저항은 육체 계열 공격으로"),
    ("신체 피해를", "육체 피해를"),
]


def main() -> None:
    total = 0

    for path in sorted(loc.glob("KO_*.txt")):
        total += rewrite(path, SAFE_ALL)

    item_related = [
        loc / "KO_ItemsTxt.txt",
        loc / "KO_RuntimeOverrides.txt",
        loc / "KO_SpcItemsTxtStats.txt",
        loc / "KO_StdItemsTxtStats.txt",
    ]
    for path in item_related:
        total += rewrite(path, MECHANICAL)

    total += rewrite(loc / "KO_ItemsTxt.txt", ITEM_FIXES)
    total += rewrite(loc / "KO_GlobalTxt.txt", GLOBAL_FIXES)
    total += rewrite(loc / "KO_StatsDescriptions.tsv", STATS_FIXES)

    # mm8lang.ini is consumed by the GrayFace/MMExtension localization layer.
    # Runtime Korean text must be CP949/EUC-KR for the native DBCS renderer.
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
