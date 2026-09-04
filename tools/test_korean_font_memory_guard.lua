-- Offline regression harness for Scripts/General/KoreanFont.lua.
-- Run from the repository root with a Lua 5.1-compatible interpreter, e.g.:
--   texlua tools/test_korean_font_memory_guard.lua
--
-- This does not emulate MM8 rendering. It exercises the legacy DBCS hook's
-- memory bookkeeping with fake FNT allocations and verifies that:
--   1) glyph-7 scratch bytes and metrics are restored exactly,
--   2) hidden DBCS byte metrics and space width are restored,
--   3) an evicted/reused DBCS page pointer is reloaded,
--   4) a reused host-font address is never overwritten by stale restore data.

local MEM = {}
local function rb(a) return MEM[a] or 0 end
local function wb(a, v) MEM[a] = v % 256 end
local function rle(a, n)
    local v = 0
    for i = 0, n - 1 do
        v = v + rb(a + i) * 2 ^ (8 * i)
    end
    return v
end
local function wle(a, n, v)
    for i = 0, n - 1 do
        wb(a + i, math.floor(v / 2 ^ (8 * i)))
    end
end
local function proxy(n)
    return setmetatable({}, {
        __index = function(_, a) return rle(a, n) end,
        __newindex = function(_, a, v) wle(a, n, v) end
    })
end

mem = {
    u1 = setmetatable({}, {
        __index = function(_, a) return rb(a) end,
        __newindex = function(_, a, v) wb(a, v) end
    }),
    i2 = proxy(2),
    i4 = proxy(4)
}
function mem.string(a, n)
    local t = {}
    for i = 0, n - 1 do
        t[#t + 1] = string.char(rb(a + i))
    end
    return table.concat(t)
end
function mem.copy(a, s)
    for i = 1, #s do
        wb(a + i - 1, s:byte(i))
    end
end

local installedHook
function mem.asmproc(_) return 0x500000 end
function mem.hook(_, fn) installedHook = fn end
function mem.asmpatch(...) end

offsets = {MMVersion = 8}
Merge = nil
Log = nil
Party = setmetatable({}, {__index = function() return {Name = ""} end})

local function makeFont(base, h, width, seed)
    wb(base, 0)
    wb(base + 1, 255)
    wb(base + 5, h)
    wle(base + 12, 4, 0x123456 + seed)
    local pos = 0
    for c = 0, 255 do
        local w = width
        if c == 32 then w = 3 end
        if c == 7 then w = 4 end
        wle(base + 32 + 12 * c, 4, 1)
        wle(base + 36 + 12 * c, 4, w)
        wle(base + 40 + 12 * c, 4, 2)
        wle(base + 3104 + 4 * c, 4, pos)
        local start = base + 4128 + pos
        for i = 0, h * w - 1 do
            wb(start + i, (seed + c + i) % 251 + 1)
        end
        pos = pos + h * w + 8
    end
end

local HOST = 0x10000
local PAGE = 0x30000
makeFont(HOST, 16, 6, 11)
makeFont(PAGE, 14, 8, 37)

local loadCount = 0
Game = {Autonote_fnt = 0}
function Game.CanLoadFileFromLod(_) return true end
function Game.LoadDataFileFromLod(_)
    loadCount = loadCount + 1
    return PAGE
end

local realOpen = io.open
io.open = function(path, mode)
    if path == "Data/LocalizeConf.ini" then
        local obj = {}
        function obj:read(_) return "[Settings]\nencoding=euc_kr\n" end
        function obj:close() end
        return obj
    end
    return realOpen(path, mode)
end

mem.copy(0x449C3B, string.char(58, 10, 114, 5, 58, 74, 1, 118, 23))
dofile("Scripts/General/KoreanFont.lua")
assert(installedHook, "KoreanFont hook not installed")

local function getStart(font, c)
    return mem.i4[font + 3104 + 4 * c] + 4128 + font
end
local function metrics(font, c)
    return mem.i4[font + 32 + 12 * c], mem.i4[font + 36 + 12 * c], mem.i4[font + 40 + 12 * c]
end
local function feed(bytes)
    for _, b in ipairs(bytes) do
        installedHook({cl = b, edx = HOST})
    end
end

local scratchAddr = getStart(HOST, 7)
local originalScratch = mem.string(scratchAddr, 16 * 8, true)
local a7, w7, c7 = metrics(HOST, 7)
local spaceW = mem.i4[HOST + 36 + 12 * 32]
local ah, wh, ch = metrics(HOST, 0xB0)
local al, wl, cl = metrics(HOST, 0xA1)

feed({14, 32, 14, 0xB0, 0xA1, 7})
assert(mem.i4[HOST + 36 + 12 * 7] == 8, "glyph 7 width not replaced")
feed({15})
assert(mem.string(scratchAddr, 16 * 8, true) == originalScratch, "scratch bytes not restored")
local aa, ww, cc = metrics(HOST, 7)
assert(aa == a7 and ww == w7 and cc == c7, "glyph 7 metrics not restored")
assert(mem.i4[HOST + 36 + 12 * 32] == spaceW, "space width not restored")
local x, y, z = metrics(HOST, 0xB0)
assert(x == ah and y == wh and z == ch, "high byte metrics not restored")
x, y, z = metrics(HOST, 0xA1)
assert(x == al and y == wl and z == cl, "low byte metrics not restored")
assert(loadCount == 1, "unexpected first page load count " .. loadCount)

-- Simulate page eviction/reuse.
wb(PAGE, 1)
feed({14, 32, 14, 0xB0, 0xA1, 7, 15})
assert(loadCount == 2, "stale DBCS page cache was not reloaded: " .. loadCount)

-- Simulate host-font allocation reuse between callbacks. The renderer must
-- drop old state without writing cached values into the new allocation.
makeFont(HOST, 16, 6, 11)
feed({14})
wb(HOST, 99)
mem.i4[HOST + 36 + 12 * 32] = 77
feed({32})
assert(mem.i4[HOST + 36 + 12 * 32] == 77, "stale host restore overwrote reused allocation")

print("PASS: exact restore; stale page reload; stale host write blocked")
