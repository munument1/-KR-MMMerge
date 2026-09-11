#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
runtime = (root / 'Scripts/General/KoreanMovieSubtitles.lua').read_text(encoding='utf-8')

required = [
    'KMS.Version = "disabled"',
    'KMS.Disabled = true',
    'native movie playback is intentionally left untouched',
]
for token in required:
    assert token in runtime, f'missing disabled-subtitle marker: {token}'

for forbidden in [
    'events.ShowMovie',
    'events.PostRender',
    'CustomUI.ShowText',
    'mem.autohook',
    'NATIVE_MOVIE_DRAW_CALLS',
    'timeGetTime',
    'Game.IsMoviePlaying',
    'io.open',
    'SUBTITLE_FILES',
]:
    assert forbidden not in runtime, f'MMMerge movie playback must stay untouched: {forbidden}'

assert runtime.isascii(), 'disabled compatibility stub must stay ASCII-only'
print('MMMerge movie subtitles: disabled; no movie/UI/native hooks registered')
