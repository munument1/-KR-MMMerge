#!/usr/bin/env python3
"""Apply source-backed corrections from player report 65960.

All item changes are scoped to exact item IDs or exact proper-era phrases inside
KO_ItemsTxt.txt.  This intentionally avoids the broad substring replacements
that previously damaged unrelated Korean prose.
"""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"

ITEM_ROW_FIXES: dict[int, list[tuple[str, str]]] = {
    121: [("용의 가죽 벨트", "드래곤의 가죽 벨트")],
    178: [("제이덤 아이올라이트", "제이덤산 아이올라이트")],
    180: [("제이덤 호박", "제이덤산 호박")],
    182: [("제이덤 토파즈", "제이덤산 토파즈")],
    185: [("제이덤 루비", "제이덤산 루비")],
    186: [("제이덤 다이아몬드", "제이덤산 다이아몬드")],
    806: [("메코리그 더 블라인드", "장님 메코리그")],
    807: [("대재앙 이전에", "침묵의 시대 이전에")],
    821: [(
        "불가사의한 시대의 무기인 이 칼은 이제 더 이상 날카롭거나 강인한 날을 만들 수 없습니다.",
        "경이의 시대에 만들어진 이 단검은, 이보다 더 날카롭거나 더 튼튼한 칼날을 만들 수 없을 정도로 완벽합니다.",
    )],
    832: [("헤드스맨 폴액스는", "참수자의 장대도끼는")],
    840: [("맹인 메코리그", "장님 메코리그")],
    880: [("메코리그 더 블라인드", "장님 메코리그")],
    991: [("안타개릭 사파이어", "안타개릭산 사파이어")],
    993: [("안타개릭 보석", "안타개릭산 보석")],
    994: [("안타개릭 다이아몬드", "안타개릭산 다이아몬드")],
    995: [("안타개릭 자수정", "안타개릭산 자수정")],
    996: [("안타개릭 토파즈", "안타개릭산 토파즈")],
    997: [("안타개릭 다이아몬드", "안타개릭산 다이아몬드")],
    998: [("안타개릭 루비", "안타개릭산 루비")],
    1310: [("눈먼 메코리그", "장님 메코리그")],
    1318: [("물 위 걷기", "수중 호흡")],
    1330: [("맹인 메코리그", "장님 메코리그")],
    1606: [("메코리그 더 블라인드", "장님 메코리그")],
    1680: [("눈먼 메코리그", "장님 메코리그")],
    2043: [(
        "석화 면역, 원거리 공격 피해 절반, 운 +20, 민첩성 -20",
        "석화 면역, 방패 주문 효과 상시 유지, 운 +20, 민첩성 -20",
    )],
}

# These phrases are all proper names of historical eras when they occur in the
# item table.  Other uses of ordinary words such as 대재앙 are intentionally
# untouched.
ITEM_ERA_FIXES = [
    ("불가사의한 시대", "경이의 시대"),
    ("불가사의의 시대", "경이의 시대"),
    ("경이로운 시대", "경이의 시대"),
    ("대침묵의 시대", "침묵의 시대"),
]

OVERLAY_FIXES: dict[str, dict[int, list[tuple[str, str]]]] = {
    "KO_GlobalTxt.txt": {
        589: [("사격 보너스", "원거리 공격 보너스")],
        590: [("사격 피해", "원거리 피해")],
    },
    "KO_SpcItemsTxtNames.txt": {
        1: [("[신들]", "[신]")],
    },
    "KO_SpcItemsTxtStats.txt": {
        1: [("7대 능력치 모두 +10.", "모든 능력치 +10.")],
    },
    "KO_RuntimeOverrides.txt": {
        2043: [(
            "살을 돌로 변하게 하는 효과 면역, 방패 사용 시 운 +20, 민첩성 -20",
            "석화 면역, 방패 주문 효과 상시 유지, 운 +20, 민첩성 -20",
        )],
    },
}

LUA_FIXES = [
    ("'보호막(Shield)' 주문 효과 자동 부여", "방패 주문 효과 자동 부여"),
]


def decode_legacy(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def split_keep_style(data: bytes, text: str) -> tuple[list[str], str]:
    if b"\r\n" in data:
        newline = "\r\n"
    elif b"\r" in data and b"\n" not in data:
        newline = "\r"
    else:
        newline = "\n"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.split("\n"), newline


def rewrite_items(path: pathlib.Path) -> int:
    original = path.read_bytes()
    text, encoding = decode_legacy(original)
    lines, newline = split_keep_style(original, text)
    changed = 0
    seen: set[int] = set()

    for index, line in enumerate(lines):
        key, sep, _rest = line.partition("\t")
        if not sep or not key.isdigit():
            continue
        item_id = int(key)
        updated = line

        if item_id in ITEM_ROW_FIXES:
            seen.add(item_id)
            for old, new in ITEM_ROW_FIXES[item_id]:
                if old in updated:
                    updated = updated.replace(old, new)
                    changed += 1
                elif new not in updated:
                    raise SystemExit(f"item {item_id}: neither old nor corrected text found: {old!r}")

        # Proper-era terminology is safe only inside the item text table.
        for old, new in ITEM_ERA_FIXES:
            if old in updated:
                count = updated.count(old)
                updated = updated.replace(old, new)
                changed += count

        lines[index] = updated

    missing = sorted(set(ITEM_ROW_FIXES) - seen)
    if missing:
        raise SystemExit(f"missing item rows: {missing}")

    wanted = newline.join(lines).encode(encoding)
    if wanted != original:
        path.write_bytes(wanted)
    return changed


def overlay_record_id(parts: list[str]) -> int | None:
    # KO overlay tables usually begin with an empty table-name column, followed
    # by a numeric record id.  Accept either first or second field for safety.
    for pos in (0, 1):
        if pos < len(parts) and parts[pos].strip().isdigit():
            return int(parts[pos].strip())
    return None


def rewrite_overlay(path: pathlib.Path, fixes: dict[int, list[tuple[str, str]]]) -> int:
    original = path.read_bytes()
    text, encoding = decode_legacy(original)
    lines, newline = split_keep_style(original, text)
    changed = 0
    seen: set[int] = set()

    for index, line in enumerate(lines):
        record_id = overlay_record_id(line.split("\t", 3))
        if record_id not in fixes:
            continue
        seen.add(record_id)
        updated = line
        for old, new in fixes[record_id]:
            if old in updated:
                updated = updated.replace(old, new)
                changed += 1
            elif new not in updated:
                raise SystemExit(f"{path.name} record {record_id}: missing {old!r}")
        lines[index] = updated

    missing = sorted(set(fixes) - seen)
    if missing:
        raise SystemExit(f"{path.name}: missing records {missing}")

    wanted = newline.join(lines).encode(encoding)
    if wanted != original:
        path.write_bytes(wanted)
    return changed


def rewrite_lua(path: pathlib.Path) -> int:
    original = path.read_text(encoding="utf-8")
    text = original
    changed = 0
    for old, new in LUA_FIXES:
        if old in text:
            text = text.replace(old, new)
            changed += 1
        elif new not in text:
            raise SystemExit(f"{path.name}: missing shield GM text")
    if text != original:
        path.write_text(text, encoding="utf-8", newline="")
    return changed


def main() -> None:
    total = rewrite_items(loc / "KO_ItemsTxt.txt")
    for name, fixes in OVERLAY_FIXES.items():
        total += rewrite_overlay(loc / name, fixes)
    total += rewrite_lua(root / "Scripts" / "General" / "KoreanStatsAndSkills.lua")
    print(f"report 65960 source fixes: {total} corrections")


if __name__ == "__main__":
    main()
