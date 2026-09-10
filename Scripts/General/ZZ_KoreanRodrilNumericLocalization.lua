-- Restore numeric assignments from Rodril's own Data/*LocalizeTables.*txt files.
--
-- Rodril's LocalizeTables.lua converts the fourth column with tonumber() before
-- assigning it to Game structures.  The Korean multiline/localization wrapper
-- currently keeps that column as a string so numeric struct fields (notably
-- NPCDataTxt.Joins) reject the assignment.  NPCFollowers checks CurNPC.Joins
-- before exposing the Hire topic, which can therefore make recruitable NPCs
-- impossible to hire.
--
-- Keep this compatibility pass deliberately narrow: only Rodril base
-- LocalizeTables files and only values that tonumber() accepts are reapplied.
-- Korean KO_*.txt display strings are not touched.

KoreanLocalization = KoreanLocalization or {}

local function lines_binary(file)
	local txt = file:read("*all")
	local pos = 1
	local size = #txt

	return function()
		if pos > size then
			return nil
		end
		local nextCrLf = string.find(txt, "\r\n", pos, true)
		local line
		if nextCrLf then
			line = string.sub(txt, pos, nextCrLf - 1)
			pos = nextCrLf + 2
		else
			line = string.sub(txt, pos)
			pos = size + 1
		end
		return line
	end
end

local function resolve_table(name)
	if not Game then
		return nil, name
	end
	if Game[name] then
		return Game[name], name
	end
	if name == "2DEvents" or name == "2DEventsTxt" then
		return Game.Houses, "Houses"
	end
	return nil, name
end

local function assign_numeric(tableName, id, field, value)
	local tbl = resolve_table(tableName)
	if not tbl then
		return false
	end

	local ok, item = pcall(function() return tbl[id] end)
	if not ok or item == nil then
		return false
	end

	local assigned
	if field ~= "" then
		assigned = pcall(function() item[field] = value end)
	else
		assigned = pcall(function() tbl[id] = value end)
	end
	if not assigned then
		return false
	end

	-- NPCFollowers tests Game.NPC[npc].Joins, while Rodril marks the static
	-- recruitable NPCs through NPCDataTxt ... Joins ... 1.  Mirror only this
	-- static permission flag so already-created/current NPC entries are repaired
	-- as well; Hired and all other save-backed state remain untouched.
	if tableName == "NPCDataTxt" and field == "Joins" and Game.NPC then
		pcall(function()
			if Game.NPC[id] ~= nil then
				Game.NPC[id].Joins = value
			end
		end)
	end

	return true
end

local function reapply_rodril_numeric_localization()
	if not path or not path.find or not Game then
		return 0, 0
	end

	local applied = 0
	local joins = 0

	for filePath in path.find("Data/*LocalizeTables.*txt") do
		local file = io.open(filePath, "rb")
		if file then
			local iter = lines_binary(file)
			iter() -- header
			local lastTable = ""

			for line in iter do
				local rawTable, rawId, rawField, rawValue = line:match("^([^\t]*)\t([^\t]*)\t([^\t]*)\t(.*)$")
				if rawTable then
					local id = tonumber(rawId)
					local value = tonumber(rawValue)
					local tableName = rawTable

					if tableName ~= "" then
						local tbl = resolve_table(tableName)
						if tbl then
							lastTable = tableName
						else
							tableName = ""
						end
					else
						tableName = lastTable
					end

					if tableName ~= "" and id and value ~= nil then
						local field = tonumber(rawField) or rawField or ""
						if assign_numeric(tableName, id, field, value) then
							applied = applied + 1
							if tableName == "NPCDataTxt" and field == "Joins" then
								joins = joins + 1
							end
						end
					end
				end
			end

			file:close()
		end
	end

	if applied > 0 and Log and Merge and Merge.Log then
		Log(Merge.Log.Info, "Restored Rodril numeric localization fields: %s (%s NPC join flags).", applied, joins)
	end
	return applied, joins
end

KoreanLocalization.ReapplyRodrilNumericLocalization = reapply_rodril_numeric_localization

-- LocalizeTables.lua registers its late GameInitialized2 pass from its own
-- ScriptsLoaded handler.  Register ours from ScriptsLoaded too; this file sorts
-- later, so the numeric restoration runs after that late text pass.
function events.ScriptsLoaded()
	events.GameInitialized2 = reapply_rodril_numeric_localization
end

function events.TxtFilesReloaded()
	reapply_rodril_numeric_localization()
end
