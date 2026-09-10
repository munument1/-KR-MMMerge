-- Repair the v1.0.29 Trans.txt row-order off-by-one at runtime.
-- Game.TransTxt is 1-based in MMExtension, and KO_TransTxt.txt IDs follow it.

KoreanTransTxtIndexFix = KoreanTransTxtIndexFix or {}
local KTI = KoreanTransTxtIndexFix

KTI.SourcePath = "Data/Text localization/KO_TransTxt.txt"
local records = nil

local function parseRecords(raw)
    local out = {}
    if type(raw) ~= "string" then
        return out
    end
    raw = raw:gsub("\r\n", "\n"):gsub("\r", "\n")
    for line in (raw .. "\n"):gmatch("([^\n]*)\n") do
        local _, idText, _, value = line:match("^([^\t]*)\t([^\t]*)\t([^\t]*)\t(.*)$")
        local id = tonumber(idText)
        if id and id >= 1 and value and value ~= "" then
            out[id] = value
        end
    end
    return out
end

local function loadRecords()
    if records then
        return records
    end
    local f = io.open(KTI.SourcePath, "rb")
    if not f then
        records = {}
        return records
    end
    local raw = f:read("*all")
    f:close()
    records = parseRecords(raw)
    KTI.Records = records
    return records
end

local function encode(text)
    if KoreanText and type(KoreanText.EncodeOnce) == "function" then
        return KoreanText.EncodeOnce(text)
    end
    if KoreanFont and type(KoreanFont.encodeSpecial) == "function" then
        return KoreanFont.encodeSpecial(text)
    end
    return text
end

function KTI.Apply()
    if not Game or not Game.TransTxt then
        return false, 0
    end
    local applied = 0
    for id, value in pairs(loadRecords()) do
        local ok = pcall(function()
            Game.TransTxt[id] = encode(value)
        end)
        if ok then
            applied = applied + 1
        end
    end
    return applied > 0, applied
end

KTI.ParseRecords = parseRecords
KTI.LoadRecords = loadRecords

function events.GameInitialized1()
    KTI.Apply()
end

function events.GameInitialized2()
    KTI.Apply()
end

if Game and Game.TransTxt then
    pcall(KTI.Apply)
end
