-- Regression guard for the narrowed v1.0.24 numeric compatibility bridge.
-- The primary LocalizeTables loader owns all Rodril numeric semantics now; this
-- script may repair only positive NPCDataTxt.Joins permissions in live NPCs.

local function iterable(t)
    return setmetatable(t, {
        __call = function(self, _, key)
            return next(self, key)
        end
    })
end

Game = {
    NPCDataTxt = iterable({
        [815] = {Joins = 1},
        [824] = {Joins = 1},
        [900] = {Joins = 0}
    }),
    NPC = {
        [815] = {Joins = 0, Hired = false, House = 123},
        [824] = {Joins = 1, Hired = true, House = 456},
        [900] = {Joins = 0, Hired = false, House = 789}
    },
    Houses = {
        [48] = {Picture = 999}
    },
    MapStats = {
        [205] = {EaxEnvironments = 77}
    }
}

events = {}
KoreanLocalization = {}
Merge = {Log = {Info = 1}}
function Log() end

assert(loadfile("Scripts/General/ZZ_KoreanRodrilNumericLocalization.lua"))()
assert(KoreanLocalization.RodrilBroadNumericSafetyNetRetired == true,
    "broad numeric safety-net retired marker is missing")
assert(type(KoreanLocalization.SyncNPCJoinPermissions) == "function",
    "targeted NPC join repair was not exported")
assert(KoreanLocalization.ReapplyRodrilNumericLocalization == nil,
    "broad Data/*LocalizeTables numeric rewriter must stay retired")

local fixed = KoreanLocalization.SyncNPCJoinPermissions()
assert(fixed == 1, "expected only one live Joins repair, got " .. tostring(fixed))
assert(Game.NPC[815].Joins == 1, "missing live Joins permission was not repaired")
assert(Game.NPC[824].Joins == 1, "existing live Joins permission was changed")
assert(Game.NPC[900].Joins == 0, "zero static Joins must not be promoted")
assert(Game.NPC[815].Hired == false and Game.NPC[824].Hired == true,
    "join repair must never touch Hired state")
assert(Game.NPC[815].House == 123 and Game.NPC[824].House == 456,
    "join repair must never touch other NPC state")
assert(Game.Houses[48].Picture == 999,
    "retired broad pass must not rewrite house numeric fields")
assert(Game.MapStats[205].EaxEnvironments == 77,
    "retired broad pass must not rewrite map numeric fields")

-- All registered hooks must remain equally narrow.
Game.NPC[815].Joins = 0
assert(type(events.GameInitialized2) == "function")
events.GameInitialized2()
assert(Game.NPC[815].Joins == 1 and Game.NPC[815].Hired == false)

Game.NPC[815].Joins = 0
assert(type(events.LoadMap) == "function")
events.LoadMap()
assert(Game.NPC[815].Joins == 1 and Game.NPC[815].House == 123)

Game.NPC[815].Joins = 0
assert(type(events.TxtFilesReloaded) == "function")
events.TxtFilesReloaded()
assert(Game.NPC[815].Joins == 1)

print("PASS: compatibility bridge repairs only live NPC Joins permissions")
