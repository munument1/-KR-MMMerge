MMMerge Korean v1.0.10a TEST - Yaro promotion dialogue fix

Cause
-----
MMMerge joins branched promotion class names using Game.GlobalTxt[634].
The current Merge localization override changes this entry from the original
two-placeholder sentence to the single separator word "or".

The Korean table incorrectly kept a complete "%s ... %s" sentence at ID 634.
This produced a malformed result such as:
  Champion + [full format sentence] + Black Knight
and the engine formatted that malformed string again, leading to literal %s
text, duplicated sentences, and a renderer crash.

Fix
---
GlobalTxt[632] : one %s placeholder
GlobalTxt[633] : one %s placeholder
GlobalTxt[634] : 또는 (no placeholder)

Expected display
----------------
이 기술 레벨은 챔피언 또는 흑기사 승급 후 배울 수 있습니다.
