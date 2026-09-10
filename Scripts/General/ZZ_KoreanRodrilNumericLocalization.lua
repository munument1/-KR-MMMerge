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
-- This deliberately never lowers Joins, never touches Hired, gold, quests,
-- houses, map environments, or any other gameplay field.

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

KoreanLocalization.SyncNPCJoinPermissions = syncNPCJoinPermissions
KoreanLocalization.RodrilBroadNumericSafetyNetRetired = true

-- The early LocalizeTables GameInitialized2 handler has already been registered
-- before this alphabetically-late Korean bridge, so static Joins values are
-- available here. LoadMap also covers live NPC arrays restored later from saves.
function events.GameInitialized2()
	syncNPCJoinPermissions()
end

function events.LoadMap()
	syncNPCJoinPermissions()
end

function events.TxtFilesReloaded()
	syncNPCJoinPermissions()
end
