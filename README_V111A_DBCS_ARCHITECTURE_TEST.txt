MMMerge Korean v1.0.11a - DBCS Architecture Test

Base: v1.0.10c Event Compatibility Test

Purpose
- Align Korean runtime text handling with the original FNT_DBCS localization design.
- Preserve all v1.0.10c translations, Yaro GlobalTxt fixes, cache repair, save-title fixes, and validator checks.

Changes
1. Added Scripts/General/KoreanFontText.lua as the single runtime DBCS conversion API.
2. Static and generated strings now use KoreanText.EncodeOnce instead of separate per-file encoders.
3. Removed the unsafe broad-byte fallback from LocalizeTables.lua and the validator.
4. Added validation for malformed, nested, orphaned, or unterminated DBCS control spans.
5. Added KoreanText.Finalize for safely closing externally truncated DBCS spans.
6. Did not hook string.format or modify the executable formatting path.
7. Did not change GlobalTxt[632], [633], or [634].

Why this is safer
- Already encoded strings are never encoded again.
- A missing KoreanFont module leaves text unchanged instead of guessing byte ranges.
- All runtime localization scripts make the same encoding decision.

Required game tests
- Startup: no addfirst error and no repeated garbage glyph output.
- Yaro trainer: one correct promotion sentence and no crash.
- MM6 NPC topics/body text.
- Map object hints and dynamic stat text.
- New-game NPC initialization and existing-save NPC names.
- Quick Save1 through Quick Save10.
- Data/KO_LocalizationValidation.log.

This remains a TEST build. Do not replace the repository main branch until in-game verification is complete.
