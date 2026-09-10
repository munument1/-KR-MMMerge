-- Regression guard for the narrowed Rodril compatibility bridge.
-- Primary LocalizeTables owns numeric semantics; this script may repair only
-- positive NPCDataTxt.Joins permissions and interrupted NPC follower Add state.

local function iterable(t)
    return setmetatable(t, {
        __call = function(self, _, key)
            return next(self, key)
        end
    })
end

if not table.find then
    function table.find(t, value)
        for k, v in pairs(t) do
            if v == value then
                return k
            end
        end
        return nil
    end
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
assert(type(KoreanLocalization.InstallHireAddGuard) == "function",
    "hire Add guard installer was not exported")
assert(KoreanLocalization.ReapplyRodrilNumericLocalization == nil,
    "broad Data/*LocalizeTables numeric rewriter must stay retired")

local fixed = KoreanLocalization.SyncNPCJoinPermissions()
assert(fixed == 1, "expected only one live Joins repair, got " .. tostring(fixed))
assert(Game.NPC[815].Joins == 1, "missing live Joins permission was not repaired")
assert(Game.NPC[824].Joins == 1, "existing live Joins permission was changed")
assert(Game.NPC[900].Joins == 0, "zero static Joins must not be promoted")
assert(Game.NPC[815].Hired == false and Game.NPC[824].Hired == true,
    "join permission repair must never touch Hired state")
assert(Game.NPC[815].House == 123 and Game.NPC[824].House == 456,
    "join permission repair must never touch other NPC state")
assert(Game.Houses[48].Picture == 999,
    "retired broad pass must not rewrite house numeric fields")
assert(Game.MapStats[205].EaxEnvironments == 77,
    "retired broad pass must not rewrite map numeric fields")

-- All registered hooks must keep Joins repair equally narrow.
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

-- Rodril deducts gold before NPCFollowers.Add(). A stale list entry with
-- Hired=false therefore used to make Add return false after the player paid.
-- The compatibility guard must turn exactly that inconsistent state into a
-- successful Add so Rodril's existing HireNPC function can finish normally.
vars = {NPCFollowers = {815}}
Game.NPC[815].Hired = false
NPCFollowers = {}
NPCFollowers.Add = function(id)
    if table.find(vars.NPCFollowers, id) then
        return false
    end
    table.insert(vars.NPCFollowers, id)
    Game.NPC[id].Hired = true
    return true
end
KoreanLocalization.HireAddGuardInstalled = nil
assert(KoreanLocalization.InstallHireAddGuard())
assert(NPCFollowers.Add(815) == true,
    "stale follower-list entry should be recovered as a completed Add")
assert(Game.NPC[815].Hired == true,
    "interrupted hire recovery did not commit Hired=true")
assert(#vars.NPCFollowers == 1 and vars.NPCFollowers[1] == 815,
    "interrupted hire recovery must not duplicate follower ids")

-- A legitimate duplicate (already Hired=true) keeps Rodril's false result.
assert(NPCFollowers.Add(815) == false,
    "legitimate already-hired duplicate must keep upstream Add semantics")
assert(#vars.NPCFollowers == 1,
    "legitimate duplicate must not change follower list")

-- If upstream Add partially inserts the id and then errors before committing
-- Hired, the wrapper may recover that exact partial state instead of leaving a
-- paid-but-not-hired NPC behind.
vars.NPCFollowers = {}
Game.NPC[824].Hired = false
NPCFollowers.Add = function(id)
    table.insert(vars.NPCFollowers, id)
    error("simulated interrupted Hired write")
end
KoreanLocalization.HireAddGuardInstalled = nil
assert(KoreanLocalization.InstallHireAddGuard())
assert(NPCFollowers.Add(824) == true,
    "partial Add error with inserted id should be recoverable")
assert(Game.NPC[824].Hired == true,
    "partial Add recovery did not restore Hired=true")
assert(#vars.NPCFollowers == 1 and vars.NPCFollowers[1] == 824,
    "partial Add recovery must keep exactly one follower id")

-- An unrelated Add error that did not insert the id must still surface; the
-- Korean bridge must not silently turn arbitrary failures into hires.
vars.NPCFollowers = {}
Game.NPC[900].Hired = false
NPCFollowers.Add = function()
    error("unrelated failure")
end
KoreanLocalization.HireAddGuardInstalled = nil
assert(KoreanLocalization.InstallHireAddGuard())
local ok = pcall(function() NPCFollowers.Add(900) end)
assert(ok == false, "unrelated Add failures must not be swallowed")
assert(#vars.NPCFollowers == 0 and Game.NPC[900].Hired == false,
    "unrelated Add failure must not fabricate follower state")

print("PASS: compatibility bridge repairs Joins and interrupted hire Add state only")
