-- Retired after the primary LocalizeTables override was fixed to preserve
-- Rodril's original tonumber() semantics for Data/*LocalizeTables.*txt.
--
-- v1.0.24 temporarily used this late compatibility pass to recover numeric
-- gameplay fields such as NPCDataTxt.Joins. Keeping that second pass active
-- would now be redundant and could overwrite legitimate changes made by other
-- GameInitialized2 handlers. Leave this no-op upgrade stub so old installs
-- replace the former late gameplay writer on disk.

KoreanLocalization = KoreanLocalization or {}
KoreanLocalization.RodrilNumericSafetyNetRetired = true
