#!/usr/bin/env python3
"""Validate report 65949 item QA pass 3."""
from __future__ import annotations

import pathlib
import sys

from apply_report_65949_item_review3 import ROW_FIXES

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

# Review 4 refines wording on these rows without changing the mechanics
# established by review 3.
SUPERSEDED_BY_REVIEW4 = {1338, 2026, 2030, 2035}


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
        if item_id not in SUPERSEDED_BY_REVIEW4 and new not in line:
            violations.append(f"item {item_id}: missing corrected phrase {new}")

required = {
    502: ["무기 전문가 기술 +7"],
    522: ["깃털 낙하"],
    527: ["(흡혈, 힘 +50, 운 -40)", "영혼 학살자"],
    1335: ["피격 회복 속도 증가"],
    1338: ["모든 저항력 +10"],
    2026: ["모든 저항력 +10, 생명력 +25"],
    2029: ["모든 능력치 +10, 주문력 +25"],
    2030: ["함정 해제/훔치기 성공 확률 2배"],
    2035: ["함정 해제/훔치기 성공 확률 2배"],
}
for item_id, fragments in required.items():
    line = rows.get(item_id, "")
    for fragment in fragments:
        if fragment not in line:
            violations.append(f"item {item_id}: required fragment missing: {fragment}")

# Semantics that were previously conflated must stay distinct.
if "1335\t" in text and "1335\t엘프 사슬 갑옷" in text:
    line = rows.get(1335, "")
    if "공격 회복 속도 증가" in line:
        violations.append("item 1335: of Recovery must not be translated as weapon/attack recovery")

if violations:
    raise SystemExit("report 65949 item review 3 validation failed:\n" + "\n".join(violations))

print(f"report 65949 item review 3 source: OK ({len(ROW_FIXES)} item rows; review 4 refinements allowed)")
