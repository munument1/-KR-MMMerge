#!/usr/bin/env python3
"""Validate canonical Korean spell names in overlays, items and static LOD."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from normalize_spell_names import (
    PROTECTED_PHRASES,
    SAFE_GLOBAL_REPLACEMENTS,
    correct_canonical_josa,
    load_terms,
)
from patch_static_global_lod import decode_dbcs_special, read_member_payload

GLOBALTXT_SPELL_NAMES = {
    6: "공기 저항",
    35: "%s(으)로 도시 귀환",
    24: "화염 저항",
    29: "육체 저항",
    70: "대지 저항",
    87: "화염 저항",
    104: "치유",
    142: "정신 저항",
    162: "마비",
    194: "물 저항",
    202: "공기 저항",
    204: "육체 저항",
    208: "대지 저항",
    213: "정신 저항",
    215: "생명체 감지",
    217: "투명화",
    219: "신들의 날",
    221: "운명",
    228: "망치손",
    229: "고통 반사",
    231: "기절",
    233: "생명 보존",
    234: "재생",
    240: "물 저항",
    279: "방패",
    441: "가속",
    443: "축복",
    452: "횃불",
    453: "마법사의 눈",
    455: "비행",
    456: "수면 보행",
    462: "마법 보호",
    493: "공중에서는 도약을 시전할 수 없습니다!",
    609: "힘의 시간",
    610: "보호의 날",
    700: "매혹",
    711: "도약",
}


def parse_overlay(path: Path) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for line in path.read_bytes().decode("cp949").splitlines():
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            result.setdefault(int(parts[1].strip()), {})[parts[2].strip()] = parts[3]
    return result


def parse_global_overlay(path: Path) -> dict[int, str]:
    values: dict[int, str] = {}
    for line in path.read_bytes().decode("cp949").splitlines():
        parts = line.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            values[int(parts[1].strip())] = parts[3]
    return values


def extract_lod_members(path: Path, wanted: set[str]) -> dict[str, bytes]:
    archive = path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{path}: invalid LOD signature")
    root_offset, root_size, flags, count = struct.unpack_from("<IIII", archive, 0x110)
    if flags != 0 or root_offset + root_size != len(archive):
        raise ValueError(f"{path}: invalid root directory metadata")
    result: dict[str, bytes] = {}
    expected_offset = count * 76
    for index in range(count):
        pos = root_offset + index * 76
        name = archive[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, member_flags = struct.unpack_from("<III", archive, pos + 64)
        if member_flags != 0 or offset != expected_offset:
            raise ValueError(f"{path}: invalid directory entry for {name}")
        record = archive[root_offset + offset:root_offset + offset + size]
        expected_offset += size
        if name.casefold() in wanted:
            raw, _compressed = read_member_payload(record)
            result[name.casefold()] = raw
    if expected_offset != root_size:
        raise ValueError(f"{path}: member sizes do not match root size")
    missing = wanted - set(result)
    if missing:
        raise ValueError(f"{path}: missing LOD members {sorted(missing)}")
    return result


def parse_lod_spells(raw: bytes) -> dict[int, dict[str, str]]:
    text = decode_dbcs_special(raw).decode("cp949")
    result: dict[int, dict[str, str]] = {}
    columns = {
        "Name": 2,
        "ShortName": 4,
        "Description": 5,
        "Normal": 6,
        "Expert": 7,
        "Master": 8,
        "GrandMaster": 9,
    }
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) >= 5 and fields[0].isdigit():
            if len(fields) < 11:
                fields.extend([""] * (11 - len(fields)))
            result[int(fields[0])] = {name: fields[column] for name, column in columns.items()}
    return result


def parse_lod_global(raw: bytes) -> dict[int, str]:
    result: dict[int, str] = {}
    for line in decode_dbcs_special(raw).decode("cp949").splitlines():
        record_id, separator, value = line.partition("\t")
        if separator and record_id.isdigit():
            result[int(record_id)] = value
    return result


def decode_localization_file(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError(f"{path}: unsupported text encoding")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    translations = root / "Data/Text localization"
    terms = load_terms(root / "tools/SPELL_TERMINOLOGY.tsv")
    spell_overlay = parse_overlay(translations / "KO_SpellsTxt.txt")

    for spell_id, term in terms.items():
        record = spell_overlay.get(spell_id, {})
        for field in ("Name", "ShortName"):
            if record.get(field) != term.canonical:
                errors.append(
                    f"KO_SpellsTxt[{spell_id}].{field}={record.get(field)!r}; expected {term.canonical!r}"
                )

    item_path = translations / "KO_ItemsTxt.txt"
    item_names: dict[int, tuple[str, str]] = {}
    aliases = {alias: term.canonical for term in terms.values() for alias in term.aliases}
    for line in item_path.read_bytes().decode("cp949").splitlines()[1:]:
        parts = line.split("\t", 3)
        if len(parts) >= 3 and parts[0].isdigit():
            item_id = int(parts[0])
            name, kind = parts[1], parts[2].strip()
            item_names[item_id] = (name, kind)
            if kind in {"두루마리", "주문서", "마법서"} and name in aliases:
                errors.append(
                    f"KO_ItemsTxt[{item_id}] still uses alias {name!r}; expected {aliases[name]!r}"
                )

    # MM8's primary scroll and spellbook ranges are a direct 1:1 mapping.
    for start in (300, 400):
        for spell_id, term in terms.items():
            item_id = start + spell_id - 1
            actual = item_names.get(item_id, (None, None))[0]
            if actual != term.canonical:
                errors.append(
                    f"KO_ItemsTxt[{item_id}]={actual!r}; expected spell {spell_id} name {term.canonical!r}"
                )

    members = extract_lod_members(
        root / "Data/zz LocKO.T.lod", {"spells.txt", "global.txt"}
    )
    lod_spells = parse_lod_spells(members["spells.txt"])
    spell_fields = ("Name", "ShortName", "Description", "Normal", "Expert", "Master", "GrandMaster")
    for spell_id in range(1, 133):
        overlay_record = spell_overlay.get(spell_id)
        lod_record = lod_spells.get(spell_id)
        if overlay_record is None or lod_record is None:
            errors.append(
                f"spell {spell_id} missing from "
                f"{'overlay' if overlay_record is None else 'LOD'}"
            )
            continue
        for field in spell_fields:
            if lod_record.get(field) != overlay_record.get(field):
                errors.append(
                    f"LOD Spells.txt[{spell_id}].{field}={lod_record.get(field)!r}; "
                    f"overlay has {overlay_record.get(field)!r}"
                )

    canonicals = tuple(term.canonical for term in terms.values())
    for spell_id, record in spell_overlay.items():
        for field, value in record.items():
            corrected = correct_canonical_josa(value, canonicals)
            if corrected != value:
                errors.append(
                    f"KO_SpellsTxt[{spell_id}].{field} has incorrect particle usage: "
                    f"{value!r}; expected {corrected!r}"
                )

    global_overlay = parse_global_overlay(translations / "KO_GlobalTxt.txt")
    lod_global = parse_lod_global(members["global.txt"])
    for record_id, expected in GLOBALTXT_SPELL_NAMES.items():
        if global_overlay.get(record_id) != expected:
            errors.append(
                f"KO_GlobalTxt[{record_id}]={global_overlay.get(record_id)!r}; expected {expected!r}"
            )
        if lod_global.get(record_id) != expected:
            errors.append(
                f"LOD Global.TXT[{record_id}]={lod_global.get(record_id)!r}; expected {expected!r}"
            )

    # Unambiguous aliases must not survive anywhere in localization prose.
    for path in sorted(translations.glob("KO_*.txt")):
        text = decode_localization_file(path)
        corrected = correct_canonical_josa(text, canonicals)
        if corrected != text:
            errors.append(f"{path.name}: incorrect particle usage remains after a canonical spell name")
        for phrase in PROTECTED_PHRASES:
            text = text.replace(phrase, "")
        for alias, canonical in SAFE_GLOBAL_REPLACEMENTS.items():
            if alias in text:
                errors.append(f"{path.name}: alias {alias!r} remains; use {canonical!r}")

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
    print("Spell terminology validation passed.")
    print(
        f"Checked 99 canonical spell names, all 132 overlay/LOD spell text records, "
        f"MM8 scrolls and spellbooks, {len(GLOBALTXT_SPELL_NAMES)} GlobalTxt spell labels, "
        "Korean particles, and all unambiguous aliases."
    )


if __name__ == "__main__":
    main()
