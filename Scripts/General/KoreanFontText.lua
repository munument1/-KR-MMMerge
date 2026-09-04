-- Shared Korean DBCS text utilities for MM8 / MMMerge.
--
-- v1.0.15 renders plain EUC-KR directly through FNT_DBCS.lua.  This module
-- keeps the existing localization API stable and still validates/decodes the
-- legacy marker format found in older saves and preprocessed resources.  It
-- intentionally does not patch Lua globals or executable formatting routines.

KoreanText = KoreanText or {}
local KT = KoreanText

KT.Version = "1.0.15-native"
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

-- Validate the retired marker grammar kept for old save/resource compatibility:
--   SO SP SO <high><low> BEL (SP SO <high><low> BEL)* SI
-- Plain EUC-KR contains none of these control bytes and therefore validates.
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
        -- Never reinterpret an old or partially encoded marker string.
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

-- Close a legacy marker span cut by an external fixed-size buffer.  Plain
-- native DBCS strings pass validation unchanged.
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

-- Fit text into an MM8 fixed-size C string without cutting an EUC-KR pair.
-- `capacity` includes the trailing NUL byte (Player.Name is string(32)).
function KT.FitFixedString(text, capacity)
    if type(text) ~= "string" or text == "" then
        return text
    end
    capacity = tonumber(capacity) or 32
    local maxPayload = math.max(0, capacity - 1)
    local plain = text
    if KT.IsEncoded(plain) and KoreanFont and type(KoreanFont.decodeSpecial) == "function" then
        local valid, reason = KT.Validate(plain)
        if not valid then
            KT.LastError = reason
            return text
        end
        local ok, decoded = pcall(KoreanFont.decodeSpecial, plain)
        if not ok or type(decoded) ~= "string" then
            KT.LastError = "Could not decode the fixed-size string safely."
            return text
        end
        plain = decoded
    end

    local accepted = ""
    local index = 1
    while index <= #plain do
        local byte = plain:byte(index)
        local width = 1
        local isHighByte = byte and ((byte >= 0xA1 and byte <= 0xAC)
            or (byte >= 0xB0 and byte <= 0xC8)
            or (byte >= 0xCA and byte <= 0xFD))
        local lowByte = plain:byte(index + 1)
        if isHighByte and lowByte and lowByte >= 0xA0 and lowByte <= 0xFE then
            width = 2
        end
        local candidatePlain = accepted .. plain:sub(index, index + width - 1)
        local candidate = KT.EncodeOnce(candidatePlain)
        if type(candidate) ~= "string" or #candidate > maxPayload then
            break
        end
        accepted = candidatePlain
        index = index + width
    end
    return KT.EncodeOnce(accepted)
end

function KT.SetPlayerName(number, plainName)
    if KoreanFont and type(KoreanFont.setPlayerName) == "function" then
        Party[number - 1].Name = KT.FitFixedString(plainName, 32)
        return true
    end
    return false
end
