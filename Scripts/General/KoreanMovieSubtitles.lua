-- MMMerge movie subtitles are intentionally disabled.
--
-- Earlier v1.0.29 hotfix builds tried to draw Korean subtitles from the native
-- Bink/Smacker movie loop. Real-game reports showed MM6/MM7 intro crashes, and
-- MM8 without an active subtitle cue did not prove the hook safe. The Korean
-- patch therefore leaves MMMerge movie playback completely untouched.
--
-- Keep this inert compatibility stub in release packages so installing a newer
-- hotfix overwrites the older crash-prone KoreanMovieSubtitles.lua on disk.

KoreanMovieSubtitles = KoreanMovieSubtitles or {}
local KMS = KoreanMovieSubtitles

KMS.Version = "disabled"
KMS.Disabled = true
KMS.Reason = "MMMerge native movie playback is intentionally left untouched."
