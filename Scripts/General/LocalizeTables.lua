-- Script simply replaces text fields of tables with ones from "LocalizeTables.txt".
-- Sacrificing a bit of perfomance for a lot of conviniency of work with localizations.

local function encode_korean(str)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(str)
	end
	-- Fail closed: never use a broad byte-range fallback that can reinterpret
	-- ASCII or control bytes as Korean. KoreanFontText.lua should load first.
	return str
end

-- Merge copies NPC names out of its source tables and also persists randomly
-- generated NPC names in save files.  Once copied, those strings are not
-- updated when NPCNames/NPCDataTxt are localized, which leaves old saves with
-- English names such as "Margaret the Docent".  Keep the English -> Korean
-- pairs observed while localizing the source tables and apply them to copies.
local npcNameTranslations = {}

-- Shared runtime localization registry. Merge builds several Lua-side caches
-- (news topics, continent news, town portal descriptions, etc.) from Game
-- tables during GameInitialized2.  If those caches are created before the
-- Korean tables are applied, they retain English copies forever.  Keep the
-- original -> localized pairs and the expected final Game-table values so
-- both the cache repairer and the validator can detect and fix that state.
KoreanLocalization = KoreanLocalization or {}
local runtimeTranslations = KoreanLocalization.RuntimeTranslations or {}
local runtimeTranslationConflicts = KoreanLocalization.RuntimeTranslationConflicts or {}
local expectedRuntimeValues = KoreanLocalization.ExpectedRuntimeValues or {}
local originalNPCNewsTopics = KoreanLocalization.OriginalNPCNewsTopics or {}
local localizedNPCNewsTopics = KoreanLocalization.LocalizedNPCNewsTopics or {}
-- Merge rewrites the four social-action topic slots whenever NPC dialogue
-- state changes. Keep their localized values separately so they can be
-- restored immediately before the dialogue UI reads them.
local volatileNPCTopics = KoreanLocalization.VolatileNPCTopics or {}
KoreanLocalization.RuntimeTranslations = runtimeTranslations
KoreanLocalization.RuntimeTranslationConflicts = runtimeTranslationConflicts
KoreanLocalization.ExpectedRuntimeValues = expectedRuntimeValues
KoreanLocalization.OriginalNPCNewsTopics = originalNPCNewsTopics
KoreanLocalization.LocalizedNPCNewsTopics = localizedNPCNewsTopics
KoreanLocalization.VolatileNPCTopics = volatileNPCTopics

local function runtimeKey(TableName, Id, Field)
	return tostring(TableName) .. "\31" .. tostring(Id) .. "\31" .. tostring(Field or "")
end

local function rememberRuntimeTranslation(original, localized)
	if type(original) ~= "string" or original == "" or
			type(localized) ~= "string" or localized == "" or
			original == localized or runtimeTranslationConflicts[original] then
		return
	end
	local Existing = runtimeTranslations[original]
	if Existing == nil or Existing == localized then
		runtimeTranslations[original] = localized
	else
		-- The same English text can have context-dependent Korean translations.
		-- Never guess in derived caches; leave ambiguous strings for a targeted
		-- handler instead of replacing them with the wrong meaning.
		runtimeTranslations[original] = nil
		runtimeTranslationConflicts[original] = true
	end
end

local function rememberExpectedRuntimeValue(TableName, Id, Field, localized)
	if type(localized) ~= "string" then
		return
	end
	expectedRuntimeValues[runtimeKey(TableName, Id, Field)] = {
		Table = TableName,
		Id = Id,
		Field = Field or "",
		Value = localized
	}
end

local function translateRuntimeString(str)
	if type(str) ~= "string" then
		return str
	end
	return runtimeTranslations[str] or npcNameTranslations[str] or str
end

function KoreanLocalization.TranslateRuntimeString(str)
	return translateRuntimeString(str)
end

function KoreanLocalization.GetRuntimeTranslations()
	return runtimeTranslations
end

function KoreanLocalization.GetRuntimeTranslationConflicts()
	return runtimeTranslationConflicts
end

function KoreanLocalization.GetExpectedRuntimeValues()
	return expectedRuntimeValues
end

function KoreanLocalization.GetNPCNewsTopicTranslations()
	return localizedNPCNewsTopics, originalNPCNewsTopics
end

