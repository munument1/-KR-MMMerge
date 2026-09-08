#!/usr/bin/env python3
"""Apply the report 65949 follow-up cleanup directly to LocKO.T.lod."""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from patch_report_65949_lod import archive_entries, build_record, encoded, unpack_record

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
    ("\t약초\t", "\t시약\t"),
]

BAD_PHRASES = [old for old, _new in EXACT_FIXES]


def patch_exact(raw: bytes) -> tuple[bytes, int]:
    changed = 0
    for old, new in EXACT_FIXES:
        old_b = encoded(old)
        count = raw.count(old_b)
        if count:
            raw = raw.replace(old_b, encoded(new))
            changed += count
    return raw, changed


def normalize_reagent_instructions(raw: bytes) -> tuple[bytes, int]:
    lines = raw.splitlines(keepends=True)
    changed = 0
    category = b"\t" + encoded("시약") + b"\t"
    start_marker = encoded("(사용하려면")
    replacement = encoded(STANDARD_REAGENT_INSTRUCTION)

    for index, line in enumerate(lines):
        if category not in line:
            continue
        start = line.find(start_marker)
        if start < 0:
            continue
        end = line.find(b")", start)
        if end < 0:
            continue
        old = line[start:end + 1]
        if old != replacement:
            lines[index] = line[:start] + replacement + line[end + 1:]
            changed += 1
    return b"".join(lines), changed


def patch_lod(source: Path, output: Path) -> dict[str, int]:
    archive = source.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    cursor = len(entries) * 76
    rebuilt: list[bytes] = []
    report: dict[str, int] = {}

    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, compressed = unpack_record(record)
        raw2, count = patch_exact(raw)
        if name.casefold() == "items.txt":
            raw2, reagent_count = normalize_reagent_instructions(raw2)
            count += reagent_count
        if count:
            record = build_record(record, raw2, compressed)
            report[name] = count
        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    result = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", result, 0x114, len(result) - root_offset)
    output.write_bytes(result)
    return report


def check_lod(path: Path) -> None:
    archive = path.read_bytes()
    root_offset, _directory, entries = archive_entries(archive)
    violations: list[str] = []
    category = b"\t" + encoded("시약") + b"\t"
    start_marker = encoded("(사용하려면")
    standard = encoded(STANDARD_REAGENT_INSTRUCTION)

    for name, offset, size in entries:
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, _compressed = unpack_record(record)
        for text in BAD_PHRASES:
            if encoded(text) in raw:
                violations.append(f"{name}: stale {text}")
        if name.casefold() == "items.txt":
            for line_no, line in enumerate(raw.splitlines(), 1):
                if category in line and start_marker in line and standard not in line:
                    violations.append(f"Items.txt:{line_no}: non-canonical reagent instruction")

    if violations:
        raise SystemExit("report 65949 follow-up LOD validation failed:\n" + "\n".join(violations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        check_lod(args.lod)
        print("report 65949 follow-up LOD: OK")
    else:
        if args.output is None:
            parser.error("--output is required")
        report = patch_lod(args.lod, args.output)
        check_lod(args.output)
        print(f"report 65949 follow-up: patched {sum(report.values())} occurrences in {len(report)} LOD members")
        for name, count in sorted(report.items(), key=lambda item: item[0].casefold()):
            print(f"{name}: {count}")
