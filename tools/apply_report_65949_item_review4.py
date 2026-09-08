#!/usr/bin/env python3
"""Apply report 65949 item QA pass 4.

This pass aligns artifact/relic descriptions with the canonical Korean UI skill
names and with the mechanics documented by the English localization source.
KO_ItemsTxt.txt is a legacy CP949/EUC-KR table, so preserve its byte encoding
and line-ending style.
"""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

ROW_FIXES: dict[int, list[tuple[str, str]]] = {
    519: [("(+40 화염, 대지, 물, 공기 저항)", "(화염, 대지, 물, 공기 저항 +40)")],
    1304: [("(무기 숙련도 +10, 인격 +40)", "(무기 전문가 기술 +10, 인격 +40)")],
    1305: [("(도둑질 기술 +5, 함정 해제 기술 +5, 운 +40)", "(훔치기 기술 +5, 함정 해제 기술 +5, 운 +40)")],
    1306: [("(미사일 공격 피해 절반 감소, 모든 능력치 +10)", "(원거리 공격 피해 절반, 모든 능력치 +10)")],
    1313: [("(맨손 전투 기술 +10, 회피 기술 +10)", "(맨손 기술 +10, 회피 기술 +10)")],
    # Merge ExtraArtifacts grants WaterBreathing for Hareck's Leather.
    1318: [("(도둑질 기술 +5, 함정 해제 기술 +5, 물 위 걷기, 운 +50, 모든 저항력 -10)", "(훔치기 기술 +5, 함정 해제 기술 +5, 수중 호흡, 운 +50, 모든 저항력 -10)")],
    1319: [("엘프 학살", "엘프 사냥")],
    1323: [("(빛 마법, 인격 +15, 힘 +15, 운 -40, 선함)", "(빛 마법, 인격 +15, 힘 +15, 운 -40, 선)")],
    1338: [("모든 저항 +10", "모든 저항력 +10")],
    2026: [("모든 저항 +10, 생명력 +25", "모든 저항력 +10, 생명력 +25")],
    2030: [("함정 해제/도둑질 성공 확률 2배", "함정 해제/훔치기 성공 확률 2배")],
    2035: [("함정 해제/도둑질 성공 확률 2배", "함정 해제/훔치기 성공 확률 2배")],
    2040: [("원소 저항 -10", "원소 저항력 -10")],
    2041: [("(특수 능력: 저항력 +20, 운 +20, 인내력 -30)", "(특수 능력: 모든 저항력 +20, 운 +20, 인내력 -30)")],
    2044: [("원소 저항 +50", "원소 저항력 +50")],
}


def decode_legacy(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode {path}")


def main() -> None:
    data = path.read_bytes()
    text, enc = decode_legacy(data)
    newline = "\r\n" if b"\r\n" in data else ("\r" if b"\r" in data and b"\n" not in data else "\n")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    changes = 0
    for i, line in enumerate(lines):
        key, sep, _rest = line.partition("\t")
        if not sep or not key.isdigit():
            continue
        item_id = int(key)
        fixes = ROW_FIXES.get(item_id)
        if not fixes:
            continue
        new_line = line
        for old, new in fixes:
            if old in new_line:
                new_line = new_line.replace(old, new)
                changes += 1
        lines[i] = new_line

    out = newline.join(lines)
    path.write_bytes(out.encode(enc))
    print(f"report 65949 item review 4: {changes} source corrections ({enc})")


if __name__ == "__main__":
    main()
