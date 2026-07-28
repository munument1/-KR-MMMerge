local LastContinent = -1

----------------------------------
--			History.txt			--
----------------------------------

local function enc(str)
	if type(str) ~= "string" or str == "" then return str end
	if KoreanFont and KoreanFont.encodeSpecial then
		return KoreanFont.encodeSpecial(str)
	end
	return str
end

-- continent id = txt file from EnglishT.lod
local HistoryFiles = {
[1] = "history.txt",
[2] = "mm7history.txt",
[3] = "mm6history.txt"
}

local ForwardHistory = {
[1] = {1},
[2] = {1,2},
[3] = {1}
}

local function CurrentHistory(Continent)
	vars.History = vars.History or {}
	vars.History[Continent] = vars.History[Continent] or {}

	return vars.History[Continent]
end

local function LoadHistoryFile(fileName)
	local filePath = "Data/Text localization/" .. fileName
	local file = io.open(filePath, "rb")
	if file then
		local content = file:read("*all")
		file:close()
		if content:sub(1, 3) == "98791" then
			content = content:sub(4)
		end
		return content
	end
	return Game.LoadTextFileFromLod(fileName)
end

local function UpdateHistoryTxt(Continent)

	for i,v in Game.HistoryTxt do
		v.Text	= ""
		--v.Time	= 0
		v.Title	= ""
	end

	local HistoryName = HistoryFiles[Continent]
	if not HistoryName then
		return
	end

	local History = LoadHistoryFile(HistoryName)
	if not History then
		return
	end

	local Lines = string.split(History, "")
	if #Lines <= 1 then
		Lines = string.split(History, "
")
	end

	if #Lines > 0 then
		table.remove(Lines, 1) -- remove header
	end

	local cnt = 1
	local lim = Game.HistoryTxt.limit or 200
	for i, line in ipairs(Lines) do
		line = line:gsub("$", "")
		if line and #line > 0 then
			local Words = string.split(line, "\9")
			local HistoryItem = Game.HistoryTxt[cnt]
			if HistoryItem and Words[2] then
				HistoryItem.Text	= enc(Words[2])
				HistoryItem.Title	= enc(Words[4] or Words[2])
				cnt = cnt + 1
				if cnt > lim then
					break
				end
			end
		end
	end

end

function events.LoadMap()
	local CurCont = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	local History = CurrentHistory(CurCont)

	for i,v in Party.History do
		Party.History[i] = History[i] or 0
	end

	if CurCont ~= LastContinent then
		UpdateHistoryTxt(CurCont)
	end
end

function events.AfterLoadMap()
	local CurCont = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	if ForwardHistory[CurCont] then
		for i,v in pairs(ForwardHistory[CurCont]) do
			Party.History[v] = i
			Game.HistoryTxt[v].Time = i
		end
	end
end

function events.LeaveMap()
	local CurCont = TownPortalControls.MapOfContinent(Map.MapStatsIndex)
	local History = CurrentHistory(CurCont)

	for i,v in Party.History do
		History[i] = v
	end

	LastContinent = CurCont
end

----------------------------------
--		Obelisk autonotes		--
----------------------------------

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
	local CurCont = TownPortalControls.MapOfContinent(Map.MapStatsIndex)

	if CurCont == LastContinent then
		return
	end

	for continent_id, bits in pairs(ObeliskAutonotes) do
		if continent_id == CurCont then
			for obit, qbit in pairs(bits) do
				Party.AutonotesBits[obit] = Party.QBits[qbit]
			end
		else
			for obit, qbit in pairs(bits) do
				Party.AutonotesBits[obit] = false
			end
		end
	end
end
