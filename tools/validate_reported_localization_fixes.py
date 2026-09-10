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


def decode_field(raw: str) -> str:
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('""', '"')
    return raw


def parse_long_overlay(text: str) -> dict[tuple[str, int, str], str]:
    records: dict[tuple[str, int, str], str] = {}
    current_table = ""
    current_key: tuple[str, int, str] | None = None

    for line_no, line in enumerate(text.splitlines()[1:], 2):
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            if parts[0].strip():
                current_table = parts[0].strip()
            if not current_table:
                raise SystemExit(f"runtime override line {line_no} has no table owner")
            key = (current_table, int(parts[1].strip()), parts[2].strip())
            if key in records:
                raise SystemExit(f"duplicate runtime override key: {key}")
            records[key] = decode_field(parts[3])
            current_key = key
        elif line.strip():
            if current_key is None:
                raise SystemExit(f"orphan runtime override continuation at line {line_no}")
            records[current_key] += "\n" + line

    return records


overrides_text = read_legacy_text(overrides_path)
overrides = parse_long_overlay(overrides_text)
ui = ui_path.read_text(encoding="utf-8-sig")
history = read_legacy_text(history_path)

# Player-reported fixes are now canonical-source-backed and projected into
# KO_RuntimeOverrides by tools/rebuild_runtime_overrides.py. Validate by stable
# table/id/field instead of depending on the old shorthand physical line format.
required_overrides: dict[tuple[str, int, str], str] = {
    ("ItemsTxt", 200, "Notes"): "연금술적 성질을 지닌 재료인 위도우스위프 열매",
    ("ItemsTxt", 201, "Notes"): "연금술적 성질을 지닌 재료인 늑대의 눈",
    ("ItemsTxt", 263, "Notes"): "마법이 없는 무기에 \"드래곤 사냥의 힘\" 효과를 부여합니다. (사용하려면",
    ("ItemsTxt", 518, "Notes"): "(민첩성 +30, 공격 회복 속도 증가, 수면 면역)",
    ("ItemsTxt", 988, "Notes"): "안타개릭산에서 채취한 수정입니다.",
    ("ItemsTxt", 1006, "Notes"): "특이한 성질을 지닌 마법의 재료. 드래곤의 눈은 붉은 물약을 만드는 데 사용할 수 있습니다.",
    ("ItemsTxt", 1012, "Name"): "양귀비꽃",
    ("ItemsTxt", 1015, "Notes"): "특이한 성질을 지닌 마법의 재료. 석류석은",
    ("ItemsTxt", 1762, "Name"): "양귀비꽃",
    ("ItemsTxt", 1764, "Name"): "위도우스위프 열매",
    ("NPCDataTxt", 340, "Name"): "마크햄 경",
    ("MapStats", 92, "Name"): "마크햄 경의 저택",
}

for key, expected in required_overrides.items():
    actual = overrides.get(key)
    if actual is None:
        raise SystemExit(f"missing reported-fix runtime projection: {key}")
    if expected not in actual:
        raise SystemExit(
            f"reported-fix runtime projection drift: {key}: expected {expected!r}, got {actual!r}"
        )

if not any("안타개릭, 제이덤은 모두 평안을 되찾을 것입니다." in value for value in overrides.values()):
    raise SystemExit("missing reported-fix ending wording in runtime projection")

# This runtime file intentionally keeps only dynamic/custom runtime wording as
# decimal EUC-KR byte escapes. The three hireling descriptions are intentionally
# pinned here rather than copied through Game.NPCText because those table indexes
# are not stable across every Merge build.
if not ui.isascii():
    raise SystemExit("ZZ_KoreanReportedLocalization.lua contains raw non-ASCII runtime text")

required_ui_fragments = [
    "local UI_TEXT = {",
    '["Free class / portrait combinations are allowed now."]',
    '["Free class / portrait combinations are disabled now."]',
    '["Interface settings"]',
    '["General settings"]',
    '["Bolster multipliers"]',
    '["Keybinds"]',
    '{Text = "M&M 8"',
    '{Text = "M&M 7"',
    '{Text = "M&M 6"',
    "Layer = 0",
    "local HIRELING_LEARNING_DESCRIPTIONS = {",
    '[4] = "\\176\\237\\191\\235',
    '[13] = "\\176\\237\\191\\235',
    '[14] = "\\176\\237\\191\\235',
    "Game.NPCProf[profession].Description = encodeKorean(description)",
]
for fragment in required_ui_fragments:
    if fragment not in ui:
        raise SystemExit(f"missing current UI/runtime hotfix contract: {fragment!r}")

for forbidden in (
    "local EXPERIENCE_TEXT = {",
    "applyExperienceTextSafety",
    "local MM7_INTRO",
    "applyMM7Intro",
    "[4] = 2324",
    "[13] = 2333",
    "[14] = 2334",
    "Game.NPCProf[profession].Description = localized",
):
    if forbidden in ui:
        raise SystemExit(f"obsolete duplicate/unstable runtime mapping returned: {forbidden!r}")

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
