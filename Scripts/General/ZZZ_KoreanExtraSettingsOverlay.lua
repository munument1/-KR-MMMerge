-- Korean overlays for Merge settings pages whose labels are baked into icon images.
-- Runtime Korean strings are CP949/EUC-KR byte escapes for the native DBCS renderer.

KoreanExtraSettingsOverlay = KoreanExtraSettingsOverlay or {}

local function encodeKorean(text)
    if KoreanText and KoreanText.EncodeOnce then
        return KoreanText.EncodeOnce(text)
    end
    return text
end

local EXTRA_UI_TEXT = {
    ["Monster bolster"] = "\184\243\189\186\197\205 \176\173\200\173",
    ["Monster Bolster"] = "\184\243\189\186\197\205 \176\173\200\173",
    ["Bolster amount"] = "\176\173\200\173 \185\232\192\178",
    ["Bolster Amount"] = "\176\173\200\173 \185\232\192\178",
    ["Weather effects"] = "\179\175\190\190 \200\191\176\250",
    ["Weather Effects"] = "\179\175\190\190 \200\191\176\250",
    ["Show weather effects"] = "\179\175\190\190 \200\191\176\250",
    ["Show Weather Effects"] = "\179\175\190\190 \200\191\176\250",
    ["Improved pathfinding"] = "\199\226\187\243\181\200 \177\230\195\163\177\226",
    ["Improved Pathfinding"] = "\199\226\187\243\181\200 \177\230\195\163\177\226",
    ["Frame limit"] = "\199\193\183\185\192\211 \193\166\199\209",
    ["Frame Limit"] = "\199\193\183\185\192\211 \193\166\199\209",
    ["EXTRA KEYBINDS"] = "\195\223\176\161 \197\176 \188\179\193\164",
    ["Extra keybinds"] = "\195\223\176\161 \197\176 \188\179\193\164",
    ["Extra Keybinds"] = "\195\223\176\161 \197\176 \188\179\193\164",
    ["Character Options"] = "\196\179\184\175\197\205 \188\179\193\164",
    ["Character options"] = "\196\179\184\175\197\205 \188\179\193\164",
    ["CharacterName:"] = "\196\179\184\175\197\205 \192\204\184\167:",
    ["stop melee attack"] = "\177\217\193\162 \176\248\176\221 \193\223\193\246",
    ["stop ranged attack"] = "\191\248\176\197\184\174 \176\248\176\221 \193\223\193\246",
    ["-NO KEY-"] = "-\197\176 \190\248\192\189-"
}

local QUICK_SPELL_PREFIX = "\196\252\189\186\198\231 "

local function translateExtraText(text)
    if type(text) ~= "string" then
        return text
    end

    local localized = EXTRA_UI_TEXT[text]
    if localized then
        return encodeKorean(localized)
    end

    local slot = string.match(text, "^Q%. SPELL (%d+)$")
    if slot then
        return encodeKorean(QUICK_SPELL_PREFIX .. slot)
    end

    return text
end

local function screenMatches(screen, named, fallback)
    if screen == fallback then
        return true
    end
    return const and const.Screens and const.Screens[named] and
        screen == const.Screens[named]
end

local function screenIsRegistered(screen)
    return type(screen) == "number" and
        CustomUI and CustomUI.ActiveElements and
        CustomUI.ActiveElements[screen] ~= nil
end

