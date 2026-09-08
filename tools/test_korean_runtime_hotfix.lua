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
            Buttons = {
                [0] = {
                    antag = {IUpSrc = "SlAntagDw", Layer = 0, Key = "antag"},
                    enroth = {IUpSrc = "SlEnrothDw", Layer = 0, Key = "enroth"},
                },
                [1] = {
                    jadam = {IUpSrc = "SlJadamDw", Layer = 1, Key = "jadam"},
                }
            }
        }
    }
}

const = {Screens = {ChooseContinent = 97}}
Game = {
    Smallnum_fnt = {},
    HistoryTxt = {
        [1] = {Text = "OLD1", Title = "OLD1"},
        [2] = {Text = "ENGLISH_SENTINEL", Title = "History Gone By"},
        [3] = {Text = "OLD3", Title = "OLD3"},
    }
}
Map = {MapStatsIndex = 1}
TownPortalControls = {
    MapOfContinent = function(index)
        return 2
    end
}

KoreanReportedLocalization = {
    InstallContinentGameLabels = function()
        -- The real installer is idempotent. Labels are already registered in
        -- this harness, exactly as they are before the late hotfix runs.
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
assert(buttons[0].antag == nil, "Antagarich button remained on layer 0")
assert(buttons[0].enroth == nil, "Enroth button remained on layer 0")
assert(buttons[1].antag and buttons[1].antag.IUpSrc == "SlAntagDw",
    "Antagarich button was not promoted to layer 1")
assert(buttons[1].enroth and buttons[1].enroth.IUpSrc == "SlEnrothDw",
    "Enroth button was not promoted to layer 1")
assert(buttons[1].antag.Layer == 1 and buttons[1].enroth.Layer == 1,
    "promoted continent button Layer field is wrong")
assert(buttons[1].jadam and buttons[1].jadam.IUpSrc == "SlJadamDw" and buttons[1].jadam.Layer == 1,
    "Jadam button was modified unexpectedly")

-- Reapplying must be harmless.
assert(KoreanRuntimeHotfix.PromoteLowerContinentButtons() == 0,
    "continent button promotion was not idempotent")
assert(KoreanRuntimeHotfix.EnsureContinentLabelsActive() == 3,
    "all three continent labels were not retained")

local records = KoreanRuntimeHotfix.ParseMM7History()
assert(records and records[1] and records[2] and records[3], "failed to parse MM7 history source")
assert(records[2].Text and #records[2].Text > 100, "MM7 history record 2 text is unexpectedly short")
assert(records[2].Title and #records[2].Title > 0, "MM7 history record 2 title is missing")

events.LoadMap()
assert(Game.HistoryTxt[1].Text ~= "OLD1", "MM7 history record 1 was not applied")
assert(Game.HistoryTxt[2].Text ~= "ENGLISH_SENTINEL", "MM7 history record 2 was not applied")
assert(Game.HistoryTxt[2].Title ~= "History Gone By", "MM7 history record 2 title remained English")
assert(Game.HistoryTxt[3].Text ~= "OLD3", "MM7 history record 3 was not applied")

print("Korean runtime hotfix: OK")
