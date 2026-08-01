-- Dagger Wound Island cannon prompt fallback. The static LOD supplies the same
-- string, and this keeps the map hint correct across Merge map-script variants.
local KoreanCannonHint = "\180\235\198\247 \185\223\187\231"
if KoreanText and type(KoreanText.EncodeOnce) == "function" then
	KoreanCannonHint = KoreanText.EncodeOnce(KoreanCannonHint)
end
evt.str[13] = KoreanCannonHint
evt.hint[457] = KoreanCannonHint
evt.hint[458] = KoreanCannonHint

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