local function installHooks()
    if not CustomUI or KoreanExtraSettingsOverlay.HooksInstalled then
        return
    end

    -- The normal Extra Settings page bakes its option labels into ExSetScr.
    -- Use ExSetScr2 as the blank canvas and draw those labels dynamically.
    -- ExtraKeybinds is different: its ExSetScrK bitmap also contains the key
    -- grid itself, so it must remain ExSetScrK.  zz LocKO.icons.lod provides a
    -- Korean ExSetScrK with the same grid and a localized heading.
    if type(CustomUI.CreateIcon) == "function" then
        local originalCreateIcon = CustomUI.CreateIcon
        CustomUI.CreateIcon = function(settings, ...)
            if type(settings) == "table" and
                    settings.Icon == "ExSetScr" and
                    screenMatches(settings.Screen, "ExtraSettings", 98) then
                settings.Icon = "ExSetScr2"
            end
            return originalCreateIcon(settings, ...)
        end
    end

    if type(CustomUI.CreateText) == "function" then
        local originalCreateText = CustomUI.CreateText
        CustomUI.CreateText = function(settings, ...)
            if type(settings) == "table" and type(settings.Text) == "string" then
                settings.Text = translateExtraText(settings.Text)
            end
            return originalCreateText(settings, ...)
        end
    end

    KoreanExtraSettingsOverlay.HooksInstalled = true
end

local function createLabel(screen, key, text, x, y, width)
    if not screenIsRegistered(screen) then
        return nil
    end
    return CustomUI.CreateText{
        Key = key,
        Text = encodeKorean(text),
        Font = Game and (Game.Lucida_fnt or Game.Smallnum_fnt) or nil,
        ColorStd = 0xFFFF,
        AlignLeft = true,
        Layer = 0,
        Screen = screen,
        X = x,
        Y = y,
        Width = width or 260,
        Height = 16
    }
end

local function installPageLabels()
    if KoreanExtraSettingsOverlay.PageLabelsInstalled or
            not CustomUI or type(CustomUI.CreateText) ~= "function" then
        return
    end

    local extraSettings = const and const.Screens and const.Screens.ExtraSettings
    local characterOptions = const and const.Screens and const.Screens.CharacterOptions

    -- Main Extra Settings page. Only touch screens that this Merge build has
    -- actually registered with InterfaceManager.  Some builds do not ship the
    -- optional CharacterOptions page; hard-coding screen 94 crashes AddElement.
    if screenIsRegistered(extraSettings) then
        createLabel(extraSettings, "KoreanExtraSettingsTitle",
            "\192\207\185\221 \188\179\193\164", 220, 151, 220)
        createLabel(extraSettings, "KoreanMonsterBolster",
            "\184\243\189\186\197\205 \176\173\200\173", 220, 177, 260)
        createLabel(extraSettings, "KoreanBolsterAmount",
            "\176\173\200\173 \185\232\192\178", 220, 220, 260)
        createLabel(extraSettings, "KoreanWeatherEffects",
            "\179\175\190\190 \200\191\176\250", 220, 253, 260)
        createLabel(extraSettings, "KoreanInfinityView",
            "\189\195\190\223 \176\197\184\174 \193\245\176\161", 220, 290, 260)
        createLabel(extraSettings, "KoreanImprovedPathfinding",
            "\199\226\187\243\181\200 \177\230\195\163\177\226", 220, 328, 280)
    end

    -- ExSetScrK in the Korean icons archive already carries the localized
    -- "추가 키 설정" heading and the key grid.  Its six Q. SPELL rows and
    -- key names are translated dynamically by the CreateText hook above.

    -- CharacterOptions is optional across Merge builds.  Add its heading only
    -- when the page exists; otherwise leave it untouched instead of fabricating
    -- screen id 94 and crashing InterfaceManager.AddElement.
    if screenIsRegistered(characterOptions) then
        createLabel(characterOptions, "KoreanCharacterOptionsTitle",
            "\196\179\184\175\197\205 \188\179\193\164", 220, 151, 240)
    end

    KoreanExtraSettingsOverlay.PageLabelsInstalled = true
end

installHooks()

function events.GameInitialized2()
    installHooks()
    installPageLabels()
end

KoreanExtraSettingsOverlay.TranslateText = translateExtraText
KoreanExtraSettingsOverlay.InstallHooks = installHooks
KoreanExtraSettingsOverlay.InstallPageLabels = installPageLabels
KoreanExtraSettingsOverlay.ScreenIsRegistered = screenIsRegistered
