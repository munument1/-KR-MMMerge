-- Plain Lua 5.1 regression harness for Scripts/General/KoreanHistory.lua.
-- Verifies that each continent receives Korean/localized history without
-- requiring a running MMExtension game process.

events = {}
vars = {}

local function callableArray(count)
    local t = {}
    for i = 1, count do
        t[i] = {Text = "ENGLISH_SENTINEL_" .. i, Title = "ENGLISH_TITLE_" .. i, Time = 0}
    end
    t.limit = count
    return setmetatable(t, {
        __call = function(self, _, previous)
            local i = (previous or 0) + 1
            if i <= count then
                return i, self[i]
            end
        end
    })
end

Game = {
    HistoryTxt = callableArray(40),
    LoadTextFileFromLod = function()
        error("localized loose history file unexpectedly missing")
    end
}

Party = {
    History = callableArray(40),
    AutonotesBits = {},
    QBits = {}
}

TownPortalControls = {
    MapOfContinent = function()
        return 1
    end
}
Map = {MapStatsIndex = 1}

-- string.split is supplied by MMExtension; provide the small equivalent used
-- by this script so the file can be executed with stock Lua 5.1.
function string.split(text, sep)
    local out = {}
    local start = 1
    while true do
        local p = string.find(text, sep, start, true)
        if not p then
            out[#out + 1] = string.sub(text, start)
            break
        end
        out[#out + 1] = string.sub(text, start, p - 1)
        start = p + #sep
    end
    return out
end

dofile("Scripts/General/KoreanHistory.lua")

local function reset()
    for i = 1, 40 do
        Game.HistoryTxt[i].Text = "ENGLISH_SENTINEL_" .. i
        Game.HistoryTxt[i].Title = "ENGLISH_TITLE_" .. i
    end
end

-- MM8: use the dedicated Korean history table, not Merge's English history.txt.
reset()
KoreanHistory.ApplyForContinent(1)
assert(Game.HistoryTxt[1].Text ~= "ENGLISH_SENTINEL_1", "MM8 history record 1 stayed English")
assert(Game.HistoryTxt[1].Title ~= "ENGLISH_TITLE_1", "MM8 history title stayed English")
local mm8records = KoreanHistory.LoadRecords(1)
assert(mm8records and mm8records[1] and next(mm8records), "MM8 Korean history did not parse")

-- MM7: record 2 is the reported 'History Gone By' regression.
reset()
KoreanHistory.ApplyForContinent(2)
assert(Game.HistoryTxt[1].Text ~= "ENGLISH_SENTINEL_1", "MM7 history record 1 stayed English")
assert(Game.HistoryTxt[2].Text ~= "ENGLISH_SENTINEL_2", "MM7 history record 2 stayed English")
assert(Game.HistoryTxt[2].Title ~= "ENGLISH_TITLE_2", "MM7 history record 2 title stayed English")
local mm7records = KoreanHistory.LoadRecords(2)
assert(mm7records and mm7records[2] and #mm7records[2].Text > 100, "MM7 Korean history record 2 did not parse")

-- MM6: Merge has no native history table; the Korean Enroth introduction must
-- replace any history left behind by the previous continent.
reset()
KoreanHistory.ApplyForContinent(3)
assert(Game.HistoryTxt[1].Text ~= "ENGLISH_SENTINEL_1", "MM6 Enroth introduction was not applied")
assert(Game.HistoryTxt[1].Title ~= "ENGLISH_TITLE_1", "MM6 Enroth title was not applied")
assert(Game.HistoryTxt[2].Text == "", "MM6 leaked another continent's history records")

print("Korean MM6/MM7/MM8 history application: OK")
