#!/usr/bin/env python3
"""Validate the terminology and formatting regressions reported for v1.0.12."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from patch_static_global_lod import encode_dbcs_special, encode_mixed_text, parse_overlay, read_member_payload

EXPECTED = {
    18: "근접",
    34: "취소",
    79: "나가기",
    168: "포인트",
    170: "퀵스펠",
    172: "퀵스펠",
    203: "원거리",
    433: "전문가",
    537: "레벨 %d까지 훈련: %d골드",
    538: "경험치 %d가 더 있어야 레벨 %d까지 훈련할 수 있습니다",
}


def parse_lua_global_values(path: Path) -> dict[int, str]:
    text = path.read_bytes().decode("cp949")
    marker = "local globalTxts = {"
    if marker not in text:
        raise ValueError(f"{path}: globalTxts table was not found")
    section = text.split(marker, 1)[1].split("\n\t}", 1)[0]
    return {
        int(record_id): value
        for record_id, value in re.findall(r'\[(\d+)\]\s*=\s*"([^"]*)"', section)
    }


def extract_lod_global(path: Path) -> bytes:
    archive = path.read_bytes()
    if archive[:4] != b"LOD\0":
        raise ValueError(f"{path}: invalid LOD signature")
    root_offset, root_size, unknown, count = struct.unpack_from("<IIII", archive, 0x110)
    if unknown != 0:
        raise ValueError(f"{path}: unsupported root flags")
    if root_offset + root_size != len(archive):
        raise ValueError(f"{path}: root size does not match archive length")

    expected_offset = count * 76
    for index in range(count):
        pos = root_offset + index * 76
        name = archive[pos:pos + 64].split(b"\0", 1)[0].decode("ascii")
        offset, size, flags = struct.unpack_from("<III", archive, pos + 64)
        if flags != 0:
            raise ValueError(f"{path}: non-zero flags on {name}")
        if offset != expected_offset:
            raise ValueError(f"{path}: non-contiguous member offset for {name}")
        record = archive[root_offset + offset:root_offset + offset + size]
        if len(record) != size:
            raise ValueError(f"{path}: truncated member {name}")
        member_name = record[:64].split(b"\0", 1)[0].decode("ascii")
        if member_name.casefold() != name.casefold():
            raise ValueError(f"{path}: directory/header name mismatch for {name}")
        expected_offset += size
        if name.casefold() == "global.txt":
            raw, _compressed = read_member_payload(record)
            global_data = raw
    if expected_offset != root_size:
        raise ValueError(f"{path}: member lengths do not match root size")
    try:
        return global_data
    except UnboundLocalError as error:
        raise ValueError(f"{path}: Global.TXT is missing") from error


def parse_global_member(raw: bytes) -> dict[int, bytes]:
    values: dict[int, bytes] = {}
    for line in raw.splitlines():
        record_id, separator, value = line.partition(b"\t")
        if separator and record_id.isdigit():
            values[int(record_id)] = value
    return values



def validate_brazier_hint_script(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="ascii")
    required = {
        'local BRAZIER_EN = "brazier"': "exact English hint key",
        'local BRAZIER_KO = "\\200\\173\\183\\206"': "CP949 Korean fire-brazier text",
        'KGF.TranslateTargetedMapHint = translateTargetedMapHint': "runtime validation entry point",
        'local pendingMapLocalizationPasses = 0': "finite post-load state",
        'pendingMapLocalizationPasses = 8': "finite post-load schedule",
        'function events.BeforeLoadMapScripts()': "pre-script evt.str pass",
        'function events.LoadMapScripts()': "post-script pass",
        'function events.AfterLoadMap()': "late map pass",
    }
    for token, description in required.items():
        if token not in source:
            errors.append(f"{path}: missing {description}")
    if 'Retired in v1.0.12' in source:
        errors.append(f"{path}: targeted map-hint fix is still replaced by the retired no-op stub")
    if source.count('["brazier"]') > 0:
        errors.append(f"{path}: broad prompt dictionary was restored instead of the exact targeted fallback")
    return errors

def validate(root: Path) -> list[str]:
    errors: list[str] = []
    overlay_path = root / "Data/Text localization/KO_GlobalTxt.txt"
    lua_path = root / "Scripts/General/KoreanStatsAndSkills.lua"
    lod_path = root / "Data/zz LocKO.T.lod"
    brazier_script_path = root / "Scripts/General/ZZ_KoreanGameplayFeedbackFixes.lua"

    errors.extend(validate_brazier_hint_script(brazier_script_path))

    overlay = parse_overlay(overlay_path)
    lua_values = parse_lua_global_values(lua_path)
    lod_values = parse_global_member(extract_lod_global(lod_path))

    for record_id, expected in EXPECTED.items():
        if overlay.get(record_id) != expected:
            errors.append(
                f"KO_GlobalTxt[{record_id}] = {overlay.get(record_id)!r}; expected {expected!r}"
            )
        if lua_values.get(record_id) != expected:
            errors.append(
                f"KoreanStatsAndSkills globalTxts[{record_id}] = {lua_values.get(record_id)!r}; expected {expected!r}"
            )
        encoded = encode_dbcs_special(encode_mixed_text(expected))
        if lod_values.get(record_id) != encoded:
            errors.append(f"LOD Global.TXT[{record_id}] does not match the canonical overlay")

    for record_id, value in lua_values.items():
        if record_id not in overlay:
            errors.append(f"Lua owns GlobalTxt[{record_id}], but the canonical overlay has no such ID")
        elif overlay[record_id] != value:
            errors.append(
                f"GlobalTxt[{record_id}] differs between overlay {overlay[record_id]!r} and Lua {value!r}"
            )

    if overlay.get(537, "").count("%d") != 2 or overlay.get(538, "").count("%d") != 2:
        errors.append("Training strings must each retain exactly two %d placeholders")

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
    print("Feedback regression validation passed.")
    print(f"Checked {len(EXPECTED)} exact GlobalTxt contracts, Lua synchronization, static LOD contents, and the targeted brazier hint fallback.")


if __name__ == "__main__":
    main()
