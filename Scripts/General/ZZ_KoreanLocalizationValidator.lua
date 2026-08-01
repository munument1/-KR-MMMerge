-- MMMerge Korean localization runtime validator.
-- Runs after the game tables are initialized and writes a detailed report to:
--   Data/KO_LocalizationValidation.log
--
-- This script never changes translated text. It checks file structure, runtime
-- table values, and Lua-side caches that can retain English strings after Merge
-- initializes continent-specific systems.

local ValidatorConfig = {
	Enabled = true,
	WriteReport = true,
	LogEachIssue = false,
	LogPassedFiles = false,
	CheckExpectedFiles = true,
	CheckRuntimeValues = true,
	CheckDerivedCaches = true,
	MaxRuntimeIssues = 200,
	ReportPath = "Data/KO_LocalizationValidation.log"
}

local ExpectedFiles = {
	"KO_2DEvents.txt",
	"KO_AutonoteTxt.txt",
	"KO_AwardsTxt.txt",
	"KO_ClassDescriptions.txt",
	"KO_ClassNames.txt",
	"KO_GlobalTxt.txt",
	"KO_ItemsTxt.txt",
	"KO_MapStats.txt",
	"KO_MessageScrolls.txt",
	"KO_Monsters.txt",
	"KO_NPCData.txt",
	"KO_NPCGreet1.txt",
	"KO_NPCGreet2.txt",
	"KO_NPCNames.txt",
	"KO_NPCNews.txt",
	"KO_NPCNewsTopics.txt",
	"KO_NPCProfessions.txt",
	"KO_NPCText.txt",
	"KO_NPCTopic.txt",
	"KO_PlaceMonTxt.txt",
	"KO_QuestsTxt.txt",
	"KO_SpcItemsTxtNames.txt",
	"KO_SpcItemsTxtStats.txt",
	"KO_SpellsTxt.txt",
	"KO_StdItemsTxtNames.txt",
	"KO_StdItemsTxtStats.txt",
	"KO_TransTxt.txt",
	"MM7History_KO.txt",
	"MM8History_KO.txt"
}

