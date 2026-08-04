#!/usr/bin/env python3
"""Validate the v1.0.13b reviewed map reaction/status translation pass."""

from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

from patch_static_global_lod import read_member_payload
from patch_static_spells_lod import decode_dbcs_special

EXPECTED_AUDIT_ROWS = 658
EXPECTED_OVERLAY_ROWS = 852
EXPECTED_INTERNAL = {
    ("outd2.str", 3): "Place Holder for Prince of Thieves.  Paul needs to provide this.",
}
EXPECTED_ANSWER_KEYS = {
    ("6d08.str", 19): "dark",
    ("6d08.str", 20): "darkness",
    ("6d08.str", 24): "arrow",
    ("6d08.str", 25): "an arrow",
    ("6d08.str", 27): "time",
    ("6d08.str", 29): "fish",
    ("6d08.str", 30): "a fish",
    ("cd1.str", 15): "JBARD",
    ("cd1.str", 16): "jbard",
    ("pyramid.str", 33): "kcopS",
    ("pyramid.str", 35): "uluS",
    ("pyramid.str", 37): "aruhU",
    ("pyramid.str", 39): "yttocS",
    ("pyramid.str", 41): "yoccM",
    ("pyramid.str", 43): "kriK",
}


def parse_audit(path: Path) -> dict[tuple[str, int], tuple[str, str]]:
    result: dict[tuple[str, int], tuple[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["MapFile", "StringId", "English", "Korean"]:
            raise ValueError(f"{path}: unexpected columns {reader.fieldnames!r}")
        for line_no, row in enumerate(reader, 2):
            if not row["StringId"].isdigit() or not row["Korean"]:
                raise ValueError(f"{path}:{line_no}: malformed translation row")
            key = (row["MapFile"].casefold(), int(row["StringId"]))
            if key in result:
                raise ValueError(f"{path}:{line_no}: duplicate key {key}")
            row["Korean"].encode("cp949")
            result[key] = (row["English"], row["Korean"])
    return result


def parse_overlay(path: Path) -> dict[tuple[str, int], str]:
    result: dict[tuple[str, int], str] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#") or line.startswith("MapFile\t"):
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3 or not parts[1].strip().isdigit():
            raise ValueError(f"{path}:{line_no}: malformed overlay row")
        key = (parts[0].strip().casefold(), int(parts[1].strip()))
        if key in result:
            raise ValueError(f"{path}:{line_no}: duplicate overlay key {key}")
        parts[2].encode("cp949")
        result[key] = parts[2]
    return result


def lod_members(path: Path) -> dict[str, bytes]:
    archive = path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{path}: invalid LOD signature")
    root, root_size, flags, count = struct.unpack_from("<IIII", archive, 0x110)
    if flags != 0 or root + root_size != len(archive):
        raise ValueError(f"{path}: invalid LOD root metadata")
    result: dict[str, bytes] = {}
    expected_offset = count * 76
    for index in range(count):
        pos = root + index * 76
        name = archive[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, member_flags = struct.unpack_from("<III", archive, pos + 64)
        if member_flags != 0 or offset != expected_offset:
            raise ValueError(f"{path}: invalid directory entry for {name}")
        record = archive[root + offset:root + offset + size]
        if len(record) != size:
            raise ValueError(f"{path}: truncated member {name}")
        raw, _compressed = read_member_payload(record)
        result[name.casefold()] = raw
        expected_offset += size
    if expected_offset != root_size:
        raise ValueError(f"{path}: member sizes do not match root size")
    return result


def decode_str_field(members: dict[str, bytes], map_name: str, index: int) -> str:
    raw = members.get(map_name.casefold())
    if raw is None:
        raise KeyError(f"LOD member {map_name} is missing")
    fields = raw.split(b"\0")
    if index < 0 or index >= len(fields):
        raise IndexError(f"{map_name}: missing evt.str[{index}]")
    return decode_dbcs_special(fields[index]).decode("cp949", errors="strict")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        audit = parse_audit(root / "tools/MAP_REACTION_TRANSLATIONS.tsv")
        overlay = parse_overlay(root / "Data/Text localization/KO_MapStrings.txt")
        members = lod_members(root / "Data/zz LocKO.T.lod")
    except Exception as exc:
        return [str(exc)]

    if len(audit) != EXPECTED_AUDIT_ROWS:
        errors.append(f"translation audit has {len(audit)} rows; expected {EXPECTED_AUDIT_ROWS}")
    if len(overlay) != EXPECTED_OVERLAY_ROWS:
        errors.append(f"map overlay has {len(overlay)} rows; expected {EXPECTED_OVERLAY_ROWS}")

    for key, (english, korean) in audit.items():
        if overlay.get(key) != korean:
            errors.append(f"overlay {key} does not match the reviewed Korean translation")
            continue
        try:
            actual = decode_str_field(members, key[0], key[1])
        except Exception as exc:
            errors.append(str(exc))
            continue
        if actual != korean:
            errors.append(f"LOD {key[0]}[{key[1]}] = {actual!r}; expected {korean!r}")
        if actual == english:
            errors.append(f"LOD {key[0]}[{key[1]}] still contains the English source")

    # All legacy map overlays, including the v1.0.13a Temple of Baa fixes,
    # must also agree with the static archive.
    for key, expected in overlay.items():
        try:
            actual = decode_str_field(members, key[0], key[1])
        except Exception as exc:
            errors.append(str(exc))
            continue
        if actual != expected:
            errors.append(f"LOD {key[0]}[{key[1]}] does not match KO_MapStrings.txt")

    for key, expected in {**EXPECTED_INTERNAL, **EXPECTED_ANSWER_KEYS}.items():
        try:
            actual = decode_str_field(members, key[0], key[1])
        except Exception as exc:
            errors.append(str(exc))
            continue
        if actual != expected:
            errors.append(f"protected map key {key} changed to {actual!r}; expected {expected!r}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Map reaction/status translation validation passed.")
    print("Checked 658 reviewed translations, 852 total overlays, internal placeholders, and puzzle answer keys.")


if __name__ == "__main__":
    main()
