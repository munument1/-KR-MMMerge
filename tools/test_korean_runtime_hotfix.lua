-- Regression harness for ZZZZ_KoreanRuntimeHotfix.lua.

events = {}

local shown = {}
CustomUI = {
    ActiveElements = {
        [97] = {
            Texts = {
                [0] = {
                    KoreanContinentGameLabel1 = {Active = true},
                    KoreanContinentGameLabel2 = {Active = true},
                    KoreanContinentGameLabel3 = {Active = true},
                }
            }
        }
    },
    ShowText = function(text, font, x, y, shift, r, g, b, wt, ht, xof, yof, color, left)
        shown[#shown + 1] = {Text = text, X = x, Y = y}
    end
}

const = {Screens = {ChooseContinent = 97}}
Game = {
    CurrentScreen = 97,
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

dofile("Scripts/General/ZZZZ_KoreanRuntimeHotfix.lua")

events.GameInitialized2()
for i = 1, 3 do
    assert(CustomUI.ActiveElements[97].Texts[0]["KoreanContinentGameLabel" .. i].Active == false,
        "legacy continent label remained active: " .. i)
end

events.FGInterfaceUpd()
assert(#shown == 3, "expected three topmost continent labels")
assert(shown[1].Text == "M&M 8", "missing M&M 8 label")
assert(shown[2].Text == "M&M 7", "missing M&M 7 label")
assert(shown[3].Text == "M&M 6", "missing M&M 6 label")

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
