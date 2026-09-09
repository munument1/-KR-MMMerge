-- Keep Merge's continent-specific history state while loading translated text.
-- The external KO history tables are raw game-encoding bytes; do not UTF-8 encode them again.

local LastContinent = -1

local HistorySources = {
	[1] = {
		Localized = "Data/Text localization/MM8History_KO.txt",
		Fallback = "history.txt"
	},
	[2] = {
		Localized = "Data/Text localization/MM7History_KO.txt",
		Fallback = "mm7history.txt"
	},
	[3] = {
		Localized = "Data/Text localization/MM6History_KO.txt"
	}
}

local ForwardHistory = {
	[1] = {1},
	[2] = {1, 2},
	[3] = {1}
}


local historyCache = {}

local function currentHistory(continent)
	vars.History = vars.History or {}
	vars.History[continent] = vars.History[continent] or {}
	return vars.History[continent]
end

local function clearHistoryText()
	for _, item in Game.HistoryTxt do
		item.Text = ""
		item.Title = ""
	end
end

local function readRawFile(path)
	local file = io.open(path, "rb")
	if not file then
		return nil
	end
	local data = file:read("*a")
	file:close()
	return data
end

local function parseHistoryRecords(data)
	if not data or data == "" then
		return nil
	end

	local records = {}
	for row in string.gmatch(data, "[^\r]+") do
		-- The tables use CR record separators and may contain LF paragraph breaks
		-- inside the text field. Strip only the LF left behind by CRLF separators.
		row = string.gsub(row, "^\n+", "")
		local tab1 = string.find(row, "\t", 1, true)
		local tab2 = tab1 and string.find(row, "\t", tab1 + 1, true)
		local tab3 = tab2 and string.find(row, "\t", tab2 + 1, true)
		if tab1 and tab2 and tab3 then
			local id = tonumber(string.sub(row, 1, tab1 - 1))
			if id then
				records[id] = {
					Text = string.sub(row, tab1 + 1, tab2 - 1),
					Title = string.sub(row, tab3 + 1)
				}
			end
		end
	end

	if next(records) then
		return records
	end
	return nil
end

local function loadHistoryRecords(continent)
	if historyCache[continent] then
		return historyCache[continent]
	end

	local source = HistorySources[continent]
	if not source then
		return nil
	end

	local data = readRawFile(source.Localized)
	if (not data or data == "") and source.Fallback and Game.LoadTextFileFromLod then
		data = Game.LoadTextFileFromLod(source.Fallback)
	end

	local records = parseHistoryRecords(data)
	if records then
		historyCache[continent] = records
	end
	return records
end

local function updateHistoryText(continent)
	clearHistoryText()

	local records = loadHistoryRecords(continent)
	if not records then
		return
	end

	for id, record in pairs(records) do
		local item = Game.HistoryTxt[id]
		if item then
			item.Text = record.Text or ""
			item.Title = record.Title or ""
		end
	end
end

KoreanHistory = KoreanHistory or {}
KoreanHistory.ApplyForContinent = updateHistoryText
KoreanHistory.ParseRecords = parseHistoryRecords
KoreanHistory.LoadRecords = loadHistoryRecords

function events.LoadMap()
	local continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	local history = currentHistory(continent)
	for i in Party.History do
		Party.History[i] = history[i] or 0
	end
	updateHistoryText(continent)
end

function events.AfterLoadMap()
	local continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	if ForwardHistory[continent] then
		for i, value in pairs(ForwardHistory[continent]) do
			Party.History[value] = i
			Game.HistoryTxt[value].Time = i
		end
	end

	-- Merge can refresh the native history table during the map-load sequence.
	-- Reapply Korean text here as well so MM8/MM7/MM6 cannot fall back to English.
	updateHistoryText(continent)
end

function events.LeaveMap()
	local continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	local history = currentHistory(continent)
	for i, value in Party.History do
		history[i] = value
	end
	LastContinent = continent
end

local ObeliskAutonotes = {
	[1] = {[8] = 190, [9] = 194, [10] = 189, [11] = 193, [12] = 188, [13] = 192, [14] = 187, [15] = 191, [16] = 186},
	[2] = {[309] = 676, [310] = 677, [311] = 678, [312] = 679, [313] = 680, [314] = 681, [315] = 682, [316] = 683, [317] = 684, [318] = 685, [319] = 686, [320] = 687, [321] = 688, [322] = 689},
	[3] = {[442] = 1384, [443] = 1385, [444] = 1386, [445] = 1386, [446] = 1388, [447] = 1389, [448] = 1390, [449] = 1391, [450] = 1392, [451] = 1393, [452] = 1394, [453] = 1395, [454] = 1396, [455] = 1397, [456] = 1398}
}

function events.LoadMap()
	local continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	if continent == LastContinent then return end
	for continentId, bits in pairs(ObeliskAutonotes) do
		for autonoteBit, questBit in pairs(bits) do
			if continentId == continent then
				Party.AutonotesBits[autonoteBit] = Party.QBits[questBit]
			else
				Party.AutonotesBits[autonoteBit] = false
			end
		end
	end
end
