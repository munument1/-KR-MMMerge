-- Korean DBCS support for Might and Magic 8 / MMMerge.
--
-- Derived from FNT_DBCS.lua by Tom CHEN (tomchen.org), MIT/Expat License.
-- Korean adaptation with MM8 version guard and runtime memory-safety checks.

KoreanFont = KoreanFont or {}
local KF = KoreanFont

KF.Debug = false
KF.Encoding = "euc_kr"
KF.FontSizes = {14, 16, 29}
KF.SpecialFonts = {Autonote = {15, "b"}}
KF.ExpectedMM8Version = "1.1 + GrayFace Patch 2.5.7"
KF.PatchAddress = 0x449C3B
KF.ExpectedSignature = "\58\10\114\5\58\74\1\118\23"

local function log(message, ...)
    local ok, text = pcall(string.format, "[KoreanFont] " .. message, ...)
    text = ok and text or "[KoreanFont] diagnostic formatting failed"
    if Log and Merge and Merge.Log then
        pcall(Log, Merge.Log.Info, "%s", text)
    else
        pcall(print, text)
    end
end

local function debugLog(message, ...)
    if KF.Debug then
        log(message, ...)
    end
end

local function readEncoding()
    local file = io.open("Data/LocalizeConf.ini", "rb")
    if not file then
        return nil
    end
    local content = file:read("*all")
    file:close()
    return content:match("\n?encoding=([^\r\n]*)")
end

local globalEncoding = readEncoding()
local encodingRegex = {
    euc_kr = "[\161-\172\176-\200\202-\253][\160-\255]"
}

local FNT = {}
KF.FNT = FNT

function FNT.getHeight(fontAddr)
    return mem.i2[fontAddr + 5]
end

function FNT.getCharWidth(fontAddr, charCode)
    return mem.i4[fontAddr + 36 + 12 * charCode]
end

function FNT.getCharSpaceBefore(fontAddr, charCode)
    return mem.i4[fontAddr + 32 + 12 * charCode]
end

function FNT.getCharSpaceAfter(fontAddr, charCode)
    return mem.i4[fontAddr + 40 + 12 * charCode]
end

function FNT.getCharStartingAddr(fontAddr, charCode)
    return mem.i4[fontAddr + 3104 + 4 * charCode] + 4128 + fontAddr
end

function FNT.getCharShape(fontAddr, charCode)
    local width = FNT.getCharWidth(fontAddr, charCode)
    local height = FNT.getHeight(fontAddr)
    return mem.string(FNT.getCharStartingAddr(fontAddr, charCode), height * width, true)
end

function FNT.setCharWidth(fontAddr, charCode, value)
    mem.i4[fontAddr + 36 + 12 * charCode] = value
end

function FNT.setCharSpaceBefore(fontAddr, charCode, value)
    mem.i4[fontAddr + 32 + 12 * charCode] = value
end

function FNT.setCharSpaceAfter(fontAddr, charCode, value)
    mem.i4[fontAddr + 40 + 12 * charCode] = value
end

function FNT.setCharShape(fontAddr, charCode, shape)
    mem.copy(FNT.getCharStartingAddr(fontAddr, charCode), shape)
end

local dbcsFonts = {}
local cachedSpaceWidth = {}
local cachedCharShape = {}
local dbcsMode = false
local activeFontAddr
local highByte = 0
local lowByte = 0
local lastByte = 0
local hiddenByte
local cachedWidth
local cachedBefore
local cachedAfter
local lastReportedError

function KF.isHighByte(byte)
    return byte == 0xA1 or (byte >= 0xB0 and byte <= 0xC8)
end

function KF.isLowByte(byte)
    return byte and byte >= 0xA0 and byte <= 0xFF
end

function KF.encodeSpecial(str)
    if type(str) ~= "string" or str == "" or str:find("\7", 1, true) then
        return str
    end
    str = str:gsub("(" .. encodingRegex.euc_kr .. ")", "\14\32\14%1\7\15")
    return str:gsub("\15\14", "")
end

function KF.decodeSpecial(str)
    str = str:gsub("\32\14(..)\7", "%1")
    return str:gsub("\14([^\15]+)\15", "%1")
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

function KF.setPlayerName(number, eucKrName)
    Party[number - 1].Name = KF.truncate(KF.encodeSpecial(eucKrName))
end

