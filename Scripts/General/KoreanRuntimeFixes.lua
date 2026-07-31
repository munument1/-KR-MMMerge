-- Runtime fixes for Korean save titles and map signposts.
-- This file stays ASCII-only; Korean text is represented as CP949 byte escapes.

local function encodeKorean(text)
    if KoreanText and KoreanText.EncodeOnce then
        return KoreanText.EncodeOnce(text)
    end
    return text
end

-- Preserve the original English map names before LocalizeTables replaces them.
-- Save-game headers cannot safely store the DBCS rendering control sequence.
KoreanRuntimeFixes = KoreanRuntimeFixes or {}
local KRF = KoreanRuntimeFixes

-- v1.0.10b: do not replace Lua's global string.format.  The trainer
-- promotion message is formatted by the game executable, not by Lua, so the
-- previous global wrapper could not fix that path and could interfere with
-- unrelated Merge scripts.  Restore the old wrapper only when this file is
-- reloaded in a process that previously loaded v1.0.9-v1.0.10a.
local originalStringFormat = KRF.OriginalStringFormat or string.format
if KRF.SafeStringFormat and string.format == KRF.SafeStringFormat then
    string.format = originalStringFormat
end
KRF.OriginalStringFormat = originalStringFormat
KRF.SafeStringFormat = nil
KRF.GlobalStringFormatHookRemoved = true

local originalMapNames = {}
local originalMapNamesByFile = {}
KRF.OriginalMapNames = originalMapNames
local temporarilyRestoredMapName
local pendingSaveKind = 0
local quickSaveSettingsApplied = false

-- House and owner names are stored twice in Merge: once in Game.Houses and
-- again as map-script strings. LocalizeTables calls RememberHouseLocalization
-- immediately before replacing each Game.Houses record, allowing us to build a
-- version-independent English-to-Korean map for evt.str and evt.hint.
local houseTextTranslations = {}
KRF.HouseTextTranslations = houseTextTranslations

local function normalizeHintKey(text)
    if type(text) ~= "string" then
        return nil
    end
    local normalized = text:lower()
    normalized = normalized:gsub("^%s+", "")
    normalized = normalized:gsub("%s+$", "")
    normalized = normalized:gsub("%s+", " ")
    normalized = normalized:gsub("[%.%!,:;]+$", "")
    return normalized
end

local function rememberHouseAlias(original, localized)
    if type(original) ~= "string" or original == "" or
        type(localized) ~= "string" or localized == "" or
        original == localized then
        return
    end
    local encoded = encodeKorean(localized)
    if houseTextTranslations[original] == nil then
        houseTextTranslations[original] = encoded
    end
    local normalized = normalizeHintKey(original)
    if normalized and houseTextTranslations[normalized] == nil then
        houseTextTranslations[normalized] = encoded
    end
end

function KRF.RememberHouseLocalization(index, house, localized)
    if not house or type(localized) ~= "table" then
        return
    end
    rememberHouseAlias(house.Name, localized.name)
    rememberHouseAlias(house.OwnerName, localized.ownerName)
    rememberHouseAlias(house.OwnerTitle, localized.ownerTitle)
    rememberHouseAlias(house.EnterText, localized.enterText)

    -- Some map scripts use "Title Name" while 2DEvents stores the two parts
    -- separately. Add the combined form when both translations are available.
    if type(house.OwnerTitle) == "string" and house.OwnerTitle ~= "" and
        type(house.OwnerName) == "string" and house.OwnerName ~= "" and
        type(localized.ownerName) == "string" and localized.ownerName ~= "" then
        local originalCombined = house.OwnerTitle .. " " .. house.OwnerName
        local localizedCombined
        if type(localized.ownerTitle) == "string" and localized.ownerTitle ~= "" then
            localizedCombined = localized.ownerName .. " " .. localized.ownerTitle
        else
            localizedCombined = localized.ownerName
        end
        rememberHouseAlias(originalCombined, localizedCombined)
    end
end

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

local function trim(text)
    if type(text) ~= "string" then return "" end
    return text:gsub("^%s+", ""):gsub("%s+$", "")
end

