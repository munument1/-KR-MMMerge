#!/usr/bin/env python3
"""Propagate report 65949 terminology/item fixes into Data/zz LocKO.T.lod."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

from apply_report_65949_fixes import SAFE_ALL, MECHANICAL, ITEM_FIXES
from patch_static_global_lod import encode_mixed_text
from patch_static_stats_lod import encode_dbcs_special

GLOBAL_VALUES = {
    1: "정확도",
    75: "인내력",
    211: "민첩성",
    248: "일시적 운",
    258: "일시적 민첩성",
    284: "공기 마법",
    291: "육체 마법",
}

EXTRA_ITEM_FIXES = [
    ("기벳", "교수대"),
]

STALE_CRITICAL = [
    "날카로행운", "아름다행운", "가까행운", "갑작스러행운", "기행운", "불행운",
    "파이널리티", "기벳", "구울스베인", "아이언 페더", "아르테무스", "샤렐레",
    "타이탄의 벨트", "울리세스", "물 마법 사용 시 속도 +40",
    "무장 해제 기술 +5", "살을 돌로 변하게 하는 효과 면역",
    "방패 사용 시 행운 +20", "재생력 +10",
]


def encoded(text: str) -> bytes:
    return encode_dbcs_special(encode_mixed_text(text))


def archive_entries(archive: bytes):
    if archive[:4] != b"LOD\0":
        raise ValueError("not a LOD archive")
    root_offset, _root_size, _unknown, count = struct.unpack_from("<IIII", archive, 0x110)
    directory_end = root_offset + count * 76
    directory = bytearray(archive[root_offset:directory_end])
    entries = []
    for index in range(count):
        pos = index * 76
        name = directory[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, unknown = struct.unpack_from("<III", directory, pos + 64)
        if unknown != 0:
            raise ValueError(f"unsupported directory flag for {name}")
        entries.append((name, offset, size))
    return root_offset, directory, entries


def unpack_record(record: bytes):
    stored = struct.unpack_from("<I", record, 68)[0]
    unpacked = struct.unpack_from("<I", record, 88)[0]
    payload = record[96:96 + stored]
    if unpacked:
        raw = zlib.decompress(payload)
        if len(raw) != unpacked:
            raise ValueError("uncompressed size mismatch")
        return raw, True
    return payload, False


def build_record(original: bytes, raw: bytes, compressed: bool):
    header = bytearray(original[:96])
    if compressed:
        payload = zlib.compress(raw, 6)
        struct.pack_into("<I", header, 68, len(payload))
        struct.pack_into("<I", header, 88, len(raw))
    else:
        payload = raw
        struct.pack_into("<I", header, 68, len(payload))
        struct.pack_into("<I", header, 88, 0)
    return bytes(header) + payload


def patch_phrases(raw: bytes):
    changed = 0
    # Exact item phrases first. Mechanical stat normalization deliberately
    # runs last, otherwise it changes the source text that exact corrections
    # are supposed to match (e.g. "속도 +40" / "행운 +20").
    replacements = SAFE_ALL + ITEM_FIXES + EXTRA_ITEM_FIXES + MECHANICAL
    for old, new in replacements:
        if old == new:
            continue
        old_b = encoded(old)
        n = raw.count(old_b)
        if n:
            raw = raw.replace(old_b, encoded(new))
            changed += n
    return raw, changed


def patch_global_rows(raw: bytes):
    lines = raw.splitlines(keepends=True)
    changed = 0
    for i, line in enumerate(lines):
        newline = b"\r\n" if line.endswith(b"\r\n") else (b"\n" if line.endswith(b"\n") else b"")
        body = line[:-len(newline)] if newline else line
        id_b, sep, _value = body.partition(b"\t")
        if not sep or not id_b.isdigit():
            continue
        record_id = int(id_b)
        if record_id in GLOBAL_VALUES:
            wanted = id_b + b"\t" + encoded(GLOBAL_VALUES[record_id]) + newline
            if wanted != line:
                lines[i] = wanted
                changed += 1
    return b"".join(lines), changed


def patch_lod(source: Path, output: Path):
    archive = source.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    cursor = len(entries) * 76
    rebuilt = []
    report = {}

    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, compressed = unpack_record(record)
        raw2, n = patch_phrases(raw)
        if name.casefold() == "global.txt":
            raw2, ng = patch_global_rows(raw2)
            n += ng
        if n:
            record = build_record(record, raw2, compressed)
            report[name] = n
        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    result = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", result, 0x114, len(result) - root_offset)
    output.write_bytes(result)
    return report


def check_lod(path: Path):
    archive = path.read_bytes()
    root_offset, _directory, entries = archive_entries(archive)
    violations = []
    global_seen = {}
    for name, offset, size in entries:
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, _ = unpack_record(record)
        if name.casefold() == "global.txt":
            for line in raw.splitlines():
                key, sep, value = line.partition(b"\t")
                if sep and key.isdigit() and int(key) in GLOBAL_VALUES:
                    global_seen[int(key)] = value
        for text in STALE_CRITICAL:
            if encoded(text) in raw:
                violations.append(f"{name}: {text}")
    for record_id, value in GLOBAL_VALUES.items():
        if global_seen.get(record_id) != encoded(value):
            violations.append(f"Global.TXT[{record_id}] != {value}")
    if violations:
        raise SystemExit("report 65949 LOD validation failed:\n" + "\n".join(violations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check_lod(args.lod)
        print("report 65949 LOD: OK")
    else:
        if args.output is None:
            parser.error("--output is required")
        report = patch_lod(args.lod, args.output)
        check_lod(args.output)
        print(f"report 65949: patched {sum(report.values())} occurrences in {len(report)} LOD members")
        for name, count in sorted(report.items(), key=lambda x: x[0].casefold()):
            print(f"{name}: {count}")
