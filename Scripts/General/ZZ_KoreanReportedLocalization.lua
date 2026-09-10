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

    -- Merge prefixes several Extra Settings page headers with a literal space
    -- (for example " Interface settings" and " Keybinds"). Exact matching
    -- therefore missed strings that were already present in UI_TEXT. Keep the
    -- layout whitespace while translating the visible core text.
    local leading, core, trailing = string.match(text, "^(%s*)(.-)(%s*)$")
    local localized = UI_TEXT[core]
    if localized then
        return leading .. encodeKorean(localized) .. trailing
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

-- Merge implements Scholar/Teacher/Instructor as raw Learning skill bonuses
-- of +5/+10/+15. Do not copy descriptions through Game.NPCText here: the
-- localized table and the profession structure do not share stable indexing
-- across every Merge build, which produced bogus values such as +60 at runtime.
local HIRELING_LEARNING_DESCRIPTIONS = {
    [4] = "\176\237\191\235 \193\223\191\161\180\194 \199\208\189\192 \177\226\188\250\192\204 5 \193\245\176\161\199\213\180\207\180\217.",
    [13] = "\176\237\191\235 \193\223\191\161\180\194 \199\208\189\192 \177\226\188\250\192\204 10 \193\245\176\161\199\213\180\207\180\217.",
    [14] = "\176\237\191\235 \193\223\191\161\180\194 \199\208\189\192 \177\226\188\250\192\204 15 \193\245\176\161\199\213\180\207\180\217."
}

local function applyHirelingLearningDescriptions()
    if not Game or not Game.NPCProf then
        return
    end

    for profession, description in pairs(HIRELING_LEARNING_DESCRIPTIONS) do
        if Game.NPCProf[profession] then
            Game.NPCProf[profession].Description = encodeKorean(description)
        end
    end
end
-- Experience/GlobalTxt wording is owned by KO_GlobalTxt/PO and is
-- re-applied through generated KO_RuntimeOverrides.txt.


function events.GameInitialized2()
    installCustomUIHooks()
    installContinentGameLabels()
    applyHirelingLearningDescriptions()
end

function events.LoadMap()
    applyHirelingLearningDescriptions()
end

function events.AfterLoadMap()
    applyHirelingLearningDescriptions()
end

KoreanReportedLocalization.TranslateUI = translateUI
KoreanReportedLocalization.ApplyHirelingLearningDescriptions = applyHirelingLearningDescriptions
KoreanReportedLocalization.InstallContinentGameLabels = installContinentGameLabels
