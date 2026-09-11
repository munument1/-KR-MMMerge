-- Standalone Lua 5.1 regression: MMMerge movie subtitles must stay disabled.

events = {}
CustomUI = {ShowText = function() error('must not draw') end}
mem = {autohook2 = function() error('must not hook native movie loop') end}

dofile('Scripts/General/KoreanMovieSubtitles.lua')

assert(type(KoreanMovieSubtitles) == 'table')
assert(KoreanMovieSubtitles.Version == 'disabled')
assert(KoreanMovieSubtitles.Disabled == true)
assert(next(events) == nil, 'disabled stub must not register event handlers')

print('MMMerge movie subtitle compatibility stub: OK')
