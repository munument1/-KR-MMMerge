#!/usr/bin/env python3
"""Validate report 65949 follow-up grammar and reagent cleanup."""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
items_path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

STANDARD_REAGENT_INSTRUCTION = (
    "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"
)

BAD_PHRASES = [
    "영광스러행운",
    "철깃털는",
    "교수대은",
    "교수대을",
    "흰독말풀는",
    "흰독말풀를",
    "'종결'라는 검",
    "태양교회가 달교회가 만들어낸",
]


def read_legacy(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode {path}")


def parse_rows(text: str) -> dict[int, list[str]]:
    rows: dict[int, list[str]] = {}
    for line in text.splitlines():
        fields = line.split("\t", 3)
        if len(fields) == 4 and fields[0].isdigit():
            rows[int(fields[0])] = fields
    return rows


text = read_legacy(items_path)
violations: list[str] = []
for phrase in BAD_PHRASES:
    if phrase in text:
        violations.append(f"stale phrase: {phrase}")

rows = parse_rows(text)
checks = {
    208: ("흰독말풀은",),
    525: ("'종결'이라는 검",),
    1303: ("철깃털은",),
    1309: ("태양교회의 노력",),
    1310: ("교수대는", "교수대를"),
    1318: ("영광스러운 해적",),
}
for record_id, wanted_parts in checks.items():
    row = rows.get(record_id)
    if row is None:
        violations.append(f"missing item row {record_id}")
        continue
    notes = row[3]
    for wanted in wanted_parts:
        if wanted not in notes:
            violations.append(f"item {record_id}: missing {wanted}")

reagent_rows = 0
for record_id, fields in rows.items():
    category = fields[2].strip()
    notes = fields[3]
    if category == "약초":
        violations.append(f"item {record_id}: stale item category 약초")
    if category == "시약" and "(사용하려면" in notes:
        reagent_rows += 1
        if STANDARD_REAGENT_INSTRUCTION not in notes:
            violations.append(f"item {record_id}: non-canonical reagent instruction")

if violations:
    raise SystemExit("report 65949 follow-up validation failed:\n" + "\n".join(violations))

print(f"report 65949 follow-up source: OK ({reagent_rows} reagent instructions canonical)")
