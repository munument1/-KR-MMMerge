#!/usr/bin/env python3
"""Validate parser-sensitive localization entries.

Some Merge scripts compare free-form Question() input directly against localized
text-table entries. Those entries are protocol tokens, not ordinary UI strings;
translating them can make quests impossible to complete on keyboards/input boxes
that only accept the original ASCII token.

This check currently protects the MM6 Enroth Light/Dark path confirmation token.
Use --fix only for the one-time canonical PO migration; normal CI should use
--check (the default).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import polib

PO_PATH = Path("translations/ko/mmmerge.po")

EXPECTED = {
    2104: "정말로 진로를 바꾸시겠습니까? 주문서에서 어둠 계열 주문이 사라지고, 머릿속에서 어둠 마법에 대한 지식도 지워집니다. 계속하려면 yes를 입력하십시오.",
    2105: "정말로 진로를 바꾸시겠습니까? 주문서에서 빛 계열 주문이 사라지고, 머릿속에서 빛 마법에 대한 지식도 지워집니다. 계속하려면 yes를 입력하십시오.",
    2108: "yes",
}


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="rewrite protected msgstr values")
    args = parser.parse_args()

    po = polib.pofile(str(PO_PATH))
    found: dict[int, polib.POEntry] = {}
    for entry in po:
        ident = npc_id(entry)
        if ident in EXPECTED:
            found[ident] = entry

    missing = sorted(set(EXPECTED) - set(found))
    if missing:
        print(f"missing protected NPCText entries: {missing}", file=sys.stderr)
        return 1

    changed = False
    bad = []
    for ident, expected in EXPECTED.items():
        entry = found[ident]
        if entry.msgstr != expected:
            bad.append((ident, entry.msgstr, expected))
            if args.fix:
                entry.msgstr = expected
                changed = True

    if args.fix and changed:
        po.save(str(PO_PATH))
        print("updated parser-sensitive localization entries in mmmerge.po")
        return 0

    if bad:
        for ident, actual, expected in bad:
            print(f"NPCText[{ident}] parser-sensitive drift: {actual!r} != {expected!r}", file=sys.stderr)
        return 1

    print("parser-sensitive localization: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
