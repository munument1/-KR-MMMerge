-- Runtime hotfixes for v1.0.17 regressions.
-- Keep this file ASCII-only.

KoreanRuntimeHotfix = KoreanRuntimeHotfix or {}

local CONTINENT_LABEL_KEYS = {
    "KoreanContinentGameLabel1",
    "KoreanContinentGameLabel2",
    "KoreanContinentGameLabel3"
}

local LOWER_CONTINENT_BUTTONS = {
    SlAntagDw = true,
    SlEnrothDw = true
}

local function ensureContinentLabelsActive()
    if KoreanReportedLocalization and
            type(KoreanReportedLocalization.InstallContinentGameLabels) == "function" then
        KoreanReportedLocalization.InstallContinentGameLabels()
    end

    if not CustomUI or not CustomUI.ActiveElements or
            not const or not const.Screens or not const.Screens.ChooseContinent then
        return 0
    end

    local screen = CustomUI.ActiveElements[const.Screens.ChooseContinent]
    local layer = screen and screen.Texts and screen.Texts[0]
    if not layer then
        return 0
    end

    local enabled = 0
    for _, key in ipairs(CONTINENT_LABEL_KEYS) do
        local element = layer[key]
        if element then
            element.Active = true
            enabled = enabled + 1
        end
    end
    return enabled
end

local function promoteLowerContinentButtons()
    if not CustomUI or not CustomUI.ActiveElements or
            not const or not const.Screens or not const.Screens.ChooseContinent then
        return 0
    end

    local screen = CustomUI.ActiveElements[const.Screens.ChooseContinent]
    local buttons = screen and screen.Buttons
    local front = buttons and buttons[0]
    local middle = buttons and buttons[1]
    if not front or not middle then
        return 0
    end

    local moves = {}
    for key, button in pairs(front) do
        if button and LOWER_CONTINENT_BUTTONS[button.IUpSrc] then
            moves[#moves + 1] = {Key = key, Button = button}
        end
    end

    for _, move in ipairs(moves) do
        front[move.Key] = nil
        move.Button.Layer = 1

        -- CustomUI generates numeric keys independently for each layer.
        -- Reusing a layer-0 key after moving the button can overwrite an
        -- existing layer-1 button (Jadame/MM8 is normally middle[1]).
        -- Give promoted buttons stable, layer-unique string keys instead.
        local newKey = "KoreanPromoted_" .. tostring(move.Button.IUpSrc or move.Key)
        local suffix = 2
        while middle[newKey] and middle[newKey] ~= move.Button do
            newKey = "KoreanPromoted_" .. tostring(move.Button.IUpSrc or move.Key) .. "_" .. suffix
            suffix = suffix + 1
        end

        move.Button.Key = newKey
        middle[newKey] = move.Button
    end

    return #moves
end

local function reapplyLocalizedHistory()
    if not KoreanHistory or type(KoreanHistory.ApplyForContinent) ~= "function" or
            not TownPortalControls or not Map then
        return nil
    end

    local ok, continent = pcall(TownPortalControls.MapOfContinent, Map.MapStatsIndex)
    if not ok or not continent then
        return nil
    end

    KoreanHistory.ApplyForContinent(continent)
    return continent
end

function events.GameInitialized2()
    -- MenuChooseContinent creates Jadam on layer 1, but Antagarich and Enroth
    -- buttons on layer 0. InterfaceManager renders Texts before Buttons inside
    -- one layer, so layer-0 MM7/MM6 labels were covered by those two buttons.
    -- Keep all three normal labels active and move only the two lower buttons
    -- behind the layer-0 labels. M&M8 remains on the path that already worked.
    ensureContinentLabelsActive()
    promoteLowerContinentButtons()
end

function events.LoadMap()
    -- ZZZZ loads after the normal localization scripts, so this is a final
    -- guard against Merge reloading native English history during map setup.
    reapplyLocalizedHistory()
end

function events.AfterLoadMap()
    reapplyLocalizedHistory()
end

KoreanRuntimeHotfix.EnsureContinentLabelsActive = ensureContinentLabelsActive
KoreanRuntimeHotfix.PromoteLowerContinentButtons = promoteLowerContinentButtons
KoreanRuntimeHotfix.ReapplyLocalizedHistory = reapplyLocalizedHistory
