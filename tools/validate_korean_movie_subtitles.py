#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
BASE = ROOT / "Data" / "Korean Subtitles"
EXPECTED = {
    "mm6": {"6intro.srt", "citytrtr.srt", "mm6end1.srt"},
    "mm7": {
        "7intro.srt", "7losegame.srt", "arbiter evil.srt", "arbiter good.srt",
        "endgame 1 good.srt", "family reunion.srt", "intro post.srt",
        "mm3 people evil.srt", "mm3 people good.srt", "pcout01.srt",
    },
    "mm8": {
        "DragonHunters.srt", "confluxkey.srt", "dragonsrevenge.srt",
        "overrept.srt", "skeltrans.srt", "wingame.srt",
    },
}
TIMING = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s+-->\s+"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$"
)


def ms(parts: tuple[str, ...]) -> int:
    h, m, s, milli = map(int, parts)
    return (((h * 60) + m) * 60 + s) * 1000 + milli


def validate_srt(path: Path) -> int:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    assert "\ufffd" not in text, f"replacement character in {path}"
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    cue_count = 0
    last_start = -1
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        timing_index = 1 if lines[0].strip().isdigit() else 0
        assert len(lines) > timing_index + 1, f"cue has no text: {path}: {block!r}"
        match = TIMING.match(lines[timing_index].strip())
        assert match, f"invalid timing in {path}: {lines[timing_index]!r}"
        start = ms(match.groups()[:4])
        finish = ms(match.groups()[4:])
        assert finish > start, f"non-positive cue duration in {path}"
        assert start >= last_start, f"out-of-order cue in {path}"
        assert any(line.strip() for line in lines[timing_index + 1:]), f"blank cue in {path}"
        last_start = start
        cue_count += 1
    assert cue_count > 0, f"no cues in {path}"
    return cue_count


def main() -> None:
    expected_paths = set()
    total_cues = 0
    for world, names in EXPECTED.items():
        world_dir = BASE / world
        actual = {p.name for p in world_dir.glob("*.srt")}
        assert actual == names, f"{world} subtitle inventory mismatch: expected={sorted(names)} actual={sorted(actual)}"
        for name in sorted(names):
            path = world_dir / name
            expected_paths.add(path)
            total_cues += validate_srt(path)

    assert sum(len(v) for v in EXPECTED.values()) == 19
    runtime = (ROOT / "Scripts" / "General" / "KoreanMovieSubtitles.lua").read_text("utf-8")
    required = [
        'string.convert, text, "utf8", 949',
        "events.ShowMovie",
        "events.PostRender",
        "Game.IsMoviePlaying",
        "CustomUI.ShowText",
        "mem.autohook2",
        "0x4BC9C7",
        "0x4BCBE6",
        "InstallNativeMovieFrameHooks",
    ]
    for token in required:
        assert token in runtime, f"runtime integration token missing: {token}"
    for path in expected_paths:
        rel = path.relative_to(ROOT).as_posix()
        assert rel in runtime, f"runtime map missing subtitle: {rel}"

    print(f"Korean cutscene subtitles: OK (19 files, {total_cues} cues; native Bink/Smacker hooks required)")


if __name__ == "__main__":
    main()
