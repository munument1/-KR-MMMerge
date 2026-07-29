-- Script simply replaces text fields of tables with ones from "LocalizeTables.txt".
-- Sacrificing a bit of perfomance for a lot of conviniency of work with localizations.

local function encode_korean(str)
	if type(str) ~= "string" or str == "" then
		return str
	end
	if str:find("\7", 1, true) then
		return str
	end
	if KoreanFont and KoreanFont.encodeSpecial then
		local result = KoreanFont.encodeSpecial(str)
		return result
	end
	local enc = str:gsub("([\129-\254][\65-\254])", "\14\32\14%1\7\15")
	local result = enc:gsub("\15\14", "")
	return result
end

local function lines_binary(file)
	local txt = file:read("*all")
	if txt:sub(1, 3) == "\239\187\191" then
		txt = txt:sub(4)
	end
	local t = txt:split('\r\n')
	local pos = 1

	return function()
		local line = t[pos]
		pos = pos + 1
		if line then
			line = line:gsub("\r$", "")
		end
		return line
	end
end

local function _RelocalizeTables(PathMask)

	for FilePath in path.find(PathMask) do

		-- Older Korean packages shipped one mixed HistoryTxt table.  History is
		-- continent-specific in Merge, so loading that file here makes MM6/MM7
		-- display MM8's "Day of the Destroyer" entries.  KoreanHistory.lua owns
		-- history switching now; keep stale files harmless during upgrades.
		local IsLegacyHistory = string.find(string.lower(FilePath), "ko_historytxt.txt", 1, true) ~= nil
		local TxtTable = not IsLegacyHistory and io.open(FilePath, "rb") or nil

		if IsLegacyHistory then
			Log(Merge.Log.Info, "Skipped legacy mixed history localization file: %s.", FilePath)
		elseif TxtTable then
			local Count = 0
			local Words
			local LineIt = lines_binary(TxtTable)
			LineIt() -- skip header

			if string.find(FilePath, "ItemsTxt.txt") then
				-- special behavior for ItemsTxt (with multiline support)
				local Items = Game.ItemsTxt
				local currentItem = nil

				local function commitItem()
					if currentItem and currentItem.num then
						local Item = Items[currentItem.num]
						if Item then
							Item.Name 				= encode_korean(currentItem.name) or Item.Name
							Item.NotIdentifiedName	= encode_korean(currentItem.notIdentifiedName) or Item.NotIdentifiedName
							Item.Notes				= encode_korean(currentItem.notes) or Item.Notes
							Count = Count + 1
						end
					end
					currentItem = nil
				end

				for line in LineIt do
					if line then
						Words = string.split(line, "\9")
						local Num = tonumber(Words[1])
						if Num then
							commitItem()
							currentItem = {
								num = Num,
								name = Words[2] or "",
								notIdentifiedName = Words[3] or "",
								notes = Words[4] or ""
							}
						elseif currentItem then
							currentItem.notes = currentItem.notes .. "\n" .. line
						end
					end
				end
				commitItem()

			elseif string.find(FilePath, "2DEvents.txt") then
				-- special behavior for 2DEvents (with multiline support)
				local Houses = Game.Houses
				local currentHouse = nil

				local function commitHouse()
					if currentHouse and currentHouse.num then
						local House = Houses[currentHouse.num]
						if House then
							House.Name 		= encode_korean(currentHouse.name) or House.Name
							House.OwnerName	= encode_korean(currentHouse.ownerName) or House.OwnerName
							House.OwnerTitle= encode_korean(currentHouse.ownerTitle) or House.OwnerTitle
							House.EnterText	= encode_korean(currentHouse.enterText) or House.EnterText
							Count = Count + 1
						end
					end
					currentHouse = nil
				end

				for line in LineIt do
					if line then
						Words = string.split(line, "\9")
						local Num = tonumber(Words[1])
						if Num then
							commitHouse()
							currentHouse = {
								num = Num,
								name = Words[2] or "",
								ownerName = Words[3] or "",
								ownerTitle = Words[4] or "",
								enterText = Words[5] or ""
							}
						elseif currentHouse then
							currentHouse.enterText = currentHouse.enterText .. "\n" .. line
						end
					end
				end
				commitHouse()

			elseif string.find(FilePath, "NPCNames.txt") then
				-- special behavior for NPCNames
				local NPCNames = Game.NPCNames
				-- Clear the existing arrays in place. Other Merge scripts retain
				-- references to these exact tables, so replacing M/F would leave
				-- their English arrays active.
				for i = #NPCNames.M, 1, -1 do
					NPCNames.M[i] = nil
				end
				for i = #NPCNames.F, 1, -1 do
					NPCNames.F[i] = nil
				end
				for line in LineIt do
					if line and #line > 0 then
						Words = string.split(line, "\9")
						if Words[1] and string.len(Words[1]) > 0 then
							table.insert(NPCNames["M"], encode_korean(Words[1]))
						end
						if Words[2] and string.len(Words[2]) > 0 then
							table.insert(NPCNames["F"], encode_korean(Words[2]))
						end
						Count = Count + 1
					end
				end

			elseif string.find(FilePath, "NPCProfessions.txt") then
				-- Merge builds this table from News topics - profession.txt.
				-- Apply Korean names after the base table has been populated.
				local Professions = Game.NPCProfessions
				for line in LineIt do
					if line and #line > 0 then
						Words = string.split(line, "\9")
						local Num = tonumber(Words[1])
						if Num and Professions and Words[2] and #Words[2] > 0 then
							Professions[Num] = encode_korean(Words[2])
							Count = Count + 1
						end
					end
				end

			else
				local len = string.len
				local LastTable = ""
				local currentRecord = nil

				local function commitRecord()
					if not currentRecord then return end
					local cTable = currentRecord.cTable
					local cId = currentRecord.cId
					local cField = currentRecord.cField
					local cText = currentRecord.cText

					if len(cTable) > 0 and cId then
						local tbl = Game[cTable]
						if tbl then
							local ok, item = pcall(function() return tbl[cId] end)
							if ok and item ~= nil then
								local val = encode_korean(cText)
								if len(cField) > 0 then
									pcall(function() item[cField] = val end)
								else
									pcall(function() tbl[cId] = val end)
								end
								Count = Count + 1
							end
						end
					end
					currentRecord = nil
				end

				for line in LineIt do
					if line then
						Words = string.split(line, "\9")
						local first = Words[1] or ""
						local second = Words[2] or ""
						local num = tonumber(second)

						local isNewRecord = false
						if len(first) > 0 then
							if Game[first] and num then
								LastTable = first
								isNewRecord = true
							end
						elseif len(LastTable) > 0 and num then
							isNewRecord = true
						end

						if isNewRecord then
							commitRecord()
							local cTable = len(first) > 0 and first or LastTable
							currentRecord = {
								cTable = cTable,
								cId = num,
								cField = tonumber(Words[3]) or Words[3] or "",
								cText = Words[4] or ""
							}
						elseif currentRecord then
							currentRecord.cText = currentRecord.cText .. "\n" .. line
						end
					end
				end
				commitRecord()

				if #LastTable == 0 then
					Log(Merge.Log.Error, "No game tables listed in %s.", FilePath)
				end
			end

			io.close(TxtTable)
			Log(Merge.Log.Info, "Loaded localization file: %s : %s entries.", FilePath, Count)
		else
			Log(Merge.Log.Error, "Could not read localization file: %s.", FilePath)
		end
	end

	for i, v in Game.QuestsTxt do
		if #v == 0 then
			Game.QuestsTxt[i] = "0"
		end
	end

end

function RelocalizeTables()
	_RelocalizeTables("Data/*LocalizeTables.*txt")
	_RelocalizeTables("Data/Text localization/KO_*.txt")
	-- The legacy Gulim bitmap does not contain the syllable in the original
	-- wording for NPCNews 55.  Use an equivalent sentence composed entirely
	-- of glyphs present in the untouched v1.0.3 font instead of rebuilding FNT.
	Game.NPCNews[55] = encode_korean("\185\174\193\166\184\166 \192\207\192\184\197\176\193\246 \184\182\189\195\191\192.")
end

function events.ScriptsLoaded() -- register after Merge's base text loaders
	events.GameInitialized2 = RelocalizeTables
end

function events.TxtFilesReloaded()
	RelocalizeTables()
end
