-- Standalone Lua 5.1 regression test for KoreanMovieSubtitles.lua.
local now = 0
local drawCalls = {}
local nativeHooks = {}

timeGetTime = function() return now end
string.convert = function(s, from, to)
    assert(from == "utf8")
    assert(to == 949)
    return s
end

Game = {
    Version = 8,
    Lucida_fnt = 123,
    IsMoviePlaying = function() return true end
}
CustomUI = {
    ShowText = function(...)
        drawCalls[#drawCalls + 1] = {...}
    end
}
mem = {
    u1 = setmetatable({}, {
        __index = function(_, address)
            if address == 0x4BC9C7 or address == 0x4BCBE6 then
                return 0xE8
            end
            return 0
        end
    }),
    autohook2 = function(address, handler)
        nativeHooks[address] = handler
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

-- Rodril/MM8 full-screen movies run a blocking native Bink/Smacker loop, so
-- subtitles must also be drawn from the native movie-frame call sites rather
-- than relying solely on the normal PostRender event.
assert(KMS.NativeFrameHooksInstalled == true)
assert(KMS.NativeFrameHookCount == 2)
assert(type(nativeHooks[0x4BC9CC]) == "function", "Bink frame hook was not installed")
assert(type(nativeHooks[0x4BCBEB]) == "function", "Smacker frame hook was not installed")

now = 1000
assert(KMS.StartMovie("7intro"))
now = 9000 -- 8 seconds into the movie
assert(KMS.GetActive() ~= nil)
nativeHooks[0x4BC9CC]()
assert(#drawCalls == 5, "native Bink frame hook did not draw subtitle")
assert(drawCalls[#drawCalls][10] == 0xFFFF, "native-hook foreground subtitle should be white")

-- Retain PostRender as a fallback for movie-player variants that yield back to
-- the normal renderer.
drawCalls = {}
events.PostRender()
assert(#drawCalls == 5, "PostRender fallback did not draw subtitle")
assert(drawCalls[#drawCalls][10] == 0xFFFF, "foreground subtitle should be white")

KMS.StopMovie()
assert(KMS.GetActive() == nil)
assert(KMS.StartMovie("movie-with-no-subtitle") == false)
print("Korean movie subtitle runtime: OK")
