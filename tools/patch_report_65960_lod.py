#!/usr/bin/env python3
"""Patch report 65960 Global/SPCITEMS corrections into zz LocKO.T.lod."""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from patch_report_65949_lod import archive_entries, unpack_record, build_record
from patch_static_global_lod import encode_mixed_text
from patch_static_stats_lod import encode_dbcs_special

GLOBAL_VALUES = {
    589: "원거리 공격 보너스",
    590: "원거리 피해",
}

SPC_REPLACEMENTS = [
    ("[신들]", "[신]"),
    ("7대 능력치 모두 +10.", "모든 능력치 +10."),
]


def encoded(text: str) -> bytes:
    return encode_dbcs_special(encode_mixed_text(text))


def patch_global(raw: bytes) -> tuple[bytes, int]:
    lines = raw.splitlines(keepends=True)
    changed = 0
    for index, line in enumerate(lines):
        newline = b"\r\n" if line.endswith(b"\r\n") else (b"\n" if line.endswith(b"\n") else b"")
        body = line[:-len(newline)] if newline else line
        key, sep, _old = body.partition(b"\t")
        if not sep or not key.isdigit():
            continue
        record_id = int(key)
        if record_id not in GLOBAL_VALUES:
            continue
        wanted = key + b"\t" + encoded(GLOBAL_VALUES[record_id]) + newline
        if wanted != line:
            lines[index] = wanted
            changed += 1
    return b"".join(lines), changed


def patch_spc(raw: bytes) -> tuple[bytes, int]:
    changed = 0
    for old, new in SPC_REPLACEMENTS:
        old_b = encoded(old)
        count = raw.count(old_b)
        if count:
            raw = raw.replace(old_b, encoded(new))
            changed += count
    return raw, changed


def patch_lod(source: Path, output: Path) -> dict[str, int]:
    archive = source.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    cursor = len(entries) * 76
    rebuilt: list[bytes] = []
    report: dict[str, int] = {}

    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, compressed = unpack_record(record)
        raw2 = raw
        changed = 0
        folded = name.casefold()
        if folded == "global.txt":
            raw2, changed = patch_global(raw2)
        elif folded == "spcitems.txt":
            raw2, changed = patch_spc(raw2)

        if changed:
            record = build_record(record, raw2, compressed)
            report[name] = changed

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
    globals_seen: dict[int, bytes] = {}
    spc_raw: bytes | None = None

    for name, offset, size in entries:
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, _compressed = unpack_record(record)
        folded = name.casefold()
        if folded == "global.txt":
            for line in raw.splitlines():
                key, sep, value = line.partition(b"\t")
                if sep and key.isdigit() and int(key) in GLOBAL_VALUES:
                    globals_seen[int(key)] = value
        elif folded == "spcitems.txt":
            spc_raw = raw

    for record_id, value in GLOBAL_VALUES.items():
        if globals_seen.get(record_id) != encoded(value):
            raise SystemExit(f"Global.TXT[{record_id}] != {value}")

    if spc_raw is None:
        raise SystemExit("SPCITEMS.TXT missing from Korean LOD")
    for old, new in SPC_REPLACEMENTS:
        if encoded(old) in spc_raw:
            raise SystemExit(f"SPCITEMS.TXT still contains {old}")
        if encoded(new) not in spc_raw:
            raise SystemExit(f"SPCITEMS.TXT missing {new}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check_lod(args.lod)
        print("report 65960 LOD: OK")
    else:
        if args.output is None:
            parser.error("--output is required")
        report = patch_lod(args.lod, args.output)
        check_lod(args.output)
        print(f"report 65960: patched {sum(report.values())} occurrences in {len(report)} LOD members")
        for name, count in sorted(report.items(), key=lambda item: item[0].casefold()):
            print(f"{name}: {count}")
