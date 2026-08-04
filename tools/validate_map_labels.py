#!/usr/bin/env python3
"""Validate the v1.0.13c map-label and object-name terminology pass."""

from __future__ import annotations

import argparse
import csv
import re
import struct
from pathlib import Path

from patch_static_global_lod import read_member_payload
from patch_static_spells_lod import decode_dbcs_special

EXPECTED_LABEL_ROWS = 181
EXPECTED_PROTECTED_ROWS = 76
EXPECTED_OVERLAY_ROWS = 852


def parse_table(path: Path, columns: list[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != columns:
            raise ValueError(f"{path}: unexpected columns {reader.fieldnames!r}")
        rows = list(reader)
    return rows


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
        raw, _compressed = read_member_payload(record)
        result[name.casefold()] = raw
        expected_offset += size
    if expected_offset != root_size:
        raise ValueError(f"{path}: member sizes do not match root size")
    return result


def decode_field(members: dict[str, bytes], map_name: str, index: int) -> str:
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
        labels = parse_table(
            root / "tools/MAP_LABEL_TRANSLATIONS.tsv",
            ["MapFile", "StringId", "English", "Korean"],
        )
        protected = parse_table(
            root / "tools/MAP_LABEL_PROTECTED.tsv",
            ["MapFile", "StringId", "English"],
        )
        overlay = parse_overlay(root / "Data/Text localization/KO_MapStrings.txt")
        members = lod_members(root / "Data/zz LocKO.T.lod")
    except Exception as exc:
        return [str(exc)]

    if len(labels) != EXPECTED_LABEL_ROWS:
        errors.append(f"label audit has {len(labels)} rows; expected {EXPECTED_LABEL_ROWS}")
    if len(protected) != EXPECTED_PROTECTED_ROWS:
        errors.append(f"protected audit has {len(protected)} rows; expected {EXPECTED_PROTECTED_ROWS}")
    if len(overlay) != EXPECTED_OVERLAY_ROWS:
        errors.append(f"map overlay has {len(overlay)} rows; expected {EXPECTED_OVERLAY_ROWS}")

    seen: set[tuple[str, int]] = set()
    for row in labels:
        if not row["StringId"].isdigit() or not row["Korean"]:
            errors.append(f"malformed label row: {row!r}")
            continue
        key = (row["MapFile"].casefold(), int(row["StringId"]))
        if key in seen:
            errors.append(f"duplicate label row {key}")
            continue
        seen.add(key)
        try:
            row["Korean"].encode("cp949")
            actual = decode_field(members, row["MapFile"], int(row["StringId"]))
        except Exception as exc:
            errors.append(str(exc))
            continue
        if overlay.get(key) != row["Korean"]:
            errors.append(f"overlay {key} does not match label audit")
        if actual != row["Korean"]:
            errors.append(f"LOD {key} = {actual!r}; expected {row['Korean']!r}")
        if actual == row["English"]:
            errors.append(f"LOD {key} still contains English source {actual!r}")

    protected_seen: set[tuple[str, int]] = set()
    for row in protected:
        if not row["StringId"].isdigit():
            errors.append(f"malformed protected row: {row!r}")
            continue
        key = (row["MapFile"].casefold(), int(row["StringId"]))
        if key in protected_seen:
            errors.append(f"duplicate protected row {key}")
            continue
        protected_seen.add(key)
        try:
            actual = decode_field(members, row["MapFile"], int(row["StringId"]))
        except Exception as exc:
            errors.append(str(exc))
            continue
        if actual != row["English"]:
            errors.append(f"protected field {key} changed to {actual!r}; expected {row['English']!r}")

    # After this pass, every English-only STR field must be one of the reviewed
    # protected keys. Korean strings may still contain proper ASCII acronyms.
    remaining: set[tuple[str, int]] = set()
    for name, raw in members.items():
        if not name.endswith(".str"):
            continue
        for index, field in enumerate(raw.split(b"\0")):
            try:
                text = decode_dbcs_special(field).decode("cp949", errors="strict")
            except Exception:
                continue
            if re.search(r"[A-Za-z]", text) and not re.search(r"[가-힣]", text):
                remaining.add((name, index))
    if remaining != protected_seen:
        for key in sorted(remaining - protected_seen):
            errors.append(f"unreviewed English-only STR field remains: {key}")
        for key in sorted(protected_seen - remaining):
            errors.append(f"protected field no longer appears English-only: {key}")

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
    print("Map label/object terminology validation passed.")
    print("Checked 181 translated labels, 76 protected fields, 852 overlays, and all compiled STR members.")


if __name__ == "__main__":
    main()
