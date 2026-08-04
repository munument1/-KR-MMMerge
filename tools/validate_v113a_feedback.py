#!/usr/bin/env python3
"""Validate the feedback fixes added after the v1.0.13 test report."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from patch_static_global_lod import parse_overlay, read_member_payload
from patch_static_spell_references_lod import decode_lod_text

EXPECTED_GLOBAL = {
    75: "체력",
    163: "인격",
    249: "일시적 인격",
}
EXPECTED_TRANS = "아이언피스트 성에 들어갑니다."
EXPECTED_MAP = {
    7: "찌릿!",
    18: '나무 표지판에는 이렇게 적혀 있습니다. "바람이 불고 계절이 바뀌어, 모든 것이 끝에 이르러야 문이 열린다."',
    19: "고통받는 영혼들의 섬뜩한 비명이 귓가를 때립니다.",
    20: '은제 표지판에는 이렇게 적혀 있습니다. "바람이 불고 계절이 바뀌어, 모든 것이 끝에 이르러야 문이 열린다."',
    21: '구리 표지판에는 이렇게 적혀 있습니다. "바람이 불고 계절이 바뀌어, 모든 것이 끝에 이르러야 문이 열린다."',
    22: '청금석 표지판에는 이렇게 적혀 있습니다. "바람이 불고 계절이 바뀌어, 모든 것이 끝에 이르러야 문이 열린다."',
    25: "누군가의 희망과 꿈이 담긴 한 줌을 퍼냅니다.",
    27: "분수에 동전 몇 닢을 던집니다.",
    30: "문에서 딸깍 소리가 납니다.",
}
EXPECTED_GUILDS = {
    1696: (25, 1832, 629),
    1697: (50, 1833, 630),
    1698: (50, 1834, 631),
    1699: (25, 1835, 632),
    1700: (50, 1836, 633),
    1701: (50, 1837, 634),
}


def lod_members(path: Path) -> dict[str, bytes]:
    archive = path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{path}: invalid LOD signature")
    root, root_size, flags, count = struct.unpack_from("<IIII", archive, 0x110)
    if flags != 0 or root + root_size != len(archive):
        raise ValueError(f"{path}: invalid LOD root metadata")
    result: dict[str, bytes] = {}
    expected = count * 76
    for index in range(count):
        pos = root + index * 76
        name = archive[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, member_flags = struct.unpack_from("<III", archive, pos + 64)
        if member_flags != 0 or offset != expected:
            raise ValueError(f"{path}: invalid directory entry for {name}")
        record = archive[root + offset:root + offset + size]
        raw, _compressed = read_member_payload(record)
        result[name.casefold()] = raw
        expected += size
    if expected != root_size:
        raise ValueError(f"{path}: member sizes do not match root size")
    return result


def parse_global_member(raw: bytes) -> dict[int, str]:
    text = decode_lod_text(raw)
    values: dict[int, str] = {}
    for line in text.splitlines():
        record_id, sep, value = line.partition("\t")
        if sep and record_id.isdigit():
            values[int(record_id)] = value
    return values


def parse_trans_member(raw: bytes) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in decode_lod_text(raw).splitlines():
        fields = line.split("\t")
        if fields and fields[0].strip().isdigit():
            rows.append(fields)
    return rows


def parse_map_overlay(path: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[0].casefold() == "6t1.str" and parts[1].isdigit():
            result[int(parts[1])] = parts[2]
    return result


def validate(root: Path) -> list[str]:
    errors: list[str] = []

    global_overlay = parse_overlay(root / "Data/Text localization/KO_GlobalTxt.txt")
    for record_id, expected in EXPECTED_GLOBAL.items():
        if global_overlay.get(record_id) != expected:
            errors.append(f"KO_GlobalTxt[{record_id}] is not {expected!r}")

    lua = (root / "Scripts/General/KoreanStatsAndSkills.lua").read_bytes().decode("cp949")
    stats_section = lua.split("local statsNames = {", 1)[1].split("\n\t}", 1)[0]
    if '[2] = "인격"' not in stats_section or '[3] = "체력"' not in stats_section:
        errors.append("KoreanStatsAndSkills statsNames does not use 인격/체력")
    global_section = lua.split("local globalTxts = {", 1)[1].split("\n\t}", 1)[0]
    if '[75] = "체력"' not in global_section or '[163] = "인격"' not in global_section:
        errors.append("KoreanStatsAndSkills GlobalTxt overrides do not use 체력/인격")

    trans_overlay = parse_overlay(root / "Data/Text localization/KO_TransTxt.txt")
    if trans_overlay.get(260) != EXPECTED_TRANS:
        errors.append("KO_TransTxt row-order entry 260 is not the Castle Ironfist text")

    map_overlay = parse_map_overlay(root / "Data/Text localization/KO_MapStrings.txt")
    for index, expected in EXPECTED_MAP.items():
        if map_overlay.get(index) != expected:
            errors.append(f"KO_MapStrings 6T1.STR[{index}] does not match the expected Korean text")

    guild_source = (root / "Scripts/Global/ZZ_KoreanServiceGuildCompatibility.lua").read_text(encoding="ascii")
    found = {
        int(topic): (int(cost), int(info), int(note))
        for topic, cost, info, note in re.findall(
            r"RestoreServiceGuildTopic\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)",
            guild_source,
        )
    }
    if found != EXPECTED_GUILDS:
        errors.append(f"service guild registrations are {found!r}; expected {EXPECTED_GUILDS!r}")

    members = lod_members(root / "Data/zz LocKO.T.lod")
    global_values = parse_global_member(members["global.txt"])
    for record_id, expected in EXPECTED_GLOBAL.items():
        if global_values.get(record_id) != expected:
            errors.append(f"LOD Global.TXT[{record_id}] is not {expected!r}")

    trans_rows = parse_trans_member(members["trans.txt"])
    if len(trans_rows) <= 260 or len(trans_rows[260]) < 2 or trans_rows[260][1] != EXPECTED_TRANS:
        errors.append("LOD Trans.txt row-order entry 260 is not the Castle Ironfist text")

    map_fields = members["6t1.str"].split(b"\0")
    from patch_static_spells_lod import decode_dbcs_special
    for index, expected in EXPECTED_MAP.items():
        if index >= len(map_fields):
            errors.append(f"LOD 6T1.STR is missing evt.str[{index}]")
            continue
        actual = decode_dbcs_special(map_fields[index]).decode("cp949", errors="replace")
        if actual != expected:
            errors.append(f"LOD 6T1.STR[{index}] = {actual!r}; expected {expected!r}")

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
    print("v1.0.13a feedback validation passed.")
    print("Checked canonical stats, Castle Ironfist text, six service guild handlers, and nine Temple of Baa strings.")


if __name__ == "__main__":
    main()
