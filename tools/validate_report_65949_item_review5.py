#!/usr/bin/env python3
"""Validate report 65949 item QA pass 5."""
from __future__ import annotations

import pathlib
import sys

from apply_report_65949_item_review5 import ROW_FIXES

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

required = {
    522: ["모든 마법 저항력 +10"],
    524: ["대혼란은 특수 능력 덕분에"],
    528: ["통치의 삼지창은 원래"],
    1309: ["언데드 사냥"],
    1313: ["달인의 손은 원래"],
    1315: ["통치자의 반지는 서기"],
}
for item_id, fragments in required.items():
    line = rows.get(item_id, "")
    for fragment in fragments:
        if fragment not in line:
            violations.append(f"item {item_id}: required fragment missing: {fragment}")

if violations:
    raise SystemExit("report 65949 item review 5 validation failed:\n" + "\n".join(violations))

print(f"report 65949 item review 5 source: OK ({len(ROW_FIXES)} item rows)")