-- NPCNews.txt stores each news body and its topic in one contiguous source
-- row. Merge's NPCNewsTopics.lua obtains the topic by reading the bytes after
-- the body string. Replacing Game.NPCNews[i] before that code runs destroys
-- the adjacency it relies on. Capture all original topics first, leave
-- NPCNews untouched during the early pass, and translate the derived caches
-- after Merge has built them.
local function readOriginalNPCNewsTopic(Id)
	if originalNPCNewsTopics[Id] ~= nil then
		return originalNPCNewsTopics[Id]
	end
	if Game and Game.NPCNewsTopics then
		local Ok, Topic = pcall(function() return Game.NPCNewsTopics[Id] end)
		if Ok and type(Topic) == "string" then
			originalNPCNewsTopics[Id] = Topic
			return Topic
		end
	end
	if not Game or not Game.NPCNews or not mem or not mem.u4 or not mem.string then
		return nil
	end
	local Ok, Topic = pcall(function()
		local Body = Game.NPCNews[Id]
		local Ptr = mem.u4[Game.NPCNews["?ptr"] + Id*4]
		local Result = mem.string(Ptr + string.len(Body) + 1)
		if string.len(Result) < 2 then
			Result = mem.string(Ptr + string.len(Body) + 2)
		end
		return Result:gsub("\9", "")
	end)
	if Ok and type(Topic) == "string" then
		originalNPCNewsTopics[Id] = Topic
		return Topic
	end
	return nil
end

local function captureOriginalNPCNewsTopics()
	if not Game or not Game.NPCNews then
		return
	end
	pcall(function()
		for Id in Game.NPCNews do
			readOriginalNPCNewsTopic(Id)
		end
	end)
end

local function setLocalizedValue(Container, Key, localized, TableName, Id, Field)
	local original
	pcall(function() original = Container[Key] end)
	rememberRuntimeTranslation(original, localized)
	rememberExpectedRuntimeValue(TableName, Id, Field, localized)
	return pcall(function() Container[Key] = localized end)
end

local function rememberNPCName(original, localized)
	if type(original) == "string" and original ~= "" and
			type(localized) == "string" and localized ~= "" and
			original ~= localized then
		npcNameTranslations[original] = localized
	end
end

local function migrateCopiedNPCNames()
	-- Game.NPC can contain unresolved MMExtension memory-backed entries while a
	-- new game is still being initialized.  Reading npc.Name at that point can
	-- raise an unreadable-memory exception.  This function is therefore called
	-- only after map scripts load, and every memory-backed access is protected.
	if Game and Game.NPC then
		for _, npc in Game.NPC do
			if npc then
				local okRead, original = pcall(function() return npc.Name end)
				if okRead and type(original) == "string" then
					local localized = npcNameTranslations[original]
					if localized then
						pcall(function() npc.Name = localized end)
					end
				end
			end
		end
	end

	-- LoadMapScripts restores this table into Game.NPC for existing saves.
	-- Migrate it too so the next save does not write the English name back.
	if vars and type(vars.RndNPCPersist) == "table" then
		for _, persisted in pairs(vars.RndNPCPersist) do
			if persisted and type(persisted.Name) == "string" then
				local localized = npcNameTranslations[persisted.Name]
				if localized then
					persisted.Name = localized
				end
			end
		end
	end
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

