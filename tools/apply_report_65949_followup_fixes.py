#!/usr/bin/env python3
"""Finish report 65949 cleanup without broad substring replacements.

This pass fixes particle damage caused by earlier canonical-name substitutions
and normalizes only the parenthetical usage instruction on rows whose item
category is exactly ``시약``.  The legacy item table stays in its original
encoding and line-ending style.
"""
from __future__ import annotations

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
items_path = root / "Data" / "Text localization" / "KO_ItemsTxt.txt"

STANDARD_REAGENT_INSTRUCTION = (
    "(사용하려면 시약을 집어 빈 물약 병 위에서 마우스 오른쪽 버튼을 클릭하세요.)"
)

EXACT_FIXES = [
    ("영광스러행운", "영광스러운"),
    ("철깃털는", "철깃털은"),
    ("교수대은", "교수대는"),
    ("교수대을", "교수대를"),
    ("흰독말풀는", "흰독말풀은"),
    ("흰독말풀를", "흰독말풀을"),
    ("'종결'라는 검", "'종결'이라는 검"),
    (
        "태양교회가 달교회가 만들어낸 끊임없이 증가하는 언데드 무리를 소탕하기 위한 노력의 일환으로 제작되었습니다.",
        "달교회가 만들어 낸 끊임없이 증가하는 언데드 무리를 소탕하기 위한 태양교회의 노력의 일환으로 제작되었습니다.",
    ),
]


def decode_with_encoding(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def normalize_reagent_instructions(text: str) -> tuple[str, int]:
    changed = 0
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        newline = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else ("\r" if line.endswith("\r") else ""))
        body = line[:-len(newline)] if newline else line
        fields = body.split("\t", 3)
        if len(fields) == 4 and fields[2].strip() == "시약" and "(사용하려면" in fields[3]:
            notes, count = re.subn(
                r"\(사용하려면[^)]*\)",
                STANDARD_REAGENT_INSTRUCTION,
                fields[3],
                count=1,
            )
            if count and notes != fields[3]:
                fields[3] = notes
                body = "\t".join(fields)
                changed += 1
        output.append(body + newline)
    return "".join(output), changed


def main() -> None:
    original = items_path.read_bytes()
    text, encoding = decode_with_encoding(original)
    exact_changes = 0
    for old, new in EXACT_FIXES:
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            exact_changes += count

    text, reagent_changes = normalize_reagent_instructions(text)
    wanted = text.encode(encoding)
    if wanted != original:
        items_path.write_bytes(wanted)

    total = exact_changes + reagent_changes
    print(
        f"report 65949 follow-up source fixes: {total} changes "
        f"({exact_changes} exact, {reagent_changes} reagent instructions; {encoding})"
    )


if __name__ == "__main__":
    main()
