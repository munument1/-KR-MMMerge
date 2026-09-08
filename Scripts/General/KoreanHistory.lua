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
	}
}

local ForwardHistory = {
	[1] = {1},
	[2] = {1, 2},
	[3] = {1}
}

local MM6Introduction = {
	Title = "\191\163\183\206\189\186 \191\172\180\235\177\226",
	Text = "\191\163\183\206\189\186\192\199 \191\170\187\231\180\194 \186\176\182\203\186\176\192\199 \185\227\176\250 \199\212\178\178 \189\195\192\219\181\203\180\207\180\217. \190\198\192\204\190\240\199\199\189\186\198\174 \191\213 \183\209\183\163\181\229\176\161 \189\199\193\190\181\199\176\237 \197\169\184\174\176\199\192\199 \196\167\176\248\192\184\183\206 \189\186\192\167\198\174 \191\246\197\205\176\161 \198\196\177\171\181\200 \181\218, \191\169\188\184 \191\181\193\214\176\161 \191\213\177\185\192\199 \191\238\184\237\192\187 \181\209\183\175\189\206\176\237 \180\235\184\179\199\213\180\207\180\217. \191\169\183\175\186\208\192\186 \180\186 \188\210\199\199\176\165\191\161\188\173 \191\169\193\164\192\187 \189\195\192\219\199\216 \191\169\188\184 \191\181\193\214\192\199 \189\194\192\206\192\187 \190\242\176\237, \199\193\184\174 \199\236\192\204\186\236\192\199 \191\192\182\243\197\172\192\187 \186\185\177\184\199\207\191\169 \197\169\184\174\176\199\192\187 \185\176\184\174\196\165 \185\230\185\253\192\187 \195\163\190\198\190\223 \199\213\180\207\180\217."
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
	if (not data or data == "") and Game.LoadTextFileFromLod then
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

	if continent == 3 then
		-- MM6 has no native history table in Merge. Keep the dedicated Korean
		-- Enroth introduction instead of leaking another continent's history.
		if Game.HistoryTxt[1] then
			Game.HistoryTxt[1].Title = MM6Introduction.Title
			Game.HistoryTxt[1].Text = MM6Introduction.Text
		end
		return
	end

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
