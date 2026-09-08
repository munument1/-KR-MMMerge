-- Runtime hotfixes for v1.0.17 regressions.
-- Keep this file ASCII-only. MM7History_KO.txt is read as raw game-encoding bytes.

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
        middle[move.Key] = move.Button
    end

    return #moves
end

local MM7_HISTORY_PATH = "Data/Text localization/MM7History_KO.txt"
local mm7HistoryRecords

local function parseMM7History()
    if mm7HistoryRecords then
        return mm7HistoryRecords
    end

    local file = io.open(MM7_HISTORY_PATH, "rb")
    if not file then
        return nil
    end

    local data = file:read("*a")
    file:close()

    local records = {}
    for row in string.gmatch(data, "[^\r]+") do
        -- Support either CR-only records or CRLF records without touching the
        -- intentional LF paragraph breaks embedded inside the Text field.
        row = string.gsub(row, "^\n+", "")
        if row ~= "" and string.sub(row, 1, 2) ~= "#\t" then
            local tab1 = string.find(row, "\t", 1, true)
            local tab2 = tab1 and string.find(row, "\t", tab1 + 1, true)
            local tab3 = tab2 and string.find(row, "\t", tab2 + 1, true)
            if tab1 and tab2 and tab3 then
                local id = tonumber(string.sub(row, 1, tab1 - 1))
                if id then
                    records[id] = {
                        Text = string.sub(row, tab1 + 1, tab2 - 1),
                        Title = string.sub(row, tab3 + 1)
                    }
                end
            end
        end
    end

    mm7HistoryRecords = records
    return records
end

local function applyAllMM7History()
    if not Game or not Game.HistoryTxt or not TownPortalControls or not Map then
        return
    end

    local ok, continent = pcall(TownPortalControls.MapOfContinent, Map.MapStatsIndex)
    if not ok or continent ~= 2 then
        return
    end

    local records = parseMM7History()
    if not records then
        return
    end

    for id, record in pairs(records) do
        if Game.HistoryTxt[id] then
            Game.HistoryTxt[id].Text = record.Text
            Game.HistoryTxt[id].Title = record.Title
        end
    end
end

function events.GameInitialized2()
    -- MenuChooseContinent creates Jadam on layer 1, but Antagarich and Enroth
    -- buttons on layer 0. InterfaceManager renders Texts before Buttons inside
    -- one layer, so layer-0 MM7/MM6 labels were covered by those two buttons.
    -- Keep the normal layer-0 labels (including the already-working M&M8 one)
    -- and move only the two lower continent buttons to layer 1.
    ensureContinentLabelsActive()
    promoteLowerContinentButtons()
end

function events.LoadMap()
    applyAllMM7History()
end

function events.AfterLoadMap()
    applyAllMM7History()
end

KoreanRuntimeHotfix.EnsureContinentLabelsActive = ensureContinentLabelsActive
KoreanRuntimeHotfix.PromoteLowerContinentButtons = promoteLowerContinentButtons
KoreanRuntimeHotfix.ParseMM7History = parseMM7History
KoreanRuntimeHotfix.ApplyAllMM7History = applyAllMM7History
