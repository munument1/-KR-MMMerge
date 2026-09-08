-- Regression harness for Scripts/General/KoreanHistory.lua.
-- Uses the real MM7/MM8 KO history tables shipped by the repository.

events = {}

local history = {}
for i = 1, 128 do
    history[i] = {Text = "ENGLISH_SENTINEL", Title = "ENGLISH_SENTINEL", Time = 0}
end
setmetatable(history, {
    __call = function(self, state, last)
        local i = (last or 0) + 1
        if self[i] then
            return i, self[i]
        end
    end
})

Game = {
    HistoryTxt = history,
    LoadTextFileFromLod = function(name)
        return ""
    end
}

dofile("Scripts/General/KoreanHistory.lua")

local function countRecords(records)
    local n = 0
    for _ in pairs(records or {}) do
        n = n + 1
    end
    return n
end

local function hasHighByte(text)
    if type(text) ~= "string" then
        return false
    end
    for i = 1, #text do
        if string.byte(text, i) >= 128 then
            return true
        end
    end
    return false
end

local mm8 = KoreanHistory.LoadRecords(1)
assert(mm8 and countRecords(mm8) >= 3, "MM8 Korean history table was not parsed")
KoreanHistory.ApplyForContinent(1)
assert(history[1].Text ~= "ENGLISH_SENTINEL", "MM8 history record 1 remained English")
assert(hasHighByte(history[1].Text), "MM8 history record 1 does not contain Korean game bytes")
assert(history[2].Text ~= "ENGLISH_SENTINEL", "MM8 history record 2 remained English")

for i = 1, 128 do
    history[i].Text = "ENGLISH_SENTINEL"
    history[i].Title = "ENGLISH_SENTINEL"
end

local mm7 = KoreanHistory.LoadRecords(2)
assert(mm7 and countRecords(mm7) >= 3, "MM7 Korean history table was not parsed")
KoreanHistory.ApplyForContinent(2)
assert(history[1].Text ~= "ENGLISH_SENTINEL", "MM7 history record 1 remained English")
assert(history[2].Text ~= "ENGLISH_SENTINEL", "MM7 history record 2 remained English")
assert(history[3].Text ~= "ENGLISH_SENTINEL", "MM7 history record 3 remained English")
assert(hasHighByte(history[1].Text), "MM7 history record 1 does not contain Korean game bytes")

for i = 1, 128 do
    history[i].Text = "ENGLISH_SENTINEL"
    history[i].Title = "ENGLISH_SENTINEL"
end

KoreanHistory.ApplyForContinent(3)
assert(history[1].Text ~= "ENGLISH_SENTINEL", "MM6 introduction remained English")
assert(history[1].Title ~= "ENGLISH_SENTINEL", "MM6 introduction title remained English")
assert(hasHighByte(history[1].Text), "MM6 introduction does not contain Korean game bytes")
assert(history[2].Text == "", "MM6 leaked another continent's history record")

print("Korean history localization: OK")
