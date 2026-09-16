#!/usr/bin/env python3
"""Migrate translated map STR entries in the Korean localization LOD to native CP949.

Older Korean packages wrapped each DBCS character in a legacy SO/BEL/SI marker
sequence. That transport expands long event strings enough to hit the engine's
~1 KiB event-text guard (for example PYRAMID.STR in the Tomb of VARN).

The current FNT_DBCS renderer handles native CP949/DBCS directly, so translated
map STR entries should be stored marker-free. This tool rewrites every entry
listed in KO_MapStrings.txt, preserves all unlisted STR lines and all other LOD
members, and can audit the source for event-text length regressions.
"""

from __future__ import annotations

import argparse
import re
import struct
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

MAX_EVENT_TEXT_PAYLOAD = 1023
DBCS_RE = re.compile(br"[\xA1-\xAC\xB0-\xC8\xCA-\xFD][\xA0-\xFF](?!\x07)")


def encode_dbcs_special(data: bytes) -> bytes:
    """Encode the historical marker format, used only for migration diagnostics."""
    data = DBCS_RE.sub(lambda match: b"\x0e\x20\x0e" + match.group(0) + b"\x07\x0f", data)
    return data.replace(b"\x0f\x0e", b"")


def decode_dbcs_special(data: bytes) -> bytes:
    data = re.sub(br"\x20\x0e(..)\x07", lambda match: match.group(1), data)
    return re.sub(br"\x0e([^\x0f]+)\x0f", lambda match: match.group(1), data)


def encode_mixed_text(text: str) -> bytes:
    """Encode Korean as CP949 while preserving CP1252 punctuation/glyph bytes."""
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
                "cp949/cp1252",
                text,
                index,
                index + 1,
                f"character {char!r} is unavailable in both target encodings",
            ) from error
    return bytes(output)


@dataclass(frozen=True)
class Translation:
    map_file: str
    string_id: int
    text: str

    @property
    def native(self) -> bytes:
        return encode_mixed_text(self.text)

    @property
    def legacy(self) -> bytes:
        return encode_dbcs_special(self.native)


def load_translations(path: Path) -> list[Translation]:
    rows: list[Translation] = []
    seen: set[tuple[str, int]] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#") or line.startswith("MapFile\t"):
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3 or not parts[1].strip().isdigit():
            raise ValueError(f"{path}:{line_no}: expected MapFile<TAB>StringId<TAB>Text")
        map_file = parts[0].strip()
        string_id = int(parts[1].strip())
        text = parts[2]
        if not map_file or not text:
            raise ValueError(f"{path}:{line_no}: map file and text must be non-empty")
        key = (map_file.casefold(), string_id)
        if key in seen:
            raise ValueError(f"{path}:{line_no}: duplicate {map_file} evt.str[{string_id}]")
        seen.add(key)
        rows.append(Translation(map_file, string_id, text))
    if not rows:
        raise ValueError(f"{path}: no map string translations found")
    return rows


def audit_translations(translations: list[Translation]) -> tuple[int, int]:
    native_oversize = [t for t in translations if len(t.native) > MAX_EVENT_TEXT_PAYLOAD]
    legacy_oversize = [t for t in translations if len(t.legacy) > MAX_EVENT_TEXT_PAYLOAD]
    if native_oversize:
        details = ", ".join(
            f"{t.map_file}[{t.string_id}]={len(t.native)}" for t in native_oversize[:10]
        )
        raise ValueError(
            f"{len(native_oversize)} native map event strings exceed "
            f"{MAX_EVENT_TEXT_PAYLOAD} bytes: {details}"
        )
    return len(translations), len(legacy_oversize)


def line_ending(line: bytes) -> bytes:
    if line.endswith(b"\r\n"):
        return b"\r\n"
    if line.endswith(b"\n"):
        return b"\n"
    if line.endswith(b"\r"):
        return b"\r"
    return b""


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


def grouped_translations(translations: list[Translation]) -> dict[str, list[Translation]]:
    grouped: dict[str, list[Translation]] = defaultdict(list)
    for row in translations:
        grouped[row.map_file.casefold()].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: row.string_id)
    return dict(grouped)


