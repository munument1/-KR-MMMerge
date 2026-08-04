-- Targeted Korean map-hint fix for v1.0.12a.
-- Keep this file ASCII-only; Korean text is stored as CP949 decimal escapes.

KoreanGameplayFeedbackFixes = KoreanGameplayFeedbackFixes or {}
local KGF = KoreanGameplayFeedbackFixes

local BRAZIER_EN = "brazier"
local BRAZIER_KO = "\200\173\183\206" -- CP949: fire brazier

local function encodeKorean(text)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(text)
	end
	return text
end

local function normalizeHint(text)
	if type(text) ~= "string" then
		return nil
	end
	local normalized = text:lower()
	normalized = normalized:gsub("^%s+", ""):gsub("%s+$", "")
	normalized = normalized:gsub("%s+", " ")
	normalized = normalized:gsub("[%.%!,:;]+$", "")
	return normalized
end

local function translateTargetedMapHint(text)
	if normalizeHint(text) == BRAZIER_EN then
		return encodeKorean(BRAZIER_KO)
	end
	return nil
end
KGF.TranslateTargetedMapHint = translateTargetedMapHint

local function localizeProxy(proxy)
	if not proxy then
		return
	end

	local visited = {}
	for index = 0, 1999 do
		local ok, text = pcall(function() return proxy[index] end)
		if ok and type(text) == "string" and text ~= "" then
			visited[index] = true
			local translated = translateTargetedMapHint(text)
			if translated then
				pcall(function() proxy[index] = translated end)
			end
		end
	end

	-- Preserve compatibility with custom maps that use non-numeric keys or
	-- event ids outside the normal range.
	local ok, iterator, state, first = pcall(pairs, proxy)
	if ok and iterator then
		for index, text in iterator, state, first do
			if not visited[index] and type(text) == "string" and text ~= "" then
				local translated = translateTargetedMapHint(text)
				if translated then
					pcall(function() proxy[index] = translated end)
				end
			end
		end
	end
end

local function localizeTargetedMapHints()
	if not evt then
		return
	end
	localizeProxy(evt.str)
	localizeProxy(evt.hint)
end

local pendingMapLocalizationPasses = 0

function events.BeforeLoadMapScripts()
	if evt then
		localizeProxy(evt.str)
	end
end

function events.LoadMapScripts()
	localizeTargetedMapHints()
	pendingMapLocalizationPasses = 8
end

function events.LoadMap()
	localizeTargetedMapHints()
	pendingMapLocalizationPasses = 8
end

function events.AfterLoadMap()
	localizeTargetedMapHints()
	pendingMapLocalizationPasses = 8
end

function events.Tick()
	if pendingMapLocalizationPasses > 0 then
		pendingMapLocalizationPasses = pendingMapLocalizationPasses - 1
		localizeTargetedMapHints()
	end
end
