-- Korean DBCS support for Might and Magic 8 / MMMerge.
--
-- Derived from FNT_DBCS.lua by Tom CHEN (tomchen.org), MIT/Expat License.
-- Korean adaptation, version guard, diagnostics, and safer missing-font checks.

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
    local text = string.format("[KoreanFont] " .. message, ...)
    if Log and Merge and Merge.Log then
        Log(Merge.Log.Info, "%s", text)
    else
        print(text)
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
    return mem.string(
        FNT.getCharStartingAddr(fontAddr, charCode),
        FNT.getHeight(fontAddr) * FNT.getCharWidth(fontAddr, charCode),
        true
    )
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
local highByte = 0
local lowByte = 0
local lastByte = 0
local cachedWidth
local cachedBefore
local cachedAfter

function KF.isHighByte(byte)
    return (byte == 0xA1)
        or (byte >= 0xB0 and byte <= 0xC8)
end

function KF.encodeSpecial(str)
    if str:find("\7", 1, true) then
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
        error("KoreanFont: no DBCS font small enough for height " .. originalHeight)
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

local function loadDbcsFont(heightAndDecoration, page)
    dbcsFonts[heightAndDecoration] = dbcsFonts[heightAndDecoration] or {}
    if dbcsFonts[heightAndDecoration][page] == nil then
        local name = "DBCS_" .. heightAndDecoration .. "_" .. string.format("%02X", page) .. ".fnt"
        if not Game.CanLoadFileFromLod(name) then
            name = "DBCS_" .. heightAndDecoration .. "_B0.fnt"
            if not Game.CanLoadFileFromLod(name) then
                name = "DBCS_" .. heightAndDecoration .. "_A1.fnt"
            end
        end
        local address = Game.LoadDataFileFromLod(name)
        if not address or address == 0 then
            return 0
        end
        dbcsFonts[heightAndDecoration][page] = address
        debugLog("loaded %s for page %02X", name, page)
    end
    return dbcsFonts[heightAndDecoration][page]
end

local originalCharTest = mem.asmproc([[
    cmp cl, [edx]
    jb absolute 0x449C44
    cmp cl, [edx+1]
    jbe absolute 0x449C5B
    jmp absolute 0x449C44
]])

local function processByte(registers)
    local byte = registers.cl
    local fontAddr = registers.edx

    local function rememberState(value)
        local valid = true
        if value == 301 and lastByte ~= 14 then
            valid = false
        elseif value == 300 and lastByte ~= 301 then
            valid = false
        end
        lastByte = value
        return valid
    end

    local function startDbcs()
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

    local function stopDbcs()
        if cachedSpaceWidth[fontAddr] and cachedSpaceWidth[fontAddr] ~= 0 then
            FNT.setCharWidth(fontAddr, 32, cachedSpaceWidth[fontAddr])
        end
        if cachedCharShape[fontAddr] then
            FNT.setCharShape(fontAddr, 7, cachedCharShape[fontAddr])
        end
        highByte = 0
        dbcsMode = false
    end

    local function hideCurrentByte()
        cachedBefore = FNT.getCharSpaceBefore(fontAddr, byte)
        cachedAfter = FNT.getCharSpaceAfter(fontAddr, byte)
        cachedWidth = FNT.getCharWidth(fontAddr, byte)
        FNT.setCharSpaceBefore(fontAddr, byte, 0)
        FNT.setCharSpaceAfter(fontAddr, byte, 0)
        FNT.setCharWidth(fontAddr, byte, 0)
    end

    if byte == 14 and rememberState(byte) then
        if not dbcsMode then
            startDbcs()
        end
    elseif dbcsMode then
        if byte == 15 and rememberState(0) then
            stopDbcs()
        elseif byte == 32 and rememberState(byte) then
            -- structural zero-width space
        elseif byte == 10 and rememberState(byte) then
            -- newline
        elseif byte == 7 and rememberState(byte) then
            local info = replacementFontInfo(fontAddr)
            local top = math.floor((info.originalHeight - info.height) / 2)
            local bottom = math.ceil((info.originalHeight - info.height) / 2)
            local pageFont = loadDbcsFont(tostring(info.height) .. info.decoration, highByte)
            local width = FNT.getCharWidth(pageFont, lowByte)
            FNT.setCharWidth(fontAddr, 7, width)
            FNT.setCharSpaceBefore(fontAddr, 7, FNT.getCharSpaceBefore(pageFont, lowByte))
            FNT.setCharSpaceAfter(fontAddr, 7, FNT.getCharSpaceAfter(pageFont, lowByte))
            FNT.setCharShape(
                fontAddr,
                7,
                string.rep("\0", top * width)
                    .. FNT.getCharShape(pageFont, lowByte)
                    .. string.rep("\0", bottom * width)
            )
            FNT.setCharSpaceBefore(fontAddr, lowByte, cachedBefore)
            FNT.setCharSpaceAfter(fontAddr, lowByte, cachedAfter)
            FNT.setCharWidth(fontAddr, lowByte, cachedWidth)
            highByte = 0
        elseif highByte == 0 then
            if not KF.isHighByte(byte) and rememberState(0) then
                stopDbcs()
            elseif rememberState(301) then
                hideCurrentByte()
                highByte = byte
            end
        elseif rememberState(300) then
            FNT.setCharSpaceBefore(fontAddr, highByte, cachedBefore)
            FNT.setCharSpaceAfter(fontAddr, highByte, cachedAfter)
            FNT.setCharWidth(fontAddr, highByte, cachedWidth)
            hideCurrentByte()
            lowByte = byte
        end
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

