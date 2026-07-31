-- Shared Korean DBCS text utilities for MM8 / MMMerge.
--
-- Keep all runtime DBCS conversion decisions in one place. Static translation
-- files remain plain EUC-KR/CP949-compatible bytes and are converted exactly
-- once when copied into a game table. This module intentionally does not patch
-- Lua's global string functions or the executable's formatting routines.

KoreanText = KoreanText or {}
local KT = KoreanText

KT.Version = "1.0.11a"
KT.LastError = nil
KT.WarnedMissingFont = KT.WarnedMissingFont or false

local function reportOnce(message)
    KT.LastError = message
    if KT.WarnedMissingFont then
        return
    end
    KT.WarnedMissingFont = true
    if Log and Merge and Merge.Log then
        pcall(Log, Merge.Log.Error, "%s", "[KoreanText] " .. message)
    else
        pcall(print, "[KoreanText] " .. message)
    end
end

function KT.IsEncoded(text)
    return type(text) == "string"
        and (text:find("\14\32\14", 1, true) ~= nil
            or text:find("\7", 1, true) ~= nil)
end

-- Validate the exact control-byte grammar produced by FNT_DBCS/KoreanFont:
--   SO SP SO <high><low> BEL (SP SO <high><low> BEL)* SI
-- ASCII bytes may appear outside encoded spans.
function KT.Validate(text)
    if type(text) ~= "string" then
        return false, "value is not a string"
    end

    local index = 1
    local inside = false
    while index <= #text do
        local byte = text:byte(index)
        if not inside then
            if byte == 14 then
                if text:byte(index + 1) ~= 32 or text:byte(index + 2) ~= 14
                    or text:byte(index + 5) ~= 7 then
                    return false, "invalid DBCS span start at byte " .. tostring(index)
                end
                local high = text:byte(index + 3)
                local low = text:byte(index + 4)
                if not high or not low then
                    return false, "truncated DBCS character at byte " .. tostring(index)
                end
                inside = true
                index = index + 6
            elseif byte == 7 or byte == 15 then
                return false, "orphan DBCS control byte at " .. tostring(index)
            else
                index = index + 1
            end
        else
            if byte == 15 then
                inside = false
                index = index + 1
            elseif byte == 32 and text:byte(index + 1) == 14 then
                if text:byte(index + 4) ~= 7 then
                    return false, "invalid continued DBCS character at byte " .. tostring(index)
                end
                local high = text:byte(index + 2)
                local low = text:byte(index + 3)
                if not high or not low then
                    return false, "truncated continued DBCS character at byte " .. tostring(index)
                end
                index = index + 5
            else
                return false, "unexpected byte inside DBCS span at " .. tostring(index)
            end
        end
    end

    if inside then
        return false, "unterminated DBCS span"
    end
    return true
end

function KT.EncodeOnce(text)
    if type(text) ~= "string" or text == "" then
        return text
    end

    if KT.IsEncoded(text) then
        local valid, reason = KT.Validate(text)
        if not valid then
            KT.LastError = reason
        end
        -- Never feed a partially encoded string through encodeSpecial again.
        return text
    end

    if not KoreanFont or type(KoreanFont.encodeSpecial) ~= "function" then
        reportOnce("KoreanFont.encodeSpecial is unavailable; leaving text unchanged")
        return text
    end

    local ok, encoded = pcall(KoreanFont.encodeSpecial, text)
    if not ok or type(encoded) ~= "string" then
        KT.LastError = ok and "encoder returned a non-string value" or tostring(encoded)
        return text
    end

    local valid, reason = KT.Validate(encoded)
    if not valid then
        KT.LastError = reason
        return text
    end
    return encoded
end

-- Close a span that was cut by an external fixed-size buffer. This mirrors the
-- safety purpose of FNT_DBCS.truncate without performing an arbitrary byte cut.
function KT.Finalize(text)
    if type(text) ~= "string" or text == "" then
        return text
    end
    local valid = KT.Validate(text)
    if valid then
        return text
    end
    if KoreanFont and type(KoreanFont.truncate) == "function" then
        local ok, repaired = pcall(KoreanFont.truncate, text)
        if ok and type(repaired) == "string" then
            local repairedValid = KT.Validate(repaired)
            if repairedValid then
                return repaired
            end
        end
    end
    return text
end

function KT.SetPlayerName(number, plainName)
    if KoreanFont and type(KoreanFont.setPlayerName) == "function" then
        return KoreanFont.setPlayerName(number, plainName)
    end
    return false
end