local function readQuickSaveConfig()
    local settings = {
        enabled = true,
        count = 10,
        name = "Quick Save",
        spaceBeforeDigit = 0,
    }
    local file = io.open("Data/KO_QuickSave.ini", "rb")
    if not file then return settings end
    local content = file:read("*all") or ""
    file:close()
    for line in content:gmatch("[^\r\n]+") do
        local key, value = line:match("^%s*([^;#][^=]-)%s*=%s*(.-)%s*$")
        if key then
            key = trim(key):lower()
            value = trim(value)
            if key == "enabled" then
                settings.enabled = value ~= "0" and value:lower() ~= "false"
            elseif key == "count" then
                local count = tonumber(value)
                if count then settings.count = math.max(1, math.min(99, math.floor(count))) end
            elseif key == "name" and value ~= "" then
                settings.name = value
            elseif key == "spacebeforedigit" then
                settings.spaceBeforeDigit = tonumber(value) == 1 and 1 or 0
            end
        end
    end
    return settings
end

local function replaceIniValue(content, key, value)
    local lowerKey = key:lower()
    local output = {}
    local found = false
    local newline = content:find("\r\n", 1, true) and "\r\n" or "\n"
    for line in (content .. newline):gmatch("(.-)" .. newline) do
        local existingKey = line:match("^%s*([^;#][^=]-)%s*=")
        if existingKey and trim(existingKey):lower() == lowerKey then
            output[#output + 1] = key .. "=" .. tostring(value)
            found = true
        else
            output[#output + 1] = line
        end
    end
    if output[#output] == "" then output[#output] = nil end
    if not found then output[#output + 1] = key .. "=" .. tostring(value) end
    return table.concat(output, newline) .. newline
end

local function backupFileOnce(sourcePath, backupPath, content)
    local existing = io.open(backupPath, "rb")
    if existing then
        existing:close()
        return true
    end
    local backup = io.open(backupPath, "wb")
    if not backup then return false end
    backup:write(content or "")
    backup:close()
    return true
end

local function updateQuickSaveIni(settings)
    if not settings.enabled then return false end
    local iniPath = (AppPath or "") .. "mm8.ini"
    local backupPath = iniPath .. ".ko-quicksave-backup"
    local file = io.open(iniPath, "rb")
    local content = ""
    if file then
        content = file:read("*all") or ""
        file:close()
    end
    local updated = content
    updated = replaceIniValue(updated, "QuickSavesCount", settings.count)
    updated = replaceIniValue(updated, "QuickSavesName", settings.name)
    updated = replaceIniValue(updated, "SpaceBeforeQuicksaveDigit", settings.spaceBeforeDigit)
    if updated == content then return false end
    if not backupFileOnce(iniPath, backupPath, content) then return false end
    local writable = io.open(iniPath, "wb")
    if not writable then return false end
    writable:write(updated)
    writable:close()
    return true
end

local function applyQuickSaveCountLive(settings)
    if not settings.enabled or not Game or not Game.PatchOptions or not mem then
        return false
    end
    local ptr
    local ok = pcall(function()
        ptr = Game.PatchOptions.Ptr("QuickSavesCount")
    end)
    if (not ok or not ptr or ptr == 0) and type(Game.PatchOptions.Ptr) == "function" then
        ok = pcall(function()
            ptr = Game.PatchOptions:Ptr("QuickSavesCount")
        end)
    end
    if not ok or not ptr or ptr == 0 then return false end
    local wrote = pcall(function() mem.i4[ptr] = settings.count end)
    return wrote
end

local function configureQuickSaves()
    if quickSaveSettingsApplied then return end
    quickSaveSettingsApplied = true
    local settings = readQuickSaveConfig()
    KRF.QuickSaveSettings = settings
    KRF.QuickSaveIniChanged = updateQuickSaveIni(settings)
    KRF.QuickSaveCountAppliedLive = applyQuickSaveCountLive(settings)
end

function events.GameInitialized2()
    captureOriginalMapNames()
    repairSaveTitles()
    configureQuickSaves()
end

function events.CanSaveGame(t)
    if type(t) == "table" and t.SaveKind ~= nil then
        pendingSaveKind = tonumber(t.SaveKind) or 0
    end
end

function events.BeforeSaveGame()
    -- GrayFace SaveKind: 0 normal, 1 autosave, 2 quick save.
    -- Quick saves must keep GrayFace's own Quick Save1/2/... title.
    if pendingSaveKind ~= 2 then
        useSafeSaveMapName()
    end
end

function events.AfterSaveGame()
    local wasQuickSave = pendingSaveKind == 2
    restoreLocalizedMapName()
    -- Never run the generic title repair on quick saves. During the first
    -- launch after installing this patch GrayFace may still hold the old
    -- localized QuickSavesName in memory; repairing that non-ASCII title
    -- would turn it into the current region name again.
    if not wasQuickSave then
        repairSaveTitles()
    end
    pendingSaveKind = 0
end

function events.BeforeNewGameAutosave()
    pendingSaveKind = 1
    useSafeSaveMapName()
end

function events.AfterNewGameAutosave()
    restoreLocalizedMapName()
    repairSaveTitles()
    pendingSaveKind = 0
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

local dayMap = {
    Sunday = "\192\207\191\228\192\207",
    Monday = "\191\249\191\228\192\207",
    Tuesday = "\200\173\191\228\192\207",
    Wednesday = "\188\246\191\228\192\207",
    Thursday = "\184\241\191\228\192\207",
    Friday = "\177\221\191\228\192\207",
    Saturday = "\197\228\191\228\192\207"
}

local monthMap = {
    January = "1\191\249",
    February = "2\191\249",
    March = "3\191\249",
    April = "4\191\249",
    May = "5\191\249",
    June = "6\191\249",
    July = "7\191\249",
    August = "8\191\249",
    September = "9\191\249",
    October = "10\191\249",
    November = "11\191\249",
    December = "12\191\249"
}

local promptMap = {
    ["a cave"] = "\181\191\177\188",
    ["all wards must be destroyed"] = "\184\240\181\231 \184\182\185\253 \186\192\192\206\192\187 \198\196\177\171\199\216\190\223 \199\209\180\217",
    ["altar"] = "\193\166\180\220",
    ["alter"] = "\193\166\180\220",
    ["anvil"] = "\184\240\183\231",
    ["bag"] = "\176\161\185\230",
    ["barrel"] = "\197\235",
    ["bed"] = "\196\167\180\235",
    ["berry bush"] = "\187\234\181\254\177\226 \180\253\186\210",
    ["boat"] = "\185\232",
    ["bones"] = "\187\192",
    ["bookcase"] = "\195\165\192\229",
    ["bookshelf"] = "\195\165\192\229",
    ["brazier"] = "\200\173\183\206",
    ["bridge"] = "\180\217\184\174",
    ["buoy"] = "\186\206\199\165",
    ["burial niche"] = "\184\197\192\229 \186\174\176\168",
    ["button"] = "\185\246\198\176",
    ["cabinet"] = "\188\246\179\179\192\229",
    ["cage"] = "\191\236\184\174",
    ["cart"] = "\188\246\183\185",
    ["castle"] = "\188\186",
    ["cave"] = "\181\191\177\188",
    ["cave entrance"] = "\181\191\177\188 \192\212\177\184",
    ["cave in"] = "\181\191\177\188 \186\216\177\171",
    ["cave-in"] = "\181\191\177\188 \186\216\177\171",
    ["cavern"] = "\181\191\177\188",
    ["ceiling"] = "\195\181\192\229",
    ["chair"] = "\192\199\192\218",
    ["chest"] = "\187\243\192\218",
    ["coffin"] = "\176\252",
    ["column"] = "\177\226\181\213",
    ["corpse"] = "\189\195\195\188",
    ["crate"] = "\179\170\185\171 \187\243\192\218",
    ["crypt"] = "\193\246\199\207\185\166\193\246",
    ["crystal"] = "\188\246\193\164",
    ["crystal ball"] = "\188\246\193\164\177\184",
    ["cylinder"] = "\191\248\197\235",
    ["dark pit"] = "\190\238\181\206\191\238 \177\184\181\162\192\204",
    ["deleted"] = "\187\232\193\166\181\202",
    ["desk"] = "\195\165\187\243",
    ["dock"] = "\188\177\194\248\192\229",
    ["docks"] = "\186\206\181\206",
    ["door"] = "\185\174",
    ["double door"] = "\190\231\185\174",
    ["drink"] = "\184\182\189\195\177\226",
    ["drink from fountain"] = "\186\208\188\246\191\161\188\173 \184\182\189\195\177\226",
    ["drink from the fountain"] = "\186\208\188\246\191\161\188\173 \184\182\189\195\177\226",
    ["drink from the well"] = "\191\236\185\176\191\161\188\173 \184\182\189\195\177\226",
    ["drink from trough"] = "\177\184\192\175\191\161\188\173 \184\182\189\195\177\226",
    ["drink from well"] = "\191\236\185\176\191\161\188\173 \184\182\189\195\177\226",
    ["east"] = "\181\191\194\202",
    ["elevator platform"] = "\189\194\176\173\177\226 \185\223\198\199",
    ["empty"] = "\186\241\190\238 \192\214\192\189",
    ["exit"] = "\195\226\177\184",
    ["exit door"] = "\195\226\177\184 \185\174",
    ["fireplace"] = "\186\174\179\173\183\206",
    ["floor"] = "\185\217\180\218",
    ["fort"] = "\191\228\187\245",
    ["found something"] = "\185\186\176\161\184\166 \195\163\190\210\180\217!",
    ["fountain"] = "\186\208\188\246",
    ["fruit tree"] = "\176\250\192\207\179\170\185\171",
    ["gate"] = "\188\186\185\174",
    ["gems"] = "\186\184\188\174",
    ["glowing dinosaur bones"] = "\186\251\179\170\180\194 \176\248\183\230 \187\192",
    ["gold vein"] = "\177\221 \177\164\184\198",
    ["grave"] = "\185\171\180\253",
    ["guano rock"] = "\177\184\190\198\179\235 \185\217\192\167",
    ["guild"] = "\177\230\181\229",
    ["guilds"] = "\177\230\181\229",
    ["house"] = "\193\253",
    ["hut"] = "\191\192\181\206\184\183",
    ["keg"] = "\188\250\197\235",
    ["key hole"] = "\191\173\188\232\177\184\184\219",
    ["keyhole"] = "\191\173\188\232\177\184\184\219",
    ["ladder"] = "\187\231\180\217\184\174",
    ["lever"] = "\183\185\185\246",
    ["lift"] = "\189\194\176\173\177\226",
    ["locked door"] = "\192\225\177\228 \185\174",
    ["look out"] = "\193\182\189\201\199\216!",
    ["lord markham"] = "\184\182\196\196 \176\230\192\199 \185\230",
    ["magic door"] = "\184\182\185\253\185\174",
    ["magic gate"] = "\184\182\185\253\185\174",
    ["magic gate open"] = "\184\182\185\253\185\174\192\204 \191\173\183\200\180\217",
    ["magic portal"] = "\184\182\185\253 \194\247\191\248\185\174",
    ["magically refreshing"] = "\184\182\185\253\195\179\183\179 \187\243\196\232\199\207\180\217!",
    ["mine"] = "\177\164\187\234",
    ["mirror"] = "\176\197\191\239",
    ["mural"] = "\186\174\200\173",
    ["no"] = "\190\198\180\207\191\228",
    ["no effect"] = "\200\191\176\250 \190\248\192\189",
    ["north"] = "\186\207\194\202",
    ["not very refreshing"] = "\186\176\183\206 \187\243\196\232\199\207\193\246 \190\202\180\217",
    ["nothing seems to have happened"] = "\190\198\185\171 \192\207\181\181 \192\207\190\238\179\170\193\246 \190\202\190\210\180\217",
    ["obelisk"] = "\191\192\186\167\184\174\189\186\197\169",
    ["old bones"] = "\179\176\192\186 \187\192",
    ["open crate"] = "\191\173\184\176 \179\170\185\171 \187\243\192\218",
    ["ore vein"] = "\177\164\184\198",
    ["ouch"] = "\190\198\190\223!",
    ["painting"] = "\177\215\184\178",
    ["pedestal"] = "\185\222\196\167\180\235",
    ["pillar"] = "\177\226\181\213",
    ["pirate ship"] = "\199\216\192\251\188\177",
    ["plaque"] = "\184\237\198\199",
    ["podium"] = "\191\172\180\220",
    ["poison"] = "\181\182!",
    ["poisoned spike"] = "\181\182 \176\161\189\195",
    ["pool"] = "\191\172\184\248",
    ["portal"] = "\194\247\191\248\185\174",
    ["portrait"] = "\195\202\187\243\200\173",
    ["read sign"] = "\199\165\193\246\198\199 \192\208\177\226",
    ["read signpost"] = "\199\165\193\246\198\199 \192\208\177\226",
    ["read the sign"] = "\199\165\193\246\198\199 \192\208\177\226",
    ["refreshing"] = "\187\243\196\232\199\207\180\217",
    ["refreshing !"] = "\187\243\196\232\199\207\180\217!",
    ["refreshing!"] = "\187\243\196\232\199\207\180\217!",
    ["rock"] = "\185\217\192\167",
    ["rubble"] = "\192\220\199\216",
    ["sack"] = "\192\218\183\231",
    ["sarcophagus"] = "\188\174\176\252",
    ["sealed crate"] = "\186\192\192\206\181\200 \179\170\185\171 \187\243\192\218",
    ["secret door"] = "\186\241\185\208\185\174",
    ["shop"] = "\187\243\193\161",
    ["shops"] = "\187\243\193\161",
    ["shrine"] = "\188\186\188\210",
    ["sign"] = "\199\165\193\246\198\199",
    ["signpost"] = "\199\165\193\246\198\199",
    ["south"] = "\179\178\194\202",
    ["stable"] = "\184\182\177\184\176\163",
    ["stables"] = "\184\182\177\184\176\163",
    ["statue"] = "\193\182\176\162\187\243",
    ["stone face"] = "\181\185 \190\243\177\188",
    ["submarine"] = "\192\225\188\246\199\212",
    ["suspicious floor"] = "\188\246\187\243\199\209 \185\217\180\218",
    ["switch"] = "\189\186\192\167\196\161",
    ["switch."] = "\189\186\192\167\196\161",
    ["table"] = "\197\185\192\218",
    ["take a drink"] = "\199\209 \184\240\177\221 \184\182\189\195\177\226",
    ["tapestry"] = "\197\194\199\199\189\186\198\174\184\174",
    ["teleporter"] = "\188\248\176\163\192\204\181\191 \192\229\196\161",
    ["temple"] = "\187\231\191\248",
    ["tent"] = "\195\181\184\183",
    ["that was not so refreshing"] = "\186\176\183\206 \187\243\196\232\199\207\193\246 \190\202\190\210\180\217",
    ["the bowl is empty"] = "\177\215\184\169\192\204 \186\241\190\238 \192\214\180\217",
    ["the chest is locked"] = "\187\243\192\218\176\161 \192\225\176\220 \192\214\180\217",
    ["the door is locked"] = "\185\174\192\204 \192\225\176\220 \192\214\180\217",
    ["the door is warded"] = "\185\174\191\161 \184\182\185\253 \186\192\192\206\192\204 \176\201\183\193 \192\214\180\217",
    ["the door will not budge"] = "\185\174\192\204 \178\222\194\189\181\181 \199\207\193\246 \190\202\180\194\180\217",
    ["the door won't budge"] = "\185\174\192\204 \178\222\194\189\181\181 \199\207\193\246 \190\202\180\194\180\217",
    ["the mead barrel is empty"] = "\185\250\178\220\188\250 \197\235\192\204 \186\241\190\238 \192\214\180\217",
    ["the sack is empty"] = "\192\218\183\231\176\161 \186\241\190\238 \192\214\180\217",
    ["there are no items that interest you"] = "\176\252\189\201 \176\161\180\194 \185\176\176\199\192\204 \190\248\180\217",
    ["this door is locked"] = "\192\204 \185\174\192\186 \192\225\176\220 \192\214\180\217",
    ["tomb"] = "\185\171\180\253",
    ["tombstone"] = "\185\166\186\241",
    ["torch"] = "\200\182\186\210",
    ["tower"] = "\197\190",
    ["trap"] = "\199\212\193\164!",
    ["trash heap"] = "\190\178\183\185\177\226 \180\245\185\204",
    ["tree"] = "\179\170\185\171",
    ["trough"] = "\177\184\192\175",
    ["unstable rock"] = "\186\210\190\200\193\164\199\209 \185\217\192\167",
    ["vault"] = "\177\221\176\237",
    ["wall"] = "\186\174",
    ["water"] = "\185\176",
    ["well"] = "\191\236\185\176",
    ["west"] = "\188\173\194\202",
    ["window"] = "\195\162\185\174",
    ["wine rack"] = "\191\205\192\206 \188\177\185\221",
    ["wooden door"] = "\179\170\185\171\185\174",
    ["yes"] = "\191\185",
    ["you found nothing of interest"] = "\200\239\185\204\183\206\191\238 \176\205\192\186 \195\163\193\246 \184\248\199\223\180\217",
    ["you found nothing useful"] = "\190\181 \184\184\199\209 \176\205\192\186 \195\163\193\246 \184\248\199\223\180\217",
    ["you pray"] = "\177\226\181\181\199\209\180\217",
    ["you pray at the shrine"] = "\188\186\188\210\191\161\188\173 \177\226\181\181\199\209\180\217",
    ["you successfully disarm the trap"] = "\199\212\193\164\192\187 \188\186\176\248\192\251\192\184\183\206 \199\216\193\166\199\223\180\217",
}

local resMap = {
    ["air"] = "\180\235\177\226 \192\250\199\215",
    ["all"] = "\184\240\181\231 \192\250\199\215",
    ["body"] = "\189\197\195\188 \192\250\199\215",
    ["dark"] = "\190\238\181\210 \192\250\199\215",
    ["earth"] = "\180\235\193\246 \192\250\199\215",
    ["elemental"] = "\191\248\188\210 \192\250\199\215",
    ["fire"] = "\200\173\191\176 \192\250\199\215",
    ["light"] = "\186\251 \192\250\199\215",
    ["magic"] = "\184\182\185\253 \192\250\199\215",
    ["mind"] = "\193\164\189\197 \192\250\199\215",
    ["poison"] = "\181\182 \192\250\199\215",
    ["spirit"] = "\191\181\200\165 \192\250\199\215",
    ["water"] = "\185\176 \192\250\199\215",
}

local statMap = {
    ["ac"] = "\185\230\190\238\183\194",
    ["accuracy"] = "\193\164\200\174\181\181",
    ["accuracy and speed"] = "\193\164\200\174\181\181 \185\215 \188\211\181\181",
    ["all statistics"] = "\184\240\181\231 \180\201\183\194\196\161",
    ["all stats"] = "\184\240\181\231 \180\201\183\194\196\161",
    ["armor class"] = "\185\230\190\238\183\194",
    ["endurance"] = "\192\206\179\187\183\194",
    ["endurance and might"] = "\192\206\179\187\183\194 \185\215 \200\251",
    ["hit point"] = "\187\253\184\237\183\194",
    ["hit points"] = "\187\253\184\237\183\194",
    ["hp"] = "\187\253\184\237\183\194",
    ["intellect"] = "\193\246\180\201",
    ["intellect and personality"] = "\193\246\180\201 \185\215 \176\179\188\186",
    ["level"] = "\183\185\186\167",
    ["luck"] = "\199\224\191\238",
    ["might"] = "\200\251",
    ["might and endurance"] = "\200\251 \185\215 \192\206\179\187\183\194",
    ["personality"] = "\176\179\188\186",
    ["power"] = "\192\167\183\194",
    ["seven statistic"] = "\184\240\181\231 \180\201\183\194\196\161",
    ["seven statistics"] = "\184\240\181\231 \180\201\183\194\196\161",
    ["sp"] = "\184\182\179\170",
    ["speed"] = "\188\211\181\181",
    ["spell point"] = "\184\182\179\170",
    ["spell points"] = "\184\182\179\170",
}

local tempStr = " (\192\207\189\195\192\251)"
local permanentStr = " (\191\181\177\184)"

local function cleanEffectDescriptor(text)
    local lower = text:lower()
    local temporary = lower:find("temporary", 1, true) or
        lower:find("temporarily", 1, true) or
        lower:match("%f[%a]temp%f[%A]")
    local permanent = lower:find("permanent", 1, true) or
        lower:find("permanently", 1, true)
    lower = lower:gsub("%((temp)%)", " ")
    lower = lower:gsub("%((temporary)%)", " ")
    lower = lower:gsub("%((permanent)%)", " ")
    lower = lower:gsub("%f[%a]temporarily%f[%A]", " ")
    lower = lower:gsub("%f[%a]temporary%f[%A]", " ")
    lower = lower:gsub("%f[%a]permanently%f[%A]", " ")
    lower = lower:gsub("%f[%a]permanent%f[%A]", " ")
    lower = lower:gsub("%f[%a]temp%f[%A]", " ")
    lower = lower:gsub("%f[%a]gained%f[%A]", " ")
    lower = lower:gsub("[%.%!]+$", "")
    lower = lower:gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
    return lower, temporary and true or false, permanent and true or false
end

local function translateEffectMessage(text)
    local clean, temporary, permanent = cleanEffectDescriptor(text)
    local amount, descriptor = clean:match("^([%+%-]?%s*%d+)%s+(.+)$")
    if not amount then
        descriptor, amount = clean:match("^(.+)%s+([%+%-]?%s*%d+)$")
    end
    if not amount or not descriptor then return nil end
    amount = amount:gsub("%s+", "")
    descriptor = descriptor:gsub("^%s+", ""):gsub("%s+$", "")

    local translated = statMap[descriptor]
    if not translated then
        local resistance = descriptor:match("^(.-)%s+resistances?$") or
            descriptor:match("^(.-)%s+resist$")
        if resistance then
            translated = resMap[resistance:gsub("^%s+", ""):gsub("%s+$", "")]
        elseif descriptor == "all resistance" or descriptor == "all resistances" then
            translated = resMap.all
        end
    end
    if not translated then return nil end
    local suffix = temporary and tempStr or (permanent and permanentStr or "")
    return encodeKorean(amount .. " " .. translated .. suffix)
end

local function translateSignText(text)
    if type(text) ~= "string" or text == "" then
        return nil
    end

    local normalizedText = normalizeHintKey(text)
    local directHouseTranslation = houseTextTranslations[text] or
        (normalizedText and houseTextTranslations[normalizedText])
    if directHouseTranslation then
        return directHouseTranslation
    end

    if text:find("\7", 1, true) then
        return nil
    end

    local promptMatch = normalizedText and promptMap[normalizedText]
    if promptMatch then
        return encodeKorean(promptMatch)
    end

    -- Flexible well and fountain matching
    local ltext = text:lower()
    if ltext:find("well") then
        if ltext:find("drink") then
            return encodeKorean("\191\236\185\176\191\161\188\173\32\184\182\189\195\177\226")
        else
            return encodeKorean("\191\236\185\176")
        end
    end
    if ltext:find("fountain") then
        if ltext:find("drink") then
            return encodeKorean("\186\208\188\246\191\161\188\173\32\184\182\189\195\177\226")
        else
            return encodeKorean("\186\208\188\246")
        end
    end

    -- Generic stat/resistance effects in either order. Handles examples such
    -- as "+10 Might Temporary", "Might +10 (Temporary)", compound stats,
    -- permanent bonuses and all/elemental/magic resistance.
    local effectText = translateEffectMessage(text)
    if effectText then
        return effectText
    end

    -- Match points restored formats: +5 points restored / 5 Spell points restored
    local pSign, ptype = text:match("([%+%-]?%s*%d+)%s+(.-)[Pp]oints%s+[Rr]estored")
    if pSign and ptype then
        ptype = ptype:lower()
        local typeStr = "\198\247\192\206\198\174\32"
        if ptype:find("hit") then
            typeStr = "\187\253\184\237\183\194\32"
        elseif ptype:find("spell") then
            typeStr = "\184\182\179\170\32"
        end
        return encodeKorean(pSign .. " " .. typeStr .. "\200\184\186\185\181\202")
    end

    -- Match date/time format anywhere in string: 10:01am Wednesday 3 January 1172
    local tm, wday, mday, mon, yr = text:match("(%d+:%d+%s*[apAP][mM])%s+([A-Za-z]+)%s+(%d+)%s+([A-Za-z]+)%s+(%d+)")
    if tm and wday and mday and mon and yr then
        local krWday = dayMap[wday]
        local krMon = monthMap[mon]
        if krWday and krMon then
            local period = tm:lower():find("am") and "\191\192\192\252\32" or "\191\192\200\196\32"
            local cleanTime = tm:lower():gsub("[ap]m", "")
            return encodeKorean(yr .. "\179\226\32" .. krMon .. " " .. mday .. "\192\207\32" .. krWday .. " " .. period .. cleanTime)
        end
    end

    local knownPlaces = {
        ["Abandoned Temple"] = "\185\246\183\193\193\248 \187\231\191\248",
        ["Blackshire"] = "\186\237\183\162\187\254\192\204\190\238",
        ["Castle Gryphonheart"] = "\177\215\184\174\198\249\199\207\198\174 \188\186",
        ["Castle Harmondale"] = "\199\207\184\243\181\165\192\207 \188\186",
        ["Castle Harmondy"] = "\199\207\184\243\181\240 \188\186",
        ["Castle Ironfist"] = "\190\198\192\204\190\240\199\199\189\186\198\174 \188\186",
        ["Castle Stone"] = "\189\186\197\230 \188\186",
        ["Dragon's Lair"] = "\191\235\192\199 \181\213\193\246",
        ["Dragoons' Caverns"] = "\181\229\182\243\177\186\192\199 \181\191\177\188",
        ["Emerald Island"] = "\191\161\184\222\182\246\181\229 \188\182",
        ["Emerald Isle"] = "\191\161\184\222\182\246\181\229 \188\182",
        ["Escaton's Crystal"] = "\191\161\189\186\196\171\197\230\192\199 \188\246\193\164",
        ["Fort Riverstride"] = "\184\174\185\246\189\186\198\174\182\243\192\204\181\229 \191\228\187\245",
        ["Free Haven"] = "\199\193\184\174 \199\236\192\204\186\236",
        ["Gharik's Forge"] = "\176\161\184\175\192\199 \180\235\192\229\176\163",
        ["Grand Temple of the Sun"] = "\197\194\190\231\192\199 \180\235\189\197\192\252",
        ["Harmondale"] = "\199\207\184\243\181\165\192\207",
        ["Ironfist Castle"] = "\190\198\192\204\190\240\199\199\189\186\198\174 \188\186",
        ["New Sorpigal"] = "\180\186 \188\210\199\199\176\165",
        ["Red Dwarf Mines"] = "\186\211\192\186 \181\229\191\246\199\193 \177\164\187\234",
        ["School of Sorcery"] = "\184\182\185\253 \199\208\177\179",
        ["Shadow Guild Hideout"] = "\177\215\184\178\192\218 \177\230\181\229 \192\186\189\197\195\179",
        ["Silver Cove"] = "\189\199\185\246 \196\218\186\234",
        ["Silver Helm Outpost"] = "\189\199\185\246 \199\239\184\167 \192\252\195\202\177\226\193\246",
        ["Silver Helm Stronghold"] = "\189\199\185\246 \199\239\184\167 \191\228\187\245",
        ["Snergle's Caverns"] = "\189\186\179\202\177\219\192\199 \181\191\177\188",
        ["Temple of Baa"] = "\185\217\190\198\192\199 \187\231\191\248",
        ["The Grand Temple of the Sun"] = "\197\194\190\231\192\199 \180\235\189\197\192\252",
        ["The Temple of the Moon"] = "\180\222\192\199 \187\231\191\248",
        ["the Arena"] = "\197\245\177\226\192\229",
        ["the Cave"] = "\181\191\177\188",
        ["the Dragon's Cave"] = "\191\235\192\199 \181\191\177\188",
        ["the Dwarven Barrow"] = "\181\229\191\246\199\193 \176\237\186\208",
        ["the Submarine"] = "\192\225\188\246\199\212",
        ["the Throne Room"] = "\191\213\193\194\192\199 \185\230",
    }
    local action, actionPlace = text:match("^([Ee]nter)%s+(.+)[%.%!]*$")
    if not action then
        action, actionPlace = text:match("^([Ll]eave)%s+(.+)[%.%!]*$")
    end
    if action and actionPlace then
        local translatedPlace = knownPlaces[actionPlace]
        if translatedPlace then
            if action:lower() == "enter" then
                return encodeKorean(translatedPlace .. "\191\161 \181\233\190\238\176\161\177\226")
            else
                return encodeKorean(translatedPlace .. "\191\161\188\173 \179\170\176\161\177\226")
            end
        end
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
    for index = 0, 1999 do
        local ok, text = pcall(function() return evt.str[index] end)
        if ok then
            local translated = translateSignText(text)
            if translated then
                pcall(function() evt.str[index] = translated end)
            end
        end
    end
end

local function localizeOneHint(index, text)
    local translated = translateSignText(text)
    if translated then
        pcall(function() evt.hint[index] = translated end)
    end
end

local function localizeEventHints()
    if not evt or not evt.hint then
        return
    end

    -- evt.hint can be a proxy table. pairs() does not enumerate every hint on
    -- all MMExtension/Merge builds, so scan the event-id range explicitly.
    local visited = {}
    for index = 0, 1999 do
        local ok, hintText = pcall(function() return evt.hint[index] end)
        if ok and type(hintText) == "string" and hintText ~= "" then
            visited[index] = true
            localizeOneHint(index, hintText)
        end
    end

    -- Preserve compatibility with custom scripts that use non-numeric keys or
    -- event ids outside the normal range.
    local ok, iterator, state, first = pcall(pairs, evt.hint)
    if ok and iterator then
        for index, hintText in iterator, state, first do
            if not visited[index] and type(hintText) == "string" and hintText ~= "" then
                localizeOneHint(index, hintText)
            end
        end
    end
end

local pendingMapLocalizationPasses = 0

local function localizeMapTextNow()
    localizeEventStrings()
    localizeEventHints()
end

local function scheduleLateMapLocalization()
    -- Some map scripts assign evt.hint after the normal LoadMap callbacks.
    -- Reapply for a few rendered frames, then stop.
    pendingMapLocalizationPasses = 8
end

-- Translate before map scripts copy evt.str values into evt.hint.
function events.BeforeLoadMapScripts()
    localizeEventStrings()
end

-- Catch strings and hints added by the map script itself.
function events.LoadMapScripts()
    localizeMapTextNow()
    scheduleLateMapLocalization()
end

function events.LoadMap()
    localizeMapTextNow()
    scheduleLateMapLocalization()
end

function events.AfterLoadMap()
    localizeMapTextNow()
    scheduleLateMapLocalization()
end

function events.Tick()
    if pendingMapLocalizationPasses > 0 then
        pendingMapLocalizationPasses = pendingMapLocalizationPasses - 1
        localizeMapTextNow()
    end
end
