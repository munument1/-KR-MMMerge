-- Compatibility fix for Emerald Island refill timers on older MMMerge cores.
--
-- The older RefillTimer implementation can advance an already-due refill
-- deadline while timers are being reconstructed after a save/load, without
-- actually invoking the refill callback. Emerald Island's HP/SP/Luck wells use
-- MapVar0/1/2 counters that are replenished only by those callbacks, so a
-- skipped callback can leave an otherwise unused well empty after loading.
--
-- Do not reset any MapVar directly here. That would turn save/load into a free
-- well refill exploit. Instead, only fix the timer scheduling semantics for
-- Emerald Island and leave the map's original event limits untouched.

KoreanEmeraldWellTimerFix = KoreanEmeraldWellTimerFix or {}
local Fix = KoreanEmeraldWellTimerFix

if Fix.Installed then
    return
end

local originalRefillTimer = RefillTimer
if type(originalRefillTimer) ~= "function" or type(Timer) ~= "function" then
    return
end

local function isEmeraldIsland()
    if not Map or type(Map.Name) ~= "string" then
        return false
    end
    local name = string.lower(Map.Name)
    return name == "7out01.odm" or name == "7out01"
end

local function getRefills()
    local sgd = internal and internal.SaveGameData
    if not sgd then
        return nil
    end
    sgd.TimerPassed = sgd.TimerPassed or {}
    local mapName = Map.Name
    sgd.TimerPassed[mapName] = sgd.TimerPassed[mapName] or {}
    return sgd.TimerPassed[mapName]
end

local function emeraldRefillTimer(f, period)
    period = period or 256
    local refills = getRefills()
    if not refills then
        return originalRefillTimer(f, period)
    end

    -- Match the stock default-mode RefillTimer start value. On a real map
    -- refill the callback is due immediately; otherwise keep the saved next
    -- refill deadline, falling back to now for an uninitialized map.
    local start
    if Map.Refilled then
        start = Game.Time
    else
        start = refills[period] or Game.Time
    end
    refills[period] = start

    -- Old Timer() calls the custom next-time function during registration when
    -- start is already due. The old NextRefill immediately moved the deadline
    -- into the future, which skipped f(). Return the same due time during that
    -- registration pass so f() runs on the next timer tick. This mirrors the
    -- newer MMMerge timer core's IsInit-aware behavior.
    local initializing = true
    local function nextRefill(time, timerPeriod, lastTick, isInit)
        if initializing or isInit then
            initializing = false
            return time
        end

        local nextTime = Game.Time + timerPeriod
        local current = getRefills()
        if current then
            current[timerPeriod] = nextTime
        end
        return nextTime
    end

    Timer(f, period, start, nextRefill)
    initializing = false
end

RefillTimer = function(f, period, third)
    -- Emerald Island's standard HP/SP/Luck refill events use the default
    -- two-argument form. Leave every other map and every explicit third-arg
    -- timer on the installed MMMerge implementation.
    if third == nil and isEmeraldIsland() then
        return emeraldRefillTimer(f, period)
    end
    return originalRefillTimer(f, period, third)
end

Fix.OriginalRefillTimer = originalRefillTimer
Fix.Installed = true
