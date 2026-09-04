-- Korean DBCS support for Might and Magic 8 / MMMerge.
--
-- Derived from FNT_DBCS.lua by Tom CHEN (tomchen.org), MIT/Expat License.
-- Korean adaptation with MM8 version guard and runtime memory-safety checks.
--
-- Safety note:
-- The legacy renderer temporarily reuses glyph 7 as a Korean glyph.  Older
-- builds cached host-font memory for the lifetime of the process and restored
-- a large fixed block later.  If Merge/GrayFace reloaded a font at the same
-- address, that stale restore could overwrite unrelated/reloaded resources.
-- This build keeps host-font backups per DBCS span/glyph, validates the font
-- identity before every restore, and restores only the exact bytes overwritten.

KoreanFont = KoreanFont or {}
local KF = KoreanFont

KF.Debug = false
KF.Encoding = "euc_kr"
KF.FontSizes = {14, 16, 29}
KF.SpecialFonts = {Autonote = {15, "b"}}
KF.ExpectedMM8Version = "1.1 + GrayFace Patch 2.5.7"
KF.PatchAddress = 0x449C3B
KF.ExpectedSignature = "\58\10\114\5\58\74\1\118\23"
KF.SafetyVersion = "1.0.14-ui-render-guard"

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

local warned = {}
local function warnOnce(key, message, ...)
    if warned[key] then
        return
    end
    warned[key] = true
    log(message, ...)
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
    -- Keep this in sync with isHighByte/isLowByte below.
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
    if #shape > 0 then
        mem.copy(FNT.getCharStartingAddr(fontAddr, charCode), shape)
    end
end

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

-- Capture fields the renderer never mutates.  They act as an identity token for
-- a font allocation so an address reused after a resource reload is not treated
-- as the old font.
local function captureFontIdentity(fontAddr)
    if not fontLooksReadable(fontAddr) then
        return nil
    end
    local ok, identity = pcall(function()
        local start7 = FNT.getCharStartingAddr(fontAddr, 7)
        local start32 = FNT.getCharStartingAddr(fontAddr, 32)
        local start65 = FNT.getCharStartingAddr(fontAddr, 65)
        if start7 < fontAddr or start32 < fontAddr or start65 < fontAddr then
            error("glyph pointer precedes font")
        end
        if start7 - fontAddr > 0x1000000
            or start32 - fontAddr > 0x1000000
            or start65 - fontAddr > 0x1000000 then
            error("glyph pointer outside sane font range")
        end
        return {
            minChar = mem.u1[fontAddr],
            maxChar = mem.u1[fontAddr + 1],
            height = FNT.getHeight(fontAddr),
            palette = mem.i4[fontAddr + 12],
            start7 = start7,
            start32 = start32,
            start65 = start65
        }
    end)
    return ok and identity or nil
end

local function sameFontIdentity(left, right)
    return left and right
        and left.minChar == right.minChar
        and left.maxChar == right.maxChar
        and left.height == right.height
        and left.palette == right.palette
        and left.start7 == right.start7
        and left.start32 == right.start32
        and left.start65 == right.start65
end

-- DBCS page fonts are long-lived in normal play, but GrayFace/Merge may reload
-- LOD-backed resources.  Cache an identity alongside the address and reload if
-- the allocation was evicted or reused.
local dbcsFonts = {}

local function pageRecordAlive(record)
    if not record or not record.address then
        return false
    end
    local current = captureFontIdentity(record.address)
    return sameFontIdentity(record.identity, current)
end