local function _RelocalizeTables(PathMask, Options)

	for FilePath in path.find(PathMask) do

		-- Older Korean packages shipped one mixed HistoryTxt table.  History is
		-- continent-specific in Merge, so loading that file here makes MM6/MM7
		-- display MM8's "Day of the Destroyer" entries.  KoreanHistory.lua owns
		-- history switching now; keep stale files harmless during upgrades.
		local LowerPath = string.lower(tostring(FilePath or "")):gsub("\\", "/")
		local FileName = LowerPath:match("([^/]+)$") or LowerPath
		local IsLegacyHistory = string.find(LowerPath, "ko_historytxt.txt", 1, true) ~= nil
		local IsSkipped = Options and Options.SkipFiles and Options.SkipFiles[FileName]
		local TxtTable = not IsLegacyHistory and not IsSkipped and io.open(FilePath, "rb") or nil

		if IsSkipped then
			-- Early localization deliberately skips Lua-side tables that Merge has
			-- not populated yet. They are handled by the late full pass.
		elseif IsLegacyHistory then
			Log(Merge.Log.Info, "Skipped legacy mixed history localization file: %s.", FilePath)
		elseif TxtTable then
			local Count = 0
			local Words
			local LineIt = lines_binary(TxtTable)
			LineIt() -- skip header

			if string.find(FilePath, "NPCNewsTopics.txt") then
				-- News topics are not a normal Game table. They are the second
				-- string embedded after each NPCNews body in the original row.
				for line in LineIt do
					if line and #line > 0 then
						Words = string.split(line, "\9")
						local Num = tonumber(Words[2])
						if Num then
							local Localized = encode_korean(Words[4] or "")
							localizedNPCNewsTopics[Num] = Localized
							local Original = readOriginalNPCNewsTopic(Num)
							rememberRuntimeTranslation(Original, Localized)
							-- Some Merge builds expose the embedded topic strings as a
							-- separate table. It is safe to update that table only in the
							-- late pass, because this file is deliberately skipped early.
							if Game.NPCNewsTopics then
								setLocalizedValue(Game.NPCNewsTopics, Num, Localized,
									"NPCNewsTopics", Num, "")
							end
							Count = Count + 1
						end
					end
				end

			elseif string.find(FilePath, "ItemsTxt.txt") then
				-- special behavior for ItemsTxt (with multiline support)
				local Items = Game.ItemsTxt
				local currentItem = nil

				local function commitItem()
					if currentItem and currentItem.num then
						local Item = Items[currentItem.num]
						if Item then
							local Name = encode_korean(currentItem.name) or Item.Name
							local Unidentified = encode_korean(currentItem.notIdentifiedName) or Item.NotIdentifiedName
							local Notes = encode_korean(currentItem.notes) or Item.Notes
							setLocalizedValue(Item, "Name", Name, "ItemsTxt", currentItem.num, "Name")
							setLocalizedValue(Item, "NotIdentifiedName", Unidentified, "ItemsTxt", currentItem.num, "NotIdentifiedName")
							setLocalizedValue(Item, "Notes", Notes, "ItemsTxt", currentItem.num, "Notes")
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
							-- Keep a mapping from the original house/map-script strings
							-- to their Korean 2DEvents values before overwriting them.
							if KoreanRuntimeFixes and KoreanRuntimeFixes.RememberHouseLocalization then
								pcall(KoreanRuntimeFixes.RememberHouseLocalization,
									currentHouse.num, House, currentHouse)
							end
							local Name = encode_korean(currentHouse.name) or House.Name
							local OwnerName = encode_korean(currentHouse.ownerName) or House.OwnerName
							local OwnerTitle = encode_korean(currentHouse.ownerTitle) or House.OwnerTitle
							local EnterText = encode_korean(currentHouse.enterText) or House.EnterText
							setLocalizedValue(House, "Name", Name, "Houses", currentHouse.num, "Name")
							setLocalizedValue(House, "OwnerName", OwnerName, "Houses", currentHouse.num, "OwnerName")
							setLocalizedValue(House, "OwnerTitle", OwnerTitle, "Houses", currentHouse.num, "OwnerTitle")
							setLocalizedValue(House, "EnterText", EnterText, "Houses", currentHouse.num, "EnterText")
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
				local OldNames = {M = {}, F = {}}
				for i = 1, #NPCNames.M do
					OldNames.M[i] = NPCNames.M[i]
				end
				for i = 1, #NPCNames.F do
					OldNames.F[i] = NPCNames.F[i]
				end
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
							local localized = encode_korean(Words[1])
							local index = #NPCNames.M + 1
							table.insert(NPCNames["M"], localized)
							rememberRuntimeTranslation(OldNames.M[index], localized)
							rememberNPCName(OldNames.M[index], localized)
						end
						if Words[2] and string.len(Words[2]) > 0 then
							local localized = encode_korean(Words[2])
							local index = #NPCNames.F + 1
							table.insert(NPCNames["F"], localized)
							rememberRuntimeTranslation(OldNames.F[index], localized)
							rememberNPCName(OldNames.F[index], localized)
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
							local localized = encode_korean(Words[2])
							setLocalizedValue(Professions, Num, localized, "NPCProfessions", Num, "")
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
						local val = encode_korean(cText)
						if cTable == "NPCNewsTopics" then
							-- Never alias embedded NPCNews topics to Game.NPCTopic.
							localizedNPCNewsTopics[cId] = val
							rememberRuntimeTranslation(readOriginalNPCNewsTopic(cId), val)
							if Game.NPCNewsTopics then
								setLocalizedValue(Game.NPCNewsTopics, cId, val,
									"NPCNewsTopics", cId, "")
							end
							Count = Count + 1
						else
							-- Bribe/Beg/Threat/Exit are volatile Merge-generated topics.
							if cTable == "NPCTopic" and cId >= 1765 and cId <= 1768 then
								volatileNPCTopics[cId] = val
							end
							local tbl = Game[cTable]
							local RuntimeTableName = cTable
							if not tbl and (cTable == "2DEvents" or cTable == "2DEventsTxt") then
								tbl = Game.Houses
								RuntimeTableName = "Houses"
							end
							if tbl then
								local ok, item = pcall(function() return tbl[cId] end)
								if ok and item ~= nil then
									if len(cField) > 0 then
										local oldValue
										pcall(function() oldValue = item[cField] end)
										if cTable == "NPCDataTxt" and cField == "Name" then
											rememberNPCName(oldValue, val)
										end
										setLocalizedValue(item, cField, val, RuntimeTableName, cId, cField)
									else
										setLocalizedValue(tbl, cId, val, RuntimeTableName, cId, "")
									end
									Count = Count + 1
								end
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
							if (Game[first] or first == "NPCNewsTopics" or
									first == "2DEvents" or first == "2DEventsTxt") and num then
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

