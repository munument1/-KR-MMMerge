#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
fix_path = root / "Scripts" / "Global" / "ZZZZ_KoreanHirelingExperienceFix.lua"

if not fix_path.is_file():
    raise SystemExit(f"missing hireling experience compatibility overlay: {fix_path}")

text = fix_path.read_text(encoding="utf-8-sig")
if not text.isascii():
    raise SystemExit("hireling experience overlay contains raw non-ASCII runtime text")

required_fragments = [
    'KoreanHirelingExperienceFix.Version = "1.1"',
    "local HIRELING_EXPERIENCE_BONUSES = {",
    "[4] = 5",
    "[13] = 10",
    "[14] = 15",
    "local LEARNING_MASTERY_MULTIPLIERS = {",
    "[0] = 1",
    "[1] = 1",
    "[2] = 2",
    "[3] = 3",
    "[4] = 5",
    "vars.NPCFollowers",
    "local npc = Game.NPC[npcId]",
    "HIRELING_EXPERIENCE_BONUSES[npc.Profession]",
    "player.Skills[const.Skills.Learning]",
    "function events.GetLearningTotalSkill(t)",
    "bonus * (multiplier - 1)",
    "t.Result = math.max(0, t.Result - bonus * (multiplier - 1))",
    "function events.EnterNPC()",
    "Game.NPCProf[profession].Description = encodeKorean(description)",
]
for fragment in required_fragments:
    if fragment not in text:
        raise SystemExit(f"missing hireling experience fix contract: {fragment!r}")

# Regression guard: GetSkill owns the character-sheet display of follower skill
# bonuses. This overlay must not remove the +5/+10/+15 value there again.
if re.search(r"(?m)^\s*function\s+events\.GetSkill\s*\(", text):
    raise SystemExit(
        "hireling experience overlay must not override events.GetSkill; "
        "that hides Rodril's visible Learning bonus"
    )

# Verify the profession map exactly: Scholar +5, Teacher +10, Instructor +15.
match = re.search(
    r"local HIRELING_EXPERIENCE_BONUSES\s*=\s*\{(?P<body>.*?)\n\}",
    text,
    re.S,
)
if not match:
    raise SystemExit("cannot parse hireling experience bonus table")
entries = {
    int(key): int(value)
    for key, value in re.findall(r"\[(\d+)\]\s*=\s*(\d+)", match.group("body"))
}
if entries != {4: 5, 13: 10, 14: 15}:
    raise SystemExit(f"unexpected hireling experience bonus table: {entries!r}")

mult_match = re.search(
    r"local LEARNING_MASTERY_MULTIPLIERS\s*=\s*\{(?P<body>.*?)\n\}",
    text,
    re.S,
)
if not mult_match:
    raise SystemExit("cannot parse Learning mastery multiplier table")
multipliers = {
    int(key): int(value)
    for key, value in re.findall(r"\[(\d+)\]\s*=\s*(\d+)", mult_match.group("body"))
}
if multipliers != {0: 1, 1: 1, 2: 2, 3: 3, 4: 5}:
    raise SystemExit(f"unexpected Learning mastery multipliers: {multipliers!r}")

# Rodril's GetSkill handler must remain visible to the UI. Its raw follower
# points therefore still enter the engine's Learning calculation. Flatten only
# the extra mastery scaling at GetLearningTotalSkill:
#   upstream = (base + follower) * mastery
#   corrected = upstream - follower * (mastery - 1)
#             = base * mastery + follower
raw_follower_bonus = sum(entries.values())
if raw_follower_bonus != 30:
    raise SystemExit(f"expected all-hireling flat bonus 30, got {raw_follower_bonus}")

base_learning = 7
for mastery, multiplier in multipliers.items():
    upstream_effective = (base_learning + raw_follower_bonus) * multiplier
    corrected_effective = upstream_effective - raw_follower_bonus * (multiplier - 1)
    expected_effective = base_learning * multiplier + raw_follower_bonus
    follower_delta = corrected_effective - base_learning * multiplier
    if corrected_effective != expected_effective or follower_delta != 30:
        raise SystemExit(
            "hireling bonus is not flat after final-skill correction: "
            f"mastery={mastery}, multiplier={multiplier}, "
            f"corrected={corrected_effective}, expected={expected_effective}"
        )

# The Korean descriptions must advertise flat XP percentages, not raw Learning
# skill ranks. Decode the decimal byte escapes to catch accidental wording drift.
def decode_lua_decimal_escapes(raw: str) -> str:
    data = bytearray()
    i = 0
    while i < len(raw):
        if raw[i] == "\\":
            m = re.match(r"\\(\d{1,3})", raw[i:])
            if not m:
                raise SystemExit(f"unsupported Lua escape in description: {raw[i:i+8]!r}")
            data.append(int(m.group(1)))
            i += len(m.group(0))
        else:
            data.extend(raw[i].encode("ascii"))
            i += 1
    return bytes(data).decode("euc_kr")

expected_descriptions = {
    4: "고용 중에는 모든 캐릭터의 획득 경험치가 5% 증가하며 아이템을 무제한으로 식별합니다.",
    13: "고용 중에는 모든 캐릭터의 획득 경험치가 10% 증가합니다.",
    14: "고용 중에는 모든 캐릭터의 획득 경험치가 15% 증가합니다.",
}

desc_match = re.search(
    r"local HIRELING_EXPERIENCE_DESCRIPTIONS\s*=\s*\{(?P<body>.*?)\n\}",
    text,
    re.S,
)
if not desc_match:
    raise SystemExit("cannot parse hireling experience descriptions")
descriptions = {
    int(key): decode_lua_decimal_escapes(value)
    for key, value in re.findall(r'\[(\d+)\]\s*=\s*"([^"]*)"', desc_match.group("body"))
}
if descriptions != expected_descriptions:
    raise SystemExit(f"hireling experience descriptions drifted: {descriptions!r}")

print("hireling experience fix: OK")
print("character-sheet Learning bonus display: preserved")
print("actual experience bonus: flat +5/+10/+15 after mastery correction")
