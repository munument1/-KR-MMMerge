-- Restore Merge's continent-specific history handling without using the old
-- History.lua filename, which was accidentally shipped malformed in an older
-- Korean package.

local LastContinent = -1

local HistoryFiles = {
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

local function EncodeKorean(Text)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(Text)
	end
	return Text
end

local function CurrentHistory(Continent)
	vars.History = vars.History or {}
	vars.History[Continent] = vars.History[Continent] or {}
	return vars.History[Continent]
end

local function ClearHistoryText()
	for i, Item in Game.HistoryTxt do
		Item.Text = ""
		Item.Title = ""
	end
end

local function LoadHistoryFile(Source)
	local File = io.open(Source.Localized, "rb")
	if File then
		local Text = File:read("*all")
		File:close()
		if Text:sub(1, 3) == "\239\187\191" then
			Text = Text:sub(4)
		end
		return Text
	end
	return Game.LoadTextFileFromLod(Source.Fallback)
end

local function UpdateHistoryText(Continent)
	ClearHistoryText()

	local Source = HistoryFiles[Continent]
	if not Source then
		-- MM6 has no native history.txt and no MM6 map scripts set History bits.
		-- Show a dedicated Enroth introduction instead of leaving the page blank
		-- or leaking MM8's "Day of the Destroyer" into it.
		if Continent == 3 and Game.HistoryTxt[1] then
			Game.HistoryTxt[1].Title = EncodeKorean(MM6Introduction.Title)
			Game.HistoryTxt[1].Text = EncodeKorean(MM6Introduction.Text)
		end
		return
	end

	local Text = LoadHistoryFile(Source)
	if not Text or Text == "" then
		return
	end

	local text = Text:gsub("\r\n", "\n"):gsub("\r", "\n")
	local lines = string.split(text, "\n")
	if #lines == 0 then
		return
	end

	table.remove(lines, 1) -- remove header
	local currentRecord = nil

	local function commitRecord()
		if not currentRecord or not currentRecord.id then return end
		local Item = Game.HistoryTxt[currentRecord.id]
		if Item then
			Item.Text = EncodeKorean(currentRecord.text or "")
			if currentRecord.title and currentRecord.title ~= "" then
				Item.Title = EncodeKorean(currentRecord.title)
			end
		end
	end

	for _, line in ipairs(lines) do
		local words = string.split(line, "\9")
		local num = tonumber(words[1])
		if num then
			commitRecord()
			currentRecord = {
				id = num,
				text = words[2] or "",
				time = words[3] or "",
				title = words[4] or ""
			}
		elseif currentRecord and #line > 0 then
			if #words > 1 and (words[#words] == "Forward" or words[#words - 1] == "Forward") then
				-- If line contains trailing title info
				currentRecord.title = words[#words]
			else
				currentRecord.text = currentRecord.text .. "\n" .. line
			end
		end
	end
	commitRecord()
end

-- Kept public for the package's runtime regression check.
KoreanHistory = KoreanHistory or {}
KoreanHistory.ApplyForContinent = UpdateHistoryText

function events.LoadMap()
	local Continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	local History = CurrentHistory(Continent)

	for i, Value in Party.History do
		Party.History[i] = History[i] or 0
	end

	-- Apply on every map load.  This also repairs the table after a manual text
	-- reload instead of relying only on continent transitions.
	UpdateHistoryText(Continent)
end

function events.AfterLoadMap()
	local Continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	if ForwardHistory[Continent] then
		for i, Value in pairs(ForwardHistory[Continent]) do
			Party.History[Value] = i
			Game.HistoryTxt[Value].Time = i
		end
	end
end

function events.LeaveMap()
	local Continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	local History = CurrentHistory(Continent)

	for i, Value in Party.History do
		History[i] = Value
	end

	LastContinent = Continent
end

local ObeliskAutonotes = {
	[1] = {
		[8] = 190, [9] = 194, [10] = 189, [11] = 193, [12] = 188,
		[13] = 192, [14] = 187, [15] = 191, [16] = 186
	},
	[2] = {
		[309] = 676, [310] = 677, [311] = 678, [312] = 679, [313] = 680,
		[314] = 681, [315] = 682, [316] = 683, [317] = 684, [318] = 685,
		[319] = 686, [320] = 687, [321] = 688, [322] = 689
	},
	[3] = {
		[442] = 1384, [443] = 1385, [444] = 1386, [445] = 1386, [446] = 1388,
		[447] = 1389, [448] = 1390, [449] = 1391, [450] = 1392, [451] = 1393,
		[452] = 1394, [453] = 1395, [454] = 1396, [455] = 1397, [456] = 1398
	}
}

function events.LoadMap()
	local Continent = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	if Continent == LastContinent then
		return
	end

	for ContinentId, Bits in pairs(ObeliskAutonotes) do
		for ObeliskBit, QuestBit in pairs(Bits) do
			if ContinentId == Continent then
				Party.AutonotesBits[ObeliskBit] = Party.QBits[QuestBit]
			else
				Party.AutonotesBits[ObeliskBit] = false
			end
		end
	end
end
