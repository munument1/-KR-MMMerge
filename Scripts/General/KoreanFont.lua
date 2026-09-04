-- Korean DBCS compatibility API for MMMerge.
-- v1.0.15 moves rendering to FNT_DBCS.lua's native direct-blit path.
-- This file installs no executable hooks and never writes host glyph memory.

KoreanFont = KoreanFont or {}
local KF = KoreanFont

KF.Debug = false
KF.Encoding = "euc_kr"
KF.NativeRenderer = DBCS and DBCS.NativeInstalled or false
KF.SafetyVersion = "1.0.15-native-dbcs"

local encodingRegex = {
    euc_kr = "[\161-\172\176-\200\202-\253][\160-\254]"
}

function KF.isHighByte(b)
    return b and ((b >= 0xA1 and b <= 0xAC)
        or (b >= 0xB0 and b <= 0xC8)
        or (b >= 0xCA and b <= 0xFD))
end

function KF.isLowByte(b)
    return b and b >= 0xA0 and b <= 0xFE
end

local function markerEncode(str)
    if type(str) ~= "string" or str == "" or str:find("\7", 1, true) then
        return str
    end
    str = str:gsub("(" .. encodingRegex.euc_kr .. ")", "\14\32\14%1\7\15")
    return str:gsub("\15\14", "")
end

function KF.encodeSpecial(str)
    if type(str) ~= "string" or str == "" then
        return str
    end
    if KF.NativeRenderer then
        return str
    end
    return markerEncode(str)
end

function KF.decodeSpecial(str)
    if type(str) ~= "string" or str == "" then
        return str
    end
    if DBCS and type(DBCS.decodeSpecial) == "function" then
        return DBCS.decodeSpecial(str)
    end
    str = str:gsub("\32\14(..)\7", "%1")
    str = str:gsub("\14([^\15]*)\15", "%1")
    return str:gsub("[\14\15]", "")
end

local function lastIndexOf(haystack, needle)
    local previous
    local found
    local position = 0
    repeat
        previous = found
        found, position = haystack:find(needle, position + 1, true)
    until found == nil
    return previous
end

function KF.truncate(str)
    if type(str) ~= "string" or not str:find("\14", 1, true) then
        return str
    end
    local position = lastIndexOf(str, "\15") or 0
    position = str:find("\14", position)
    if not position then
        return str
    end
    while str:sub(position + 5, position + 5) == "\7"
        and str:sub(position + 1, position + 1) == "\32"
        and str:sub(position + 2, position + 2) == "\14"
        and position + 5 < #str do
        position = position + 5
    end
    return str:sub(1, position) .. "\15"
end

local function fitPlainDbcs(str, capacity)
    local maxPayload = math.max(0, (tonumber(capacity) or 32) - 1)
    local out = ""
    local i = 1
    while i <= #str do
        local b = str:byte(i)
        local width = 1
        if KF.isHighByte(b) and KF.isLowByte(str:byte(i + 1)) then
            width = 2
        end
        if #out + width > maxPayload then
            break
        end
        out = out .. str:sub(i, i + width - 1)
        i = i + width
    end
    return out
end

function KF.setPlayerName(number, name)
    if type(name) ~= "string" then
        return false
    end
    local value
    if KoreanText and type(KoreanText.FitFixedString) == "function" then
        value = KoreanText.FitFixedString(name, 32)
    elseif KF.NativeRenderer then
        value = fitPlainDbcs(KF.decodeSpecial(name), 32)
    else
        value = KF.truncate(markerEncode(name))
    end
    Party[number - 1].Name = value
    return true
end
