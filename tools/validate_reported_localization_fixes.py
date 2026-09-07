#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

overrides_path = root / "Data" / "Text localization" / "KO_RuntimeOverrides.txt"
ui_path = root / "Scripts" / "General" / "ZZ_KoreanReportedLocalization.lua"
history_path = root / "Data" / "Text localization" / "MM7History_KO.txt"


def read_legacy_text(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp949"):
        try:
            text = data.decode(encoding)
            return text.replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode localization source: {path}")


def decode_legacy_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    return ""


def contains_encoded(data: bytes, text: str) -> bool:
    encodings = []
    for encoding in ("utf-8", "cp949"):
        encoded = text.encode(encoding)
        if encoded not in encodings:
            encodings.append(encoded)
    return any(encoded in data for encoded in encodings)


overrides = overrides_path.read_text(encoding="utf-8-sig")
ui = ui_path.read_text(encoding="utf-8-sig")
history = read_legacy_text(history_path)

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
    '{Text = "M&M 8"',
    '{Text = "M&M 7"',
    '{Text = "M&M 6"',
    "[4] = {",
    "NPCText = 2324",
    "학습 기술에 +5 보너스를 주고 아이템을 무제한으로 식별합니다. 학습 숙련도 배율이 적용됩니다.",
    "[13] = {",
    "NPCText = 2333",
    "학습 기술에 +10 보너스를 줍니다. 학습 숙련도 배율이 적용됩니다.",
    "[14] = {",
    "NPCText = 2334",
    "학습 기술에 +15 보너스를 줍니다. 학습 숙련도 배율이 적용됩니다.",
    "Game.NPCProf[profession].Description = localized",
]

for fragment in required_ui_fragments:
    if fragment not in ui:
        raise SystemExit(f"missing UI/history runtime fix: {fragment!r}")

if not history.startswith("#\tText\tTime\tPage Title\n1\t마크햄 경은"):
    raise SystemExit("MM7 history source no longer starts with the translated Markham foreword")

# Prevent the player-reported mistranslations from quietly surviving in a
# different Korean source table. Search raw bytes because many legacy .txt
# files are intentionally CP949 and marked binary in git.
stale_terms = [
    "자다메",
    "자데임",
    "안타가리",
    "마컴",
    "사드래곤",
    "과부쥐",
    "포피스냅",
    "가넷",
    "늑대 눈은",
    "늑대 눈을",
    "이동 속도 +30",
]

scan_roots = [root / "Data" / "Text localization", root / "Scripts"]
violations: list[str] = []
for scan_root in scan_roots:
    for path in scan_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".tsv", ".lua"}:
            continue
        data = path.read_bytes()
        matched = [term for term in stale_terms if contains_encoded(data, term)]
        if not matched:
            continue
        decoded = decode_legacy_bytes(data)
        rel = path.relative_to(root)
        for term in matched:
            found_context = False
            for line_no, line in enumerate(decoded.splitlines(), 1):
                if term in line:
                    excerpt = line.strip().replace("\t", " | ")
                    if len(excerpt) > 240:
                        excerpt = excerpt[:237] + "..."
                    violations.append(f"{rel}:{line_no}: {term}: {excerpt}")
                    found_context = True
            if not found_context:
                violations.append(f"{rel}: {term}")

if violations:
    raise SystemExit("stale reported translations remain:\n" + "\n".join(violations))

print("reported localization fixes: OK")