local function loadDbcsFont(heightAndDecoration, page, forceReload)
    dbcsFonts[heightAndDecoration] = dbcsFonts[heightAndDecoration] or {}
    local pages = dbcsFonts[heightAndDecoration]
    if forceReload then
        pages[page] = nil
    end

    local cached = pages[page]
    if cached and pageRecordAlive(cached) then
        return cached.address
    elseif cached then
        debugLog("discarding stale DBCS page %s/%02X", heightAndDecoration, page)
    end
    pages[page] = nil

    local name = "DBCS_" .. heightAndDecoration .. "_" .. string.format("%02X", page) .. ".fnt"
    if not Game.CanLoadFileFromLod(name) then
        name = "DBCS_" .. heightAndDecoration .. "_B0.fnt"
        if not Game.CanLoadFileFromLod(name) then
            name = "DBCS_" .. heightAndDecoration .. "_A1.fnt"
        end
    end

    local ok, address = pcall(Game.LoadDataFileFromLod, name)
    address = ok and tonumber(address) or 0
    local identity = address ~= 0 and captureFontIdentity(address) or nil
    if not identity then
        return 0
    end

    pages[page] = {address = address, identity = identity}
    debugLog("loaded %s for page %02X @ 0x%X", name, page, address)
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
        local shape = width > 0 and FNT.getCharShape(pageFont, character) or ""
        return {
            width = width,
            before = FNT.getCharSpaceBefore(pageFont, character),
            after = FNT.getCharSpaceAfter(pageFont, character),
            shape = shape
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

-- Per-span state only.  Nothing here survives a completed encoded span.
local dbcsMode = false
local activeFontAddr
local activeFontIdentity
local activeSpaceWidth
local activeScratch
local highByte = 0
local lowByte = 0
local lastByte = 0
local hiddenByte
local cachedWidth
local cachedBefore
local cachedAfter
local lastReportedError

local function resetState()
    dbcsMode = false
    activeFontAddr = nil
    activeFontIdentity = nil
    activeSpaceWidth = nil
    activeScratch = nil
    highByte = 0
    lowByte = 0
    lastByte = 0
    hiddenByte = nil
    cachedWidth = nil
    cachedBefore = nil
    cachedAfter = nil
end

local function activeFontStillValid(fontAddr)
    if not fontAddr or fontAddr ~= activeFontAddr then
        return false
    end
    return sameFontIdentity(activeFontIdentity, captureFontIdentity(fontAddr))
end

-- Glyph 7 is used only until the engine consumes the current BEL byte.  Restore
-- it at the next callback instead of leaving a large modified area alive for an
-- entire Korean span.
local function restoreScratch(fontAddr)
    if not activeScratch then
        return true
    end
    if not activeFontStillValid(fontAddr) then
        warnOnce(
            "stale-scratch",
            "prevented stale glyph restore after a font/resource reload (0x%X)",
            tonumber(fontAddr) or 0
        )
        activeScratch = nil
        return false
    end

    local scratch = activeScratch
    local ok = pcall(function()
        if #scratch.shape > 0 then
            mem.copy(scratch.address, scratch.shape)
        end
        FNT.setCharSpaceBefore(fontAddr, 7, scratch.before)
        FNT.setCharSpaceAfter(fontAddr, 7, scratch.after)
        FNT.setCharWidth(fontAddr, 7, scratch.width)
    end)
    activeScratch = nil
    return ok
end

local function restoreHiddenByte(fontAddr)
    if not hiddenByte then
        return true
    end
    if not activeFontStillValid(fontAddr) then
        hiddenByte = nil
        return false
    end
    local ok = pcall(function()
        if cachedWidth ~= nil and cachedBefore ~= nil and cachedAfter ~= nil then
            FNT.setCharSpaceBefore(fontAddr, hiddenByte, cachedBefore)
            FNT.setCharSpaceAfter(fontAddr, hiddenByte, cachedAfter)
            FNT.setCharWidth(fontAddr, hiddenByte, cachedWidth)
        end
    end)
    hiddenByte = nil
    return ok
end

local function stopDbcs(fontAddr)
    fontAddr = fontAddr or activeFontAddr
    if fontAddr and activeFontAddr then
        if activeFontStillValid(fontAddr) then
            restoreScratch(fontAddr)
            restoreHiddenByte(fontAddr)
            if activeSpaceWidth ~= nil then
                pcall(FNT.setCharWidth, fontAddr, 32, activeSpaceWidth)
            end
        else
            -- Never write a cached value through an address whose allocation
            -- changed.  Dropping the state is safer than "repairing" new data.
            warnOnce(
                "stale-font",
                "font allocation changed during DBCS rendering; skipped all restores at 0x%X",
                tonumber(fontAddr) or 0
            )
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

    -- The previous BEL has already been consumed by the engine by the time this
    -- callback begins.  Restore its exact scratch region immediately.
    if activeScratch then
        restoreScratch(activeFontAddr)
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
        local identity = captureFontIdentity(fontAddr)
        if not identity then
            error("source font identity is unreadable")
        end
        activeFontAddr = fontAddr
        activeFontIdentity = identity
        activeSpaceWidth = FNT.getCharWidth(fontAddr, 32)
        FNT.setCharWidth(fontAddr, 32, 0)
        dbcsMode = true
    end

    local function hideCurrentByte()
        if not activeFontStillValid(fontAddr) then
            error("source font changed while hiding a DBCS byte")
        end
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

    if not activeFontStillValid(fontAddr) then
        stopDbcs(fontAddr)
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
        local replacementShape = string.rep("\0", top * glyph.width)
            .. glyph.shape
            .. string.rep("\0", bottom * glyph.width)

        -- Back up exactly what this one replacement will overwrite.  This is
        -- intentionally per glyph; no stale process-lifetime snapshot exists.
        local scratchAddress = FNT.getCharStartingAddr(fontAddr, 7)
        activeScratch = {
            address = scratchAddress,
            shape = #replacementShape > 0
                and mem.string(scratchAddress, #replacementShape, true)
                or "",
            width = FNT.getCharWidth(fontAddr, 7),
            before = FNT.getCharSpaceBefore(fontAddr, 7),
            after = FNT.getCharSpaceAfter(fontAddr, 7)
        }

        FNT.setCharWidth(fontAddr, 7, glyph.width)
        FNT.setCharSpaceBefore(fontAddr, 7, glyph.before)
        FNT.setCharSpaceAfter(fontAddr, 7, glyph.after)
        FNT.setCharShape(fontAddr, 7, replacementShape)

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
    log("enabled for %s (%s)", KF.ExpectedMM8Version, KF.SafetyVersion)
    return true
end

KF.Enabled = false
installHook()
