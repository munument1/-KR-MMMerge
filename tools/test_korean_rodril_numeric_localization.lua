-- Regression harness for Rodril numeric LocalizeTables values.
-- Run with: lua5.1 tools/test_korean_rodril_numeric_localization.lua

local temp = os.tmpname()
local file = assert(io.open(temp, "wb"))
file:write("Table (of Game struct)\tId\tField\tNew text\r\n")
file:write("NPCDataTxt\t815\tJoins\t1\r\n")
file:write("\t824\tJoins\t1\r\n")
file:write("Dummy\t1\tValue\t-2.5\r\n")
file:write("Dummy\t2\tValue\tnot-a-number\r\n")
file:close()

path = {
	find = function(mask)
		assert(mask == "Data/*LocalizeTables.*txt")
		local yielded = false
		return function()
			if not yielded then
				yielded = true
				return temp
			end
		end
	end
}

Game = {
	NPCDataTxt = {
		[815] = {Joins = 0},
		[824] = {Joins = 0}
	},
	NPC = {
		[815] = {Joins = 0, Hired = false},
		[824] = {Joins = 0, Hired = true}
	},
	Dummy = {
		[1] = {Value = 0},
		[2] = {Value = 7}
	}
}

events = {}
Merge = {Log = {Info = 1}}
function Log() end
KoreanLocalization = {}

assert(loadfile("Scripts/General/ZZ_KoreanRodrilNumericLocalization.lua"))()
assert(type(KoreanLocalization.ReapplyRodrilNumericLocalization) == "function")

local applied, joins = KoreanLocalization.ReapplyRodrilNumericLocalization()
assert(applied == 3, "expected exactly three numeric records, got " .. tostring(applied))
assert(joins == 2, "expected two NPC Joins records, got " .. tostring(joins))

assert(type(Game.NPCDataTxt[815].Joins) == "number" and Game.NPCDataTxt[815].Joins == 1)
assert(type(Game.NPCDataTxt[824].Joins) == "number" and Game.NPCDataTxt[824].Joins == 1)
assert(type(Game.NPC[815].Joins) == "number" and Game.NPC[815].Joins == 1)
assert(type(Game.NPC[824].Joins) == "number" and Game.NPC[824].Joins == 1)
assert(Game.NPC[815].Hired == false, "repair must not touch Hired state")
assert(Game.NPC[824].Hired == true, "repair must preserve existing Hired state")
assert(type(Game.Dummy[1].Value) == "number" and Game.Dummy[1].Value == -2.5)
assert(Game.Dummy[2].Value == 7, "non-numeric display text must be ignored")

-- The ScriptsLoaded registration must expose the same repair as a late
-- GameInitialized2 handler, after LocalizeTables' own late pass in-game.
Game.NPCDataTxt[815].Joins = 0
Game.NPC[815].Joins = 0
assert(type(events.ScriptsLoaded) == "function")
events.ScriptsLoaded()
assert(type(events.GameInitialized2) == "function")
events.GameInitialized2()
assert(Game.NPCDataTxt[815].Joins == 1 and Game.NPC[815].Joins == 1)

os.remove(temp)
print("PASS: Rodril numeric localization and NPC Joins permissions are restored as numbers")
