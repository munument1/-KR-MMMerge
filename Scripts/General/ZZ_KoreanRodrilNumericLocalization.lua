-- Compatibility bridge for saves/installations affected by the v1.0.24
-- LocalizeTables numeric-type regression.
--
-- The primary LocalizeTables override now preserves Rodril's original
-- tonumber() semantics, so the former broad late pass that reparsed every
-- numeric Data/*LocalizeTables.*txt field is retired. Keep only the one piece
-- that existing saves may still need: copy a positive static NPCDataTxt.Joins
-- permission into the live Game.NPC entry. NPCFollowers reads Game.NPC.Joins
-- when deciding whether to expose the Hire topic.
--
-- v1.0.25 field reports also exposed a second failure mode: Rodril deducts the
-- hireling fee immediately before calling NPCFollowers.Add(). If Add() sees a
-- stale follower-list entry, or an interrupted earlier hire inserted the entry
-- before Hired was committed, the player can lose gold without the hire branch
-- completing. The guard below repairs only that inconsistent Add() state and
-- leaves normal Rodril hire semantics untouched.

KoreanLocalization = KoreanLocalization or {}

local function syncNPCJoinPermissions()
	if not Game or not Game.NPCDataTxt or not Game.NPC then
		return 0
	end

	local fixed = 0
	for id, source in Game.NPCDataTxt do
		local joins = source and source.Joins
		if type(joins) == "number" and joins > 0 then
			local ok, current = pcall(function() return Game.NPC[id] end)
			if ok and current then
				local currentJoins
				pcall(function() currentJoins = current.Joins end)
				if type(currentJoins) ~= "number" or currentJoins < joins then
					if pcall(function() current.Joins = joins end) then
						fixed = fixed + 1
					end
				end
			end
		end
	end

	if fixed > 0 and Log and Merge and Merge.Log then
		Log(Merge.Log.Info, "Restored %s live NPC join permissions from NPCDataTxt.", fixed)
	end
	return fixed
end

local function followerIndex(id)
	if not vars or type(vars.NPCFollowers) ~= "table" then
		return nil
	end
	if table and type(table.find) == "function" then
		return table.find(vars.NPCFollowers, id)
	end
	for k, v in pairs(vars.NPCFollowers) do
		if v == id then
			return k
		end
	end
	return nil
end

local function installHireAddGuard()
	if not NPCFollowers or type(NPCFollowers.Add) ~= "function" then
		return false
	end
	if KoreanLocalization.HireAddGuardInstalled then
		return true
	end

	local originalAdd = NPCFollowers.Add
	NPCFollowers.Add = function(id)
		vars.NPCFollowers = vars.NPCFollowers or {}

		-- Preserve the upstream result on a clean hire. pcall lets us inspect the
		-- only recoverable partial state: the id was inserted but Hired was not.
		local ok, result = pcall(originalAdd, id)
		if ok and result then
			return true
		end

		local pos = followerIndex(id)
		local npc
		if Game and Game.NPC then
			pcall(function() npc = Game.NPC[id] end)
		end

		-- Rodril's Add() returns false when the id is already present. If the live
		-- NPC is not actually marked hired, this is a stale/interrupted hire, not
		-- a legitimate duplicate. Complete that one missing state transition and
		-- return true so Rodril can continue MoveNPC/hide/topic cleanup.
		if pos and npc then
			local hired
			pcall(function() hired = npc.Hired end)
			if not hired then
				local committed = pcall(function() npc.Hired = true end)
				if committed then
					if Log and Merge and Merge.Log then
						Log(Merge.Log.Info, "Recovered interrupted NPC follower hire for NPC %s.", id)
					end
					return true
				end
			end
		end

		if not ok then
			error(result)
		end
		return result
	end

	KoreanLocalization.HireAddGuardInstalled = true
	return true
end

KoreanLocalization.SyncNPCJoinPermissions = syncNPCJoinPermissions
KoreanLocalization.InstallHireAddGuard = installHireAddGuard
KoreanLocalization.RodrilBroadNumericSafetyNetRetired = true

-- NPCFollowers is normally loaded before this alphabetically-late bridge.
-- Keep event-time retries for unusual loader orders and reloads.
installHireAddGuard()

function events.GameInitialized2()
	syncNPCJoinPermissions()
	installHireAddGuard()
end

function events.LoadMap()
	syncNPCJoinPermissions()
	installHireAddGuard()
end

function events.LoadMapScripts()
	installHireAddGuard()
end

function events.TxtFilesReloaded()
	syncNPCJoinPermissions()
	installHireAddGuard()
end
