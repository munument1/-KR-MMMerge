-- Targeted Korean runtime fixes for training text, map feedback and the clock.
-- ASCII-only source: Korean strings use CP949 decimal escapes.

KoreanGameplayFeedbackFixes = KoreanGameplayFeedbackFixes or {}
local KGF = KoreanGameplayFeedbackFixes

local function encodeKorean(text)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(text)
	end
	return text
end

local function applyTrainingTextFixes()
	if not Game or not Game.GlobalTxt then
		return
	end
	-- The executable supplies (target level, gold cost).
	Game.GlobalTxt[537] = encodeKorean("\183\185\186\167 %d\177\238\193\246 \200\198\183\195: %d\176\241\181\229")
	-- The executable supplies (experience still needed, target level).
	Game.GlobalTxt[538] = encodeKorean("\176\230\199\232\196\161 %d\176\161 \180\245 \192\214\190\238\190\223 \183\185\186\167 %d\177\238\193\246 \200\198\183\195\199\210 \188\246 \192\214\189\192\180\207\180\217")
end

-- LocalizeTables registers a late GameInitialized2 pass from ScriptsLoaded.
-- Register after it so the corrected argument order remains in effect.
function events.ScriptsLoaded()
	events.GameInitialized2 = applyTrainingTextFixes
	events.TxtFilesReloaded = applyTrainingTextFixes
end

local function currentMapName()
	if not Map or type(Map.Name) ~= "string" then
		return ""
	end
	return Map.Name:lower()
end

local function currentMapId()
	if not Map then
		return -1
	end
	return tonumber(Map.MapStatsIndex) or -1
end

local function normalizeEnglish(text)
	if type(text) ~= "string" then
		return ""
	end
	local normalized = text:lower()
	normalized = normalized:gsub("^%s+", ""):gsub("%s+$", "")
	normalized = normalized:gsub("%s+", " "):gsub("[%.%!,:;]+$", "")
	return normalized
end

local function applyAppleMessageFix()
	local apple = encodeKorean("\187\231\176\250\184\166 \182\164\189\192\180\207\180\217!")
	for index = 0, 499 do
		local ok, text = pcall(function() return evt.str[index] end)
		local normalized = ok and normalizeEnglish(text) or ""
		if normalized == "you pick an apple" or
			normalized == "you picked the apple" then
			pcall(function() evt.str[index] = apple end)
		end
	end
end

local function applyDisplayedMessageFixes()
	if not Game then
		return
	end

	local status = Game.StatusMessage
	local normalizedStatus = normalizeEnglish(status)
	if normalizedStatus == "you pick an apple" or
		normalizedStatus == "you picked the apple" then
		Game.StatusMessage = encodeKorean("\187\231\176\250\184\166 \182\164\189\192\180\207\180\217!")
		Game.NeedUpdateStatusBar = true
	elseif currentMapId() == 151 and type(status) == "string" and
		status:find("Might and Magic VIII", 1, true) then
		Game.StatusMessage = encodeKorean("\187\243\196\232\199\213\180\207\180\217!")
		Game.NeedUpdateStatusBar = true
	end

	local hint = Game.MouseOverStatusMessage
	local normalizedHint = normalizeEnglish(hint)
	if normalizedHint == "fire the cannon" then
		Game.MouseOverStatusMessage = encodeKorean("\180\235\198\247 \185\223\187\231")
		Game.NeedUpdateStatusBar = true
	end
end

local function applyMapFeedbackFixes()
	if not evt or not evt.str then
		return
	end

	local name = currentMapName()
	local mapId = currentMapId()
	if mapId == 151 or name == "oute3.odm" or name == "oute3.ddm" then -- New Sorpigal
		evt.str[7] = encodeKorean("\186\208\188\246\191\161\188\173 \184\182\189\195\177\226")
		evt.str[8] = encodeKorean("\187\243\196\232\199\213\180\207\180\217!")
		evt.str[14] = encodeKorean("+5 \187\253\184\237\183\194 \200\184\186\185")
		evt.str[15] = encodeKorean("+10 \184\182\179\170 \200\184\186\185")
		evt.str[16] = encodeKorean("\200\251 +10 (\192\207\189\195\192\251)")
	elseif mapId == 1 or name == "out01.odm" or name == "out01.ddm" then -- Dagger Wound cannons
		local cannon = encodeKorean("\180\235\198\247 \185\223\187\231")
		evt.str[13] = cannon
		if evt.hint then
			evt.hint[457] = cannon
			evt.hint[458] = cannon
		end
	end
	applyAppleMessageFix()
end

local pendingMapFixPasses = 0

function events.BeforeLoadMapScripts()
	applyMapFeedbackFixes()
end

function events.LoadMapScripts()
	applyMapFeedbackFixes()
	pendingMapFixPasses = 16
end

function events.LoadMap()
	applyMapFeedbackFixes()
	pendingMapFixPasses = 16
end

function events.AfterLoadMap()
	applyMapFeedbackFixes()
	pendingMapFixPasses = 16
end

function events.Tick()
	if pendingMapFixPasses > 0 then
		pendingMapFixPasses = pendingMapFixPasses - 1
		applyMapFeedbackFixes()
	end
	applyDisplayedMessageFixes()
end

local weekdays = {
	"\191\249\191\228\192\207", -- Monday
	"\200\173\191\228\192\207", -- Tuesday
	"\188\246\191\228\192\207", -- Wednesday
	"\184\241\191\228\192\207", -- Thursday
	"\177\221\191\228\192\207", -- Friday
	"\197\228\191\228\192\207", -- Saturday
	"\192\207\191\228\192\207", -- Sunday
}

local function buildKoreanDate()
	local hour = Game.Hour or 0
	local displayHour = hour % 12
	if displayHour == 0 then
		displayHour = 12
	end
	local period = hour < 12 and "\191\192\192\252 " or "\191\192\200\196 "
	local weekday = weekdays[((Game.DayOfMonth or 0) % 7) + 1]
	local text = tostring(Game.Year or 0) .. "\179\226 " ..
		tostring((Game.Month or 0) + 1) .. "\191\249 " ..
		tostring((Game.DayOfMonth or 0) + 1) .. "\192\207 " ..
		weekday .. " " .. period ..
		string.format("%d:%02d", displayHour, Game.Minute or 0)
	return encodeKorean(text)
end

-- MM8 formats the clock tooltip at 0x432706 and consumes Game.TextBuffer at
-- 0x432710. Replace the completed English string between those two steps.
if offsets.MMVersion == 8 and not KGF.DateHookInstalled then
	mem.autohook(0x43270B, function()
		Game.TextBuffer = buildKoreanDate()
	end)
	KGF.DateHookInstalled = true
end
