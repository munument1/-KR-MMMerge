#!/usr/bin/env python3
"""Propagate the second report 65949 item QA pass into LocKO.T.lod."""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from apply_report_65949_item_review2 import ROW_FIXES
from patch_report_65949_lod import archive_entries, build_record, encoded, unpack_record


def patch_items(raw: bytes) -> tuple[bytes, int]:
    lines = raw.splitlines(keepends=True)
    seen: set[int] = set()
    changed = 0
    for index, line in enumerate(lines):
        id_b, sep, _rest = line.partition(b"\t")
        if not sep or not id_b.isdigit():
            continue
        item_id = int(id_b)
        fixes = ROW_FIXES.get(item_id)
        if not fixes:
            continue
        seen.add(item_id)
        updated = line
        for old, new in fixes:
            old_b = encoded(old)
            new_b = encoded(new)
            if old_b in updated:
                updated = updated.replace(old_b, new_b)
                changed += 1
            elif new_b not in updated:
                raise SystemExit(f"LOD Items.txt item {item_id}: neither old nor corrected phrase found: {old!r}")
        lines[index] = updated
    missing = sorted(set(ROW_FIXES) - seen)
    if missing:
        raise SystemExit(f"LOD Items.txt missing item rows: {missing}")
    return b"".join(lines), changed


def patch_lod(source: Path, output: Path) -> dict[str, int]:
    archive = source.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    cursor = len(entries) * 76
    rebuilt: list[bytes] = []
    report: dict[str, int] = {}
    found = False

    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        if name.casefold() == "items.txt":
            raw, compressed = unpack_record(record)
            patched, count = patch_items(raw)
            if count:
                record = build_record(record, patched, compressed)
                report[name] = count
            found = True
        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    if not found:
        raise SystemExit("Items.txt not found in localization LOD")

    result = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", result, 0x114, len(result) - root_offset)
    output.write_bytes(result)
    return report


def check_lod(path: Path) -> None:
    archive = path.read_bytes()
    root_offset, _directory, entries = archive_entries(archive)
    found = False
    violations: list[str] = []
    for name, offset, size in entries:
        if name.casefold() != "items.txt":
            continue
        found = True
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, _compressed = unpack_record(record)
        lines = raw.splitlines()
        by_id = {}
        for line in lines:
            key, sep, _rest = line.partition(b"\t")
            if sep and key.isdigit():
                by_id[int(key)] = line
        for item_id, fixes in ROW_FIXES.items():
            line = by_id.get(item_id)
            if line is None:
                violations.append(f"missing Items.txt row {item_id}")
                continue
            for old, new in fixes:
                if encoded(old) in line:
                    violations.append(f"item {item_id}: stale {old}")
                if encoded(new) not in line:
                    violations.append(f"item {item_id}: missing {new}")
    if not found:
        violations.append("Items.txt not found")
    if violations:
        raise SystemExit("report 65949 item review 2 LOD validation failed:\n" + "\n".join(violations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check_lod(args.lod)
        print("report 65949 item review 2 LOD: OK")
    else:
        if args.output is None:
            parser.error("--output is required")
        report = patch_lod(args.lod, args.output)
        check_lod(args.output)
        print(f"report 65949 item review 2: patched {sum(report.values())} occurrences in {len(report)} LOD members")
        for name, count in report.items():
            print(f"{name}: {count}")
