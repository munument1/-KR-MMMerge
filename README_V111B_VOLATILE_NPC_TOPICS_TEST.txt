MMMerge Korean v1.0.11b - Volatile NPC Topic Test

Fixes an issue where the dynamic NPC dialogue actions Beg and Threat could
alternate between Korean and English on repeated conversations.

Cause:
MMMerge rewrites NPCTopic slots 1765-1768 (Bribe/Beg/Threat/Exit) whenever
NPC dialogue state changes. A one-time table localization pass could therefore
be overwritten after initialization.

Change:
The localized values of NPCTopic[1765..1768] are now tracked separately and
restored after initialization, map loading, NPC entry, and immediately before
NPC greeting/dialogue rendering.

Test:
Enter and leave NPC dialogue repeatedly and confirm that Bribe, Beg, Threat,
and Exit remain Korean every time.
