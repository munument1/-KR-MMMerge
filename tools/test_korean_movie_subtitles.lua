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

assert(KMS.Version == "1.2")
assert(KMS.NormalizeMovieName('  "7INTRO.smk"  ') == "7intro")
assert(KMS.NormalizeMovieName("Anims\\DragonHunters.bik") == "dragonhunters")
assert(KMS.ParseTimestamp("00:02:03,456") == 123456)

local cues = assert(KMS.Load("7intro"))
assert(#cues == 32)
assert(KMS.FindCue(cues, 7680).Utf8:find("아이언피스트", 1, true))
assert(KMS.FindCue(cues, 13000) == nil)

assert(KMS.NativeFrameHooksInstalled == true)
assert(KMS.NativeFrameHookCount == 2)
assert(type(nativeHooks[0x4BC9CC]) == "function", "Bink frame hook was not installed")
assert(type(nativeHooks[0x4BCBEB]) == "function", "Smacker frame hook was not installed")
assert(KMS.NativeSafeStems.dragonhunters == true)
assert(KMS.NativeSafeStems["7intro"] == nil)
assert(KMS.NativeSafeStems["6intro"] == nil)

-- MM6/MM7 native callbacks must never draw. This is the crash regression.
now = 1000
assert(KMS.StartMovie("7intro"))
now = 9000
nativeHooks[0x4BC9CC]()
assert(#drawCalls == 0, "MM7 native movie callback must be display-disabled")

-- The ordinary renderer fallback remains available for non-native-safe movies.
events.PostRender()
assert(#drawCalls == 5, "PostRender fallback did not draw MM7 subtitle")
assert(drawCalls[#drawCalls][10] == 0xFFFF)

-- MM8 movies keep native-frame subtitles.
drawCalls = {}
now = 20000
assert(KMS.StartMovie("dragonhunters"))
local mm8cues = assert(KMS.Load("dragonhunters"))
now = 20000 + mm8cues[1].Start + 1
nativeHooks[0x4BC9CC]()
assert(#drawCalls == 5, "MM8 native Bink frame hook did not draw subtitle")
assert(drawCalls[#drawCalls][10] == 0xFFFF)

KMS.StopMovie()
assert(KMS.GetActive() == nil)
assert(KMS.StartMovie("movie-with-no-subtitle") == false)
print("Korean movie subtitle runtime: OK")