local function trim(Value)
	if type(Value) ~= "string" then
		return Value
	end
	return (Value:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function encodeForRuntime(Value)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(Value)
	end
	return Value
end

local function parseBool(Value, Default)
	if Value == nil then
		return Default
	end
	Value = string.lower(trim(Value))
	if Value == "1" or Value == "true" or Value == "yes" or Value == "on" then
		return true
	elseif Value == "0" or Value == "false" or Value == "no" or Value == "off" then
		return false
	end
	return Default
end

local function loadValidatorConfig()
	local File = io.open("Data/KO_LocalizationValidator.ini", "rb")
	if not File then
		return
	end

	for Line in File:lines() do
		Line = Line:gsub("\r$", "")
		local Key, Value = Line:match("^%s*([^;#%[%]][^=]-)%s*=%s*(.-)%s*$")
		if Key and Value then
			Key = string.lower(trim(Key))
			if Key == "enabled" then
				ValidatorConfig.Enabled = parseBool(Value, ValidatorConfig.Enabled)
			elseif Key == "writereport" then
				ValidatorConfig.WriteReport = parseBool(Value, ValidatorConfig.WriteReport)
			elseif Key == "logeachissue" then
				ValidatorConfig.LogEachIssue = parseBool(Value, ValidatorConfig.LogEachIssue)
			elseif Key == "logpassedfiles" then
				ValidatorConfig.LogPassedFiles = parseBool(Value, ValidatorConfig.LogPassedFiles)
			elseif Key == "checkexpectedfiles" then
				ValidatorConfig.CheckExpectedFiles = parseBool(Value, ValidatorConfig.CheckExpectedFiles)
			elseif Key == "checkruntimevalues" then
				ValidatorConfig.CheckRuntimeValues = parseBool(Value, ValidatorConfig.CheckRuntimeValues)
			elseif Key == "checkderivedcaches" then
				ValidatorConfig.CheckDerivedCaches = parseBool(Value, ValidatorConfig.CheckDerivedCaches)
			elseif Key == "maxruntimeissues" then
				ValidatorConfig.MaxRuntimeIssues = tonumber(Value) or ValidatorConfig.MaxRuntimeIssues
			elseif Key == "reportpath" and trim(Value) ~= "" then
				ValidatorConfig.ReportPath = trim(Value)
			end
		end
	end

	File:close()
end

loadValidatorConfig()

local function baseName(FilePath)
	local Normalized = tostring(FilePath or ""):gsub("\\", "/")
	return Normalized:match("([^/]+)$") or Normalized
end

local function readBinaryLines(File)
	local Text = File:read("*all") or ""
	if Text:sub(1, 3) == "\239\187\191" then
		Text = Text:sub(4)
	end
	Text = Text:gsub("\r\n", "\n"):gsub("\r", "\n")
	local Lines = string.split(Text, "\n")
	local Position = 1

	return function()
		local Line = Lines[Position]
		Position = Position + 1
		return Line
	end
end

local function newState(Trigger)
	local Stamp = "unknown"
	if os and os.date then
		local Ok, Value = pcall(os.date, "%Y-%m-%d %H:%M:%S")
		if Ok and Value then
			Stamp = Value
		end
	end

	return {
		Trigger = Trigger or "runtime",
		Timestamp = Stamp,
		Files = 0,
		Records = 0,
		Errors = 0,
		Warnings = 0,
		Issues = {},
		FileResults = {},
		FoundFiles = {},
		RuntimeValuesChecked = 0,
		DerivedStringsChecked = 0,
		RuntimeIssuesTruncated = false
	}
end

local function addIssue(State, Level, FilePath, LineNumber, Message)
	local Issue = {
		Level = Level,
		File = FilePath or "<runtime>",
		Line = LineNumber,
		Message = Message or "Unknown validation issue"
	}
	table.insert(State.Issues, Issue)

	if Level == "ERROR" then
		State.Errors = State.Errors + 1
	else
		State.Warnings = State.Warnings + 1
	end

	if ValidatorConfig.LogEachIssue then
		local Location = Issue.File
		if Issue.Line then
			Location = Location .. ":" .. tostring(Issue.Line)
		end
		local LogLevel = Level == "ERROR" and Merge.Log.Error or Merge.Log.Info
		Log(LogLevel, "KO localization validator [%s] %s - %s", Level, Location, Issue.Message)
	end
end

local function validateKoreanTextModule(State)
	if not KoreanText or type(KoreanText.EncodeOnce) ~= "function" or
			type(KoreanText.Validate) ~= "function" then
		addIssue(State, "ERROR", "KoreanText", nil,
			"shared DBCS text module is not loaded")
		return
	end
	local Probe = KoreanText.EncodeOnce("DBCS probe")
	local Valid, Reason = KoreanText.Validate(Probe)
	if not Valid then
		addIssue(State, "ERROR", "KoreanText", nil,
			"shared DBCS validator rejected probe: " .. tostring(Reason))
	end
end

local function addFileResult(State, FilePath, Records, ErrorsBefore, WarningsBefore)
	local Result = {
		File = FilePath,
		Records = Records or 0,
		Errors = State.Errors - ErrorsBefore,
		Warnings = State.Warnings - WarningsBefore
	}
	table.insert(State.FileResults, Result)
	State.Files = State.Files + 1
	State.Records = State.Records + Result.Records
	State.FoundFiles[string.lower(baseName(FilePath))] = true

	if ValidatorConfig.LogPassedFiles and Result.Errors == 0 and Result.Warnings == 0 then
		Log(Merge.Log.Info, "KO localization validator passed: %s (%s records).", FilePath, Result.Records)
	end
end

local function resolveGameTable(TableName)
	local TableValue = Game and Game[TableName]
	if TableValue then
		return TableValue, TableName
	end
	if TableName == "NPCNewsTopics" then
		-- NPCNews topics are embedded after each NPCNews body in the source row.
		-- They must never be treated as Game.NPCTopic entries.
		return Game and Game.NPCNewsTopics, "NPCNewsTopics"
	elseif TableName == "2DEvents" or TableName == "2DEventsTxt" then
		return Game and Game.Houses, "Houses"
	end
	return nil, TableName
end

local function safeRead(Container, Key)
	local Ok, Value = pcall(function()
		return Container[Key]
	end)
	return Ok, Value
end

local function validateAccessible(State, FilePath, LineNumber, Container, Key, Description)
	local ReadOk, OldValue = safeRead(Container, Key)
	if not ReadOk then
		addIssue(State, "ERROR", FilePath, LineNumber,
			"Cannot access " .. Description .. " (key " .. tostring(Key) .. ").")
		return false, nil
	end
	if OldValue == nil then
		addIssue(State, "WARNING", FilePath, LineNumber,
			"Target field resolves to nil: " .. Description .. ".")
	end
	return true, OldValue
end

local function validateGenericTarget(State, FilePath, LineNumber, TableName, Id, Field)
	local TargetTable, ResolvedName = resolveGameTable(TableName)
	if not TargetTable then
		addIssue(State, "ERROR", FilePath, LineNumber,
			"Game table does not exist: " .. tostring(TableName) .. ".")
		return false
	end

	local ReadOk, Item = safeRead(TargetTable, Id)
	if not ReadOk then
		addIssue(State, "ERROR", FilePath, LineNumber,
			"Cannot read " .. tostring(ResolvedName) .. "[" .. tostring(Id) .. "].")
		return false
	end
	if Item == nil then
		addIssue(State, "ERROR", FilePath, LineNumber,
			"Target ID does not exist: " .. tostring(ResolvedName) .. "[" .. tostring(Id) .. "].")
		return false
	end

	if Field ~= nil and Field ~= "" then
		return validateAccessible(State, FilePath, LineNumber, Item, Field,
			tostring(ResolvedName) .. "[" .. tostring(Id) .. "]." .. tostring(Field))
	end

	return validateAccessible(State, FilePath, LineNumber, TargetTable, Id,
		tostring(ResolvedName) .. "[" .. tostring(Id) .. "]")
end

local function validateHeader(State, FilePath, Header, MinimumColumns)
	if Header == nil or Header == "" then
		addIssue(State, "ERROR", FilePath, 1, "Header line is missing.")
		return
	end
	if Header:find("\0", 1, true) then
		addIssue(State, "ERROR", FilePath, 1, "Header contains a NUL byte.")
	end
	local Columns = string.split(Header, "\9")
	if #Columns < (MinimumColumns or 2) then
		addIssue(State, "WARNING", FilePath, 1,
			"Header has fewer columns than expected (found " .. tostring(#Columns) .. ").")
	end
end

local function validateItemsFile(State, FilePath, LineIterator)
	local Records = 0
	local Seen = {}
	local Current = nil
	local LineNumber = 1

	local function commitCurrent()
		if not Current then
			return
		end
		Records = Records + 1
		local Id = Current.Id
		if Seen[Id] then
			addIssue(State, "WARNING", FilePath, Current.Line,
				"Duplicate item ID " .. tostring(Id) .. "; previous line " .. tostring(Seen[Id]) .. ".")
		else
			Seen[Id] = Current.Line
		end

		local Items = Game and Game.ItemsTxt
		if not Items then
			addIssue(State, "ERROR", FilePath, Current.Line, "Game.ItemsTxt is unavailable.")
			Current = nil
			return
		end
		local Ok, Item = safeRead(Items, Id)
		if not Ok or Item == nil then
			addIssue(State, "ERROR", FilePath, Current.Line,
				"Item ID does not exist: ItemsTxt[" .. tostring(Id) .. "].")
			Current = nil
			return
		end
		validateAccessible(State, FilePath, Current.Line, Item, "Name", "ItemsTxt[" .. tostring(Id) .. "].Name")
		validateAccessible(State, FilePath, Current.Line, Item, "NotIdentifiedName", "ItemsTxt[" .. tostring(Id) .. "].NotIdentifiedName")
		validateAccessible(State, FilePath, Current.Line, Item, "Notes", "ItemsTxt[" .. tostring(Id) .. "].Notes")
		Current = nil
	end

	for Line in LineIterator do
		LineNumber = LineNumber + 1
		local Words = string.split(Line or "", "\9")
		local Id = tonumber(Words[1])
		if Id then
			commitCurrent()
			if #Words < 4 then
				addIssue(State, "WARNING", FilePath, LineNumber,
					"Item record has fewer than four columns.")
			end
			Current = {Id = Id, Line = LineNumber}
		elseif not Current and trim(Line or "") ~= "" then
			addIssue(State, "ERROR", FilePath, LineNumber,
				"Text continuation appears before the first item record.")
		end
	end
	commitCurrent()
	return Records
end

local function validateHousesFile(State, FilePath, LineIterator)
	local Records = 0
	local Seen = {}
	local Current = nil
	local LineNumber = 1

	local function commitCurrent()
		if not Current then
			return
		end
		Records = Records + 1
		local Id = Current.Id
		if Seen[Id] then
			addIssue(State, "WARNING", FilePath, Current.Line,
				"Duplicate house ID " .. tostring(Id) .. "; previous line " .. tostring(Seen[Id]) .. ".")
		else
			Seen[Id] = Current.Line
		end

		local Houses = Game and Game.Houses
		if not Houses then
			addIssue(State, "ERROR", FilePath, Current.Line, "Game.Houses is unavailable.")
			Current = nil
			return
		end
		local Ok, House = safeRead(Houses, Id)
		if not Ok or House == nil then
			addIssue(State, "ERROR", FilePath, Current.Line,
				"House ID does not exist: Houses[" .. tostring(Id) .. "].")
			Current = nil
			return
		end
		validateAccessible(State, FilePath, Current.Line, House, "Name", "Houses[" .. tostring(Id) .. "].Name")
		validateAccessible(State, FilePath, Current.Line, House, "OwnerName", "Houses[" .. tostring(Id) .. "].OwnerName")
		validateAccessible(State, FilePath, Current.Line, House, "OwnerTitle", "Houses[" .. tostring(Id) .. "].OwnerTitle")
		validateAccessible(State, FilePath, Current.Line, House, "EnterText", "Houses[" .. tostring(Id) .. "].EnterText")
		Current = nil
	end

	for Line in LineIterator do
		LineNumber = LineNumber + 1
		local Words = string.split(Line or "", "\9")
		local Id = tonumber(Words[1])
		if Id then
			commitCurrent()
			if #Words < 5 then
				addIssue(State, "WARNING", FilePath, LineNumber,
					"2DEvents record has fewer than five columns.")
			end
			Current = {Id = Id, Line = LineNumber}
		elseif not Current and trim(Line or "") ~= "" then
			addIssue(State, "ERROR", FilePath, LineNumber,
				"Text continuation appears before the first 2DEvents record.")
		end
	end
	commitCurrent()
	return Records
end

local function validateNPCNamesFile(State, FilePath, LineIterator)
	local Records = 0
	local MaleCount = 0
	local FemaleCount = 0
	local LineNumber = 1

	for Line in LineIterator do
		LineNumber = LineNumber + 1
		if Line and Line ~= "" then
			local Words = string.split(Line, "\9")
			if #Words < 2 then
				addIssue(State, "WARNING", FilePath, LineNumber,
					"NPC name row has fewer than two columns.")
			end
			if Words[1] and Words[1] ~= "" then
				MaleCount = MaleCount + 1
			end
			if Words[2] and Words[2] ~= "" then
				FemaleCount = FemaleCount + 1
			end
			Records = Records + 1
		end
	end

	local Names = Game and Game.NPCNames
	if not Names or not Names.M or not Names.F then
		addIssue(State, "ERROR", FilePath, nil, "Game.NPCNames.M/F is unavailable.")
	else
		local MaleExpected = #Names.M
		local FemaleExpected = #Names.F
		if MaleCount ~= MaleExpected then
			addIssue(State, "WARNING", FilePath, nil,
				"Male NPC name count differs from the current game table: file " ..
				tostring(MaleCount) .. ", game " .. tostring(MaleExpected) .. ".")
		end
		if FemaleCount ~= FemaleExpected then
			addIssue(State, "WARNING", FilePath, nil,
				"Female NPC name count differs from the current game table: file " ..
				tostring(FemaleCount) .. ", game " .. tostring(FemaleExpected) .. ".")
		end
	end
	return Records
end

local function validateNPCProfessionsFile(State, FilePath, LineIterator)
	local Records = 0
	local Seen = {}
	local LineNumber = 1
	local Professions = Game and Game.NPCProfessions
	if not Professions then
		addIssue(State, "ERROR", FilePath, nil, "Game.NPCProfessions is unavailable.")
	end

	for Line in LineIterator do
		LineNumber = LineNumber + 1
		if Line and trim(Line) ~= "" then
			local Words = string.split(Line, "\9")
			local Id = tonumber(Words[1])
			if not Id then
				addIssue(State, "ERROR", FilePath, LineNumber, "Profession ID is not numeric.")
			else
				Records = Records + 1
				if Seen[Id] then
					addIssue(State, "WARNING", FilePath, LineNumber,
						"Duplicate profession ID " .. tostring(Id) .. "; previous line " .. tostring(Seen[Id]) .. ".")
				else
					Seen[Id] = LineNumber
				end
				if Professions then
					local Ok, Value = safeRead(Professions, Id)
					if not Ok or Value == nil then
						addIssue(State, "ERROR", FilePath, LineNumber,
							"Profession ID does not exist: NPCProfessions[" .. tostring(Id) .. "].")
					else
						validateAccessible(State, FilePath, LineNumber, Professions, Id,
							"NPCProfessions[" .. tostring(Id) .. "]")
					end
				end
			end
		end
	end
	return Records
end

local function validateNPCNewsTopicsFile(State, FilePath, LineIterator)
	local Records = 0
	local Seen = {}
	local Current = nil
	local LastTable = ""
	local LineNumber = 1
	local LocalizedTopics, OriginalTopics

	if KoreanLocalization and KoreanLocalization.GetNPCNewsTopicTranslations then
		local Ok, Localized, Original = pcall(KoreanLocalization.GetNPCNewsTopicTranslations)
		if Ok then
			LocalizedTopics = Localized
			OriginalTopics = Original
		end
	end
	if type(LocalizedTopics) ~= "table" or type(OriginalTopics) ~= "table" then
		addIssue(State, "ERROR", FilePath, nil,
			"NPCNews topic translation registry is unavailable.")
	end

	local function commitCurrent()
		if not Current then
			return
		end
		Records = Records + 1
		local Id = Current.Id
		if Seen[Id] then
			addIssue(State, "WARNING", FilePath, Current.Line,
				"Duplicate NPCNews topic ID " .. tostring(Id) ..
				"; previous line " .. tostring(Seen[Id]) .. ".")
		else
			Seen[Id] = Current.Line
		end

		local News = Game and Game.NPCNews
		if not News then
			addIssue(State, "ERROR", FilePath, Current.Line, "Game.NPCNews is unavailable.")
		else
			local Ok, Body = safeRead(News, Id)
			if not Ok or Body == nil then
				addIssue(State, "ERROR", FilePath, Current.Line,
					"NPCNews row does not exist for embedded topic ID " .. tostring(Id) .. ".")
			end
		end

		if type(LocalizedTopics) == "table" then
			local Registered = LocalizedTopics[Id]
			local Expected = encodeForRuntime(Current.Text)
			if Registered == nil then
				addIssue(State, "ERROR", FilePath, Current.Line,
					"NPCNews topic was not registered at runtime: ID " .. tostring(Id) .. ".")
			elseif Registered ~= Expected then
				addIssue(State, "ERROR", FilePath, Current.Line,
					"Registered NPCNews topic differs from the localization file: ID " .. tostring(Id) .. ".")
			end
		end
		if type(OriginalTopics) == "table" and OriginalTopics[Id] == nil then
			addIssue(State, "ERROR", FilePath, Current.Line,
				"Original embedded NPCNews topic could not be captured: ID " .. tostring(Id) .. ".")
		end
		Current = nil
	end

	for Line in LineIterator do
		LineNumber = LineNumber + 1
		local Words = string.split(Line or "", "\9")
		local First = Words[1] or ""
		local Id = tonumber(Words[2])
		local IsRecord = false
		if First ~= "" and Id then
			LastTable = First
			IsRecord = true
		elseif LastTable ~= "" and Id then
			IsRecord = true
		end

		if IsRecord then
			commitCurrent()
			if string.lower(First ~= "" and First or LastTable) ~= "npcnewstopics" then
				addIssue(State, "ERROR", FilePath, LineNumber,
					"Unexpected table name in NPCNews topic file.")
			end
			if #Words < 4 then
				addIssue(State, "WARNING", FilePath, LineNumber,
					"NPCNews topic record has fewer than four columns.")
			end
			Current = {Id = Id, Text = Words[4] or "", Line = LineNumber}
		elseif Current and trim(Line or "") ~= "" then
			Current.Text = Current.Text .. "\n" .. (Line or "")
		elseif trim(Line or "") ~= "" then
			addIssue(State, "ERROR", FilePath, LineNumber,
				"Line is not a topic record and appears before the first record.")
		end
	end
	commitCurrent()

	if LastTable == "" then
		addIssue(State, "ERROR", FilePath, 1, "No NPCNewsTopics table name was found.")
	end
	return Records
end

local function validateGenericFile(State, FilePath, LineIterator)
	local Records = 0
	local Seen = {}
	local LastTable = ""
	local Current = nil
	local LineNumber = 1

	local function commitCurrent()
		if not Current then
			return
		end
		Records = Records + 1
		local Key = Current.Table .. "\31" .. tostring(Current.Id) .. "\31" .. tostring(Current.Field)
		if Seen[Key] then
			addIssue(State, "WARNING", FilePath, Current.Line,
				"Duplicate target " .. Current.Table .. "[" .. tostring(Current.Id) .. "]" ..
				(Current.Field ~= "" and ("." .. tostring(Current.Field)) or "") ..
				"; previous line " .. tostring(Seen[Key]) .. ".")
		else
			Seen[Key] = Current.Line
		end
		validateGenericTarget(State, FilePath, Current.Line,
			Current.Table, Current.Id, Current.Field)
		Current = nil
	end

	for Line in LineIterator do
		LineNumber = LineNumber + 1
		local Words = string.split(Line or "", "\9")
		local First = Words[1] or ""
		local Second = Words[2] or ""
		local Id = tonumber(Second)
		local IsNewRecord = false

		if First ~= "" and Id then
			LastTable = First
			IsNewRecord = true
		elseif LastTable ~= "" and Id then
			IsNewRecord = true
		end

		if IsNewRecord then
			commitCurrent()
			if #Words < 4 then
				addIssue(State, "WARNING", FilePath, LineNumber,
					"Localization record has fewer than four columns.")
			end
			local Field = Words[3] or ""
			Current = {
				Table = First ~= "" and First or LastTable,
				Id = Id,
				Field = tonumber(Field) or Field,
				Line = LineNumber
			}
		elseif Current then
			-- Multiline text continuation. No target validation is required here.
		elseif trim(Line or "") ~= "" then
			addIssue(State, "ERROR", FilePath, LineNumber,
				"Line is not a record and appears before any multiline record.")
		end
	end
	commitCurrent()

	if LastTable == "" then
		addIssue(State, "ERROR", FilePath, 1, "No game table name was found.")
	end
	return Records
end

local function validateLocalizationFile(State, FilePath)
	local ErrorsBefore = State.Errors
	local WarningsBefore = State.Warnings
	local File = io.open(FilePath, "rb")
	if not File then
		addIssue(State, "ERROR", FilePath, nil, "Could not open localization file.")
		addFileResult(State, FilePath, 0, ErrorsBefore, WarningsBefore)
		return
	end

	local Iterator = readBinaryLines(File)
	local Header = Iterator()
	local Name = string.lower(baseName(FilePath))
	local Records = 0

	if Name == "ko_itemstxt.txt" then
		validateHeader(State, FilePath, Header, 4)
		Records = validateItemsFile(State, FilePath, Iterator)
	elseif Name == "ko_2devents.txt" then
		validateHeader(State, FilePath, Header, 5)
		Records = validateHousesFile(State, FilePath, Iterator)
	elseif Name == "ko_npcnames.txt" then
		validateHeader(State, FilePath, Header, 2)
		Records = validateNPCNamesFile(State, FilePath, Iterator)
	elseif Name == "ko_npcprofessions.txt" then
		validateHeader(State, FilePath, Header, 2)
		Records = validateNPCProfessionsFile(State, FilePath, Iterator)
	elseif Name == "ko_npcnewstopics.txt" then
		validateHeader(State, FilePath, Header, 4)
		Records = validateNPCNewsTopicsFile(State, FilePath, Iterator)
	else
		validateHeader(State, FilePath, Header, 4)
		Records = validateGenericFile(State, FilePath, Iterator)
	end

	File:close()
	addFileResult(State, FilePath, Records, ErrorsBefore, WarningsBefore)
end

local function validateHistoryFile(State, FilePath)
	local ErrorsBefore = State.Errors
	local WarningsBefore = State.Warnings
	local File = io.open(FilePath, "rb")
	if not File then
		addIssue(State, "ERROR", FilePath, nil, "Could not open history localization file.")
		addFileResult(State, FilePath, 0, ErrorsBefore, WarningsBefore)
		return
	end

	local Iterator = readBinaryLines(File)
	local Header = Iterator()
	validateHeader(State, FilePath, Header, 4)
	local Records = 0
	local Seen = {}
	local Current = nil
	local LineNumber = 1

	local function commitCurrent()
		if not Current then
			return
		end
		Records = Records + 1
		if Seen[Current.Id] then
			addIssue(State, "WARNING", FilePath, Current.Line,
				"Duplicate history ID " .. tostring(Current.Id) .. "; previous line " .. tostring(Seen[Current.Id]) .. ".")
		else
			Seen[Current.Id] = Current.Line
		end
		local History = Game and Game.HistoryTxt
		if not History then
			addIssue(State, "ERROR", FilePath, Current.Line, "Game.HistoryTxt is unavailable.")
		else
			local Ok, Item = safeRead(History, Current.Id)
			if not Ok or Item == nil then
				addIssue(State, "ERROR", FilePath, Current.Line,
					"History ID does not exist: HistoryTxt[" .. tostring(Current.Id) .. "].")
			else
				validateAccessible(State, FilePath, Current.Line, Item, "Text",
					"HistoryTxt[" .. tostring(Current.Id) .. "].Text")
				validateAccessible(State, FilePath, Current.Line, Item, "Title",
					"HistoryTxt[" .. tostring(Current.Id) .. "].Title")
			end
		end
		Current = nil
	end

	for Line in Iterator do
		LineNumber = LineNumber + 1
		local Words = string.split(Line or "", "\9")
		local Id = tonumber(Words[1])
		if Id then
			commitCurrent()
			if #Words < 2 then
				addIssue(State, "WARNING", FilePath, LineNumber,
					"History record has fewer than two columns.")
			end
			Current = {Id = Id, Line = LineNumber}
		elseif Current then
			-- Multiline history continuation.
		elseif trim(Line or "") ~= "" then
			addIssue(State, "ERROR", FilePath, LineNumber,
				"History continuation appears before the first record.")
		end
	end
	commitCurrent()
	File:close()
	addFileResult(State, FilePath, Records, ErrorsBefore, WarningsBefore)
end

local function validateLocalizeConfig(State)
	local FilePath = "Data/LocalizeConf.ini"
	local File = io.open(FilePath, "rb")
	if not File then
		addIssue(State, "ERROR", FilePath, nil, "LocalizeConf.ini is missing.")
		return
	end
	local Text = string.lower(File:read("*all") or "")
	File:close()
	if not Text:find("encoding%s*=%s*euc_kr") then
		addIssue(State, "WARNING", FilePath, nil,
			"Expected 'encoding=euc_kr' was not found.")
	end
end

local function checkExpectedFiles(State)
	if not ValidatorConfig.CheckExpectedFiles then
		return
	end
	for _, Name in ipairs(ExpectedFiles) do
		if not State.FoundFiles[string.lower(Name)] then
			local FilePath = "Data/Text localization/" .. Name
			addIssue(State, "ERROR", FilePath, nil, "Expected localization file is missing.")
		end
	end
end

local function runtimeIssueAllowed(State)
	local Total = State.Errors + State.Warnings
	if Total < ValidatorConfig.MaxRuntimeIssues then
		return true
	end
	State.RuntimeIssuesTruncated = true
	return false
end

local function readExpectedValue(Entry)
	local TargetTable, ResolvedName = resolveGameTable(Entry.Table)
	if not TargetTable then
		return false, nil, "Game table does not exist: " .. tostring(Entry.Table)
	end
	local Ok, Item = safeRead(TargetTable, Entry.Id)
	if not Ok or Item == nil then
		return false, nil, "Cannot read " .. tostring(ResolvedName) .. "[" .. tostring(Entry.Id) .. "]"
	end
	if Entry.Field ~= nil and Entry.Field ~= "" then
		local FieldOk, Value = safeRead(Item, Entry.Field)
		if not FieldOk then
			return false, nil, "Cannot read " .. tostring(ResolvedName) .. "[" .. tostring(Entry.Id) .. "]." .. tostring(Entry.Field)
		end
		return true, Value, tostring(ResolvedName) .. "[" .. tostring(Entry.Id) .. "]." .. tostring(Entry.Field)
	end
	return true, Item, tostring(ResolvedName) .. "[" .. tostring(Entry.Id) .. "]"
end

local function validateRuntimeValues(State)
	if not ValidatorConfig.CheckRuntimeValues then
		return
	end
	if not KoreanLocalization or not KoreanLocalization.GetExpectedRuntimeValues then
		addIssue(State, "WARNING", "<runtime>", nil,
			"Korean runtime expectation registry is unavailable; value comparison was skipped.")
		return
	end
	local Ok, Expected = pcall(KoreanLocalization.GetExpectedRuntimeValues)
	if not Ok or type(Expected) ~= "table" then
		addIssue(State, "WARNING", "<runtime>", nil,
			"Korean runtime expectation registry could not be read.")
		return
	end
	for _, Entry in pairs(Expected) do
		State.RuntimeValuesChecked = State.RuntimeValuesChecked + 1
		local ReadOk, Actual, Description = readExpectedValue(Entry)
		if not ReadOk then
			if runtimeIssueAllowed(State) then
				addIssue(State, "ERROR", "<runtime>", nil, Description)
			end
		elseif Actual ~= Entry.Value then
			if runtimeIssueAllowed(State) then
				addIssue(State, "ERROR", "<runtime>", nil,
					"Runtime value differs from the Korean localization: " .. Description .. ".")
			end
		end
	end
end

local function countLiteral(Value, Needle)
	if type(Value) ~= "string" or Needle == "" then
		return 0
	end
	local Count = 0
	local Position = 1
	while true do
		local StartAt, EndAt = Value:find(Needle, Position, true)
		if not StartAt then
			break
		end
		Count = Count + 1
		Position = EndAt + 1
	end
	return Count
end

local function validateMergePromotionStrings(State)
	if not Game or not Game.GlobalTxt then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Game.GlobalTxt is unavailable for the Merge promotion-string check.")
		return
	end

	local Contracts = {
		[632] = 1,
		[633] = 1,
		[634] = 0
	}
	for Id, ExpectedPlaceholders in pairs(Contracts) do
		local Ok, Value = pcall(function() return Game.GlobalTxt[Id] end)
		if not Ok or type(Value) ~= "string" then
			addIssue(State, "ERROR", "<runtime>", nil,
				"Cannot read Game.GlobalTxt[" .. tostring(Id) .. "] for the Merge promotion-string check.")
		else
			local ActualPlaceholders = countLiteral(Value, "%s")
			if ActualPlaceholders ~= ExpectedPlaceholders then
				addIssue(State, "ERROR", "<runtime>", nil,
					"Game.GlobalTxt[" .. tostring(Id) .. "] has " ..
					tostring(ActualPlaceholders) .. " %s placeholder(s); Merge requires " ..
					tostring(ExpectedPlaceholders) .. ". GlobalTxt[634] is only the class-name separator.")
			end
		end
	end

	local ExpectedSeparator = encodeForRuntime("\182\199\180\194") -- CP949: 또는
	local Ok, Separator = pcall(function() return Game.GlobalTxt[634] end)
	if Ok and type(Separator) == "string" and Separator ~= ExpectedSeparator then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Game.GlobalTxt[634] must be the Korean separator equivalent of 'or', not a complete format sentence.")
	end
end

local function validateGlobalFormatHook(State)
	local KRF = rawget(_G, "KoreanRuntimeFixes")
	if type(KRF) ~= "table" then
		addIssue(State, "WARNING", "<runtime>", nil,
			"KoreanRuntimeFixes is unavailable for the global string.format check.")
		return
	end
	if KRF.SafeStringFormat ~= nil then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Legacy Korean safeStringFormat hook is still registered. The promotion path is engine-side and must not replace Lua string.format globally.")
	end
	if KRF.GlobalStringFormatHookRemoved ~= true then
		addIssue(State, "WARNING", "<runtime>", nil,
			"The v1.0.10b global string.format removal marker was not detected.")
	end
end

local function validateDerivedCache(State, Root, RootName, Translations, MaxDepth, AllowedKeys)
	if type(Root) ~= "table" then
		return
	end
	local Seen = {}
	local function Walk(T, Path, Depth)
		if type(T) ~= "table" or Seen[T] or Depth > MaxDepth then
			return
		end
		Seen[T] = true
		for Key, Value in pairs(T) do
			local ChildPath = Path .. "." .. tostring(Key)
			if type(Value) == "string" and (not AllowedKeys or AllowedKeys[Key]) then
				State.DerivedStringsChecked = State.DerivedStringsChecked + 1
				local Expected = Translations[Value]
				if Expected and Expected ~= Value and runtimeIssueAllowed(State) then
					addIssue(State, "ERROR", "<runtime-cache>", nil,
						"Untranslated source string remains in " .. ChildPath .. ".")
				end
			elseif type(Value) == "table" then
				Walk(Value, ChildPath, Depth + 1)
			end
		end
	end
	local Ok = pcall(Walk, Root, RootName, 0)
	if not Ok and runtimeIssueAllowed(State) then
		addIssue(State, "WARNING", "<runtime-cache>", nil,
			"Could not fully inspect " .. RootName .. ".")
	end
end

local function validateDerivedCaches(State)
	if not ValidatorConfig.CheckDerivedCaches then
		return
	end
	if not KoreanLocalization or not KoreanLocalization.GetRuntimeTranslations then
		addIssue(State, "WARNING", "<runtime-cache>", nil,
			"Korean runtime translation registry is unavailable; cache inspection was skipped.")
		return
	end
	local Ok, Translations = pcall(KoreanLocalization.GetRuntimeTranslations)
	if not Ok or type(Translations) ~= "table" then
		addIssue(State, "WARNING", "<runtime-cache>", nil,
			"Korean runtime translation registry could not be read.")
		return
	end
	local CacheNames = {
		"MapNews",
		"ContinentNews",
		"ProfessionNews"
	}
	local NewsFields = {Name = true, Text = true}
	for _, Name in ipairs(CacheNames) do
		if Game then
			local CacheOk, Cache = pcall(function() return Game[Name] end)
			if CacheOk then
				validateDerivedCache(State, Cache, "Game." .. Name, Translations, 6, NewsFields)
			end
		end
	end
	if TownPortalControls and type(TownPortalControls.Sets) == "table" then
		validateDerivedCache(State, TownPortalControls.Sets,
			"TownPortalControls.Sets", Translations, 5, {Desc = true})
	end
end

local function writeReport(State)
	if not ValidatorConfig.WriteReport then
		return
	end
	local File = io.open(ValidatorConfig.ReportPath, "wb")
	if not File then
		Log(Merge.Log.Error, "KO localization validator could not write report: %s", ValidatorConfig.ReportPath)
		return
	end

	local Result = State.Errors > 0 and "FAIL" or (State.Warnings > 0 and "PASS WITH WARNINGS" or "PASS")
	File:write("MMMerge Korean Localization Validation Report\r\n")
	File:write("============================================\r\n")
	File:write("Result: ", Result, "\r\n")
	File:write("Run time: ", State.Timestamp, "\r\n")
	File:write("Trigger: ", State.Trigger, "\r\n")
	File:write("Files checked: ", tostring(State.Files), "\r\n")
	File:write("Records checked: ", tostring(State.Records), "\r\n")
	File:write("Errors: ", tostring(State.Errors), "\r\n")
	File:write("Warnings: ", tostring(State.Warnings), "\r\n")
	File:write("Runtime values compared: ", tostring(State.RuntimeValuesChecked), "\r\n")
	File:write("Derived cache strings inspected: ", tostring(State.DerivedStringsChecked), "\r\n\r\n")

	File:write("Per-file summary\r\n")
	File:write("----------------\r\n")
	for _, Entry in ipairs(State.FileResults) do
		File:write(string.format("%s | records=%d errors=%d warnings=%d\r\n",
			Entry.File, Entry.Records, Entry.Errors, Entry.Warnings))
	end

	File:write("\r\nIssues\r\n")
	File:write("------\r\n")
	if #State.Issues == 0 then
		File:write("No issues found.\r\n")
	else
		for _, Issue in ipairs(State.Issues) do
			local Location = Issue.File
			if Issue.Line then
				Location = Location .. ":" .. tostring(Issue.Line)
			end
			File:write("[", Issue.Level, "] ", Location, " - ", Issue.Message, "\r\n")
		end
	end

	File:write("\r\nNotes\r\n")
	File:write("-----\r\n")
	File:write("This validator checks file structure, exact runtime values, and known derived caches.\r\n")
	File:write("It does not check glyph coverage, visual clipping, or arbitrary text embedded only in map scripts.\r\n")
	if State.RuntimeIssuesTruncated then
		File:write("Runtime issue output was truncated by MaxRuntimeIssues.\r\n")
	end
	File:close()
end

local function runValidation(Trigger)
	if not ValidatorConfig.Enabled then
		return
	end
	local State = newState(Trigger)
	validateKoreanTextModule(State)

	for FilePath in path.find("Data/Text localization/KO_*.txt") do
		validateLocalizationFile(State, FilePath)
	end
	validateHistoryFile(State, "Data/Text localization/MM7History_KO.txt")
	validateHistoryFile(State, "Data/Text localization/MM8History_KO.txt")
	validateLocalizeConfig(State)
	checkExpectedFiles(State)
	validateRuntimeValues(State)
	validateMergePromotionStrings(State)
	validateGlobalFormatHook(State)
	validateDerivedCaches(State)
	writeReport(State)

	if State.Errors > 0 then
		Log(Merge.Log.Error,
			"KO localization validation FAILED: %s errors, %s warnings. See %s",
			State.Errors, State.Warnings, ValidatorConfig.ReportPath)
	elseif State.Warnings > 0 then
		Log(Merge.Log.Info,
			"KO localization validation passed with warnings: %s warnings. See %s",
			State.Warnings, ValidatorConfig.ReportPath)
	else
		Log(Merge.Log.Info,
			"KO localization validation passed: %s files, %s records checked.",
			State.Files, State.Records)
	end
end

function events.ScriptsLoaded()
	-- Register after LocalizeTables.lua has installed its early and late passes.
	-- The previous validator ran before localization and could not detect English
	-- values that remained in runtime caches.
	events.GameInitialized2 = function()
		runValidation("GameInitialized2")
	end
	events.TxtFilesReloaded = function()
		runValidation("TxtFilesReloaded")
	end
end
