#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

overrides_path = root / "Data" / "Text localization" / "KO_RuntimeOverrides.txt"
ui_path = root / "Scripts" / "General" / "ZZ_KoreanReportedLocalization.lua"
history_path = root / "Data" / "Text localization" / "MM7History_KO.txt"

overrides = overrides_path.read_text(encoding="utf-8-sig")
ui = ui_path.read_text(encoding="utf-8-sig")
history = history_path.read_text(encoding="utf-8-sig")

required_override_fragments = [
    "ItemsTxt\t200\tNotes\t연금술적 성질을 지닌 재료인 위도우스위프 열매",
    "\t201\tNotes\t연금술적 성질을 지닌 재료인 늑대의 눈",
    "\t263\tNotes\t마법이 없는 무기에 \"드래곤 사냥의 힘\" 효과를 부여합니다. (사용하려면",
    "\t518\tNotes\t(속도 +30, 신속, 수면 면역)",
    "\t988\tNotes\t안타개릭산에서 채취한 수정입니다.",
    "\t1006\tNotes\t특이한 성질을 지닌 마법의 재료. 드래곤의 눈은 붉은 물약을 만드는 데 사용할 수 있습니다.",
    "\t1012\tName\t양귀비꽃",
    "\t1015\tNotes\t특이한 성질을 지닌 마법의 재료. 석류석은",
    "\t1762\tName\t양귀비꽃",
    "\t1764\tName\t위도우스위프 열매",
    "NPCDataTxt\t340\tName\t마크햄 경",
    "MapStats\t92\tName\t마크햄 경의 저택",
    "안타개릭, 제이덤은 모두 평안을 되찾을 것입니다.",
]

for fragment in required_override_fragments:
    if fragment not in overrides:
        raise SystemExit(f"missing reported-fix override: {fragment!r}")

required_ui_fragments = [
    '["Free class / portrait combinations are allowed now."]',
    '["UI depends on continent"] = "대륙에 따라 UI 변경"',
    '["Increase view range"] = "시야 거리 증가"',
    '["Smaller potion bottles"] = "작은 물약병"',
    'Title = "저자의 서문"',
    "continent == 2",
]

for fragment in required_ui_fragments:
    if fragment not in ui:
        raise SystemExit(f"missing UI/history runtime fix: {fragment!r}")

if not history.startswith("#\tText\tTime\tPage Title\n1\t마크햄 경은"):
    raise SystemExit("MM7 history source no longer starts with the translated Markham foreword")

print("reported localization fixes: OK")
