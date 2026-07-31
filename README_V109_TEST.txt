MMMerge Korean v1.0.9 integrated test fix

Implemented:
- New-game-safe NPC name migration (no Game.NPC access during GameInitialized2).
- Safe Korean string.format: decode -> format -> encode once.
- Promotion messages keep actual required class names.
- Corrected MM7 class order: Champion ID 18, Black Knight ID 19.
- Patched all 209 STR resources for common map labels/effects.
- STR replacements: 2323 occurrences / 330 distinct English strings.
- Expanded runtime object/sign dictionary and event scan range.
- Handles +10 Might Temporary and related stat/resistance formats.

This is a test build. Completely exit the game before overwriting files.
