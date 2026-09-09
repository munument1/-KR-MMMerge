-- Retired in v1.0.21.
--
-- Older Korean packages wrapped the global RefillTimer function to compensate
-- for an old MMMerge timer-core behavior on Emerald Island. Rodril's current
-- baseline already handles initialization through its IsInit-aware NextRefill
-- path, so a localization patch must not override gameplay timer semantics.
--
-- Keep this no-op file in the package so upgrading users overwrite the former
-- gameplay hook on disk instead of leaving it active from an older release.

KoreanEmeraldWellTimerFix = KoreanEmeraldWellTimerFix or {}
KoreanEmeraldWellTimerFix.Retired = true
