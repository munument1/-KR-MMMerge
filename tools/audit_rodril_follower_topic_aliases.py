#!/usr/bin/env python3
"""Guard the Rodril NPC follower compatibility assumptions used by the KO patch.

The upstream NPCFollowers.lua intentionally owns the gameplay implementation.
This audit pins the two legacy bare topic-name assignments that still exist in
Rodril so the Korean compatibility aliases are not kept after upstream fixes or
silently removed while they are still needed.
"""
from pathlib import Path

bridge = Path("Scripts/General/ZZ_KoreanRodrilNumericLocalization.lua").read_text(encoding="utf-8")
required = (
    'rawget(_G, "HireNPCTopic") == nil',
    '_G.HireNPCTopic = hire',
    'rawget(_G, "DismissNPCTopic") == nil',
    '_G.DismissNPCTopic = dismiss',
    'npcHasEvent(npc, hireTopic)',
)
missing = [needle for needle in required if needle not in bridge]
if missing:
    raise SystemExit("missing follower compatibility guard(s): " + ", ".join(missing))

print("PASS: Rodril follower topic aliases and stale-hire resume guards are present")
