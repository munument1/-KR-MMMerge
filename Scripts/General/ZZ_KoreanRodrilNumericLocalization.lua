-- Compatibility bridge for Rodril NPC follower/localization state.
--
-- The primary LocalizeTables override preserves Rodril's original tonumber()
-- semantics.  This file therefore stays deliberately narrow: it repairs only
-- the live NPC Joins permission lost by older Korean builds and follower-hire
-- states that can leave the player charged without the hire transaction being
-- allowed to finish.

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

local function npcHasEvent(npc, eventId)
	if not npc or not npc.Events or type(eventId) ~= "number" then
		return false
	end
	for i = 0, 5 do
		local value
		local ok = pcall(function() value = npc.Events[i] end)
		if ok and value == eventId then
			return true
		end
	end
	return false
end

-- Rodril's NPCFollowers.lua stores the ids on NPCFollowers.*, but two old
-- transaction lines still reference bare HireNPCTopic/DismissNPCTopic globals.
-- No such globals are defined anywhere in the Rodril tree.  Supplying aliases
-- here lets those original lines use the ids they clearly intended without
-- replacing or forking the upstream NPCFollowers.lua file.
local function installFollowerTopicAliases()
	if not NPCFollowers then
		return false
	end
	local hire = NPCFollowers.HireNPCTopic
	local dismiss = NPCFollowers.DismissNPCTopic
	if type(hire) ~= "number" or type(dismiss) ~= "number" then
		return false
	end
	if rawget(_G, "HireNPCTopic") == nil then
		_G.HireNPCTopic = hire
	end
	if rawget(_G, "DismissNPCTopic") == nil then
		_G.DismissNPCTopic = dismiss
	end
	KoreanLocalization.FollowerTopicAliasesInstalled = true
	return true
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

		local ok, result = pcall(originalAdd, id)
		if ok and result then
			return true
		end

		local pos = followerIndex(id)
		local npc
		if Game and Game.NPC then
			pcall(function() npc = Game.NPC[id] end)
		end

		if pos and npc then
			local hired
			pcall(function() hired = npc.Hired end)

			-- Partial Add: id was inserted but Hired was never committed.
			if not hired then
				local committed = pcall(function() npc.Hired = true end)
				if committed then
					if Log and Merge and Merge.Log then
						Log(Merge.Log.Info, "Recovered interrupted NPC follower hire for NPC %s.", id)
					end
					return true
				end
			end

			-- Older failed attempts can get one step farther: Add already inserted
			-- the follower and set Hired=true, but the Hire topic is still active
			-- because the transaction died before topic cleanup.  A genuinely
			-- completed follower is given Dismiss instead, so this combination is
			-- safe to resume when the same NPC is the one currently being hired.
			local currentId
			if type(GetCurrentNPC) == "function" then
				pcall(function() currentId = GetCurrentNPC() end)
			end
			local hireTopic = NPCFollowers.HireNPCTopic
			if hired and currentId == id and npcHasEvent(npc, hireTopic) then
				if Log and Merge and Merge.Log then
					Log(Merge.Log.Info, "Resuming stale paid NPC follower hire for NPC %s.", id)
				end
				return true
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
KoreanLocalization.InstallFollowerTopicAliases = installFollowerTopicAliases
KoreanLocalization.RodrilBroadNumericSafetyNetRetired = true

-- NPCFollowers normally loads before this alphabetically-late bridge.  Retry
-- at the engine events as well so script reload/order differences cannot leave
-- the compatibility pieces uninstalled.
installFollowerTopicAliases()
installHireAddGuard()

function events.GameInitialized2()
	syncNPCJoinPermissions()
	installFollowerTopicAliases()
	installHireAddGuard()
end

function events.LoadMap()
	syncNPCJoinPermissions()
	installFollowerTopicAliases()
	installHireAddGuard()
end

function events.LoadMapScripts()
	installFollowerTopicAliases()
	installHireAddGuard()
end

function events.TxtFilesReloaded()
	syncNPCJoinPermissions()
	installFollowerTopicAliases()
	installHireAddGuard()
end
