-- Merge does not register the MM6 non-magic guild events 1696-1701.
-- Restore only the two services reported broken by the Korean patch users.

local PendingServiceGuildTopic = 0

function events.EnterNPC()
	PendingServiceGuildTopic = 0
end

local function JoinServiceGuild(TopicId, Cost, InfoText, AutonoteBit)
	if PendingServiceGuildTopic ~= TopicId then
		PendingServiceGuildTopic = TopicId
		Message(Game.NPCText[InfoText])
		return
	end

	if Party.AutonotesBits[AutonoteBit] then
		Message(Game.NPCText[124]) -- Already a member of this guild.
	elseif Party.Gold >= Cost then
		evt.Subtract{"Gold", Cost}
		evt.Add{"AutonotesBits", AutonoteBit}
		Message(Game.NPCText[InfoText])
	else
		Message(Game.GlobalTxt[155]) -- Not enough gold.
	end

	FirstClick = false
	PendingServiceGuildTopic = 0
end

local function RestoreServiceGuildTopic(TopicId, Cost, InfoText, AutonoteBit)
	evt.Global[TopicId]:clear()
	evt.Global[TopicId] = function()
		JoinServiceGuild(TopicId, Cost, InfoText, AutonoteBit)
	end
end

RestoreServiceGuildTopic(1696, 25, 1832, 629) -- Buccaneers' Lair
RestoreServiceGuildTopic(1699, 25, 1835, 632) -- Blade's End
