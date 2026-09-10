-- Standalone Lua 5.1 regression for the 1-based Game.TransTxt repair.
Game = {TransTxt = {}}
events = {}
KoreanText = {EncodeOnce = function(s) return s end}

dofile("Scripts/General/ZZZZ_KoreanTransTxtIndexFix.lua")
local KTI = KoreanTransTxtIndexFix
local records = KTI.LoadRecords()
assert(records[1] and records[25] and records[41])
assert(records[0] == nil)

local ok, count = KTI.Apply()
assert(ok and count > 0)
assert(Game.TransTxt[1] == records[1])
assert(Game.TransTxt[25] == records[25])
assert(Game.TransTxt[41] == records[41])
assert(Game.TransTxt[0] == nil)
print("Korean TransTxt 1-based runtime repair: OK (" .. tostring(count) .. " records)")