local EarlySkipFiles = {
	["ko_npcnames.txt"] = true,
	["ko_npcprofessions.txt"] = true,
	["ko_npcnews.txt"] = true,
	["ko_npcnewstopics.txt"] = true
}

local function applyFixedOverrides()
	if Game and Game.NPCNews then
		local Fixed = encode_korean("\185\174\193\166\184\166 \192\207\192\184\197\176\193\246 \184\182\189\195\191\192.")
		setLocalizedValue(Game.NPCNews, 55, Fixed, "NPCNews", 55, "")
	end
end

-- First pass: run before Merge's GameInitialized2 handlers that build
-- Lua-side caches. NPCNames/NPCProfessions do not exist yet. NPCNews and
-- NPCNewsTopics must also remain untouched until NPCNewsTopics.lua has read
-- the original body/topic adjacency from the source rows.
local function RelocalizeSourceTables()
	captureOriginalNPCNewsTopics()
	_RelocalizeTables("Data/*LocalizeTables.*txt", {SkipFiles = EarlySkipFiles})
	_RelocalizeTables("Data/Text localization/KO_*.txt", {SkipFiles = EarlySkipFiles})
	-- Fixed NPCNews overrides are intentionally late-only for the same reason.
end

function RelocalizeTables()
	captureOriginalNPCNewsTopics()
	_RelocalizeTables("Data/*LocalizeTables.*txt")
	_RelocalizeTables("Data/Text localization/KO_*.txt")
	applyFixedOverrides()
	-- Do not access Game.NPC during GameInitialized2. New-game NPC pointers are
	-- not guaranteed to be valid until LoadMapScripts has completed.
end

local function repairLuaStringCache(Root, MaxDepth)
	if type(Root) ~= "table" then
		return 0
	end
	local Seen = {}
	local Fixed = 0
	local function Walk(T, Depth)
		if type(T) ~= "table" or Seen[T] or Depth > MaxDepth then
			return
		end
		Seen[T] = true
		for Key, Value in pairs(T) do
			if type(Value) == "string" then
				local Localized = translateRuntimeString(Value)
				if Localized ~= Value then
					T[Key] = Localized
					Fixed = Fixed + 1
				end
			elseif type(Value) == "table" then
				Walk(Value, Depth + 1)
			end
		end
	end
	pcall(Walk, Root, 0)
	return Fixed
end

local function repairTownPortalCache()
	if not TownPortalControls or type(TownPortalControls.Sets) ~= "table" then
		return 0
	end
	local Fixed = 0
	for _, Set in pairs(TownPortalControls.Sets) do
		if type(Set) == "table" then
			for _, Entry in pairs(Set) do
				if type(Entry) == "table" and type(Entry.Desc) == "string" then
					local Localized = translateRuntimeString(Entry.Desc)
					if Localized ~= Entry.Desc then
						Entry.Desc = Localized
						if mem and mem.topointer then
							Entry.DescAdr = mem.topointer(Localized)
						end
						Fixed = Fixed + 1
					end
				end
			end
		end
	end
	if Fixed > 0 and TownPortalControls.SwitchTo and TownPortalControls.GetCurrentSwitch then
		pcall(function()
			TownPortalControls.SwitchTo(TownPortalControls.GetCurrentSwitch())
		end)
	end
	return Fixed
end

