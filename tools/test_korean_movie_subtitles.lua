-- Standalone Lua 5.1 regression test for KoreanMovieSubtitles.lua.
local now = 0
local drawCalls = {}

timeGetTime = function() return now end
string.convert = function(s, from, to)
    assert(from == "utf8")
    assert(to == 949)
    return s
end

Game = {
    Lucida_fnt = 123,
    IsMoviePlaying = function() return true end
}
CustomUI = {
    ShowText = function(...)
        drawCalls[#drawCalls + 1] = {...}
    end
}
events = {}
Merge = nil
Log = nil

dofile("Scripts/General/KoreanMovieSubtitles.lua")
local KMS = KoreanMovieSubtitles

assert(KMS.NormalizeMovieName('  "7INTRO.smk"  ') == "7intro")
assert(KMS.NormalizeMovieName("Anims\\DragonHunters.bik") == "dragonhunters")
assert(KMS.ParseTimestamp("00:02:03,456") == 123456)

local cues = assert(KMS.Load("7intro"))
assert(#cues == 32)
assert(KMS.FindCue(cues, 7680).Utf8:find("아이언피스트", 1, true))
assert(KMS.FindCue(cues, 13000) == nil)

now = 1000
assert(KMS.StartMovie("7intro"))
now = 9000 -- 8 seconds into the movie
assert(KMS.GetActive() ~= nil)
events.PostRender()
assert(#drawCalls == 5, "expected four outline draws plus one foreground draw")
assert(drawCalls[#drawCalls][10] == 0xFFFF, "foreground subtitle should be white")

KMS.StopMovie()
assert(KMS.GetActive() == nil)
assert(KMS.StartMovie("movie-with-no-subtitle") == false)
print("Korean movie subtitle runtime: OK")
