-- Korean-only Dagger Wound Island map hint overlay.
-- Keep this outside Scripts/Maps/out01.lua so the Korean patch does not replace
-- Rodril MMMerge's gameplay map script just to localize two cannon hints.

local function isDaggerWoundIsland()
    if not Map or type(Map.Name) ~= "string" then
        return false
    end
    local name = string.lower(Map.Name)
    return name == "out01.odm" or name == "out01"
end

local function applyDaggerWoundCannonHints()
    if not isDaggerWoundIsland() or not evt or not evt.str or not evt.hint then
        return
    end

    -- The translated STR entry is canonical. Reuse it rather than embedding a
    -- second Korean literal in Lua.
    local localized = evt.str[13]
    if type(localized) == "string" and localized ~= "" then
        evt.hint[457] = localized
        evt.hint[458] = localized
    end
end

function events.LoadMap()
    applyDaggerWoundCannonHints()
end

function events.AfterLoadMap()
    applyDaggerWoundCannonHints()
end
