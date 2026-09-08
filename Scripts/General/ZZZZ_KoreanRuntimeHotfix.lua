-- Runtime hotfixes for v1.0.17 regressions.
-- Keep this file ASCII-only. MM7History_KO.txt is read as raw game-encoding bytes.

KoreanRuntimeHotfix = KoreanRuntimeHotfix or {}

local CONTINENT_LABEL_KEYS = {
    "KoreanContinentGameLabel1",
    "KoreanContinentGameLabel2",
    "KoreanContinentGameLabel3"
}

local CONTINENT_LABELS = {
    {Text = "M&M 8", X = 290, Y = 207},
    {Text = "M&M 7", X = 404, Y = 404},
    {Text = "M&M 6", X = 176, Y = 404}
}

local function deactivateLegacyContinentLabels()
    if not CustomUI or not CustomUI.ActiveElements or
            not const or not const.Screens or not const.Screens.ChooseContinent then
        return
    end

    local screen = CustomUI.ActiveElements[const.Screens.ChooseContinent]
    local layer = screen and screen.Texts and screen.Texts[0]
    if not layer then
        return
    end

    for _, key in ipairs(CONTINENT_LABEL_KEYS) do
        local element = layer[key]
        if element then
            element.Active = false
        end
    end
end

local function drawContinentLabelsOnTop()
    if not CustomUI or type(CustomUI.ShowText) ~= "function" or
            not const or not const.Screens or not const.Screens.ChooseContinent or
            not Game or Game.CurrentScreen ~= const.Screens.ChooseContinent or
            not Game.Smallnum_fnt then
        return
    end

    for _, label in ipairs(CONTINENT_LABELS) do
        CustomUI.ShowText(
            label.Text,
            Game.Smallnum_fnt,
            label.X,
            label.Y,
            3,
            0, 0, 0,
            70, 16,
            0, 0,
            0xFFFF,
            true
        )
    end
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
    -- ZZ_KoreanReportedLocalization.lua registers the legacy labels earlier in
    -- the load order, so disable them here. We redraw after layer-0 buttons.
    deactivateLegacyContinentLabels()
end

function events.FGInterfaceUpd()
    -- InterfaceManager calls FGInterfaceUpd after processing layer-0 Texts and
    -- Buttons. This keeps MM6/MM7 labels from being painted over by their
    -- layer-0 continent buttons. (MM8 happened to work because its button is
    -- layer 1.)
    drawContinentLabelsOnTop()
end

function events.LoadMap()
    applyAllMM7History()
end

function events.AfterLoadMap()
    applyAllMM7History()
end

KoreanRuntimeHotfix.DeactivateLegacyContinentLabels = deactivateLegacyContinentLabels
KoreanRuntimeHotfix.DrawContinentLabelsOnTop = drawContinentLabelsOnTop
KoreanRuntimeHotfix.ParseMM7History = parseMM7History
KoreanRuntimeHotfix.ApplyAllMM7History = applyAllMM7History
