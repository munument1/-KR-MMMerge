-- Keep Merge's continent-specific history state while loading translated text
-- from the static Korean LOD. No external KO history table is reapplied.

local LastContinent = -1

local HistoryFiles = {
	[1] = "history.txt",
	[2] = "mm7history.txt"
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

local function encodeKorean(text)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(text)
	end
	return text
end

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

local function updateHistoryText(continent)
	clearHistoryText()
	local source = HistoryFiles[continent]
	if not source then
		if continent == 3 and Game.HistoryTxt[1] then
			Game.HistoryTxt[1].Title = encodeKorean(MM6Introduction.Title)
			Game.HistoryTxt[1].Text = encodeKorean(MM6Introduction.Text)
		end
		return
	end

	local text = Game.LoadTextFileFromLod(source)
	if not text or text == "" then
		return
	end
	local lines = string.split(text:gsub("\r\n", "\n"):gsub("\r", "\n"), "\n")
	table.remove(lines, 1)
	local record
	local function commit()
		if not record then return end
		local item = Game.HistoryTxt[record.id]
		if item then
			item.Text = encodeKorean(record.text or "")
			if record.title and record.title ~= "" then
				item.Title = encodeKorean(record.title)
			end
		end
	end
	for _, line in ipairs(lines) do
		local words = string.split(line, "\9")
		local id = tonumber(words[1])
		if id then
			commit()
			record = {id = id, text = words[2] or "", title = words[4] or ""}
		elseif record and #line > 0 then
			if #words > 1 and (words[#words] == "Forward" or words[#words - 1] == "Forward") then
				record.title = words[#words]
			else
				record.text = record.text .. "\n" .. line
			end
		end
	end
	commit()
end

KoreanHistory = KoreanHistory or {}
KoreanHistory.ApplyForContinent = updateHistoryText

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
