#!/usr/bin/env python3
"""Synchronize spell-reference tables in the Korean static localization LOD.

The v1.0.13 terminology pass changes spell names not only in Spells.txt, but in
notes, quests, NPC text, scroll messages and item bonus tables. This tool uses
the already-tested localized LOD as its structural skeleton and rewrites only
the localized display fields owned by those KO_*.txt overlays.
"""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from build_static_localization import (
    TsvDocument,
    apply_by_order,
    apply_direct,
    decode_field,
    encode_dbcs_special,
    encode_mixed_text,
    parse_overlay,
)
from patch_static_spells_lod import build_member_record, read_member_payload

DBCS_GROUP_RE = re.compile(br"\x0e((?:\x20\x0e..\x07)+)\x0f", re.S)


def decode_lod_text(raw: bytes) -> str:
    """Decode marked CP949 runs while preserving unmarked CP1252 source bytes."""
    output: list[str] = []
    position = 0
    for match in DBCS_GROUP_RE.finditer(raw):
        output.append(raw[position:match.start()].decode("cp1252"))
        pairs = re.findall(br"\x20\x0e(..)\x07", match.group(1), re.S)
        output.append(b"".join(pairs).decode("cp949"))
        position = match.end()
    output.append(raw[position:].decode("cp1252"))
    return "".join(output)


def encode_lod_text(text: str) -> bytes:
    return encode_dbcs_special(encode_mixed_text(text))


def changed_overlay(translations: Path, base_translations: Path, name: str) -> dict[tuple[int, str], str]:
    current = parse_overlay(translations / name)
    base = parse_overlay(base_translations / name)
    return {key: value for key, value in current.items() if base.get(key) != value}


def patch_autonote(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    count = apply_direct(doc, changed_overlay(translations, base_translations, "KO_AutonoteTxt.txt"), 1)
    return doc.render(), count


def patch_npctopic(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    count = apply_direct(doc, changed_overlay(translations, base_translations, "KO_NPCTopic.txt"), 1)
    return doc.render(), count


def patch_quests(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    count = apply_direct(doc, changed_overlay(translations, base_translations, "KO_QuestsTxt.txt"), 1)
    return doc.render(), count


def patch_npcgreet(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    count = apply_direct(
        doc, changed_overlay(translations, base_translations, "KO_NPCGreet1.txt"), 1, overlay_field="0"
    )
    count += apply_direct(
        doc, changed_overlay(translations, base_translations, "KO_NPCGreet2.txt"), 2, overlay_field="1"
    )
    return doc.render(), count


def patch_npctext(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    count = apply_direct(doc, changed_overlay(translations, base_translations, "KO_NPCText.txt"), 1)
    return doc.render(), count


def patch_scroll(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    eligible = lambda row, index: bool(
        row.fields and decode_field(row.fields[0]).strip().isdigit()
    )
    count = apply_by_order(
        doc, changed_overlay(translations, base_translations, "KO_MessageScrolls.txt"), 1, eligible
    )
    return doc.render(), count


def patch_spcitems(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    eligible = lambda row, index: index >= 4 and len(row.fields) >= 2 and bool(
        decode_field(row.fields[0]).strip()
    )
    count = apply_by_order(
        doc,
        changed_overlay(translations, base_translations, "KO_SpcItemsTxtStats.txt"),
        0,
        eligible,
        overlay_field="BonusStat",
    )
    return doc.render(), count


def patch_stditems(text: str, translations: Path, base_translations: Path) -> tuple[str, int]:
    doc = TsvDocument(text)
    eligible = lambda row, index: index >= 4 and len(row.fields) >= 2 and bool(
        decode_field(row.fields[0]).strip()
    )
    count = apply_by_order(
        doc,
        changed_overlay(translations, base_translations, "KO_StdItemsTxtStats.txt"),
        0,
        eligible,
        overlay_field="BonusStat",
    )
    count += apply_by_order(
        doc,
        changed_overlay(translations, base_translations, "KO_StdItemsTxtNames.txt"),
        1,
        eligible,
        overlay_field="NameAdd",
    )
    return doc.render(), count


PATCHERS = {
    "autonote.txt": patch_autonote,
    "npcgreet.txt": patch_npcgreet,
    "npctext.txt": patch_npctext,
    "npctopic.txt": patch_npctopic,
    "quests.txt": patch_quests,
    "scroll.txt": patch_scroll,
    "spcitems.txt": patch_spcitems,
    "stditems.txt": patch_stditems,
}


def patch_lod(lod_path: Path, translations: Path, base_translations: Path, output_path: Path) -> dict[str, int]:
    archive = lod_path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{lod_path} is not a LOD archive")
    root_offset, _root_size, flags, count = struct.unpack_from("<IIII", archive, 0x110)
    if flags != 0:
        raise ValueError("unsupported non-zero LOD root flags")
    directory_end = root_offset + count * 76
    directory = bytearray(archive[root_offset:directory_end])

    entries: list[tuple[str, int, int]] = []
    for index in range(count):
        pos = index * 76
        name = directory[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, member_flags = struct.unpack_from("<III", directory, pos + 64)
        if member_flags != 0:
            raise ValueError(f"unsupported non-zero directory flag for {name}")
        entries.append((name, offset, size))

    reports: dict[str, int] = {}
    rebuilt: list[bytes] = []
    cursor = directory_end - root_offset
    for index, (name, offset, size) in enumerate(entries):
        record = archive[root_offset + offset:root_offset + offset + size]
        if len(record) != size:
            raise ValueError(f"LOD member {name} is truncated")
        patcher = PATCHERS.get(name.casefold())
        if patcher is not None:
            raw, compressed = read_member_payload(record)
            localized, changes = patcher(decode_lod_text(raw), translations, base_translations)
            record = build_member_record(record, encode_lod_text(localized), compressed)
            reports[name] = changes

        pos = index * 76 + 64
        struct.pack_into("<III", directory, pos, cursor, len(record), 0)
        rebuilt.append(record)
        cursor += len(record)

    missing = set(PATCHERS) - {name.casefold() for name, _, _ in entries}
    if missing:
        raise ValueError(f"LOD is missing required members: {sorted(missing)}")

    output = bytearray(archive[:root_offset]) + directory + b"".join(rebuilt)
    struct.pack_into("<I", output, 0x114, len(output) - root_offset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lod", type=Path, required=True)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--base-translations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = patch_lod(args.lod, args.translations, args.base_translations, args.output)
    for name, count in sorted(reports.items(), key=lambda item: item[0].casefold()):
        print(f"{name}: synchronized {count} localized fields")


if __name__ == "__main__":
    main()
