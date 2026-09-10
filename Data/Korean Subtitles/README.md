# Korean cutscene subtitles for MMMerge

These UTF-8 SRT files are the reviewed Korean cutscene subtitles authored for the Korean OpenYAMM project and reused by MMMerge.

At runtime `Scripts/General/KoreanMovieSubtitles.lua` loads the SRT matching the `events.ShowMovie` movie stem, converts cue text from UTF-8 to Windows code page 949 with MMExtension's `string.convert`, and draws it after the movie frame with `events.PostRender` + `CustomUI.ShowText`.

The original `.vid`, `.smk`, and `.bik` movie assets are not modified. This keeps the patch small and avoids re-encoding legacy video.

Coverage: 19 dialogue-bearing cutscenes (MM6: 3, MM7: 10, MM8: 6). OpenYAMM's reviewed inventory separately classifies the remaining runtime cutscenes as no-audio or no-dialogue.
