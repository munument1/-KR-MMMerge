#!/usr/bin/env python3
"""Validate report 65949 artifact/relic QA pass 4."""
from __future__ import annotations

import pathlib
import sys

from apply_report_65949_item_review4 import ROW_FIXES

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

# Report 65992 intentionally refines these mechanics/wording after review 4.
SUPERSEDED = {1306, 2026}


def read_legacy(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode {path}")


text = read_legacy(path)
rows: dict[int, str] = {}
for line in text.splitlines():
    key, sep, _rest = line.partition("\t")
    if sep and key.isdigit():
        rows[int(key)] = line

violations: list[str] = []
for item_id, fixes in ROW_FIXES.items():
    line = rows.get(item_id)
    if line is None:
        violations.append(f"missing item row {item_id}")
        continue
    for old, new in fixes:
        if old in line:
            violations.append(f"item {item_id}: stale phrase {old}")
        if item_id not in SUPERSEDED and new not in line:
            violations.append(f"item {item_id}: missing corrected phrase {new}")

required = {
    519: ["화염, 대지, 물, 공기 저항 +40"],
    1304: ["무기 전문가 기술 +10"],
    1305: ["훔치기 기술 +5", "함정 해제 기술 +5"],
    1306: ["방패 주문 상시 유지", "모든 능력치 +10"],
    1313: ["맨손 기술 +10", "회피 기술 +10"],
    1318: ["맨손 기술 +5", "함정 해제 기술 +5", "수중 호흡", "모든 저항력 -10"],
    1319: ["엘프 사냥"],
    1323: ["운 -40, 선)"],
    1338: ["모든 저항력 +10"],
    2026: ["방패 주문 상시 유지", "돌가죽 주문 상시 유지", "생명력 +25"],
    2030: ["함정 해제/훔치기 성공 확률 2배"],
    2035: ["함정 해제/훔치기 성공 확률 2배"],
    2040: ["원소 저항력 -10"],
    2041: ["모든 저항력 +20"],
    2044: ["원소 저항력 +50"],
}
for item_id, fragments in required.items():
    line = rows.get(item_id, "")
    for fragment in fragments:
        if fragment not in line:
            violations.append(f"item {item_id}: required fragment missing: {fragment}")

if violations:
    raise SystemExit("report 65949 item review 4 validation failed:\n" + "\n".join(violations))

print(f"report 65949 item review 4 source: OK ({len(ROW_FIXES)} item rows; later refinements allowed)")
