-- Targeted fixes for player-reported event text that bypasses the normal
-- localization tables. Keep Korean runtime strings as EUC-KR/CP949 byte
-- escapes so this source remains ASCII-only and is safe for MMExtension Lua.
--
-- Two reports are covered here:
--   1) MM6 Control Center item 2166 (Proclamation) was showing a potion recipe.
--      Rodril's RemoveItemsLimits keeps a parallel u2 item-id array immediately
--      after Game.MessageScrolls; use that authoritative mapping instead of a
--      hard-coded MessageScrolls row number.
--   2) The MM7 Emerald Island contest messenger is stored as a raw NPC
--      conversation literal and therefore is not owned by 7out01.str.

KoreanReportedEventHotfixes = KoreanReportedEventHotfixes or {}

local function encodeKorean(text)
    if KoreanText and KoreanText.EncodeOnce then
        return KoreanText.EncodeOnce(text)
    end
    return text
end

local PROCLAMATION_ITEM_ID = 2166
local PROCLAMATION_TEXT = "\195\224\199\207\199\213\180\207\180\217\33\32\192\204\183\206\189\225\32\191\169\183\175\186\208\32\184\240\181\206\184\166\32\189\180\198\219\32\177\184\185\246\183\206\32\188\177\198\247\199\213\180\207\180\217\33"

local EMERALD_MESSENGER_MARKER = "Great competition going to happen very soon!"
local EMERALD_MESSENGER_END_MARKER = "Putting paper in your hands, he runs away"
local EMERALD_MESSENGER_TEXT = "\40\188\210\179\226\192\204\32\180\231\189\197\191\161\176\212\32\180\222\183\193\191\194\180\217\46\41\10\10\192\250\177\226\191\228\44\32\179\170\184\174\181\233\33\32\176\240\32\197\171\32\186\184\185\176\195\163\177\226\32\180\235\200\184\176\161\32\191\173\183\193\191\228\33\10\10\40\188\210\179\226\192\186\32\180\231\189\197\32\188\213\191\161\32\193\190\192\204\184\166\32\193\227\191\169\32\193\214\176\237\32\180\222\190\198\179\173\180\217\46\41"

-- Rodril's Scripts/Structs/RemoveItemsLimits.lua allocates MessageScrolls as:
--   [count * 4 bytes of text pointers][4 bytes][count * 2 bytes of item ids]
-- and publishes the text-pointer base through structs.o.GameStructure.
-- Reading this parallel id array lets localization follow the actual SCROLL.TXT
-- row order of the installed Merge build instead of assuming an i18n row index.
local function findMessageScrollRow(itemId)
    if not Game or not Game.MessageScrolls or not mem or
            not structs or not structs.o or not structs.o.GameStructure then
        return nil
    end

    local base = structs.o.GameStructure["MessageScrolls"]
    local high = Game.MessageScrolls.high
    if type(base) ~= "number" or type(high) ~= "number" or high < 0 then
        return nil
    end

    local count = high + 1
    local itemIndex = base + count * 4 + 4
    for row = 0, high do
        if mem.u2[itemIndex + row * 2] == itemId then
            return row
        end
    end
    return nil
end

local function applyProclamationText()
    if not Game or not Game.MessageScrolls then
        return false
    end

    local row = findMessageScrollRow(PROCLAMATION_ITEM_ID)
    if row == nil then
        return false
    end

    Game.MessageScrolls[row] = encodeKorean(PROCLAMATION_TEXT)
    KoreanReportedEventHotfixes.ProclamationRow = row
    return true
end

local function translateEmeraldMessenger(text)
    if type(text) ~= "string" then
        return text
    end
    if text:find(EMERALD_MESSENGER_MARKER, 1, true) and
            text:find(EMERALD_MESSENGER_END_MARKER, 1, true) then
        return encodeKorean(EMERALD_MESSENGER_TEXT)
    end
    return text
end

local function applyEmeraldMessengerText()
    if not Game or not Game.NPCText then
        return 0
    end

    local changed = 0
    for i in Game.NPCText do
        local original = Game.NPCText[i]
        local localized = translateEmeraldMessenger(original)
        if localized ~= original then
            Game.NPCText[i] = localized
            changed = changed + 1
        end
    end
    return changed
end

local function applyAll()
    applyProclamationText()
    applyEmeraldMessengerText()
end

function events.GameInitialized2()
    applyAll()
end

function events.LoadMap()
    applyAll()
end

function events.AfterLoadMap()
    applyAll()
end

KoreanReportedEventHotfixes.FindMessageScrollRow = findMessageScrollRow
KoreanReportedEventHotfixes.ApplyProclamationText = applyProclamationText
KoreanReportedEventHotfixes.TranslateEmeraldMessenger = translateEmeraldMessenger
KoreanReportedEventHotfixes.ApplyEmeraldMessengerText = applyEmeraldMessengerText
