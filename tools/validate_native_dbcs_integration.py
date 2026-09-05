#!/usr/bin/env python3
"""Static regression checks for the MMMerge Korean native DBCS renderer."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
UPSTREAM_REV = "aea1b22666ef556f34a71b4f3945904b04de1466"
UPSTREAM_BLOB = "867d3d9e5077205ab1cd691a49c25e664bd6f09f"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


native_path = ROOT / "Scripts/General/FNT_DBCS.lua"
compat_path = ROOT / "Scripts/General/KoreanFont.lua"
text_path = ROOT / "Scripts/General/KoreanFontText.lua"
feedback_path = ROOT / "Scripts/General/ZZ_KoreanGameplayFeedbackFixes.lua"
ini_path = ROOT / "Data/LocalizeConf.ini"

for path in (native_path, compat_path, text_path, feedback_path, ini_path):
    require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")

# .gitattributes intentionally checks Lua files out as CRLF for the Windows
# game.  Normalize only for comparison with the pinned upstream LF Git blob.
native_bytes = native_path.read_bytes().replace(b"\r\n", b"\n")
native = native_bytes.decode("utf-8")
compat = compat_path.read_text(encoding="utf-8")
text_util = text_path.read_text(encoding="utf-8")
feedback = feedback_path.read_text(encoding="utf-8")
ini = ini_path.read_text(encoding="ascii")

# Preserve and verify the exact upstream baseline separately. The shipped
# renderer intentionally differs by the reviewed safety/diagnostic changes.
baseline = ROOT / "tools/fixtures/FNT_DBCS.upstream.lua"
require(baseline.is_file(), "pinned upstream baseline missing")
require(git_blob_sha(baseline.read_bytes().replace(b"\r\n", b"\n")) == UPSTREAM_BLOB,
        "pinned upstream baseline changed")
require('SafetyRevision = "ui-test1"' in native, "test renderer revision mismatch")
require('EngineCap = 2047' in native, "MM8 engine buffer bound missing")
require('local longWrapBuffer = mem.StaticAlloc(WRAP_CAP + 1)' in native,
        "owned long-wrap allocation missing")
require('__mode = "v"' not in native, "unbounded weak-string cache returned")

for token in (
    "GetLineWidth",
    "WordWrap",
    "DrawTextLimited",
    "BlitGlyph",
    "LEGACY MARKER TEXT BRIDGE",
    "NativeInstalled = not installFailed",
    'euc_kr    = {leadMin = 0xA1',
):
    require(token in native, f"native renderer contract missing: {token}")

# The compatibility layer must never regress into the retired host-glyph scratch
# architecture or install a second set of executable hooks.
for forbidden in (
    "mem.hook",
    "mem.hookfunction",
    "mem.asmpatch",
    "mem.asmhook",
    "mem.copy",
    "setCharShape",
    "setCharWidth",
):
    require(forbidden not in compat, f"KoreanFont.lua reintroduced low-level renderer code: {forbidden}")
require('KF.SafetyVersion = "1.0.15-native-dbcs"' in compat, "compatibility API version mismatch")
require("function KF.encodeSpecial(str)\n    return str\nend" in compat, "new marker encoding must remain retired")
require(not (ROOT / "Scripts/General/KoreanFontLegacy.lua").exists(), "legacy glyph-7 renderer must not ship")

require('KT.Version = "1.0.15-native"' in text_util, "KoreanText native-mode version mismatch")
require("lowByte <= 0xFE" in text_util, "fixed-string EUC-KR trail range must stop at FE")

# The old one-word map fix repeatedly touched evt.str/evt.hint around map load.
# It is intentionally a no-op upgrade stub now.
for forbidden in (
    "function events.BeforeLoadMapScripts",
    "function events.LoadMapScripts",
    "function events.LoadMap",
    "function events.AfterLoadMap",
    "function events.Tick",
    "localizeProxy",
):
    require(forbidden not in feedback, f"retired map-transition rewrite returned: {forbidden}")

require("encoding=euc_kr" in ini, "LocalizeConf.ini must select EUC-KR")
require("fontSizes=14,16,29" in ini, "Korean page-font heights must be 14,16,29")
require("specialFonts=Autonote:15b" in ini, "Autonote must keep the 15b page font")

# Existing Korean assets cover the punctuation page and all KS X 1001 Hangul
# pages used by the patch.  Check every required page for every host size.
required_hi = [0xA1, *range(0xB0, 0xC9)]
for tag in ("14", "15b", "16", "29"):
    for hi in required_hi:
        page = ROOT / f"DataFiles/DBCS_{tag}_{hi:02X}.fnt"
        require(page.is_file() and page.stat().st_size > 0, f"missing Korean page font: {page.name}")

print("PASS: upstream provenance, safety contracts, compatibility API and page presence validated; run runtime regressions separately")
