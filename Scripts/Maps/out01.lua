-- Dagger Wound Island cannon prompt fallback. The static STR translation is
-- canonical; reuse its localized string for map-script hint ids instead of
-- maintaining a second Korean literal here.
local KoreanCannonHint = evt.str[13]
if type(KoreanCannonHint) == "string" and KoreanCannonHint ~= "" then
	evt.hint[457] = KoreanCannonHint
	evt.hint[458] = KoreanCannonHint
end

-- Dimension door

function events.TileSound(t)
	if t.X == 63 and t.Y == 59 then
		TownPortalControls.DimDoorEvent()
	end
end

-- Town portal

function events.LoadMap()
	Party.QBits[185] = true
end