local function repairDerivedLocalizationCaches()
	local Fixed = 0
	local CacheNames = {
		"MapNews",
		"ContinentNews",
		"ProfessionNews",
		"NPCProfessions",
		"NPCPersonalities"
	}
	for _, Name in ipairs(CacheNames) do
		if Game then
			local Ok, Cache = pcall(function() return Game[Name] end)
			if Ok then
				Fixed = Fixed + repairLuaStringCache(Cache, 6)
			end
		end
	end
	if vars and type(vars.RndNPCPersist) == "table" then
		Fixed = Fixed + repairLuaStringCache(vars.RndNPCPersist, 4)
	end
	Fixed = Fixed + repairTownPortalCache()
	if Fixed > 0 then
		Log(Merge.Log.Info, "Repaired %s cached localization strings.", Fixed)
	end
	return Fixed
end

KoreanLocalization.RepairDerivedCaches = repairDerivedLocalizationCaches

local function restoreVolatileNPCTopics()
	if not Game or not Game.NPCTopic then
		return 0
	end
	local Fixed = 0
	for Id = 1765, 1768 do
		local Localized = volatileNPCTopics[Id]
		if type(Localized) == "string" and Localized ~= "" then
			local Ok, Current = pcall(function() return Game.NPCTopic[Id] end)
			if Ok and Current ~= Localized then
				if pcall(function() Game.NPCTopic[Id] = Localized end) then
					Fixed = Fixed + 1
				end
			end
		end
	end
	return Fixed
end

KoreanLocalization.RestoreVolatileNPCTopics = restoreVolatileNPCTopics

local function localizeActiveNPCTopics(NPCId)
	if not Game or not Game.NPC or not Game.NPCTopic or type(NPCId) ~= "number" then
		return
	end
	local Ok, NPC = pcall(function() return Game.NPC[NPCId] end)
	if not Ok or not NPC then
		return
	end
	for Slot = 0, 5 do
		local EventOk, EventId = pcall(function() return NPC.Events[Slot] end)
		if EventOk and type(EventId) == "number" and EventId > 0 then
			local TextOk, Text = pcall(function() return Game.NPCTopic[EventId] end)
			if TextOk and type(Text) == "string" then
				local Localized = translateRuntimeString(Text)
				if Localized ~= Text then
					pcall(function() Game.NPCTopic[EventId] = Localized end)
				end
			end
		end
	end
end

local function localizeNPCGreeting(T)
	-- This runs after Merge prepares the current dialogue choices.
	restoreVolatileNPCTopics()
	if T and type(T.Text) == "string" then
		T.Text = translateRuntimeString(T.Text)
	end
end

local function localizeTransitionText(T)
	if not T then
		return
	end
	if type(T.Text) == "string" then
		T.Text = translateRuntimeString(T.Text)
	end
	if type(T.CustomText) == "string" then
		T.CustomText = translateRuntimeString(T.CustomText)
	end
end

-- Register the early pass immediately while General scripts are being loaded.
-- This uses MMExtension's standard event assignment syntax and therefore works
-- on builds that don't expose addfirst/AddFirst helper methods. Since this file
-- loads before NPCFollowers.lua in the normal General-script order, its handler
-- is registered before the main NPC news cache builder. Late cache repair below
-- remains as a safety net for handlers registered earlier by numbered scripts.
events.GameInitialized2 = RelocalizeSourceTables

function events.ScriptsLoaded() -- register late repair handlers
	-- Apply the complete set again after all base handlers. This populates the
	-- custom NPCNames/NPCProfessions tables and repairs any late overwrite.
	events.GameInitialized2 = function()
		RelocalizeTables()
		repairDerivedLocalizationCaches()
		restoreVolatileNPCTopics()
	end

	-- Existing saves restore copied random-NPC names during LoadMapScripts.
	events.LoadMapScripts = function()
		migrateCopiedNPCNames()
		repairDerivedLocalizationCaches()
		restoreVolatileNPCTopics()
	end

	-- Runtime safety nets for topics and greetings generated after initialization.
	events.EnterNPC = function(NPCId)
		localizeActiveNPCTopics(NPCId)
		restoreVolatileNPCTopics()
	end
	events.DrawNPCGreeting = localizeNPCGreeting
	events.GetTransitionText = localizeTransitionText
end

function events.TxtFilesReloaded()
	RelocalizeTables()
	repairDerivedLocalizationCaches()
	restoreVolatileNPCTopics()
end
