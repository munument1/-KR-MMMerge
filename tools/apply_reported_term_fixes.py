#!/usr/bin/env python3
"""Apply the 2026-09-08 player-reported Korean terminology corrections.

Legacy localization tables are CP949/EUC-KR and marked binary in git.  This
script deliberately preserves each file's original encoding and line endings;
it only replaces the reported Korean text.
"""

from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc_dir = root / "Data" / "Text localization"

# Specific phrases must precede their shorter roots.
REPLACEMENTS = [
    ("안타가리찬 산", "안타개릭산"),
    ("안타가리찬산", "안타개릭산"),
    ("안타가리찬", "안타개릭"),
    ("안타가리치", "안타개릭"),
    ("자다메", "제이덤"),
    ("자데임", "제이덤"),
    ("마컴", "마크햄"),
    ("사드래곤하려면", "사용하려면"),
    ("사드래곤할 수", "사용할 수"),
    ("과부쥐 열매", "위도우스위프 열매"),
    ("포피스냅스", "양귀비꽃"),
    ("포피스냅은", "양귀비꽃은"),
    ("가넷", "석류석"),
    ("늑대 눈은", "늑대의 눈은"),
    ("늑대 눈을", "늑대의 눈을"),
    ("(이동 속도 +30", "(속도 +30"),
]


def decode_with_encoding(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def main() -> None:
    changed_files = 0
    total_replacements = 0

    for path in sorted(loc_dir.glob("KO_*.txt")):
        original = path.read_bytes()
        try:
            text, encoding = decode_with_encoding(original)
        except UnicodeDecodeError:
            print(f"skip undecodable file: {path.relative_to(root)}")
            continue

        changed = 0
        for old, new in REPLACEMENTS:
            count = text.count(old)
            if count:
                text = text.replace(old, new)
                changed += count

        if not changed:
            continue

        rebuilt = text.encode(encoding)
        path.write_bytes(rebuilt)
        changed_files += 1
        total_replacements += changed
        print(f"{path.relative_to(root)}: {changed} replacements ({encoding})")

    print(f"reported term fixes: {total_replacements} replacements in {changed_files} files")
    if total_replacements == 0:
        print("nothing to change")


if __name__ == "__main__":
    main()
