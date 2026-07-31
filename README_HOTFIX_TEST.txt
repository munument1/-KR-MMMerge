MMMerge Korean Patch v1.0.9 Test Hotfix
=========================================

Reported issues addressed
-------------------------
1. Merchant buy/sell/repair/identify dialogue remained in English.
   - Replaced the embedded MERCHANT.TXT resource in Data/zz LocKO.T.lod.
   - All original %06/%24/%25/%27/%28/%29 control tokens were preserved.

2. House and owner names such as "Lord Markham" remained in English outdoors.
   - LocalizeTables now records the original Game.Houses strings before applying KO_2DEvents.
   - KoreanRuntimeFixes uses that mapping for evt.str and evt.hint.

3. Yaro trainer dialogue displayed broken %s text and crashed in KoreanFont.lua.
   - Added guarded DBCS font-page reads, stale-pointer reload, malformed-byte recovery,
     font-switch state reset, and hook-level pcall recovery.
   - Preserved GlobalTxt 632-634 promotion-class placeholders so required class names are displayed
     placeholders for this test build.

Also cleaned the unsupported empty GlobalTxt records 750-757 so the validator should no
longer report those eight errors. The existing NPC-name count warning may remain.

Installation
------------
Copy Data and Scripts into the MMMerge game directory and overwrite existing files.
Close the game before installing. Keep a backup of the current patch.

Test points
-----------
- Reopen the same shop and select a purchasable item.
- Stand outside Lord Markham's house and point at the entrance.
- Speak to Yaro in Long-Tail's Hut and open the trainer dialogue repeatedly.
- Check Data/KO_LocalizationValidation.log after one launch.

This build passed Lua syntax tests, a mocked invalid-font-pointer recovery test, LOD
structure/decompression checks for all 234 entries, and MERCHANT.TXT placeholder checks.
The actual MM8/MMMerge executable could not be run in the build environment, so this is
a test hotfix rather than a confirmed release.

Correction v1.0.8a:
- Restored %s placeholders in promotion requirement messages.


Correction v1.0.9:
- Kept the original %s promotion-class placeholders for Yaro's trainer message.
- Added map-hint translations: Anvil -> 모루, Sign/Signpost -> 표지판.
- Normalized whitespace and punctuation when matching house/sign hints.
- Scans evt.hint numerically because some Merge builds do not expose all hints to pairs().
- Reapplies map-hint localization for eight frames after map load so late map scripts
  cannot restore the English labels.
