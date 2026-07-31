-- Korean Signpost and Map Hint localization script for MM6/7/8 Merge

local function enc(str)
	if KoreanText and KoreanText.EncodeOnce then
		return KoreanText.EncodeOnce(str)
	end
	return str
end

local placeTranslations = {
	["Emerald Isle"] = "에메랄드 섬",
	["Emerald Island"] = "에메랄드 섬",
	["Harmondale"] = "하몬데일",
	["Erathia"] = "에라시아",
	["Tularean Forest"] = "툴라레안 숲",
	["Deyja"] = "데이자",
	["Bracada Desert"] = "브라카다 사막",
	["Bracada"] = "브라카다",
	["Celeste"] = "셀레스테",
	["The Pit"] = "더 핏",
	["Evenmorn Island"] = "이븐모른 섬",
	["Mount Nighon"] = "나이혼 산",
	["Nighon"] = "나이혼",
	["Avlee"] = "에블리",
	["Land of the Giants"] = "거인의 땅",
	["New Sorpagal"] = "뉴 소피갈",
	["Castle Ironfist"] = "아이언피스트 성",
	["Ironfist"] = "아이언피스트",
	["Mire of the Damned"] = "저주받은 자의 늪",
	["Free Haven"] = "프리 헤이븐",
	["Silver Cove"] = "실버 코브",
	["Mist"] = "안개 섬",
	["Bootleg Bay"] = "밀수꾼의 만",
	["Kriegspire"] = "크리그스파이어",
	["Blackshire"] = "블랙샤이어",
	["Dragonsand"] = "드래곤샌드",
	["Hermit's Isle"] = "은둔자의 섬",
	["Sweet Water"] = "스위트 워터",
	["Dagger Wound Island"] = "대거 운드 섬",
	["Dagger Wound"] = "대거 운드",
	["Ravenshore"] = "레이븐쇼어",
	["Alvar"] = "알바르",
	["Ironsand Desert"] = "아이언샌드 사막",
	["Ironsand"] = "아이언샌드",
	["Garrote Gorge"] = "가로트 협곡",
	["Shadowspire"] = "섀도스파이어",
	["Murmurwoods"] = "머머우즈",
	["Ravage Roaming"] = "라비지 로밍",
	["Regna"] = "레그나",
	["Plane of Air"] = "대기의 차원",
	["Plane of Earth"] = "대지의 차원",
	["Plane of Fire"] = "화염의 차원",
	["Plane of Water"] = "물의 차원",
	["Between Planes"] = "차원 사이의 차원"
}

local function translateSignText(text)
	if type(text) ~= "string" or text == "" then return text end

	-- 1. "Welcome to <Place>" -> "<Place>에 오신 것을 환영합니다"
	local welcomePlace = text:match("^[Ww]elcome%s+to%s+(.+)$")
	if welcomePlace then
		local cleanPlace = welcomePlace:gsub("[%.%!]$", "")
		local koPlace = placeTranslations[cleanPlace] or cleanPlace
		return enc(koPlace .. "에 오신 것을 환영합니다")
	end

	-- 2. "To <Place>" -> "<Place> 방향"
	local toPlace = text:match("^[Tt]o%s+(.+)$")
	if toPlace then
		local cleanPlace = toPlace:gsub("[%.%!]$", "")
		local koPlace = placeTranslations[cleanPlace] or cleanPlace
		return enc(koPlace .. " 방향")
	end

	-- 3. Exact match from dictionary
	if placeTranslations[text] then
		return enc(placeTranslations[text])
	end

	return nil
end

local function LocalizeMapStrings()
	if not evt or not evt.str then return end
	for i = 0, 499 do
		local ok, s = pcall(function() return evt.str[i] end)
		if ok and type(s) == "string" and s ~= "" then
			local translated = translateSignText(s)
			if translated then
				pcall(function() evt.str[i] = translated end)
			end
		end
	end
end

function events.LoadMap()
	LocalizeMapStrings()
end

function events.AfterLoadMap()
	LocalizeMapStrings()
end