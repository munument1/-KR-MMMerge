-- Regression harness for ZZZZ_KoreanRuntimeHotfix.lua.

events = {}

CustomUI = {
    ActiveElements = {
        [97] = {
            Texts = {
                [0] = {
                    KoreanContinentGameLabel1 = {Active = true},
                    KoreanContinentGameLabel2 = {Active = true},
                    KoreanContinentGameLabel3 = {Active = true},
                }
            },
            -- Match InterfaceManager's real AddElement behavior: each layer
            -- independently receives numeric keys starting at 1.
            Buttons = {
                [0] = {
                    [1] = {IUpSrc = "SlAntagDw", Layer = 0, Key = 1},
                    [2] = {IUpSrc = "SlEnrothDw", Layer = 0, Key = 2},
                },
                [1] = {
                    [1] = {IUpSrc = "SlJadamDw", Layer = 1, Key = 1},
                }
            }
        }
    }
}

const = {Screens = {ChooseContinent = 97}}
Map = {MapStatsIndex = 1}

local currentContinent = 1
TownPortalControls = {
    MapOfContinent = function(index)
        return currentContinent
    end
}

KoreanReportedLocalization = {
    InstallContinentGameLabels = function()
        -- The real installer is idempotent. Labels are already registered in
        -- this harness, exactly as they are before the late hotfix runs.
    end
}

local applied = {}
KoreanHistory = {
    ApplyForContinent = function(continent)
        applied[#applied + 1] = continent
    end
}

dofile("Scripts/General/ZZZZ_KoreanRuntimeHotfix.lua")

events.GameInitialized2()

-- v1.0.17a disabled these three labels and relied on an FGInterfaceUpd redraw;
-- in the real chooser that redraw was not visible, so even M&M8 disappeared.
for i = 1, 3 do
    assert(CustomUI.ActiveElements[97].Texts[0]["KoreanContinentGameLabel" .. i].Active == true,
        "continent label was disabled: " .. i)
end

local buttons = CustomUI.ActiveElements[97].Buttons
assert(buttons[0][1] == nil, "Antagarich button remained on layer 0")
assert(buttons[0][2] == nil, "Enroth button remained on layer 0")

local antag = buttons[1].KoreanPromoted_SlAntagDw
local enroth = buttons[1].KoreanPromoted_SlEnrothDw
assert(antag and antag.IUpSrc == "SlAntagDw",
    "Antagarich button was not promoted to a collision-free layer-1 key")
assert(enroth and enroth.IUpSrc == "SlEnrothDw",
    "Enroth button was not promoted to a collision-free layer-1 key")
assert(antag.Layer == 1 and enroth.Layer == 1,
    "promoted continent button Layer field is wrong")
assert(antag.Key == "KoreanPromoted_SlAntagDw" and enroth.Key == "KoreanPromoted_SlEnrothDw",
    "promoted continent button Key field is wrong")

-- Critical MM8 regression: Jadame already occupies layer-1 numeric key 1.
-- Promoting MM7/MM6 must never overwrite or mutate it.
assert(buttons[1][1] and buttons[1][1].IUpSrc == "SlJadamDw" and buttons[1][1].Layer == 1,
    "Jadame/MM8 button was overwritten during layer promotion")
assert(buttons[1][1].Key == 1,
    "Jadame/MM8 button key was modified unexpectedly")

-- Reapplying must be harmless.
assert(KoreanRuntimeHotfix.PromoteLowerContinentButtons() == 0,
    "continent button promotion was not idempotent")
assert(KoreanRuntimeHotfix.EnsureContinentLabelsActive() == 3,
    "all three continent labels were not retained")

-- The late ZZZZ guard must reapply whichever continent is actually loaded,
-- not only MM7. This catches the MM6/MM8 English-history regression.
for continent = 1, 3 do
    currentContinent = continent
    assert(KoreanRuntimeHotfix.ReapplyLocalizedHistory() == continent,
        "late history reapply returned wrong continent")
    assert(applied[#applied] == continent,
        "late history reapply did not call KoreanHistory for continent " .. continent)
end

print("Korean runtime hotfix: OK")
