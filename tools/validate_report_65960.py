#!/usr/bin/env python3
"""Validate source corrections for player report 65960."""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"


def decode(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode {path}")


def numeric_rows(path: pathlib.Path) -> dict[int, str]:
    rows: dict[int, str] = {}
    text = decode(path).replace("\r\n", "\n").replace("\r", "\n")
    for line in text.split("\n"):
        key, sep, _rest = line.partition("\t")
        if sep and key.strip().isdigit():
            rows[int(key.strip())] = line
    return rows


def overlay_rows(path: pathlib.Path) -> dict[int, str]:
    rows: dict[int, str] = {}
    text = decode(path).replace("\r\n", "\n").replace("\r", "\n")
    for line in text.split("\n"):
        parts = line.split("\t", 3)
        for pos in (0, 1):
            if pos < len(parts) and parts[pos].strip().isdigit():
                rows[int(parts[pos].strip())] = line
                break
    return rows


def require(row: str, wanted: str, label: str) -> None:
    if wanted not in row:
        raise SystemExit(f"{label}: missing {wanted!r}\n{row}")


def forbid(row: str, stale: str, label: str) -> None:
    if stale in row:
        raise SystemExit(f"{label}: stale text {stale!r}\n{row}")


def main() -> None:
    items_path = loc / "KO_ItemsTxt.txt"
    items_text = decode(items_path)
    items = numeric_rows(items_path)

    # Proper-era terminology. These stale variants should no longer exist in
    # the item table; unrelated Cataclysm/대재앙 prose is deliberately allowed.
    for stale in ("불가사의한 시대", "불가사의의 시대", "경이로운 시대", "대침묵의 시대"):
        if stale in items_text:
            raise SystemExit(f"KO_ItemsTxt still contains stale era term: {stale}")
    require(items[807], "침묵의 시대 이전에", "item 807 Duelist Blade")
    forbid(items[807], "대재앙 이전에", "item 807 Duelist Blade")
    require(items[821], "경이의 시대에 만들어진 이 단검은", "item 821 Wonder Dagger")
    require(items[1621], "경이의 시대", "item 1621 Jeweled Dagger")

    # Mekorig proper-name consistency, scoped to the known item references.
    for item_id in (806, 840, 880, 1310, 1330, 1606, 1680):
        require(items[item_id], "장님 메코리그", f"item {item_id} Mekorig")
        for stale in ("메코리그 더 블라인드", "맹인 메코리그", "눈먼 메코리그"):
            forbid(items[item_id], stale, f"item {item_id} Mekorig")

    # Exact item wording/mechanics from the report and Merge code.
    require(items[121], "드래곤의 가죽 벨트", "item 121 Artificer's Belt")
    require(items[522], "깃털 낙하", "item 522 Archangel Wings")
    require(items[531], "활 기술 +5", "item 531 Tournament Bow")
    require(items[832], "참수자의 장대도끼는", "item 832 Headsman's Poleaxe")
    forbid(items[832], "헤드스맨 폴액스는", "item 832 Headsman's Poleaxe")
    require(items[1318], "수중 호흡", "item 1318 Hareck's Leather")
    forbid(items[1318], "물 위 걷기", "item 1318 Hareck's Leather")
    require(items[1327], "민첩성 +50", "item 1327 Twilight")
    require(items[2024], "공격 회복 속도 증가, 주문력 +40", "item 2024 Merlin")
    require(items[2041], "모든 저항력 +20", "item 2041 Apollo")
    require(items[2043], "방패 주문 효과 상시 유지", "item 2043 Aegis")
    forbid(items[2043], "방패 기술 +20", "item 2043 Aegis")

    # Gem provenance: every Jadame/Antagarich gem description in the affected
    # blocks now uses the same -산 construction as the already-correct rows.
    for item_id in range(177, 187):
        if item_id in items:
            require(items[item_id], "제이덤산", f"Jadame gem {item_id}")
    for item_id in range(988, 999):
        if item_id in items:
            require(items[item_id], "안타개릭산", f"Antagarich gem {item_id}")

    global_rows = overlay_rows(loc / "KO_GlobalTxt.txt")
    require(global_rows[589], "원거리 공격 보너스", "GlobalTxt 589")
    require(global_rows[590], "원거리 피해", "GlobalTxt 590")
    forbid(global_rows[589], "사격 보너스", "GlobalTxt 589")
    forbid(global_rows[590], "사격 피해", "GlobalTxt 590")

    spc_names = overlay_rows(loc / "KO_SpcItemsTxtNames.txt")
    spc_stats = overlay_rows(loc / "KO_SpcItemsTxtStats.txt")
    require(spc_names[1], "[신]", "SPCITEMS name 1")
    forbid(spc_names[1], "[신들]", "SPCITEMS name 1")
    require(spc_stats[1], "모든 능력치 +10.", "SPCITEMS stat 1")
    forbid(spc_stats[1], "7대 능력치 모두 +10.", "SPCITEMS stat 1")

    runtime = overlay_rows(loc / "KO_RuntimeOverrides.txt")
    require(runtime[2043], "석화 면역, 방패 주문 효과 상시 유지, 운 +20, 민첩성 -20", "runtime Aegis")

    skills = decode(root / "Scripts" / "General" / "KoreanStatsAndSkills.lua")
    if "[8]=\"방패 주문 효과 자동 부여\"" not in skills:
        raise SystemExit("Shield GM description is not the canonical Korean wording")
    if "보호막(Shield)" in skills:
        raise SystemExit("Shield GM description still contains 보호막(Shield)")

    print("report 65960 source validation: OK")


if __name__ == "__main__":
    main()
