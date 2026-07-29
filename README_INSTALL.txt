==================================================
Might and Magic 6.7.8 Merge Korean Patch Release (v1.0.5)
==================================================
[Installation Instructions]
Copy all folders (Data, DataFiles, Scripts) from this release package 
directly into your installed Might and Magic 8 game folder.
[Target Game Directory Structure]
D:\GOG\Might and Magic 8\
 ??? Data\
 ?   ??? LocalizeConf.ini
 ?   ??? zz LocKO.T.lod
 ?   ??? Text localization\ (Contains KO_*.txt translation files)
 ??? DataFiles\ (Contains DBCS font files)
 ??? Scripts\
     ??? General\
         ??? LocalizeTables.lua
         ??? KoreanHistory.lua
[Translation File Placement]
Put your translated text files (KO_*.txt) in:
  D:\GOG\Might and Magic 8\Data\Text localization\

[v1.0.5 History Fix]
- MM8 and MM7 history tables now switch with the active continent.
- MM6 shows an Enroth introduction instead of retaining MM8 Day of the Destroyer text.
- Legacy KO_HistoryTxt.txt files are ignored automatically.
- Do not restore Scripts\General\History.lua from an older package.

[v1.0.5 Font Fix]
- Restored the verified clean 14/15b/16-pixel DBCS fonts used in the 2026-07-28 09:15 game screenshot.
- Applied ChungjuKimSaeng only to the 29-pixel book-title fonts.
- Kept the compact MM8 opening history below the engine's encoded-text buffer limit.

[v1.0.1 Translation Fixes]
- Replaced the packaged dialogue tables with the completed Korean translation.
- Added Korean random NPC names (KO_NPCNames.txt).
- Added Korean spell names, descriptions, and mastery effects (KO_SpellsTxt.txt).
- Updated LocalizeTables.lua for multiline records and broader Korean byte handling.
