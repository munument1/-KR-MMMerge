#!/usr/bin/env python3
"""Third source-backed item QA pass for report 65949.

This pass resolves special-enchantment semantics against Merge's SPCITEMS.TXT
and fixes a few remaining proper-name/terminology inconsistencies.  Every
replacement is scoped to one exact item ID.
"""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

ROW_FIXES: dict[int, list[tuple[str, str]]] = {
    502: [("(무기 숙련도 +7, 공기 저항 +30)", "(무기 전문가 기술 +7, 공기 저항 +30)")],
    503: [("오우거 처치", "오우거 사냥")],
    522: [("(깃털 떨어짐,", "(깃털 낙하,")],
    527: [
        ("(흡혈귀, 힘 +50, 운 -40)", "(흡혈, 힘 +50, 운 -40)"),
        ("'영혼살자'", "'영혼 학살자'"),
    ],
    1325: [("이것은 단명했던 피낙스 제국의 잃어버린(잃어버린) 왕관입니다.", "이것은 단명했던 피낙스 제국의 한때 잃어버렸던 왕관입니다.")],
    1330: [("향상된 자기 능력과 힘", "향상된 자기 계열 마법 능력과 힘")],
    # SPCITEMS: of Recovery = recovery from being hit, not Swift/weapon speed.
    1335: [("(공격 회복 속도 증가, 민첩성 +15, 정확도 +15, 엘프)", "(피격 회복 속도 증가, 민첩성 +15, 정확도 +15, 엘프)")],
    # SPCITEMS: of Protection = +10 to all resistances.
    1338: [("(물 위 걷기, 깃털처럼 가벼운 낙하, 보호, 여성용)", "(물 위 걷기, 깃털 낙하, 모든 저항 +10, 여성)")],
    # SPCITEMS: of Protection = +10 all resistances.
    2026: [("(특수 능력: 보호 및 생명력 +25)", "(특수 능력: 모든 저항 +10, 생명력 +25)")],
    # SPCITEMS: of The Gods = +10 to all seven statistics.
    2029: [("(특수 능력: '신의 것' 및 주문력 +25)", "(특수 능력: 모든 능력치 +10, 주문력 +25)")],
    # SPCITEMS: Thievery doubles lockpick/steal chance; it is not a +30/+20 skill bonus.
    2030: [("(특수 능력: 운 +30, 도둑질 +30, 독 면역)", "(특수 능력: 운 +30, 함정 해제/도둑질 성공 확률 2배, 독 면역)")],
    2035: [("(특수 능력: 독 피해 +20, 운 +20, 도둑질 +20, 생명력 지속 감소)", "(특수 능력: 독 피해 +20, 운 +20, 함정 해제/도둑질 성공 확률 2배, 생명력 지속 감소)")],
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
    print(f"report 65949 item review 3: {changed} source corrections ({encoding})")


if __name__ == "__main__":
    main()
