#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
fix_path = root / "Scripts" / "Global" / "ZZZZ_KoreanMM7CivilianWitnessFix.lua"

if not fix_path.is_file():
    raise SystemExit(f"missing MM7 civilian witness compatibility overlay: {fix_path}")

text = fix_path.read_text(encoding="utf-8-sig")
if not text.isascii():
    raise SystemExit("MM7 civilian witness overlay contains raw non-ASCII text")

required_fragments = [
    "KoreanMM7CivilianWitnessFix.WitnessRadius",
    "or 4096",
    "TownPortalControls.MapOfContinent(Map.MapStatsIndex) == 2",
    "function events.MonsterAttacked(t)",
    "t.Attacker.Player",
    "Game.Bolster.MonstersSource",
    "src.Creed == const.Bolster.Creed.Peasant",
    "mon.NPC_ID > 0",
    "mon.Group == 38 or mon.Group == 55",
    "local ax, ay, az = XYZ(a)",
    "local bx, by, bz = XYZ(b)",
    "(ax - bx) ^ 2 + (ay - by) ^ 2 + (az - bz) ^ 2",
    "mon.Hostile = true",
    "mon.ShowAsHostile = true",
    "mon.HostileType = 4",
    "and not mon.Hostile",
]
for fragment in required_fragments:
    if fragment not in text:
        raise SystemExit(f"missing MM7 civilian witness fix contract: {fragment!r}")

for forbidden in (
    "MapAlert",
    "OnAlertMap",
    "evt.SetMonGroupBit",
    "Reputation",
    "mon.AIState =",
):
    if forbidden in text:
        raise SystemExit(f"over-broad MM7 civilian witness behavior returned: {forbidden!r}")

radius_match = re.search(
    r"KoreanMM7CivilianWitnessFix\.WitnessRadius\s+or\s+(\d+)", text
)
if not radius_match:
    raise SystemExit("cannot parse MM7 civilian witness default radius")
radius = int(radius_match.group(1))
if radius != 4096:
    raise SystemExit(f"unexpected MM7 civilian witness default radius: {radius}")

# Keep the compatibility scope intentionally narrow: Antagarich only, party
# attacks only, civilian targets only. The overlay must not turn this into a
# global reputation/crime system or rewrite whole monster groups.
if text.count("TownPortalControls.MapOfContinent(Map.MapStatsIndex) == 2") != 1:
    raise SystemExit("Antagarich scope guard drifted")
if text.count("function events.MonsterAttacked(t)") != 1:
    raise SystemExit("MonsterAttacked compatibility handler drifted")

print("MM7 civilian witness fix: OK")
