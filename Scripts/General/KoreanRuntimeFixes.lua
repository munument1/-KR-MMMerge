-- Runtime fixes for Korean save titles and map signposts.
-- This file stays ASCII-only; Korean text is represented as CP949 byte escapes.

local function encodeKorean(text)
    if type(text) ~= "string" or text == "" then
        return text
    end
    if text:find("\7", 1, true) then
        return text
    end
    if KoreanFont and KoreanFont.encodeSpecial then
        return KoreanFont.encodeSpecial(text)
    end
    return text
end

-- Preserve the original English map names before LocalizeTables replaces them.
-- Save-game headers cannot safely store the DBCS rendering control sequence.
KoreanRuntimeFixes = KoreanRuntimeFixes or {}
local KRF = KoreanRuntimeFixes
local originalMapNames = {}
local originalMapNamesByFile = {}
KRF.OriginalMapNames = originalMapNames
local temporarilyRestoredMapName

local function captureOriginalMapNames()
    if not Game or not Game.MapStats then
        return
    end
    for index, item in Game.MapStats do
        if item and type(item.Name) == "string" and item.Name ~= "" then
            originalMapNames[index] = item.Name
            if type(item.FileName) == "string" and item.FileName ~= "" then
                originalMapNamesByFile[item.FileName:lower()] = item.Name
            end
        end
    end
end

local function readU4(data, position)
    local a, b, c, d = data:byte(position, position + 3)
    if not d then return nil end
    return a + b * 0x100 + c * 0x10000 + d * 0x1000000
end

local function readCString(data, position, maximum)
    local text = data:sub(position, position + maximum - 1)
    local zero = text:find("\0", 1, true)
    return zero and text:sub(1, zero - 1) or text
end

local function isSafeAsciiTitle(title)
    if title == "" then return false end
    for index = 1, #title do
        local byte = title:byte(index)
        if byte < 0x20 or byte > 0x7E then
            return false
        end
    end
    return true
end

local function backupSaveOnce(filePath, data)
    local backupPath = filePath .. ".ko-title-backup"
    local existing = io.open(backupPath, "rb")
    if existing then
        existing:close()
        return true
    end
    local backup = io.open(backupPath, "wb")
    if not backup then return false end
    backup:write(data)
    backup:close()
    return true
end

