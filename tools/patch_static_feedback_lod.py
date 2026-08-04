#!/usr/bin/env python3
"""Patch v1.0.13a feedback fixes into the existing Korean localization LOD.

Only two members are rewritten:
- Trans.txt row-order entry 260 (Castle Ironfist transition text)
- 6T1.STR exact Temple of Baa map strings listed in KO_MapStrings.txt

All other LOD members are preserved byte-for-byte.
"""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from build_static_localization import (
    TsvDocument,
    apply_by_order,
    decode_field,
    encode_dbcs_special,
    encode_mixed_text,
    parse_overlay,
)
from patch_static_spells_lod import build_member_record, read_member_payload
from patch_static_spell_references_lod import decode_lod_text, encode_lod_text

TARGET_TRANS_INDEX = 260
TARGET_MAP = "6t1.str"


def parse_map_overlays(path: Path) -> dict[str, dict[int, str]]:
    result: dict[str, dict[int, str]] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#") or line.startswith("MapFile\t"):
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3 or not parts[1].strip().isdigit():
            raise ValueError(f"{path}:{line_no}: malformed map overlay row")
        result.setdefault(parts[0].strip().casefold(), {})[int(parts[1].strip())] = parts[2]
    return result


def patch_trans(raw: bytes, overlay_path: Path) -> tuple[bytes, int]:
    overlay = parse_overlay(overlay_path)
    key = (TARGET_TRANS_INDEX, "")
    if key not in overlay:
        raise ValueError(f"{overlay_path}: missing row-order entry {TARGET_TRANS_INDEX}")
    doc = TsvDocument(decode_lod_text(raw))
    eligible = lambda row, index: bool(
        row.fields and decode_field(row.fields[0]).strip().isdigit()
    )
    changed = apply_by_order(doc, {key: overlay[key]}, 1, eligible)
    return encode_lod_text(doc.render()), changed


def patch_compiled_str(raw: bytes, replacements: dict[int, str]) -> tuple[bytes, int]:
    fields = raw.split(b"\0")
    changed = 0
    for index, text in sorted(replacements.items()):
        if index < 0 or index >= len(fields):
            raise ValueError(f"compiled STR is missing evt.str[{index}]")
        encoded = encode_dbcs_special(encode_mixed_text(text))
        if fields[index] != encoded:
            fields[index] = encoded
            changed += 1
    return b"\0".join(fields), changed


def patch_lod(
    lod_path: Path,
    trans_overlay_path: Path,
    map_overlay_path: Path,
    output_path: Path,
) -> dict[str, int]:
    archive = lod_path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{lod_path}: invalid LOD signature")
    root_offset, _root_size, root_flags, count = struct.unpack_from("<IIII", archive, 0x110)
    if root_flags != 0:
        raise ValueError("unsupported non-zero root flags")
    directory_end = root_offset + count * 76
    directory = bytearray(archive[root_offset:directory_end])

    entries: list[tuple[str, int, int]] = []
    for index in range(count):
        pos = index * 76
        name = directory[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, flags = struct.unpack_from("<III", directory, pos + 64)
        if flags != 0:
            raise ValueError(f"unsupported non-zero flags for {name}")
        entries.append((name, offset, size))

    map_overlays = parse_map_overlays(map_overlay_path)
    replacements = map_overlays.get(TARGET_MAP)
    if not replacements:
        raise ValueError(f"{map_overlay_path}: no {TARGET_MAP} overlays")

    reports: dict[str, int] = {}
    rebuilt: list[bytes] = []
    cursor = directory_end - root_offset
    found_trans = False
    found_map = False

    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        folded = name.casefold()
        if folded == "trans.txt":
            raw, compressed = read_member_payload(record)
            patched, changed = patch_trans(raw, trans_overlay_path)
            record = build_member_record(record, patched, compressed)
            reports[name] = changed
            found_trans = True
        elif folded == TARGET_MAP:
            raw, compressed = read_member_payload(record)
            patched, changed = patch_compiled_str(raw, replacements)
            record = build_member_record(record, patched, compressed)
            reports[name] = changed
            found_map = True

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    if not found_trans:
        raise ValueError("Trans.txt is missing from the LOD")
    if not found_map:
        raise ValueError("6T1.STR is missing from the LOD")

    output = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", output, 0x114, len(output) - root_offset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--trans-overlay", type=Path, required=True)
    parser.add_argument("--map-overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = patch_lod(args.lod, args.trans_overlay, args.map_overlay, args.output)
    for name, count in reports.items():
        print(f"{name}: patched {count} entries")


if __name__ == "__main__":
    main()
