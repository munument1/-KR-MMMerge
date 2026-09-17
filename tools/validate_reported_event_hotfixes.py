#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
hotfix_path = root / "Scripts" / "General" / "ZZZ_KoreanReportedEventHotfixes.lua"
scrolls_path = root / "Data" / "Text localization" / "KO_MessageScrolls.txt"

hotfix_bytes = hotfix_path.read_bytes()
try:
    hotfix = hotfix_bytes.decode("ascii")
except UnicodeDecodeError as exc:
    raise SystemExit(f"event hotfix must remain ASCII-only: {hotfix_path}: {exc}")

# .gitattributes checks out Lua files with CRLF. Normalize line endings before
# applying line-anchored source checks so the validator behaves identically on
# GitHub Actions and local LF worktrees.
hotfix = hotfix.replace("\r\n", "\n").replace("\r", "\n")

required_fragments = [
    "local PROCLAMATION_ITEM_ID = 2166",
    'structs.o.GameStructure["MessageScrolls"]',
    "local itemIndex = base + count * 4 + 4",
    "mem.u2[itemIndex + row * 2] == itemId",
    "Game.MessageScrolls[row] = encodeKorean(PROCLAMATION_TEXT)",
    'local EMERALD_MESSENGER_MARKER = "Great competition going to happen very soon!"',
    'local EMERALD_MESSENGER_END_MARKER = "Putting paper in your hands, he runs away"',
    "for i in Game.NPCText do",
    "Game.NPCText[i] = localized",
]
for fragment in required_fragments:
    if fragment not in hotfix:
        raise SystemExit(f"missing reported event hotfix contract: {fragment!r}")

for forbidden in (
    "Game.MessageScrolls[26] =",
    "PROCLAMATION_ROW = 26",
    "2166 - 2140",
):
    if forbidden in hotfix:
        raise SystemExit(f"unsafe hard-coded proclamation mapping returned: {forbidden!r}")


def decode_lua_decimal_bytes(variable: str) -> str:
    pattern = rf'^local {re.escape(variable)} = "(.*)"$'
    match = re.search(pattern, hotfix, re.MULTILINE)
    if not match:
        raise SystemExit(f"missing byte-escaped string: {variable}")
    raw = match.group(1)
    pieces = re.findall(r"\\(\d{1,3})", raw)
    if "".join("\\" + p for p in pieces) != raw:
        raise SystemExit(f"{variable} must contain only decimal Lua byte escapes")
    values = bytes(int(piece) for piece in pieces)
    try:
        return values.decode("cp949")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"{variable} is not valid CP949: {exc}")


proclamation = decode_lua_decimal_bytes("PROCLAMATION_TEXT")
expected_proclamation = "축하합니다! 이로써 여러분 모두를 슈퍼 구버로 선포합니다!"
if proclamation != expected_proclamation:
    raise SystemExit(
        f"proclamation translation drift: expected {expected_proclamation!r}, got {proclamation!r}"
    )

messenger = decode_lua_decimal_bytes("EMERALD_MESSENGER_TEXT")
expected_messenger = (
    "(소년이 당신에게 달려온다.)\n\n"
    "저기요, 나리들! 곧 큰 보물찾기 대회가 열려요!\n\n"
    "(소년은 당신 손에 종이를 쥐여 주고 달아난다.)"
)
if messenger != expected_messenger:
    raise SystemExit(
        f"Emerald Island messenger translation drift: expected {expected_messenger!r}, got {messenger!r}"
    )

# MessageScrolls row 26 is a legitimate MM8 potion recipe. Guard against a
# tempting but destructive workaround that replaces it with the MM6 item 2166
# proclamation. The runtime fix must resolve 2166 through Rodril's item-id map.
scrolls_data = scrolls_path.read_bytes()
for encoding in ("utf-8-sig", "cp949"):
    try:
        scrolls = scrolls_data.decode(encoding)
        break
    except UnicodeDecodeError:
        continue
else:
    raise SystemExit(f"cannot decode {scrolls_path}")

row26 = next((line for line in scrolls.splitlines() if line.startswith("\t26\t")), None)
if row26 is None or "흰 화염 저항 물약" not in row26:
    raise SystemExit("KO_MessageScrolls row 26 must remain the white Fire Resistance potion recipe")
if "슈퍼 구버" in row26 or "선포" in row26:
    raise SystemExit("MM6 Proclamation was incorrectly written into KO_MessageScrolls row 26")

print("reported event text hotfixes: OK")
