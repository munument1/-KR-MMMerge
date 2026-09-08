-- Targeted fixes for player-reported strings that are not owned by the normal
-- localization tables. Keep runtime Korean strings as EUC-KR byte escapes:
-- the native DBCS renderer consumes game-encoding bytes, not UTF-8 source bytes.

KoreanReportedLocalization = KoreanReportedLocalization or {}

local function encodeKorean(text)
    if KoreanText and KoreanText.EncodeOnce then
        return KoreanText.EncodeOnce(text)
    end
    return text
end

local UI_TEXT = {
    ["Free class / portrait combinations are allowed now."] = "\192\204\193\166 \197\172\183\161\189\186/\195\202\187\243\200\173 \193\182\199\213\192\187 \192\218\192\175\183\211\176\212 \188\177\197\195\199\210 \188\246 \192\214\189\192\180\207\180\217.",
    ["Free class/portrait combinations are allowed now."] = "\192\204\193\166 \197\172\183\161\189\186/\195\202\187\243\200\173 \193\182\199\213\192\187 \192\218\192\175\183\211\176\212 \188\177\197\195\199\210 \188\246 \192\214\189\192\180\207\180\217.",
    ["Free class / portrait combinations are disabled now."] = "\192\204\193\166 \197\172\183\161\189\186/\195\202\187\243\200\173 \193\182\199\213 \193\166\199\209\192\204 \192\251\191\235\181\203\180\207\180\217.",
    ["Free class/portrait combinations are disabled now."] = "\192\204\193\166 \197\172\183\161\189\186/\195\202\187\243\200\173 \193\182\199\213 \193\166\199\209\192\204 \192\251\191\235\181\203\180\207\180\217.",
    ["Interface:"] = "\192\206\197\205\198\228\192\204\189\186:",
    ["Interface"] = "\192\206\197\205\198\228\192\204\189\186",
    ["UI depends on continent"] = "\180\235\183\250\191\161 \181\251\182\243 UI \186\175\176\230",
    ["Increase view range"] = "\189\195\190\223 \176\197\184\174 \193\245\176\161",
    ["Smaller potion bottles"] = "\192\219\192\186 \185\176\190\224\186\180",
    ["Interface settings"] = "\192\206\197\205\198\228\192\204\189\186 \188\179\193\164",
    ["Interface Settings"] = "\192\206\197\205\198\228\192\204\189\186 \188\179\193\164",
    ["Extra settings"] = "\195\223\176\161 \188\179\193\164",
    ["Extra Settings"] = "\195\223\176\161 \188\179\193\164",
    ["General settings"] = "\192\207\185\221 \188\179\193\164",
    ["General Settings"] = "\192\207\185\221 \188\179\193\164",
    ["Bolster multipliers"] = "\184\243\189\186\197\205 \176\173\200\173 \185\232\192\178",
    ["Bolster Multipliers"] = "\184\243\189\186\197\205 \176\173\200\173 \185\232\192\178",
    ["Keybinds"] = "\197\176 \188\179\193\164"
}

local function translateUI(text)
    if type(text) ~= "string" then
        return text
    end
    local localized = UI_TEXT[text]
    if localized then
        return encodeKorean(localized)
    end
    return text
end

-- Merge creates part of the Extra Settings / Controls additions through
-- CustomUI. Wrap only exact player-facing literals so logic keys and unrelated
-- strings are never altered. (Text baked into icon images is handled separately.)
local function installCustomUIHooks()
    if not CustomUI or KoreanReportedLocalization.CustomUIHooksInstalled then
        return
    end

    if type(CustomUI.CreateText) == "function" then
        local originalCreateText = CustomUI.CreateText
        CustomUI.CreateText = function(settings, ...)
            if type(settings) == "table" and type(settings.Text) == "string" then
                settings.Text = translateUI(settings.Text)
            end
            return originalCreateText(settings, ...)
        end
    end

    if type(CustomUI.DisplayTooltip) == "function" then
        local originalDisplayTooltip = CustomUI.DisplayTooltip
        CustomUI.DisplayTooltip = function(text, ...)
            return originalDisplayTooltip(translateUI(text), ...)
        end
    end

    KoreanReportedLocalization.CustomUIHooksInstalled = true
