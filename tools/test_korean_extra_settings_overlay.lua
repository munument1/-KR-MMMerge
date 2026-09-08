-- Minimal Lua 5.1 regression harness for ZZZ_KoreanExtraSettingsOverlay.lua.

events = {}
local createdIcons = {}
local createdTexts = {}

KoreanText = {
    EncodeOnce = function(text)
        return text
    end
}

const = {Screens = {}}
Game = {
    Lucida_fnt = {},
    Smallnum_fnt = {}
}

CustomUI = {
    -- Main Extra Settings and keybind pages exist in this simulated Merge build.
    -- CharacterOptions (94) is deliberately absent to reproduce the v1.0.17
    -- AddElement crash reported by players.
    ActiveElements = {
        [98] = {},
        [96] = {},
    },
    CreateIcon = function(settings)
        table.insert(createdIcons, settings)
        return settings
    end,
    CreateText = function(settings)
        table.insert(createdTexts, settings)
        return settings
    end
}

dofile("Scripts/General/ZZZ_KoreanExtraSettingsOverlay.lua")

local mainBg = CustomUI.CreateIcon{Icon = "ExSetScr", Screen = 98}
assert(mainBg.Icon == "ExSetScr2", "main Extra Settings background was not replaced")

-- ExSetScrK contains the key grid and is localized as an image in
-- zz LocKO.icons.lod. Replacing it with ExSetScr2 would erase the grid.
local keysBg = CustomUI.CreateIcon{Icon = "ExSetScrK", Screen = 96}
assert(keysBg.Icon == "ExSetScrK", "Extra Keybinds grid artwork was incorrectly replaced")

local unrelated = CustomUI.CreateIcon{Icon = "UIExample", Screen = 28}
assert(unrelated.Icon == "UIExample", "unrelated icon was modified")

local characterName = CustomUI.CreateText{Text = "CharacterName:", Screen = 94}
assert(characterName.Text == "\196\179\184\175\197\205 \192\204\184\167:",
    "CharacterName label was not localized")

local melee = CustomUI.CreateText{Text = "stop melee attack", Screen = 94}
assert(melee.Text == "\177\217\193\162 \176\248\176\221 \193\223\193\246",
    "melee option was not localized")

local ranged = CustomUI.CreateText{Text = "stop ranged attack", Screen = 94}
assert(ranged.Text == "\191\248\176\197\184\174 \176\248\176\221 \193\223\193\246",
    "ranged option was not localized")

local quick = CustomUI.CreateText{Text = "Q. SPELL 3", Screen = 96}
assert(quick.Text == "\196\252\189\186\198\231 3",
    "quick-spell slot label was not localized")

local noKey = CustomUI.CreateText{Text = "-NO KEY-", Screen = 96}
assert(noKey.Text == "-\197\176 \190\248\192\189-",
    "no-key label was not localized")

const.Screens.ExtraSettings = 98
const.Screens.ExtraKeybinds = 96
const.Screens.CharacterOptions = 94

-- Must not attempt CustomUI.CreateText on missing screen 94.
events.GameInitialized2()

local expectedKeys = {
    KoreanExtraSettingsTitle = true,
    KoreanMonsterBolster = true,
    KoreanBolsterAmount = true,
    KoreanWeatherEffects = true,
    KoreanInfinityView = true,
    KoreanImprovedPathfinding = true,
}

local sawCharacterTitle = false
for _, settings in ipairs(createdTexts) do
    if settings.Key then
        expectedKeys[settings.Key] = nil
        if settings.Key == "KoreanCharacterOptionsTitle" then
            sawCharacterTitle = true
        end
    end
end

for key in pairs(expectedKeys) do
    error("missing Korean settings overlay label: " .. key)
end
assert(not sawCharacterTitle, "created CharacterOptions title on an unregistered screen")
assert(KoreanExtraSettingsOverlay.ScreenIsRegistered(94) == false,
    "unregistered CharacterOptions screen was treated as valid")

print("Korean Extra Settings overlay: OK")
