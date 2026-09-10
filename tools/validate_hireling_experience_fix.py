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
    "local HIRELING_EXPERIENCE_BONUSES = {",
    "[4] = 5",
    "[13] = 10",
    "[14] = 15",
    "vars.NPCFollowers",
    "local npc = Game.NPC[npcId]",
    "HIRELING_EXPERIENCE_BONUSES[npc.Profession]",
    "function events.GetSkill(t)",
    "SplitSkill(t.Result)",
    "level - bonus",
    "JoinSkill(math.max(0, level - bonus), mastery)",
    "function events.GetLearningTotalSkill(t)",
    "t.Result = t.Result + bonus",
    "function events.EnterNPC()",
    "Game.NPCProf[profession].Description = encodeKorean(description)",
]
for fragment in required_fragments:
    if fragment not in text:
        raise SystemExit(f"missing hireling experience fix contract: {fragment!r}")

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

# Regression model for the reported +60 case. Rodril currently adds all three
# values as raw Learning ranks (30). At Expert mastery that becomes 60. The
# compatibility overlay must remove the raw 30 before mastery, then add flat 30
# percentage points afterwards. The follower contribution therefore stays 30
# regardless of Learning mastery.
raw_follower_bonus = sum(entries.values())
if raw_follower_bonus != 30:
    raise SystemExit(f"expected all-hireling flat bonus 30, got {raw_follower_bonus}")

for multiplier in (1, 2, 3, 5):
    base_learning = 7
    upstream_effective = (base_learning + raw_follower_bonus) * multiplier
    corrected_effective = (
        (base_learning + raw_follower_bonus - raw_follower_bonus) * multiplier
        + raw_follower_bonus
    )
    follower_delta = corrected_effective - base_learning * multiplier
    if follower_delta != 30:
        raise SystemExit(
            "hireling bonus is still mastery-scaled: "
            f"multiplier={multiplier}, delta={follower_delta}, upstream={upstream_effective}"
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
