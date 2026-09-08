#!/usr/bin/env python3
"""Second source-backed item QA pass for player report 65949.

Every replacement is scoped to an exact item ID.  This avoids repeating the
broad substring substitutions that previously damaged Korean prose.
"""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

ROW_FIXES: dict[int, list[tuple[str, str]]] = {
    508: [("(흡혈, 독 피해 10점, 흡혈)", "(흡혈, 독 피해 10점, 뱀파이어)")],
    511: [("(방어막의 힘; 질병, 마비, 독에 면역)", "(원거리 공격 피해 절반; 질병, 마비, 독 면역)")],
    516: [("퀘스트 아이템: (정신, 육체, 마음의 전리품, 사제)", "퀘스트 아이템: (영혼 마법, 육체 마법, 정신 마법, 성직자)")],
    517: [("(+8 함정 해제, 활, 무기 숙련 기술)", "(함정 해제 기술 +8, 활 기술 +8, 무기 전문가 기술 +8)")],
    523: [("대상 이동 속도 감소", "대상 공격 회복 속도 감소")],
    530: [("(공기 마법, 불 마법, 물 마법, 대지 마법,", "(공기 마법, 화염 마법, 물 마법, 대지 마법,")],
    532: [("극도의 숙련된 사용자", "고도로 숙련된 사용자")],
    539: [("찰스 퀴호테의 개인 드래곤 사냥드래곤 창, 에보니스트는 참으로 훌륭한 무기입니다.", "찰스 퀴호테가 애용하던 드래곤 사냥용 창인 에보네스트는 참으로 훌륭한 무기입니다.")],
    1321: [("정신 및 신체 기반 공격", "정신 및 육체 계열 공격")],
    1322: [("투사체 공격 피해 절반 감소", "원거리 공격 피해 절반")],
    1323: [("(빛의 마법,", "(빛 마법,")],
    1324: [("(학습 능력 +15,", "(학습 기술 +15,")],
    1329: [
        ("(언데드 처치, 정신 마법, 육체 마법, -40 이동 속도, 선)", "(언데드 사냥, 정신 마법, 육체 마법, 민첩성 -40, 선)"),
        ("이동 속도가 약간 느리지만", "민첩성이 감소하지만"),
    ],
    1331: [("(+100 속도, +50 정확도, +50 공기 저항, 생명력 회복, 주문력 회복, 낙하 시 깃털 보호)", "(민첩성 +100, 정확도 +50, 공기 저항 +50, 생명력 회복, 주문력 회복, 깃털 낙하)")],
    1333: [
        ("(방패의 검, 엘프 사냥꾼의 검, 고블린의 검)", "(원거리 공격 피해 절반, 엘프 사냥, 고블린)"),
        ("엘프 사냥꾼의 검", "엘프베인"),
    ],
    1334: [
        ("(+15 지력, +15 인격,", "(지능 +15, 인격 +15,"),
        ("지력과 인격을", "지능과 인격을"),
    ],
    1335: [("(회복력 +15, 민첩성 +15, 정확도 +15, 엘프 특성)", "(공격 회복 속도 증가, 민첩성 +15, 정확도 +15, 엘프)")],
    1336: [
        ("(+30 화염 저항, +15 힘, +15 체력, 드워프)", "(화염 저항 +30, 힘 +15, 인내력 +15, 드워프)"),
        ("드워프의 힘과 체력을", "드워프의 힘과 인내력을"),
    ],
    1337: [("(+5 무기 숙련, +15 힘,", "(무기 전문가 기술 +5, 힘 +15,")],
    2024: [
        ("멀린은 신속의 마법이 걸려 있어", "멀린은 공격 회복 속도를 높이는 마법이 걸려 있어"),
        ("(특수 능력: 신속 및 마법력 +40)", "(특수 능력: 공격 회복 속도 증가, 주문력 +40)"),
    ],
    2028: [("(특수 능력: 보호 및 정확도 +30)", "(특수 능력: 원거리 공격 피해 절반, 정확도 +30)")],
    2034: [("'불, 공기, 물, 대지 마법'", "'화염, 공기, 물, 대지 마법'")],
    2037: [("사용자의 힘, 체력, 정확도를 증가시키지만", "사용자의 힘, 인내력, 정확도를 증가시키지만")],
    2039: [("지력을 저하시킵니다", "지능을 저하시킵니다")],
    2042: [("지력 테스트", "지능 테스트")],
    2048: [("착용자의 지력을 크게 향상시키지만", "착용자의 지능을 크게 향상시키지만")],
}


def decode_with_encoding(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def main() -> None:
    original = path.read_bytes()
    text, encoding = decode_with_encoding(original)
    lines = text.splitlines(keepends=True)
    seen: set[int] = set()
    changed = 0

    for index, line in enumerate(lines):
        body = line.rstrip("\r\n")
        id_text, sep, _rest = body.partition("\t")
        if not sep or not id_text.isdigit():
            continue
        item_id = int(id_text)
        fixes = ROW_FIXES.get(item_id)
        if not fixes:
            continue
        seen.add(item_id)
        updated = line
        for old, new in fixes:
            if old in updated:
                updated = updated.replace(old, new)
                changed += 1
            elif new not in updated:
                raise SystemExit(f"item {item_id}: neither old nor corrected phrase found: {old!r}")
        lines[index] = updated

    missing = sorted(set(ROW_FIXES) - seen)
    if missing:
        raise SystemExit(f"missing item rows: {missing}")

    wanted = "".join(lines).encode(encoding)
    if wanted != original:
        path.write_bytes(wanted)
    print(f"report 65949 item review 2: {changed} source corrections ({encoding})")


if __name__ == "__main__":
    main()
