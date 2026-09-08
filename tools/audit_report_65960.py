#!/usr/bin/env python3
"""Audit localization strings reported in DCInside report 65960.

Read text files using UTF-8/CP949 without modifying them.  Output exact lines for
all candidate terms so fixes can be scoped to concrete records instead of broad
blind replacements.
"""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"

PATTERNS = [
    "불가사의한 시대", "불가사의의 시대", "경이로운 시대", "경이의 시대",
    "대재앙", "대침묵의 시대", "침묵의 시대",
    "메코리그 더 블라인드", "맹인 메코리그", "눈먼 메코리그", "장님 메코리그",
    "사격 보너스", "사격 피해",
    "보호막(Shield)", "보호막", "방패 주문",
    "헤드스맨 폴액스", "참수자의 장대도끼",
    "7대 능력치", "신들",
    "용의 가죽 벨트", "드래곤의 가죽 벨트",
    "깃털 떨어짐", "깃털 낙하",
    "물 위 걷기", "수중 호흡",
    "신속", "마법력 +40", "주문력 +40",
    "활 숙련도 +5", "활 기술 +5",
    "안타개릭 다이아몬드", "안타개릭산 다이아몬드",
    "제이덤 다이아몬드", "제이덤산 다이아몬드",
    "아이기스", "아폴로", "하렉의 가죽 갑옷", "황혼", "멀린", "토너먼트 활",
]


def decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1")


def main() -> None:
    files = sorted(loc.glob("KO_*.txt")) + [loc / "KO_StatsDescriptions.tsv"]
    hits = 0
    for path in files:
        if not path.is_file():
            continue
        text = decode(path.read_bytes()).replace("\r\n", "\n").replace("\r", "\n")
        for lineno, line in enumerate(text.split("\n"), 1):
            found = [p for p in PATTERNS if p in line]
            if found:
                hits += 1
                print(f"{path.relative_to(root)}:{lineno}: [{', '.join(found)}] {line}")
    print(f"report 65960 audit: {hits} matching lines")


if __name__ == "__main__":
    main()
