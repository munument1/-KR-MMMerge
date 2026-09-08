#!/usr/bin/env python3
"""Apply report 65949 item QA pass 5.

This pass fixes remaining artifact/relic name drift inside descriptions and a
few player-facing terminology inconsistencies.  Replacements are scoped to
exact item IDs and preserve the legacy table encoding.
"""
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

ROW_FIXES: dict[int, list[tuple[str, str]]] = {
    522: [("모든 마법 저항 +10", "모든 마법 저항력 +10")],
    524: [("하복은 특수 능력 덕분에", "대혼란은 특수 능력 덕분에")],
    528: [("지배의 삼지창은 원래", "통치의 삼지창은 원래")],
    1309: [("(언데드 처치, 마비 면역, 화염 피해 3-18)", "(언데드 사냥, 마비 면역, 화염 피해 3-18)")],
    1313: [("마스터의 손은 원래", "달인의 손은 원래")],
    1315: [("지배자의 반지는 서기", "통치자의 반지는 서기")],
}


def decode_with_encoding(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def main() -> None:
    original = path.read_bytes()
    text, encoding = decode_with_encoding(original)
    lines = text.splitlines(keepends=True)
    seen: set[int] = set()
    changed = 0

    for index, line in enumerate(lines):
        body = line.rstrip("\r\n")
        id_text, sep, _rest = body.partition("\t")
        if not sep or not id_text.isdigit():
            continue
        item_id = int(id_text)
        fixes = ROW_FIXES.get(item_id)
        if not fixes:
            continue
        seen.add(item_id)
        updated = line
        for old, new in fixes:
            if old in updated:
                updated = updated.replace(old, new)
                changed += 1
            elif new not in updated:
                raise SystemExit(f"item {item_id}: neither old nor corrected phrase found: {old!r}")
        lines[index] = updated

    missing = sorted(set(ROW_FIXES) - seen)
    if missing:
        raise SystemExit(f"missing item rows: {missing}")

    wanted = "".join(lines).encode(encoding)
    if wanted != original:
        path.write_bytes(wanted)
    print(f"report 65949 item review 5: {changed} source corrections ({encoding})")


if __name__ == "__main__":
    main()