end

installCustomUIHooks()

-- The continent chooser background is layer 1. CustomUI layer 0 is the front
-- layer; layer 2 sits behind the background and made the v1.0.16 labels invisible.
local function installContinentGameLabels()
    if KoreanReportedLocalization.ContinentLabelsInstalled or
            not CustomUI or type(CustomUI.CreateText) ~= "function" or
            not const or not const.Screens or not const.Screens.ChooseContinent or
            not Game or not Game.Smallnum_fnt then
        return
    end

    local screen = const.Screens.ChooseContinent
    local labels = {
        {Text = "M&M 8", X = 290, Y = 207}, -- Jadame
        {Text = "M&M 7", X = 404, Y = 404}, -- Antagarich
        {Text = "M&M 6", X = 176, Y = 404}  -- Enroth
    }

    for index, label in ipairs(labels) do
        CustomUI.CreateText{
            Key = "KoreanContinentGameLabel" .. index,
            Text = label.Text,
            Font = Game.Smallnum_fnt,
            ColorStd = 0xFFFF,
            AlignLeft = true,
            Layer = 0,
            Screen = screen,
            X = label.X,
            Y = label.Y,
            Width = 70,
            Height = 16
        }
    end

    KoreanReportedLocalization.ContinentLabelsInstalled = true
end

-- Merge implements Scholar/Teacher/Instructor as raw Learning skill bonuses,
-- not flat experience percentages. Learning mastery then multiplies the effect.
local HIRELING_LEARNING_DESCRIPTIONS = {
    [4] = {
        NPCText = 2324,
        Text = "\184\240\181\231 \196\179\184\175\197\205\192\199 \199\208\189\192 \177\226\188\250\191\161 +5 \186\184\179\202\189\186\184\166 \193\214\176\237 \190\198\192\204\197\219\192\187 \185\171\193\166\199\209\192\184\183\206 \189\196\186\176\199\213\180\207\180\217. \199\208\189\192 \188\247\183\195\181\181 \185\232\192\178\192\204 \192\251\191\235\181\203\180\207\180\217."
    },
    [13] = {
        NPCText = 2333,
        Text = "\184\240\181\231 \196\179\184\175\197\205\192\199 \199\208\189\192 \177\226\188\250\191\161 +10 \186\184\179\202\189\186\184\166 \193\221\180\207\180\217. \199\208\189\192 \188\247\183\195\181\181 \185\232\192\178\192\204 \192\251\191\235\181\203\180\207\180\217."
    },
    [14] = {
        NPCText = 2334,
        Text = "\184\240\181\231 \196\179\184\175\197\205\192\199 \199\208\189\192 \177\226\188\250\191\161 +15 \186\184\179\202\189\186\184\166 \193\221\180\207\180\217. \199\208\189\192 \188\247\183\195\181\181 \185\232\192\178\192\204 \192\251\191\235\181\203\180\207\180\217."
    }
}

local function applyHirelingLearningDescriptions()
    if not Game then
        return
    end

    for profession, entry in pairs(HIRELING_LEARNING_DESCRIPTIONS) do
        local localized = encodeKorean(entry.Text)
        if Game.NPCText then
            Game.NPCText[entry.NPCText] = localized
        end
        if Game.NPCProf and Game.NPCProf[profession] then
            Game.NPCProf[profession].Description = localized
        end
    end
end

-- Experience right-click uses a mixture of stats.txt and GlobalTxt strings.
-- Reapply the dynamic labels/formats as known-good EUC-KR bytes so UTF-8 Lua
-- source bytes cannot reach the native DBCS drawing/wrapping paths.
local EXPERIENCE_TEXT = {
    [17] = "\176\230\199\232\196\161",
    [83] = "\176\230\199\232\196\161",
    [537] = "\183\185\186\167 %d\177\238\193\246 \200\198\183\195: %d\176\241\181\229",
    [538] = "\176\230\199\232\196\161 %d\176\161 \180\245 \192\214\190\238\190\223 \183\185\186\167 %d\177\238\193\246 \200\198\183\195\199\210 \188\246 \192\214\189\192\180\207\180\217"
}