def patch_str_data(raw: bytes, rows: list[Translation], name: str) -> bytes:
    lines = raw.splitlines(keepends=True)
    for row in rows:
        if row.string_id < 0 or row.string_id >= len(lines):
            raise ValueError(f"{name}: missing evt.str[{row.string_id}]")
        current = lines[row.string_id]
        ending = line_ending(current)
        lines[row.string_id] = row.native + ending
    result = b"".join(lines)
    validate_str_data(result, rows, name)
    return result


def validate_str_data(raw: bytes, rows: list[Translation], name: str) -> None:
    lines = raw.splitlines(keepends=True)
    for row in rows:
        if row.string_id < 0 or row.string_id >= len(lines):
            raise ValueError(f"{name}: missing evt.str[{row.string_id}]")
        current = lines[row.string_id]
        ending = line_ending(current)
        body = current[:-len(ending)] if ending else current
        expected = row.native
        if body != expected:
            legacy_plain = decode_dbcs_special(body)
            if legacy_plain == expected:
                raise ValueError(
                    f"{name} evt.str[{row.string_id}] still uses legacy DBCS marker encoding; "
                    "native CP949 is required"
                )
            raise ValueError(f"{name} evt.str[{row.string_id}] byte/content mismatch")
        if len(body) > MAX_EVENT_TEXT_PAYLOAD:
            raise ValueError(
                f"{name} evt.str[{row.string_id}] is {len(body)} bytes; "
                f"maximum safe payload is {MAX_EVENT_TEXT_PAYLOAD}"
            )


def patch_lod(lod_path: Path, translations: list[Translation], output_path: Path) -> tuple[int, int]:
    archive = lod_path.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    directory_end = root_offset + len(entries) * 76
    grouped = grouped_translations(translations)
    found: set[str] = set()
    patched_strings = 0
    rebuilt_members: list[bytes] = []
    cursor = directory_end - root_offset

    for index, (name, offset, size) in enumerate(entries):
        absolute = root_offset + offset
        record = archive[absolute:absolute + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        key = name.casefold()
        rows = grouped.get(key)
        if rows:
            raw, compressed = read_member_payload(record)
            record = build_member_record(record, patch_str_data(raw, rows, name), compressed)
            found.add(key)
            patched_strings += len(rows)

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt_members.append(record)
        cursor += len(record)

    missing = sorted(set(grouped) - found)
    if missing:
        raise ValueError(f"map STR members missing from LOD: {', '.join(missing)}")

    prefix = bytearray(archive[:root_offset])
    output = prefix + directory + b"".join(rebuilt_members)
    struct.pack_into("<I", output, 0x114, len(output) - root_offset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return len(found), patched_strings


def check_lod(lod_path: Path, translations: list[Translation]) -> tuple[int, int]:
    archive = lod_path.read_bytes()
    root_offset, _directory, entries = archive_entries(archive)
    grouped = grouped_translations(translations)
    found: set[str] = set()
    verified = 0
    for name, offset, size in entries:
        rows = grouped.get(name.casefold())
        if not rows:
            continue
        absolute = root_offset + offset
        record = archive[absolute:absolute + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        raw, _compressed = read_member_payload(record)
        validate_str_data(raw, rows, name)
        found.add(name.casefold())
        verified += len(rows)
    missing = sorted(set(grouped) - found)
    if missing:
        raise ValueError(f"map STR members missing from LOD: {', '.join(missing)}")
    return len(found), verified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--lod", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()

    translations = load_translations(args.translations)
    count, legacy_oversize = audit_translations(translations)
    print(
        f"Map STR source audit: {count} translations; native payloads <= "
        f"{MAX_EVENT_TEXT_PAYLOAD} bytes; {legacy_oversize} would exceed the limit "
        "under legacy marker encoding"
    )

    if args.audit and args.lod is None:
        return
    if args.lod is None:
        parser.error("--lod is required unless --audit is used by itself")
    if args.check:
        files, strings = check_lod(args.lod, translations)
        print(f"Verified {strings} native-CP949 map strings across {files} STR members")
        return
    if args.output is None:
        parser.error("--output is required unless --check is used")
    files, strings = patch_lod(args.lod, translations, args.output)
    check_lod(args.output, translations)
    print(f"Patched and verified {strings} native-CP949 map strings across {files} STR members")


if __name__ == "__main__":
    main()
