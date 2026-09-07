#!/usr/bin/env python3
"""Patch player-reported Korean terminology directly inside LocKO.T.lod.

The archive already contains DBCS-special encoded Korean.  Replace only exact
encoded byte sequences, preserving every unrelated byte, member order, and the
original compression state.
"""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

from patch_static_stats_lod import encode_dbcs_special

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


def encoded(text: str) -> bytes:
    return encode_dbcs_special(text.encode("cp949"))


def archive_entries(archive: bytes) -> tuple[int, bytearray, list[tuple[str, int, int]]]:
    if archive[:4] != b"LOD\0":
        raise ValueError("not a LOD archive")
    root_offset, _root_size, _unknown, count = struct.unpack_from("<IIII", archive, 0x110)
    directory_end = root_offset + count * 76
    if directory_end > len(archive):
        raise ValueError("LOD directory extends beyond the archive")
    directory = bytearray(archive[root_offset:directory_end])
    entries: list[tuple[str, int, int]] = []
    for index in range(count):
        pos = index * 76
        name = directory[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, unknown = struct.unpack_from("<III", directory, pos + 64)
        if unknown != 0:
            raise ValueError(f"unsupported non-zero directory flag for {name}")
        entries.append((name, offset, size))
    return root_offset, directory, entries


def unpack_record(record: bytes) -> tuple[bytes, bool]:
    if len(record) < 96:
        raise ValueError("LOD member record is shorter than 96 bytes")
    stored_size = struct.unpack_from("<I", record, 68)[0]
    unpacked_size = struct.unpack_from("<I", record, 88)[0]
    payload = record[96:96 + stored_size]
    if len(payload) != stored_size:
        raise ValueError("LOD member payload is truncated")
    if unpacked_size:
        raw = zlib.decompress(payload)
        if len(raw) != unpacked_size:
            raise ValueError("LOD member uncompressed size mismatch")
        return raw, True
    return payload, False


def build_record(original: bytes, raw: bytes, compressed: bool) -> bytes:
    header = bytearray(original[:96])
    if compressed:
        payload = zlib.compress(raw, level=6)
        struct.pack_into("<I", header, 68, len(payload))
        struct.pack_into("<I", header, 88, len(raw))
    else:
        payload = raw
        struct.pack_into("<I", header, 68, len(payload))
        struct.pack_into("<I", header, 88, 0)
    return bytes(header) + payload


def patch_payload(raw: bytes) -> tuple[bytes, int]:
    count = 0
    for old, new in REPLACEMENTS:
        old_bytes = encoded(old)
        occurrences = raw.count(old_bytes)
        if occurrences:
            raw = raw.replace(old_bytes, encoded(new))
            count += occurrences
    return raw, count


def patch_lod(source: Path, output: Path) -> tuple[int, dict[str, int]]:
    archive = source.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    directory_end = root_offset + len(entries) * 76
    cursor = directory_end - root_offset
    rebuilt: list[bytes] = []
    reports: dict[str, int] = {}

    for index, (name, offset, size) in enumerate(entries):
        absolute = root_offset + offset
        record = archive[absolute:absolute + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        raw, compressed = unpack_record(record)
        patched, count = patch_payload(raw)
        if count:
            record = build_record(record, patched, compressed)
            reports[name] = count

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    result = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", result, 0x114, len(result) - root_offset)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    return sum(reports.values()), reports


def check_lod(path: Path) -> None:
    archive = path.read_bytes()
    root_offset, _directory, entries = archive_entries(archive)
    violations: list[str] = []
    for name, offset, size in entries:
        record = archive[root_offset + offset:root_offset + offset + size]
        raw, _compressed = unpack_record(record)
        for old, _new in REPLACEMENTS:
            if encoded(old) in raw:
                violations.append(f"{name}: {old}")
    if violations:
        raise SystemExit("stale reported terms remain in LOD:\n" + "\n".join(violations))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        check_lod(args.lod)
        print("reported terminology in LOD: OK")
        return
    if args.output is None:
        parser.error("--output is required unless --check is used")

    count, reports = patch_lod(args.lod, args.output)
    check_lod(args.output)
    print(f"patched {count} reported-term occurrences in {len(reports)} LOD members")
    for name, member_count in sorted(reports.items(), key=lambda item: item[0].casefold()):
        print(f"{name}: {member_count}")


if __name__ == "__main__":
    main()