local function applyExperienceTextSafety()
    if not Game or not Game.GlobalTxt then
        return
    end
    for id, text in pairs(EXPERIENCE_TEXT) do
        Game.GlobalTxt[id] = encodeKorean(text)
    end
end

-- The compact MM7 history table embedded in the Korean LOD does not contain
-- the translated foreword. Apply record 1 using game-encoding byte escapes.
local MM7_FOREWORD = {
    Title = "\192\250\192\218\192\199 \188\173\185\174",
    Text = "\184\182\197\169\199\220 \176\230\192\186 \185\204\183\161 \188\188\180\235\181\233\192\204 \192\204\176\247\191\161\188\173 \185\250\190\238\193\246\180\194 \192\167\180\235\199\209 \192\207\181\233\192\187 \192\216\193\246 \190\202\181\181\183\207 \199\207\184\243\181\165\192\207 \188\186\176\250 \177\215 \188\210\192\175\193\214\181\233\191\161 \180\235\199\209 \192\204 \191\170\187\231\184\166 \192\219\188\186\199\216 \180\222\182\243\176\237 \179\187\176\212 \186\206\197\185\199\223\180\217. \192\204 \192\211\185\171\191\161 \195\230\189\199\199\210 \188\246 \192\214\177\226\184\166 \185\217\182\245\180\217. \193\214\191\228 \187\231\176\199\181\233\192\204 \192\207\190\238\179\175 \182\167\184\182\180\217 \177\215\176\205\192\204 \193\193\181\231 \179\170\187\218\181\231 \176\161\180\201\199\209 \199\209 \195\230\189\199\199\207\176\212 \192\204 \195\165\191\161 \177\226\183\207\199\210 \176\205\192\187 \185\207\190\238\181\181 \193\193\180\217. \192\204\176\247\191\161\188\173 \192\207\190\238\179\170\180\194 \192\207\192\187 \198\199\180\220\199\207\180\194 \176\205\192\186 \179\187 \191\170\199\210\192\204 \190\198\180\207\184\231, \191\192\193\247 \177\226\183\207\199\210 \187\211\192\204\180\217.\n\n\199\193\183\206\186\241\180\248\189\186\176\161 \191\236\184\174\191\161\176\212 \185\204\188\210 \193\254\177\226\184\166!\n\n\192\162\181\168 \198\174\192\167\181\229\n\177\195\193\164 \191\170\187\231\176\161"
}

local function applyMM7Foreword()
    if not Game or not Game.HistoryTxt or not Game.HistoryTxt[1] or
            not TownPortalControls or not Map then
        return
    end

    local ok, continent = pcall(TownPortalControls.MapOfContinent, Map.MapStatsIndex)
    if ok and continent == 2 then
        Game.HistoryTxt[1].Title = encodeKorean(MM7_FOREWORD.Title)
        Game.HistoryTxt[1].Text = encodeKorean(MM7_FOREWORD.Text)
    end
end

function events.GameInitialized2()
    installCustomUIHooks()
    installContinentGameLabels()
    applyHirelingLearningDescriptions()
    applyExperienceTextSafety()
end

function events.LoadMap()
    applyMM7Foreword()
    applyHirelingLearningDescriptions()
    applyExperienceTextSafety()
end

function events.AfterLoadMap()
    applyMM7Foreword()
    applyHirelingLearningDescriptions()
    applyExperienceTextSafety()
end

KoreanReportedLocalization.TranslateUI = translateUI
KoreanReportedLocalization.ApplyMM7Foreword = applyMM7Foreword
KoreanReportedLocalization.ApplyHirelingLearningDescriptions = applyHirelingLearningDescriptions
KoreanReportedLocalization.ApplyExperienceTextSafety = applyExperienceTextSafety
KoreanReportedLocalization.InstallContinentGameLabels = installContinentGameLabels
