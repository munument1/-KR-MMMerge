#!/usr/bin/env python3
"""Synchronize Global.TXT inside a MM8 localization LOD with KO_GlobalTxt.txt.

The static localization archive stores each member as a 96-byte record header
followed by raw or zlib-compressed data. Directory offsets are relative to the
root directory offset. This tool rewrites only Global.TXT and preserves every
other archive member byte-for-byte.
"""

from __future__ import annotations

import argparse
import re
import struct
import zlib
from pathlib import Path

DBCS_RE = re.compile(br"[\xA1-\xAC\xB0-\xC8\xCA-\xFD][\xA0-\xFF](?!\x07)")


def encode_dbcs_special(data: bytes) -> bytes:
    data = DBCS_RE.sub(lambda match: b"\x0e\x20\x0e" + match.group(0) + b"\x07\x0f", data)
    return data.replace(b"\x0f\x0e", b"")


def decode_dbcs_special(data: bytes) -> bytes:
    data = re.sub(br"\x20\x0e(..)\x07", lambda match: match.group(1), data)
    return re.sub(br"\x0e([^\x0f]+)\x0f", lambda match: match.group(1), data)


def encode_mixed_text(text: str) -> bytes:
    output = bytearray()
    for index, char in enumerate(text):
        try:
            output.extend(char.encode("cp1252"))
            continue
        except UnicodeEncodeError:
            pass
        try:
            output.extend(char.encode("cp949"))
        except UnicodeEncodeError as error:
            raise UnicodeEncodeError(
                "cp949/cp1252", text, index, index + 1,
                f"character {char!r} is unavailable in both target encodings",
            ) from error
    return bytes(output)


def parse_overlay(path: Path) -> dict[int, str]:
    records: dict[int, str] = {}
    for line_no, line in enumerate(path.read_bytes().decode("cp949").splitlines(), 1):
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            records[int(parts[1].strip())] = parts[3]
        elif line_no != 1 and line.strip():
            raise ValueError(f"{path}:{line_no}: malformed GlobalTxt overlay row")
    return records


def patch_global_data(raw: bytes, overlay: dict[int, str]) -> tuple[bytes, int]:
    lines = raw.splitlines(keepends=True)
    changed = 0
    seen: set[int] = set()
    for index, line in enumerate(lines):
        newline = b"\r\n" if line.endswith(b"\r\n") else (b"\n" if line.endswith(b"\n") else b"")
        body = line[:-len(newline)] if newline else line
        id_text, separator, _value = body.partition(b"\t")
        if not separator or not id_text.isdigit():
            continue
        record_id = int(id_text)
        if record_id not in overlay:
            continue
        encoded = encode_dbcs_special(encode_mixed_text(overlay[record_id]))
        lines[index] = id_text + b"\t" + encoded + newline
        changed += 1
        seen.add(record_id)
    missing = sorted(set(overlay) - seen)
    if missing:
        raise ValueError(f"Global.TXT is missing overlay IDs: {missing[:20]}")
    result = b"".join(lines)
    if decode_dbcs_special(result) == b"":
        raise ValueError("Global.TXT unexpectedly became empty")
    return result, changed


def read_member_payload(record: bytes) -> tuple[bytes, bool]:
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
            raise ValueError("LOD member uncompressed size does not match its header")
        return raw, True
    return payload, False


def build_member_record(original: bytes, raw: bytes, compressed: bool) -> bytes:
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


def patch_lod(lod_path: Path, overlay_path: Path, output_path: Path) -> int:
    archive = lod_path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{lod_path} is not a LOD archive")
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

    overlay = parse_overlay(overlay_path)
    rebuilt_members: list[bytes] = []
    changed = 0
    cursor = directory_end - root_offset
    found = False

    for index, (name, offset, size) in enumerate(entries):
        absolute = root_offset + offset
        record = archive[absolute:absolute + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        if name.casefold() == "global.txt":
            raw, compressed = read_member_payload(record)
            patched_raw, changed = patch_global_data(raw, overlay)
            record = build_member_record(record, patched_raw, compressed)
            found = True

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt_members.append(record)
        cursor += len(record)

    if not found:
        raise ValueError("Global.TXT was not found in the LOD archive")

    prefix = bytearray(archive[:root_offset])
    output = prefix + directory + b"".join(rebuilt_members)
    struct.pack_into("<I", output, 0x114, len(output) - root_offset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    changed = patch_lod(args.lod, args.overlay, args.output)
    print(f"Patched {changed} Global.TXT rows in {args.output}")


if __name__ == "__main__":
    main()
