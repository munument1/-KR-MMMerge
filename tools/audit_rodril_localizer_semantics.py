#!/usr/bin/env python3
"""Audit the Korean LocalizeTables override for Rodril gameplay semantics.

The Korean override may add encoding/multiline support, but Rodril's base
Data/*LocalizeTables.*txt files are not translation-only data: they also carry
numeric gameplay fields and the upstream loader normalizes blank quest entries
to the sentinel string "0". Keep those semantics explicit so localization
changes cannot silently disable game systems again.

The concrete Rodril fixtures are exercised by the Lua regression harness; this
static audit guards the override implementation itself.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCALIZER = ROOT / "Scripts/General/LocalizeTables.lua"


def fail(message: str) -> None:
    print(f"- {message}")
    global FAILED
    FAILED = True


FAILED = False
source = LOCALIZER.read_text(encoding="utf-8")

# Rodril's original loader uses tonumber(Words[4]) before falling back to text.
# Preserve that for Data/*LocalizeTables.*txt while Korean KO_*.txt display
# records stay strings for Korean encoding/multiline handling.
if not re.search(r"not\s+IsKoreanSource[\s\S]{0,250}tonumber\(cText\)", source):
    fail("Rodril base LocalizeTables values are not converted with tonumber(cText)")

# Rodril normalizes empty quest strings to "0". Merge's automatic-quest
# migration later tests exactly s == "0" before clearing obsolete QBits.
if not re.search(
    r"for\s+i\s*,\s*v\s+in\s+Game\.QuestsTxt\s+do[\s\S]{0,180}#v\s*==\s*0"
    r"[\s\S]{0,120}Game\.QuestsTxt\[i\]\s*=\s*[\"']0[\"']",
    source,
):
    fail('blank Game.QuestsTxt entries are not normalized to the upstream "0" sentinel')

# Multiline continuation is a Korean KO extension. Rodril's base long table
# treats spacer/unrecognized lines as no-op records; appending them to the
# preceding value changes upstream semantics and can pollute display text.
if not re.search(
    r"elseif\s+currentRecord\s+and\s+IsKoreanSource\s+then"
    r"[\s\S]{0,450}currentRecord\.cText\s*=",
    source,
):
    fail("base Rodril spacer/unrecognized lines can still bleed into the previous text record")

if FAILED:
    print("Rodril localizer semantics audit: FAILED")
    sys.exit(1)

print("Rodril localizer semantics audit: OK")
print("  base numeric coercion: preserved")
print('  blank quest sentinel "0": preserved')
print("  base spacer-line bleed: blocked")
