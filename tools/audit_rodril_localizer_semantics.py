#!/usr/bin/env python3
"""Audit the Korean LocalizeTables override for Rodril gameplay semantics.

The Korean override may add encoding/multiline support, but Rodril's base
Data/*LocalizeTables.*txt files are not translation-only data: they also carry
numeric gameplay fields and the upstream loader normalizes blank quest entries
to the sentinel string "0". Keep those semantics explicit so localization
changes cannot silently disable game systems again.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCALIZER = ROOT / "Scripts/General/LocalizeTables.lua"
UPSTREAM_DATA = ROOT / "Data/03 LocalizeTables.txt"


def fail(message: str) -> None:
    print(f"- {message}")
    global FAILED
    FAILED = True


FAILED = False
source = LOCALIZER.read_text(encoding="utf-8")

if not re.search(r"not\s+IsKoreanSource[\s\S]{0,250}tonumber\(cText\)", source):
    fail("Rodril base LocalizeTables values are not converted with tonumber(cText)")

if not re.search(
    r"for\s+i\s*,\s*v\s+in\s+Game\.QuestsTxt\s+do[\s\S]{0,180}#v\s*==\s*0"
    r"[\s\S]{0,120}Game\.QuestsTxt\[i\]\s*=\s*[\"']0[\"']",
    source,
):
    fail('blank Game.QuestsTxt entries are not normalized to the upstream "0" sentinel')

if not re.search(
    r"elseif\s+currentRecord\s+and\s+IsKoreanSource\s+then\s*\n"
    r"\s*currentRecord\.cText\s*=",
    source,
):
    fail("base Rodril spacer/unrecognized lines can still bleed into the previous text record")

data = UPSTREAM_DATA.read_text(encoding="utf-8", errors="replace")
required = {
    "Houses Picture": r"(?m)^Houses\t\d+\tPicture\t\d+\s*$",
    "MapStats EaxEnvironments": r"(?m)^MapStats\t\d+\tEaxEnvironments\t\d+\s*$",
    "NPCDataTxt Joins": r"(?m)^NPCDataTxt\t\d+\tJoins\t\d+\s*$",
}
for label, pattern in required.items():
    if not re.search(pattern, data):
        fail(f"expected Rodril numeric fixture missing from Data/03 LocalizeTables.txt: {label}")

if FAILED:
    print("Rodril localizer semantics audit: FAILED")
    sys.exit(1)

print("Rodril localizer semantics audit: OK")
print("  base numeric coercion: preserved")
print('  blank quest sentinel "0": preserved')
print("  base spacer-line bleed: blocked")
