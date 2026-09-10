-- Regression guard for the narrow Rodril compatibility bridge.
-- Primary LocalizeTables owns numeric semantics; this script may repair only
-- positive NPCDataTxt.Joins permissions and interrupted NPC follower state.

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
        [815] = {Joins = 0, Hired = false, House = 123, Events = {[0] = 0, 0, 0, 0, 0, 0}},
        [824] = {Joins = 1, Hired = true, House = 456, Events = {[0] = 0, 0, 0, 0, 0, 0}},
        [900] = {Joins = 0, Hired = false, House = 789, Events = {[0] = 0, 0, 0, 0, 0, 0}}
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
assert(type(KoreanLocalization.InstallFollowerTopicAliases) == "function",
    "follower topic alias installer was not exported")
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

-- Rodril defines the topic ids only as NPCFollowers fields, yet its hire and
-- dismiss transaction bodies still contain one bare DismissNPCTopic and one
-- bare HireNPCTopic reference.  Install aliases without overwriting an
-- already-defined external value.
_G.HireNPCTopic = nil
_G.DismissNPCTopic = nil
NPCFollowers = {
    HireNPCTopic = 1512,
    DismissNPCTopic = 1511
}
assert(KoreanLocalization.InstallFollowerTopicAliases() == true,
    "Rodril follower topic aliases were not installed")
assert(HireNPCTopic == 1512 and DismissNPCTopic == 1511,
    "Rodril bare follower topic aliases have wrong values")
_G.HireNPCTopic = 777
assert(KoreanLocalization.InstallFollowerTopicAliases() == true)
assert(HireNPCTopic == 777,
    "compatibility alias must not overwrite an existing external global")
_G.HireNPCTopic = 1512

-- Rodril deducts gold before NPCFollowers.Add(). A stale list entry with
-- Hired=false must be recoverable so the original transaction can continue.
vars = {NPCFollowers = {815}}
Game.NPC[815].Hired = false
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

-- A normal duplicate already marked hired remains false when there is no
-- active Hire topic/current-NPC transaction to resume.
function GetCurrentNPC() return nil end
assert(NPCFollowers.Add(815) == false,
    "legitimate already-hired duplicate must keep upstream Add semantics")
assert(#vars.NPCFollowers == 1,
    "legitimate duplicate must not change follower list")

-- A previous transaction may have already inserted the id and set Hired=true
-- but died before replacing Hire with Dismiss.  If that same NPC is currently
-- being hired and still exposes the Hire topic, resume the upstream post-Add
-- branch instead of charging money and returning false forever.
Game.NPC[815].Events[2] = NPCFollowers.HireNPCTopic
function GetCurrentNPC() return 815 end
assert(NPCFollowers.Add(815) == true,
    "Hired=true plus stale Hire topic should resume the paid hire transaction")
assert(#vars.NPCFollowers == 1 and Game.NPC[815].Hired == true,
    "resumed paid hire must not duplicate or lower follower state")
Game.NPC[815].Events[2] = NPCFollowers.DismissNPCTopic
assert(NPCFollowers.Add(815) == false,
    "completed follower with Dismiss topic must remain a normal duplicate")

-- If upstream Add partially inserts the id and then errors before committing
-- Hired, the wrapper may recover that exact partial state.
vars.NPCFollowers = {}
Game.NPC[824].Hired = false
Game.NPC[824].Events[1] = 0
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

-- An unrelated Add error that did not insert the id must still surface.
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

print("PASS: compatibility bridge repairs Joins and interrupted Rodril follower hire state only")