local function replacementFontInfo(fontAddr)
    local originalHeight = FNT.getHeight(fontAddr)
    for name, setting in pairs(KF.SpecialFonts) do
        if Game[name .. "_fnt"] == fontAddr then
            return {height = setting[1], decoration = setting[2], originalHeight = originalHeight}
        end
    end
    if originalHeight < KF.FontSizes[1] then
        error("no Korean font is small enough for source height " .. tostring(originalHeight))
    end
    for index = 2, #KF.FontSizes do
        if originalHeight < KF.FontSizes[index] then
            return {height = KF.FontSizes[index - 1], decoration = "", originalHeight = originalHeight}
        end
    end
    return {
        height = KF.FontSizes[#KF.FontSizes],
        decoration = "",
        originalHeight = originalHeight
    }
end

local function fontLooksReadable(fontAddr)
    if type(fontAddr) ~= "number" or fontAddr <= 0 then
        return false
    end
    local ok, height, width = pcall(function()
        return FNT.getHeight(fontAddr), FNT.getCharWidth(fontAddr, 32)
    end)
    return ok and type(height) == "number" and height >= 1 and height <= 64
        and type(width) == "number" and width >= 0 and width <= 256
end

local function loadDbcsFont(heightAndDecoration, page, forceReload)
    dbcsFonts[heightAndDecoration] = dbcsFonts[heightAndDecoration] or {}
    if forceReload then
        dbcsFonts[heightAndDecoration][page] = nil
    end

    local cached = dbcsFonts[heightAndDecoration][page]
    if cached and fontLooksReadable(cached) then
        return cached
    end
    dbcsFonts[heightAndDecoration][page] = nil

    local name = "DBCS_" .. heightAndDecoration .. "_" .. string.format("%02X", page) .. ".fnt"
    if not Game.CanLoadFileFromLod(name) then
        name = "DBCS_" .. heightAndDecoration .. "_B0.fnt"
        if not Game.CanLoadFileFromLod(name) then
            name = "DBCS_" .. heightAndDecoration .. "_A1.fnt"
        end
    end

    local address = Game.LoadDataFileFromLod(name)
    if not fontLooksReadable(address) then
        return 0
    end
    dbcsFonts[heightAndDecoration][page] = address
    debugLog("loaded %s for page %02X", name, page)
    return address
end

local function readPageGlyph(heightAndDecoration, page, character)
    local function readOnce(forceReload)
        local pageFont = loadDbcsFont(heightAndDecoration, page, forceReload)
        if pageFont == 0 then
            error("could not load a Korean font page")
        end
        local width = FNT.getCharWidth(pageFont, character)
        local height = FNT.getHeight(pageFont)
        if type(width) ~= "number" or width < 0 or width > 128 then
            error("invalid Korean glyph width")
        end
        if type(height) ~= "number" or height < 1 or height > 64 then
            error("invalid Korean font height")
        end
        return {
            width = width,
            before = FNT.getCharSpaceBefore(pageFont, character),
            after = FNT.getCharSpaceAfter(pageFont, character),
            shape = FNT.getCharShape(pageFont, character)
        }
    end

    local ok, glyph = pcall(readOnce, false)
    if ok then
        return glyph
    end
    ok, glyph = pcall(readOnce, true)
    if ok then
        return glyph
    end
    error(glyph)
end

local function resetState()
    dbcsMode = false
    activeFontAddr = nil
    highByte = 0
    lowByte = 0
    lastByte = 0
    hiddenByte = nil
    cachedWidth = nil
    cachedBefore = nil
    cachedAfter = nil
end

local function restoreHiddenByte(fontAddr)
    if hiddenByte and cachedWidth ~= nil and cachedBefore ~= nil and cachedAfter ~= nil then
        pcall(FNT.setCharSpaceBefore, fontAddr, hiddenByte, cachedBefore)
        pcall(FNT.setCharSpaceAfter, fontAddr, hiddenByte, cachedAfter)
        pcall(FNT.setCharWidth, fontAddr, hiddenByte, cachedWidth)
    end
    hiddenByte = nil
end

local function stopDbcs(fontAddr)
    fontAddr = fontAddr or activeFontAddr
    if fontAddr then
        restoreHiddenByte(fontAddr)
        if cachedSpaceWidth[fontAddr] ~= nil and cachedSpaceWidth[fontAddr] ~= 0 then
            pcall(FNT.setCharWidth, fontAddr, 32, cachedSpaceWidth[fontAddr])
        end
        if cachedCharShape[fontAddr] then
            pcall(FNT.setCharShape, fontAddr, 7, cachedCharShape[fontAddr])
        end
    end
    resetState()
end

local function reportAndAbort(fontAddr, err)
    stopDbcs(fontAddr)
    local text = tostring(err)
    if text ~= lastReportedError then
        lastReportedError = text
        log("recovered from malformed text or an invalid font pointer: %s", text)
    end
end

local originalCharTest = mem.asmproc([[
    cmp cl, [edx]
    jb absolute 0x449C44
    cmp cl, [edx+1]
    jbe absolute 0x449C5B
    jmp absolute 0x449C44
]])

local function processByteUnsafe(registers)
    local byte = registers.cl
    local fontAddr = registers.edx

    if type(byte) ~= "number" or type(fontAddr) ~= "number" or fontAddr <= 0 then
        stopDbcs(activeFontAddr)
        return
    end

    -- Text drawing can switch fonts between callbacks. Never carry a half-read
    -- Korean sequence into a different source font.
    if dbcsMode and activeFontAddr and activeFontAddr ~= fontAddr then
        stopDbcs(activeFontAddr)
    end

    local function rememberState(value)
        if value == 301 and lastByte ~= 14 then
            return false
        elseif value == 300 and lastByte ~= 301 then
            return false
        end
        lastByte = value
        return true
    end

    local function startDbcs()
        activeFontAddr = fontAddr
        if cachedSpaceWidth[fontAddr] == nil then
            cachedSpaceWidth[fontAddr] = FNT.getCharWidth(fontAddr, 32)
        end
        FNT.setCharWidth(fontAddr, 32, 0)
        if cachedCharShape[fontAddr] == nil then
            cachedCharShape[fontAddr] = mem.string(
                FNT.getCharStartingAddr(fontAddr, 7),
                FNT.getHeight(fontAddr) ^ 2 * 2,
                true
            )
        end
        dbcsMode = true
    end

    local function hideCurrentByte()
        cachedBefore = FNT.getCharSpaceBefore(fontAddr, byte)
        cachedAfter = FNT.getCharSpaceAfter(fontAddr, byte)
        cachedWidth = FNT.getCharWidth(fontAddr, byte)
        FNT.setCharSpaceBefore(fontAddr, byte, 0)
        FNT.setCharSpaceAfter(fontAddr, byte, 0)
        FNT.setCharWidth(fontAddr, byte, 0)
        hiddenByte = byte
    end

    if byte == 14 then
        lastByte = 14
        if not dbcsMode then
            startDbcs()
        end
        return
    end

    if not dbcsMode then
        return
    end

    if byte == 15 then
        lastByte = 0
        stopDbcs(fontAddr)
    elseif byte == 32 or byte == 10 then
        lastByte = byte
    elseif byte == 7 then
        if highByte == 0 or not KF.isHighByte(highByte)
            or not KF.isLowByte(lowByte) or hiddenByte ~= lowByte then
            stopDbcs(fontAddr)
            return
        end

        lastByte = 7
        local info = replacementFontInfo(fontAddr)
        local top = math.floor((info.originalHeight - info.height) / 2)
        local bottom = math.ceil((info.originalHeight - info.height) / 2)
        local glyph = readPageGlyph(tostring(info.height) .. info.decoration, highByte, lowByte)

        FNT.setCharWidth(fontAddr, 7, glyph.width)
        FNT.setCharSpaceBefore(fontAddr, 7, glyph.before)
        FNT.setCharSpaceAfter(fontAddr, 7, glyph.after)
        FNT.setCharShape(
            fontAddr,
            7,
            string.rep("\0", top * glyph.width)
                .. glyph.shape
                .. string.rep("\0", bottom * glyph.width)
        )
        restoreHiddenByte(fontAddr)
        highByte = 0
        lowByte = 0
    elseif highByte == 0 then
        if not KF.isHighByte(byte) or not rememberState(301) then
            stopDbcs(fontAddr)
            return
        end
        hideCurrentByte()
        highByte = byte
    else
        if not KF.isLowByte(byte) or not rememberState(300) then
            stopDbcs(fontAddr)
            return
        end
        restoreHiddenByte(fontAddr)
        hideCurrentByte()
        lowByte = byte
    end
end

local function processByte(registers)
    local ok, err = pcall(processByteUnsafe, registers)
    if not ok then
        reportAndAbort(registers and registers.edx or activeFontAddr, err)
    end
end

local function installHook()
    if offsets.MMVersion ~= 8 then
        log("disabled: only MM8/MMMerge is supported by this build")
        return false
    end
    if globalEncoding ~= KF.Encoding then
        log("disabled: Data/LocalizeConf.ini must contain encoding=%s", KF.Encoding)
        return false
    end
    local actual = mem.string(KF.PatchAddress, #KF.ExpectedSignature, true)
    if actual ~= KF.ExpectedSignature then
        log("disabled: executable signature mismatch at 0x%X", KF.PatchAddress)
        return false
    end
    mem.hook(originalCharTest, processByte)
    mem.asmpatch(KF.PatchAddress, "jmp absolute " .. originalCharTest, 9)
    KF.Enabled = true
    log("enabled for %s", KF.ExpectedMM8Version)
    return true
end

KF.Enabled = false
installHook()
