#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"
pattern = re.compile(r"[가-힣]행운")


def decode(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    return ""

count = 0
for path in sorted(loc.glob("KO_*")):
    if not path.is_file():
        continue
    text = decode(path)
    for no, line in enumerate(text.splitlines(), 1):
        if pattern.search(line):
            count += 1
            print(f"{path.name}:{no}: {line[:500]}")
print(f"embedded-luck suspicious lines: {count}")
if count:
    raise SystemExit("embedded-luck corruption remains")
