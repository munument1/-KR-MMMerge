-- Regression harness for the retired ZZ_KoreanEmeraldWellTimerFix.lua.
-- A localization patch must not replace Rodril's gameplay timer functions.

local originalTimer = function() end
local originalRefillTimer = function() end

Timer = originalTimer
RefillTimer = originalRefillTimer
KoreanEmeraldWellTimerFix = nil

dofile("Scripts/General/ZZ_KoreanEmeraldWellTimerFix.lua")

assert(Timer == originalTimer, "retired Korean overlay replaced Timer")
assert(RefillTimer == originalRefillTimer, "retired Korean overlay replaced RefillTimer")
assert(KoreanEmeraldWellTimerFix and KoreanEmeraldWellTimerFix.Retired == true,
    "retired marker missing")
assert(KoreanEmeraldWellTimerFix.OriginalRefillTimer == nil,
    "retired overlay retained gameplay hook state")
assert(KoreanEmeraldWellTimerFix.Installed == nil,
    "retired overlay still reports an installed gameplay hook")

print("PASS: retired Emerald timer overlay is inert")
