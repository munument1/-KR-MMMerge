events = {}
Map = {Name = "out01.odm"}
evt = {
    str = {[13] = "localized cannon hint"},
    hint = {}
}

dofile("Scripts/General/ZZ_KoreanDaggerWoundHints.lua")

assert(type(events.LoadMap) == "function", "LoadMap handler was not registered")
assert(type(events.AfterLoadMap) == "function", "AfterLoadMap handler was not registered")

events.LoadMap()
assert(evt.hint[457] == evt.str[13], "cannon hint 457 was not localized")
assert(evt.hint[458] == evt.str[13], "cannon hint 458 was not localized")

-- The overlay must be map-scoped and leave unrelated maps alone.
Map.Name = "out02.odm"
evt.hint[457] = "unchanged 457"
evt.hint[458] = "unchanged 458"
events.AfterLoadMap()
assert(evt.hint[457] == "unchanged 457", "overlay leaked to another map")
assert(evt.hint[458] == "unchanged 458", "overlay leaked to another map")

print("Dagger Wound Korean hint overlay: OK")
