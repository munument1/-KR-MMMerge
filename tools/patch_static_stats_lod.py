#!/usr/bin/env python3
"""Patch Korean stats.txt tooltip descriptions inside the MM8 localization LOD.

Only the second column of stats.txt is replaced. The first column (stat name),
member order, compression state, and every other archive member are preserved.

The current Korean renderer handles EUC-KR/CP949 DBCS directly.  Store these
static tooltip strings as native bytes instead of the older SO/BEL/SI marker
format.  The marker bridge is kept only for legacy data; using it here roughly
doubles long rows such as Condition and Experience and needlessly routes stat
right-click help through that compatibility path.
"""

from __future__ import annotations

import argparse
import re
import struct
import zlib
from pathlib import Path

DBCS_RE = re.compile(br"[\xA1-\xAC\xB0-\xC8\xCA-\xFD][\xA0-\xFF](?!\x07)")
EXPECTED_ROWS = 26


def encode_dbcs_special(data: bytes) -> bytes:
    """Encode the historical marker format used by older static resources.

    Other migration tools still import this helper, so keep it available even
    though stats.txt itself is now written as native CP949.
    """
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


def load_translations(path: Path) -> list[str]:
    rows: dict[int, str] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line_no == 1 and line.startswith("Index\t"):
            continue
        index_text, separator, description = line.partition("\t")
        if not separator or not index_text.isdigit() or not description:
            raise ValueError(f"{path}:{line_no}: expected Index<TAB>Description")
        index = int(index_text)
        if index in rows:
            raise ValueError(f"{path}:{line_no}: duplicate index {index}")
        rows[index] = description
    expected = set(range(EXPECTED_ROWS))
    if set(rows) != expected:
        missing = sorted(expected - set(rows))
        extra = sorted(set(rows) - expected)
        raise ValueError(f"translation indices mismatch: missing={missing}, extra={extra}")
    return [rows[index] for index in range(EXPECTED_ROWS)]


def quote_field(text: str) -> str:
    return '"' + text.replace('"', '""') + '"'


def unquote_field(text: str) -> str:
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('""', '"')
    return text


def line_ending(line: bytes) -> bytes:
    if line.endswith(b"\r\n"):
        return b"\r\n"
    if line.endswith(b"\n"):
        return b"\n"
    if line.endswith(b"\r"):
        return b"\r"
    return b""


def stats_rows(raw: bytes) -> list[int]:
    lines = raw.splitlines(keepends=True)
    indices: list[int] = []
    for index, line in enumerate(lines):
        ending = line_ending(line)
        body = line[:-len(ending)] if ending else line
        if b"\t" not in body:
            continue
        first, _separator, _second = body.partition(b"\t")
        # First-column labels may still come from an older marker-encoded base
        # archive, so accept either representation while locating data rows.
        plain_first = decode_dbcs_special(first)
        try:
            label = plain_first.decode("cp949").strip()
        except UnicodeDecodeError:
            label = plain_first.decode("cp1252").strip()
        if label.casefold() == "stats descriptions" or label == "스탯 설명":
            continue
        indices.append(index)
    if len(indices) != EXPECTED_ROWS:
        raise ValueError(f"stats.txt has {len(indices)} data rows; expected {EXPECTED_ROWS}")
    return indices


def patch_stats_data(raw: bytes, translations: list[str]) -> bytes:
    lines = raw.splitlines(keepends=True)
    indices = stats_rows(raw)
    for row_number, line_index in enumerate(indices):
        line = lines[line_index]
        ending = line_ending(line)
        body = line[:-len(ending)] if ending else line
        first, separator, _second = body.partition(b"\t")
        if not separator:
            raise ValueError(f"stats.txt row {row_number} has no description column")

        # Native FNT_DBCS renders these high-byte pairs directly. Do not wrap
        # every Korean pair in the historical 0E/20/0E ... 07/0F markers.
        encoded = encode_mixed_text(quote_field(translations[row_number]))
        lines[line_index] = first + b"\t" + encoded + ending

    result = b"".join(lines)
    validate_stats_data(result, translations)
    return result


def validate_stats_data(raw: bytes, translations: list[str]) -> None:
    lines = raw.splitlines(keepends=True)
    indices = stats_rows(raw)
    for row_number, line_index in enumerate(indices):
        line = lines[line_index]
        ending = line_ending(line)
        body = line[:-len(ending)] if ending else line
        _first, separator, second = body.partition(b"\t")
        if not separator:
            raise ValueError(f"stats.txt row {row_number} has no description column")

        expected = translations[row_number]
        expected_bytes = encode_mixed_text(quote_field(expected))
        if second != expected_bytes:
            # Give an actionable error when content is semantically current but
            # the old marker transport has crept back into the archive.
            legacy_plain = decode_dbcs_special(second)
            try:
                legacy_actual = unquote_field(legacy_plain.decode("cp949"))
            except UnicodeDecodeError:
                legacy_actual = None
            if legacy_actual == expected:
                raise ValueError(
                    f"stats.txt row {row_number} still uses legacy DBCS marker encoding; "
                    "native CP949 is required"
                )
            raise ValueError(
                f"stats.txt row {row_number} byte/content mismatch for native CP949 storage"
            )


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


def extract_stats_raw(archive: bytes) -> bytes:
    root_offset, _directory, entries = archive_entries(archive)
    for name, offset, size in entries:
        if name.casefold() != "stats.txt":
            continue
        absolute = root_offset + offset
        record = archive[absolute:absolute + size]
        if len(record) != size:
            raise ValueError("stats.txt member is truncated")
        raw, _compressed = read_member_payload(record)
        return raw
    raise ValueError("stats.txt was not found in the LOD archive")


def patch_lod(lod_path: Path, translations: list[str], output_path: Path) -> None:
    archive = lod_path.read_bytes()
    root_offset, directory, entries = archive_entries(archive)
    directory_end = root_offset + len(entries) * 76
    rebuilt_members: list[bytes] = []
    cursor = directory_end - root_offset
    found = False

    for index, (name, offset, size) in enumerate(entries):
        absolute = root_offset + offset
        record = archive[absolute:absolute + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        if name.casefold() == "stats.txt":
            raw, compressed = read_member_payload(record)
            patched_raw = patch_stats_data(raw, translations)
            record = build_member_record(record, patched_raw, compressed)
            found = True

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt_members.append(record)
        cursor += len(record)

    if not found:
        raise ValueError("stats.txt was not found in the LOD archive")

    prefix = bytearray(archive[:root_offset])
    output = prefix + directory + b"".join(rebuilt_members)
    struct.pack_into("<I", output, 0x114, len(output) - root_offset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)


def check_lod(lod_path: Path, translations: list[str]) -> None:
    raw = extract_stats_raw(lod_path.read_bytes())
    validate_stats_data(raw, translations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    translations = load_translations(args.translations)
    if args.check:
        check_lod(args.lod, translations)
        print(f"stats.txt: {EXPECTED_ROWS} native-CP949 Korean tooltip descriptions verified")
        return
    if args.output is None:
        parser.error("--output is required unless --check is used")
    patch_lod(args.lod, translations, args.output)
    check_lod(args.output, translations)
    print(f"Patched and verified {EXPECTED_ROWS} native-CP949 stats.txt tooltip descriptions in {args.output}")


if __name__ == "__main__":
    main()
