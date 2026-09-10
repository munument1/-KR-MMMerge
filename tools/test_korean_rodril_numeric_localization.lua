-- Regression guard for the retired v1.0.24 late numeric safety net.
-- The primary Scripts/General/LocalizeTables.lua now preserves Rodril's
-- tonumber() semantics directly, so this upgrade stub must never register a
-- second gameplay-writing pass.

events = {}
KoreanLocalization = {}

assert(loadfile("Scripts/General/ZZ_KoreanRodrilNumericLocalization.lua"))()
assert(KoreanLocalization.RodrilNumericSafetyNetRetired == true,
    "retired marker is missing")
assert(KoreanLocalization.ReapplyRodrilNumericLocalization == nil,
    "late numeric gameplay writer must stay retired")
assert(events.ScriptsLoaded == nil,
    "retired safety net must not register ScriptsLoaded")
assert(events.GameInitialized2 == nil,
    "retired safety net must not register GameInitialized2")
assert(events.TxtFilesReloaded == nil,
    "retired safety net must not rewrite numeric fields on TXT reload")

print("PASS: late Rodril numeric safety net is retired; primary loader owns semantics")
