-- MMMerge Korean patch: keep the two-click guild confirmation alive across
-- the intermediate NPC/house dialog transition.

local PendingGuildTopic = 0

function events.EnterNPC()
	PendingGuildTopic = 0
end

local function JoinGuild(GuildType, Cost, Text, ABit, TopicId)
	if PendingGuildTopic ~= TopicId then
		PendingGuildTopic = TopicId
		Message(Game.NPCText[Text])
		return
	end

	vars.GuildMembership = vars.GuildMembership or {}

	if vars.GuildMembership[GuildType] then
		Message(Game.NPCText[124]) -- Already member of this guild.
	elseif Party.Gold >= Cost then
		evt.Subtract{"Gold", Cost}
		evt.Add{"AutonotesBits", ABit}
		vars.GuildMembership[GuildType] = true
		Message(Game.NPCText[Text])
	else
		Message(Game.GlobalTxt[155]) -- Not enough gold.
	end

	FirstClick = false
	PendingGuildTopic = 0
end

local function SetGuildTopic(TopicId, GuildType, Cost, Text, ABit)
	evt.Global[TopicId]:clear()
	evt.Global[TopicId] = function()
		JoinGuild(GuildType, Cost, Text, ABit, TopicId)
	end
end

-- Antagarich
SetGuildTopic(1150, 14, 100, 1830, 564) -- Elements
SetGuildTopic(1151, 15, 100, 1039, 565) -- Self
SetGuildTopic(1152, 6, 50, 1040, 566)   -- Air
SetGuildTopic(1153, 8, 50, 1041, 567)   -- Earth
SetGuildTopic(1154, 5, 50, 1042, 568)   -- Fire
SetGuildTopic(1155, 7, 50, 1043, 569)   -- Water
SetGuildTopic(1156, 11, 50, 1044, 570)  -- Body
SetGuildTopic(1157, 10, 50, 1045, 571)  -- Mind
SetGuildTopic(1158, 9, 50, 1046, 572)   -- Spirit
SetGuildTopic(1159, 12, 1000, 1047, 573) -- Light
SetGuildTopic(1160, 13, 1000, 1048, 574) -- Dark

-- Enroth
SetGuildTopic(1694, 14, 100, 1830, 564)
SetGuildTopic(1695, 15, 100, 1039, 565)
SetGuildTopic(1702, 6, 50, 1040, 566)
SetGuildTopic(1703, 8, 50, 1041, 567)
SetGuildTopic(1704, 5, 50, 1042, 568)
SetGuildTopic(1705, 7, 50, 1043, 569)
SetGuildTopic(1706, 11, 50, 1044, 570)
SetGuildTopic(1707, 10, 50, 1045, 571)
SetGuildTopic(1708, 9, 50, 1046, 572)
SetGuildTopic(1709, 12, 1000, 1047, 573)
SetGuildTopic(1710, 13, 1000, 1048, 574)
