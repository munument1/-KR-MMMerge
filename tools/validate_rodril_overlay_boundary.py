#!/usr/bin/env python3
"""Guard the Korean patch from silently becoming a gameplay fork of Rodril MMMerge."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Scripts"

# These direct General-script names are localization infrastructure rather than
# Korean-prefixed compatibility overlays. LocalizeTables.lua is the one known
# same-path override of Rodril MMMerge and is documented in UPSTREAM_BASELINE.md.
GENERAL_EXCEPTIONS = {
    "FNT_DBCS.lua",
    "LocalizeSignposts.lua",
    "LocalizeTables.lua",
}

REQUIRED_FILES = {
    "UPSTREAM_BASELINE.md",
    "Scripts/General/LocalizeTables.lua",
    "Scripts/General/ZZ_KoreanDaggerWoundHints.lua",
}

FORBIDDEN_UPSTREAM_AREAS = (
    "Scripts/Core",
    "Scripts/Modules",
    "Scripts/Structs",
)

# A translation overlay may observe game events and alter text/UI presentation,
# but it must not replace Rodril/MMExtension's core gameplay scheduling API.
# v1.0.20 accidentally carried a RefillTimer wrapper; keep that class of hook
# from silently returning under a harmless-looking Korean-prefixed filename.
PROTECTED_GAMEPLAY_GLOBALS = {
    "Timer",
    "RefillTimer",
    "RemoveTimer",
    "Sleep",
    "Sleep2",
}


def is_korean_overlay_name(name: str) -> bool:
    lower = name.lower()
    return lower.startswith("korean") or lower.startswith("zz_korean") or lower.startswith("zzz_korean") or lower.startswith("zzzz_korean")


def gameplay_global_overrides(path: Path) -> list[str]:
    if not is_korean_overlay_name(path.name):
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    found: list[str] = []
    for name in sorted(PROTECTED_GAMEPLAY_GLOBALS):
        assign = re.compile(rf"(?m)^\s*{re.escape(name)}\s*=")
        declare = re.compile(rf"(?m)^\s*function\s+{re.escape(name)}\s*\(")
        if assign.search(text) or declare.search(text):
            found.append(name)
    return found


def main() -> int:
    problems: list[str] = []

    for rel in sorted(REQUIRED_FILES):
        if not (ROOT / rel).is_file():
            problems.append(f"required overlay file missing: {rel}")

    # Korean localization should not carry core/runtime copies from the game
    # project. If one ever becomes necessary, it must be an explicit policy
    # change rather than an accidental copy into the release tree.
    for rel in FORBIDDEN_UPSTREAM_AREAS:
        directory = ROOT / rel
        if directory.exists():
            files = [p for p in directory.rglob("*") if p.is_file()]
            for path in files:
                problems.append(f"upstream gameplay/runtime area is vendored: {path.relative_to(ROOT)}")

    # Map scripts are especially fragile because a same-name file replaces the
    # installed MMMerge map script. Map-local translations must be implemented
    # through Korean-only general overlays instead.
    maps_dir = SCRIPTS / "Maps"
    if maps_dir.exists():
        for path in maps_dir.rglob("*.lua"):
            problems.append(f"map script override is forbidden: {path.relative_to(ROOT)}")

    general_dir = SCRIPTS / "General"
    if general_dir.exists():
        for path in general_dir.glob("*.lua"):
            if path.name not in GENERAL_EXCEPTIONS and not is_korean_overlay_name(path.name):
                problems.append(
                    "unclassified General script; use a Korean-prefixed overlay or document it: "
                    f"{path.relative_to(ROOT)}"
                )
            for name in gameplay_global_overrides(path):
                problems.append(
                    "localization overlay replaces protected gameplay global "
                    f"{name}: {path.relative_to(ROOT)}"
                )

    global_dir = SCRIPTS / "Global"
    if global_dir.exists():
        for path in global_dir.glob("*.lua"):
            if not is_korean_overlay_name(path.name):
                problems.append(
                    "unclassified Global script; use a Korean-prefixed overlay or document it: "
                    f"{path.relative_to(ROOT)}"
                )
            for name in gameplay_global_overrides(path):
                problems.append(
                    "localization overlay replaces protected gameplay global "
                    f"{name}: {path.relative_to(ROOT)}"
                )

    # Historical regression: this file used to duplicate Rodril's out01.lua
    # just to patch two localized hints.
    legacy_out01 = ROOT / "Scripts/Maps/out01.lua"
    if legacy_out01.exists():
        problems.append("legacy Rodril map override returned: Scripts/Maps/out01.lua")

    if problems:
        print("Rodril overlay boundary validation: FAILED", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print("Rodril overlay boundary validation: OK")
    print("Baseline: letr.rod/mmmerge Rodril_nightly_build @ c0b6b4e9532e80413d1a3c27cbe25f57538c9a29")
    print("Intentional upstream script-path overrides: 1 (Scripts/General/LocalizeTables.lua)")
    print("Upstream map-script overrides: 0")
    print("Protected gameplay global overrides in Korean overlays: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
