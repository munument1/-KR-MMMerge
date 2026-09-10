-- Restore MM7-style local witness hostility for civilians in Antagarich.
--
-- Rodril's reputation framework is disabled for Antagarich, so the MM8 engine
-- fallback can leave nearby civilians and guards neutral when the party attacks
-- a civilian. Keep this compatibility fix local: only party-origin attacks on
-- Antagarich civilians alert nearby civilian/guard witnesses.

KoreanMM7CivilianWitnessFix = KoreanMM7CivilianWitnessFix or {}
KoreanMM7CivilianWitnessFix.WitnessRadius =
    KoreanMM7CivilianWitnessFix.WitnessRadius or 4096

local function isAntagarich()
    return TownPortalControls
        and TownPortalControls.MapOfContinent
        and Map
        and Map.MapStatsIndex ~= nil
        and TownPortalControls.MapOfContinent(Map.MapStatsIndex) == 2
end

local function getMonsterSource(mon)
    if not mon or not Game or not Game.Bolster or not Game.Bolster.MonstersSource then
        return nil
    end
    return Game.Bolster.MonstersSource[mon.Id]
end

local function isCivilian(mon)
    local src = getMonsterSource(mon)
    return src
        and const
        and const.Bolster
        and const.Bolster.Creed
        and src.Creed == const.Bolster.Creed.Peasant
        and mon.NPC_ID > 0
end

local function isGuard(mon)
    return mon and (mon.Group == 38 or mon.Group == 55)
end

local function isPresent(mon)
    if not mon or mon.HP <= 0 then
        return false
    end

    if not const or not const.AIState then
        return true
    end

    local state = mon.AIState
    return state ~= const.AIState.Dying
        and state ~= const.AIState.Dead
        and state ~= const.AIState.Removed
        and state ~= const.AIState.Invisible
end

local function getSqDistance(a, b)
    local ax, ay, az = XYZ(a)
    local bx, by, bz = XYZ(b)
    return (ax - bx) ^ 2 + (ay - by) ^ 2 + (az - bz) ^ 2
end

local function makeHostile(mon)
    if not mon then
        return
    end

    mon.Hostile = true
    mon.ShowAsHostile = true
    mon.HostileType = 4
end

local function alertWitnesses(target)
    if not target or not Map or not Map.Monsters then
        return
    end

    local radius = tonumber(KoreanMM7CivilianWitnessFix.WitnessRadius) or 4096
    if radius < 0 then
        radius = 0
    end
    local radiusSq = radius * radius

    -- The assaulted civilian always reacts, even if no other witness is near.
    makeHostile(target)

    for _, mon in Map.Monsters do
        if mon ~= target
                and isPresent(mon)
                and not mon.Hostile
                and (isCivilian(mon) or isGuard(mon))
                and getSqDistance(target, mon) <= radiusSq then
            makeHostile(mon)
        end
    end
end

function events.MonsterAttacked(t)
    if not isAntagarich()
            or not t
            or not t.Attacker
            or not t.Attacker.Player
            or not isCivilian(t.Monster) then
        return
    end

    alertWitnesses(t.Monster)
end

KoreanMM7CivilianWitnessFix.IsAntagarich = isAntagarich
KoreanMM7CivilianWitnessFix.IsCivilian = isCivilian
KoreanMM7CivilianWitnessFix.IsGuard = isGuard
KoreanMM7CivilianWitnessFix.AlertWitnesses = alertWitnesses
