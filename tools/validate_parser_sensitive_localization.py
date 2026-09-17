#!/usr/bin/env python3
"""Validate parser-sensitive localization entries.

Some Merge scripts compare free-form Question() input directly against localized
text-table entries or hard-coded ASCII tokens. Translating a control token, or
translating its prompt without preserving the required input, can make quest and
travel interactions impossible to complete.

The protected entries below are confirmed by the upstream Lua call sites. Use
--fix only for a one-time canonical PO migration; normal CI should run in check
mode (the default).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import polib

PO_PATH = Path("translations/ko/mmmerge.po")

NPC_EXPECTED = {
    2104: "정말로 진로를 바꾸시겠습니까? 주문서에서 어둠 계열 주문이 사라지고, 머릿속에서 어둠 마법에 대한 지식도 지워집니다. 계속하려면 yes를 입력하십시오.",
    2105: "정말로 진로를 바꾸시겠습니까? 주문서에서 빛 계열 주문이 사라지고, 머릿속에서 빛 마법에 대한 지식도 지워집니다. 계속하려면 yes를 입력하십시오.",
    2108: "yes",
}

MAP_EXPECTED = {
    ("breach.str", 1): "빈 홈에 텔레로케이터를 끼우자 균열이 변해 그 너머의 풍경이 보이지 않습니다. 들어가려면 y를 입력하십시오.",
}

MAP_CONTEXT_RE = re.compile(r"/(?P<file>[^/|]+)\|string=(?P<index>\d+)$")


def npc_id(entry: polib.POEntry) -> int | None:
    context = entry.msgctxt or ""
    marker = "|table=NPCText|id="
    if marker not in context:
        return None
    tail = context.split(marker, 1)[1]
    raw = tail.split("|", 1)[0]
    try:
        return int(raw)
    except ValueError:
        return None


def map_key(entry: polib.POEntry) -> tuple[str, int] | None:
    match = MAP_CONTEXT_RE.search(entry.msgctxt or "")
    if not match:
        return None
    return match.group("file").casefold(), int(match.group("index"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="rewrite protected msgstr values")
    args = parser.parse_args()

    po = polib.pofile(str(PO_PATH))
    found_npc: dict[int, polib.POEntry] = {}
    found_map: dict[tuple[str, int], polib.POEntry] = {}

    for entry in po:
        ident = npc_id(entry)
        if ident in NPC_EXPECTED:
            found_npc[ident] = entry

        key = map_key(entry)
        if key in MAP_EXPECTED:
            found_map[key] = entry

    missing_npc = sorted(set(NPC_EXPECTED) - set(found_npc))
    missing_map = sorted(set(MAP_EXPECTED) - set(found_map))
    if missing_npc or missing_map:
        if missing_npc:
            print(f"missing protected NPCText entries: {missing_npc}", file=sys.stderr)
        if missing_map:
            print(f"missing protected MapStrings entries: {missing_map}", file=sys.stderr)
        return 1

    changed = False
    bad: list[tuple[str, str, str]] = []

    for ident, expected in NPC_EXPECTED.items():
        entry = found_npc[ident]
        if entry.msgstr != expected:
            bad.append((f"NPCText[{ident}]", entry.msgstr, expected))
            if args.fix:
                entry.msgstr = expected
                changed = True

    for key, expected in MAP_EXPECTED.items():
        entry = found_map[key]
        if entry.msgstr != expected:
            bad.append((f"MapStrings[{key[0]}:{key[1]}]", entry.msgstr, expected))
            if args.fix:
                entry.msgstr = expected
                changed = True

    if args.fix and changed:
        po.save(str(PO_PATH))
        print("updated parser-sensitive localization entries in mmmerge.po")
        return 0

    if bad:
        for label, actual, expected in bad:
            print(f"{label} parser-sensitive drift: {actual!r} != {expected!r}", file=sys.stderr)
        return 1

    print("parser-sensitive localization: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
