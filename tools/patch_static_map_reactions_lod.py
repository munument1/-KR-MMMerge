#!/usr/bin/env python3
"""Patch all reviewed user-visible map reaction/status strings into LocKO.T.lod.

The overlay is keyed by exact map member name and zero-based evt.str index.
Only STR members listed in KO_MapStrings.txt are rebuilt; every other member is
preserved byte-for-byte.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from build_static_localization import encode_dbcs_special, encode_mixed_text
from patch_static_spells_lod import build_member_record, read_member_payload


def parse_map_overlays(path: Path) -> dict[str, dict[int, str]]:
    result: dict[str, dict[int, str]] = {}
    seen: set[tuple[str, int]] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#") or line.startswith("MapFile\t"):
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3 or not parts[1].strip().isdigit():
            raise ValueError(f"{path}:{line_no}: malformed map overlay row")
        name = parts[0].strip()
        index = int(parts[1].strip())
        key = (name.casefold(), index)
        if key in seen:
            raise ValueError(f"{path}:{line_no}: duplicate overlay for {name}[{index}]")
        seen.add(key)
        result.setdefault(name.casefold(), {})[index] = parts[2]
    if not result:
        raise ValueError(f"{path}: no map overlays found")
    return result


def patch_compiled_str(raw: bytes, replacements: dict[int, str]) -> tuple[bytes, int]:
    fields = raw.split(b"\0")
    changed = 0
    for index, text in sorted(replacements.items()):
        if index < 0 or index >= len(fields):
            raise ValueError(f"compiled STR is missing evt.str[{index}]")
        plain = encode_mixed_text(text)
        encoded = encode_dbcs_special(plain)
        if fields[index] != encoded:
            fields[index] = encoded
            changed += 1
    return b"\0".join(fields), changed


def patch_lod(lod_path: Path, overlay_path: Path, output_path: Path) -> dict[str, int]:
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

    overlays = parse_map_overlays(overlay_path)
    found: set[str] = set()
    reports: dict[str, int] = {}
    rebuilt: list[bytes] = []
    cursor = directory_end - root_offset

    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        folded = name.casefold()
        if folded in overlays:
            raw, compressed = read_member_payload(record)
            patched, changed = patch_compiled_str(raw, overlays[folded])
            record = build_member_record(record, patched, compressed)
            reports[name] = changed
            found.add(folded)

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    missing = sorted(set(overlays) - found)
    if missing:
        raise ValueError(f"LOD is missing overlay members: {', '.join(missing)}")

    output = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", output, 0x114, len(output) - root_offset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = patch_lod(args.lod, args.overlay, args.output)
    print(f"Patched {len(reports)} STR members.")
    print(f"Changed {sum(reports.values())} map-string entries.")
    for name, count in sorted(reports.items(), key=lambda item: item[0].casefold()):
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