local function repairSaveTitle(filePath)
    local file = io.open(filePath, "rb")
    if not file then return false end
    local data = file:read("*all")
    file:close()

    local recordPosition = data:find("header.bin\0", 1, true)
    if not recordPosition or (recordPosition - 1) % 32 ~= 0 then
        return false
    end
    local dataOffset = readU4(data, recordPosition + 16)
    local dataSize = readU4(data, recordPosition + 20)
    if not dataOffset or not dataSize or dataSize < 84 then
        return false
    end

    -- LOD record offsets are relative to the archive's 0x100-byte header.
    local headerPosition = 0x100 + dataOffset + 1
    local titlePosition = headerPosition + 0x20
    local mapPosition = headerPosition + 0x34
    local title = readCString(data, titlePosition, 20)
    if isSafeAsciiTitle(title) then
        return false
    end

    local mapFile = readCString(data, mapPosition, 20)
    local safeTitle = originalMapNamesByFile[mapFile:lower()] or mapFile
    if safeTitle == "" then safeTitle = "Recovered Save" end
    safeTitle = safeTitle:sub(1, 19)
    local replacement = safeTitle .. string.rep("\0", 20 - #safeTitle)

    if not backupSaveOnce(filePath, data) then
        return false
    end
    local writable = io.open(filePath, "r+b")
    if not writable then return false end
    writable:seek("set", titlePosition - 1)
    writable:write(replacement)
    writable:close()
    return true
end

local function repairSaveTitles()
    local repaired = 0
    for filePath in path.find("Saves/*.dod") do
        local ok, changed = pcall(repairSaveTitle, filePath)
        if ok and changed then repaired = repaired + 1 end
    end
    KRF.LastSaveRepairCount = repaired
    return repaired
end
KRF.RepairSaveTitles = repairSaveTitles

local function useSafeSaveMapName()
    if temporarilyRestoredMapName or not Map or not Game or not Game.MapStats then
        return
    end
    local index = Map.MapStatsIndex
    local item = index and Game.MapStats[index]
    if not item then
        return
    end
    temporarilyRestoredMapName = {index = index, name = item.Name}
    item.Name = originalMapNames[index] or item.FileName or "Map"
end
KRF.UseSafeSaveMapName = useSafeSaveMapName

local function restoreLocalizedMapName()
    local saved = temporarilyRestoredMapName
    temporarilyRestoredMapName = nil
    if saved and Game and Game.MapStats and Game.MapStats[saved.index] then
        Game.MapStats[saved.index].Name = saved.name
    end
end
KRF.RestoreLocalizedMapName = restoreLocalizedMapName

function events.GameInitialized2()
    captureOriginalMapNames()
    repairSaveTitles()
end

function events.BeforeSaveGame()
    useSafeSaveMapName()
end

function events.AfterSaveGame()
    restoreLocalizedMapName()
    repairSaveTitles()
end

function events.BeforeNewGameAutosave()
    useSafeSaveMapName()
end

function events.AfterNewGameAutosave()
    restoreLocalizedMapName()
    repairSaveTitles()
end

local placeTranslations = {
    ["Emerald Isle"] = "\191\161\184\222\182\246\181\229 \188\182",
    ["Emerald Island"] = "\191\161\184\222\182\246\181\229 \188\182",
    ["Harmondale"] = "\199\207\184\243\181\165\192\207",
    ["Erathia"] = "\191\161\182\243\189\195\190\198",
    ["Tularean Forest"] = "\197\248\182\243\183\185\190\200 \189\163",
    ["Deyja"] = "\181\165\192\204\192\218",
    ["Bracada Desert"] = "\186\234\182\243\196\171\180\217 \187\231\184\183",
    ["Bracada"] = "\186\234\182\243\196\171\180\217",
    ["Celeste"] = "\188\191\183\185\189\186\197\215",
    ["The Pit"] = "\180\245 \199\205",
    ["Evenmorn Island"] = "\192\204\186\236\184\240\184\165 \188\182",
    ["Mount Nighon"] = "\179\170\192\204\200\165 \187\234",
    ["Nighon"] = "\179\170\192\204\200\165",
    ["Avlee"] = "\191\161\186\237\184\174",
    ["Land of the Giants"] = "\176\197\192\206\192\199 \182\165",
    ["New Sorpigal"] = "\180\186 \188\210\199\199\176\165",
    ["New Sorpagal"] = "\180\186 \188\210\199\199\176\165",
    ["Castle Ironfist"] = "\190\198\192\204\190\240\199\199\189\186\198\174 \188\186",
    ["Ironfist"] = "\190\198\192\204\190\240\199\199\189\186\198\174",
    ["Mire of the Damned"] = "\192\250\193\214\185\222\192\186 \192\218\192\199 \180\203",
    ["Free Haven"] = "\199\193\184\174 \199\236\192\204\186\236",
    ["Silver Cove"] = "\189\199\185\246 \196\218\186\234",
    ["Mist"] = "\190\200\176\179 \188\182",
    ["Bootleg Bay"] = "\185\208\188\246\178\219\192\199 \184\184",
    ["Kriegspire"] = "\197\169\184\174\177\215\189\186\198\196\192\204\190\238",
    ["Blackshire"] = "\186\237\183\162\187\254\192\204\190\238",
    ["Dragonsand"] = "\181\229\183\161\176\239\187\247\181\229",
    ["Hermit's Isle"] = "\192\186\181\208\192\218\192\199 \188\182",
    ["Sweet Water"] = "\189\186\192\167\198\174 \191\246\197\205",
    ["Dagger Wound Island"] = "\180\235\176\197 \191\238\181\229 \188\182",
    ["Dagger Wound"] = "\180\235\176\197 \191\238\181\229",
    ["Ravenshore"] = "\183\185\192\204\186\236\188\238\190\238",
    ["Alvar"] = "\190\203\185\217\184\163",
    ["Ironsand Desert"] = "\190\198\192\204\190\240\187\247\181\229 \187\231\184\183",
    ["Ironsand"] = "\190\198\192\204\190\240\187\247\181\229",
    ["Garrote Gorge"] = "\176\161\183\206\198\174 \199\249\176\238",
    ["Shadowspire"] = "\188\168\181\181\189\186\198\196\192\204\190\238",
    ["Murmurwoods"] = "\184\211\184\211\191\236\193\238",
    ["Ravage Roaming"] = "\182\243\186\241\193\246 \183\206\185\214",
    ["Regna"] = "\183\185\177\215\179\170",
    ["Plane of Air"] = "\180\235\177\226\192\199 \194\247\191\248",
    ["Plane of Earth"] = "\180\235\193\246\192\199 \194\247\191\248",
    ["Plane of Fire"] = "\200\173\191\176\192\199 \194\247\191\248",
    ["Plane of Water"] = "\185\176\192\199 \194\247\191\248",
    ["Between Planes"] = "\194\247\191\248 \187\231\192\204\192\199 \194\247\191\248"
}

local placeNames = {}
for name in pairs(placeTranslations) do
    placeNames[#placeNames + 1] = name
end
table.sort(placeNames, function(a, b) return #a > #b end)

local function escapePattern(text)
    return (text:gsub("([^%w])", "%%%1"))
end

local function translateSignText(text)
    if type(text) ~= "string" or text == "" or text:find("\7", 1, true) then
        return nil
    end

    local welcomePlace = text:match("^[Ww]elcome%s+to%s+(.+)$")
    if welcomePlace then
        local cleanPlace = welcomePlace:gsub("[%.%!]$", "")
        local translatedPlace = placeTranslations[cleanPlace]
        if translatedPlace then
            return encodeKorean(translatedPlace .. "\191\161 \191\192\189\197 \176\205\192\187 \200\175\191\181\199\213\180\207\180\217")
        end
    end

    local toPlace = text:match("^[Tt]o%s+(.+)$")
    if toPlace then
        local cleanPlace = toPlace:gsub("[%.%!]$", "")
        local translatedPlace = placeTranslations[cleanPlace]
        if translatedPlace then
            return encodeKorean(translatedPlace .. " \185\230\184\233")
        end
    end

    local translated = text
    for _, name in ipairs(placeNames) do
        translated = translated:gsub(escapePattern(name), placeTranslations[name])
    end
    if translated ~= text then
        return encodeKorean(translated)
    end
    return nil
end
KRF.TranslateSignText = translateSignText

local function localizeEventStrings()
    if not evt or not evt.str then
        return
    end
    for index = 0, 499 do
        local ok, text = pcall(function() return evt.str[index] end)
        if ok then
            local translated = translateSignText(text)
            if translated then
                pcall(function() evt.str[index] = translated end)
            end
        end
    end
end

local function localizeEventHints()
    if not evt or not evt.hint then
        return
    end
    for index, text in pairs(evt.hint) do
        local translated = translateSignText(text)
        if translated then
            evt.hint[index] = translated
        end
    end
end

-- Translate before map scripts copy evt.str values into evt.hint.
function events.BeforeLoadMapScripts()
    localizeEventStrings()
end

-- Catch strings and hints added by the map script itself.
function events.LoadMapScripts()
    localizeEventStrings()
    localizeEventHints()
end

function events.LoadMap()
    localizeEventStrings()
    localizeEventHints()
end

function events.AfterLoadMap()
    localizeEventStrings()
    localizeEventHints()
end
