-- Regression harness for the Rodril semantics that the Korean LocalizeTables
-- override must preserve. Run with:
--   lua5.1 tools/test_localize_tables_upstream_semantics.lua

local temp = os.tmpname()
local file = assert(io.open(temp, "wb"))
file:write("Table (of Game struct)\tId\tField\tNew text\r\n")
file:write("Houses\t48\tPicture\t330\r\n")
file:write("\t48\tName\tTunnels to Eeofol\r\n")
file:write("MapStats\t205\tEaxEnvironments\t25\r\n")
file:write("NPCDataTxt\t815\tJoins\t1\r\n")
file:write("GlobalTxt\t676\t\tVictory text\r\n")
-- Rodril's real 03 LocalizeTables file contains tab-only separators. The
-- upstream loader treats them as no-op rows, not multiline continuation text.
file:write("\t\t\t\r\n")
file:write("GlobalTxt\t737\t\tHigh magic\r\n")
file:close()

function string.split(value, separator)
    local result = {}
    local start = 1
    while true do
        local first, last = string.find(value, separator, start, true)
        if not first then
            result[#result + 1] = string.sub(value, start)
            break
        end
        result[#result + 1] = string.sub(value, start, first - 1)
        start = last + 1
    end
    return result
end

path = {}
function path.find(mask)
    local values = {}
    if mask == "Data/*LocalizeTables.*txt" then
        values[1] = temp
    end
    local index = 0
    return function()
        index = index + 1
        return values[index]
    end
end

local quests = {
    [1] = "",
    [2] = "Existing quest"
}
setmetatable(quests, {
    __call = function(self, _, key)
        return next(self, key)
    end
})

Game = {
    Houses = {
        [48] = {Picture = 0, Name = "Old tunnel"}
    },
    MapStats = {
        [205] = {EaxEnvironments = 0}
    },
    NPCDataTxt = {
        [815] = {Joins = 0}
    },
    GlobalTxt = {
        [676] = "Old victory text",
        [737] = "Old magic text"
    },
    QuestsTxt = quests
}

KoreanText = {
    EncodeOnce = function(value)
        assert(type(value) == "string", "display encoder must only receive strings")
        return value
    end
}
KoreanLocalization = {}
events = {}
Merge = {Log = {Info = 1, Error = 2}}
function Log() end

assert(loadfile("Scripts/General/LocalizeTables.lua"))()
assert(type(events.GameInitialized2) == "function", "early source-table pass was not registered")
events.GameInitialized2()

assert(type(Game.Houses[48].Picture) == "number" and Game.Houses[48].Picture == 330,
    "Houses.Picture must preserve Rodril numeric semantics")
assert(Game.Houses[48].Name == "Tunnels to Eeofol",
    "inherited table rows must still resolve through LastTable")
assert(type(Game.MapStats[205].EaxEnvironments) == "number" and Game.MapStats[205].EaxEnvironments == 25,
    "MapStats.EaxEnvironments must preserve Rodril numeric semantics")
assert(type(Game.NPCDataTxt[815].Joins) == "number" and Game.NPCDataTxt[815].Joins == 1,
    "NPCDataTxt.Joins must preserve Rodril numeric semantics")
assert(Game.GlobalTxt[676] == "Victory text",
    "tab-only base separator leaked into the preceding GlobalTxt record")
assert(Game.GlobalTxt[737] == "High magic",
    "record after a tab-only separator was not loaded")
assert(Game.QuestsTxt[1] == "0",
    "blank quest entries must use Rodril's sentinel string '0'")
assert(Game.QuestsTxt[2] == "Existing quest",
    "nonblank quest entries must not be changed by normalization")

os.remove(temp)
print("PASS: Korean LocalizeTables preserves Rodril numeric, spacer, and quest semantics")
