# UI investigation test1

Based on -KR-MMMerge b0c6208, retaining native DBCS upstream aea1b22666ef556f34a71b4f3945904b04de1466 as the reviewed baseline.

Long native wrap output previously wrote up to 4096 bytes including NUL at a documented 2048-byte engine buffer. Results larger than 2047 bytes now use a 4096-byte static allocation. The original buffer keeps a DBCS/control-token-safe prefix for direct legacy field readers. Native draw/measure/page consumers use the wrap return pointer; the existing upstream L1-L4 patches are retained. The MMExtension Font.WordWrap ReturnPointer method is adapted to provide a full byte-array view on long results. Short results and short ASCII fallback keep their original behavior. Long ASCII also takes the bounded path.

This preserves the prior 4095-byte output cap, not arbitrary-length text. Direct consumers of Game.WordWrappedText still see the bounded 2047-byte field; use the returned pointer or Font.WordWrap for complete long output. The shipped 3711-byte history body is covered by a regression test. Runtime game compatibility of the modified pointer path still needs player verification.

The weak-value string cache is replaced with a 256-entry FIFO cache with at most 512KiB of key/value string bytes (Lua table overhead is additional). It clears on AfterLoadMap. Other upstream font/page caches are unchanged. The earlier page identity and partial installation concerns are not claimed fixed by this patch.

ZZ_KoreanUIDiagnostics is opt-in via Data/KO_UIDiagnostics.ini. Diagnostic test packages enable it explicitly. It observes existing BG/FG events and wraps only the unmodified MM8 Begin2D entry after a six-byte signature check. It does not patch End2D, change clip/render state, repair UI, send data, or alter saves. Tick readings are labelled outside-draw to avoid treating a normally-zero Begin2D counter as a failure. The native probe counts failed Begin2D returns and preserves the original call/return. Logs include phase-specific samples, manual incident markers, memory usage and renderer errors; bounded rotation prevents unbounded logs. There is instrumentation overhead.

Validation: Lua 5.1 syntax; upstream 53/53; additional 18/18 using the shipped EUC-KR config/page files and history data, with fake memory/engine functions. Error handling, disabled mode, signature mismatch, marker hotkey and rotation are exercised. A future full game test must verify text height, pages, scrolling and rare render paths, and then the original long-play failure.

The old integration validator's exact-upstream assertion has been changed to verify a separately stored upstream baseline plus local safety contracts and runtime regressions. CI now selects Lua 5.1 explicitly and runs the additional tests. Test fixtures and build tools are excluded from installed General scripts. The old README/audit documents describe historical versions and should not be read as current test validation.

Runtime test packages: DiagnosticsOnly leaves v1.0.15 renderer behavior unchanged, while FullTest applies both fixes plus identical diagnostics. Compare one variable at a time. No GitHub release or push is performed by the local packaging tool.
