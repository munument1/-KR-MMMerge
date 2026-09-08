-- Regression harness for ZZ_KoreanEmeraldWellTimerFix.lua.
-- It models the older MMMerge Timer registration behavior that could skip a
-- due refill callback while reconstructing timers after load.

local LastTick = 1000
local originalCalls = 0
local registered

Game = {Time = 1000}
Map = {Name = "7out01.odm", Refilled = true}
internal = {SaveGameData = {TimerPassed = {}}}

function Timer(f, period, start, exact)
    if start and start <= Game.Time and start <= LastTick then
        start = exact(start, period, LastTick)
    end
    registered = {f = f, period = period, start = start, exact = exact}
end

function RefillTimer(f, period, third)
    originalCalls = originalCalls + 1
end

KoreanEmeraldWellTimerFix = nil

dofile("Scripts/General/ZZ_KoreanEmeraldWellTimerFix.lua")

local fired = 0
RefillTimer(function()
    fired = fired + 1
end, 100)

assert(originalCalls == 0, "Emerald default refill timer was not intercepted")
assert(registered and registered.start == Game.Time,
    "due Emerald refill was advanced during timer reconstruction")

-- Simulate the next game timer tick: the refill callback must still be due.
registered.f()
assert(fired == 1, "Emerald refill callback did not run")
local nextTime = registered.exact(registered.start, registered.period, LastTick)
assert(nextTime == Game.Time + registered.period, "next refill deadline is wrong")
assert(internal.SaveGameData.TimerPassed[Map.Name][registered.period] == nextTime,
    "next refill deadline was not persisted")

-- Reproduce a save/load reconstruction where the saved refill deadline is
-- already due. The wrapper must again keep it due instead of skipping it.
Map.Refilled = false
Game.Time = 2000
LastTick = 2000
internal.SaveGameData.TimerPassed[Map.Name][100] = 2000
registered = nil
fired = 0

RefillTimer(function()
    fired = fired + 1
end, 100)

assert(registered and registered.start == Game.Time,
    "save/load reconstruction skipped an already-due Emerald refill")
registered.f()
assert(fired == 1, "save/load refill callback did not run")

-- Other maps must keep the installed MMMerge behavior untouched.
Map.Name = "7out02.odm"
registered = nil
RefillTimer(function() end, 100)
assert(originalCalls == 1, "non-Emerald refill timer was unexpectedly intercepted")

print("PASS: Emerald Island due refill callbacks survive old Timer reconstruction")
