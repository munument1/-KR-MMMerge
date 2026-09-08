#!/usr/bin/env python3
"""Validate the second source-backed item QA pass for report 65949."""
from __future__ import annotations

import pathlib
import sys

from apply_report_65949_item_review2 import ROW_FIXES

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"


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
        if new not in line:
            violations.append(f"item {item_id}: missing corrected phrase {new}")

# Explicit mechanics/terminology guards for the worst mistranslations.
required = {
    508: ["뱀파이어"],
    511: ["원거리 공격 피해 절반"],
    516: ["영혼 마법, 육체 마법, 정신 마법, 성직자"],
    523: ["대상 공격 회복 속도 감소"],
    539: ["드래곤 사냥용 창인 에보네스트"],
    1329: ["민첩성 -40"],
    1333: ["원거리 공격 피해 절반, 엘프 사냥, 고블린", "엘프베인"],
    1335: ["공격 회복 속도 증가"],
    2024: ["공격 회복 속도 증가, 주문력 +40"],
    2028: ["원거리 공격 피해 절반, 정확도 +30"],
}
for item_id, fragments in required.items():
    line = rows.get(item_id, "")
    for fragment in fragments:
        if fragment not in line:
            violations.append(f"item {item_id}: required fragment missing: {fragment}")

if violations:
    raise SystemExit("report 65949 item review 2 source validation failed:\n" + "\n".join(violations))

print(f"report 65949 item review 2 source: OK ({len(ROW_FIXES)} item rows)")
