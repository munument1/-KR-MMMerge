#!/usr/bin/env python3
"""Patch the localized regular-Merchant buy line without changing its tokens."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD_TEXT = (
    "보통 %24 같은 물건은 %25골드에 팝니다. "
    "하지만 흥정을 잘하시니 %27골드에 드리지요."
)
NEW_TEXT = "%24의 기준 가격은 %25골드이며, 현재 구매 가격은 %27골드입니다."


def encode_special(text: str) -> bytes:
    """Reproduce KoreanFont.encodeSpecial for CP949 Korean characters."""
    encoded = bytearray()
    for character in text:
        raw = character.encode("cp949")
        if len(raw) == 2 and all(0xA1 <= value <= 0xFE for value in raw):
            encoded.extend(b"\x0e\x20\x0e")
            encoded.extend(raw)
            encoded.extend(b"\x07\x0f")
        else:
            encoded.extend(raw)
    return bytes(encoded).replace(b"\x0f\x0e", b"")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("merchant_txt", type=Path)
    args = parser.parse_args()

    old = encode_special(OLD_TEXT)
    new = encode_special(NEW_TEXT)
    data = args.merchant_txt.read_bytes()
    matches = data.count(old)
    if matches != 1:
        raise SystemExit(f"expected exactly one old Merchant line, found {matches}")

    args.merchant_txt.write_bytes(data.replace(old, new, 1))
    print(f"patched {args.merchant_txt}: {len(old)} -> {len(new)} bytes")


if __name__ == "__main__":
    main()
