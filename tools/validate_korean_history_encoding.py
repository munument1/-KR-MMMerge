#!/usr/bin/env python3
"""Validate loose Korean history tables are safe for the native DBCS renderer.

KoreanHistory.lua reads these files as raw bytes and assigns those bytes directly
to Game.HistoryTxt. FNT_DBCS.lua is configured for ``euc_kr`` and its accepted
lead/trail ranges match the KS X 1001 EUC-KR repertoire, not the wider CP949
extension ranges. A history file must therefore be strict EUC-KR bytes.

The history loader also uses CR as the record separator and permits LF inside
the Text field for paragraph breaks. Validate that physical layout too so a
normal newline conversion cannot silently merge all records into one.
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_FILES = (
    Path("Data/Text localization/MM6History_KO.txt"),
    Path("Data/Text localization/MM7History_KO.txt"),
    Path("Data/Text localization/MM8History_KO.txt"),
)

MIN_RECORDS = {
    "MM6History_KO.txt": 1,
    "MM7History_KO.txt": 3,
    "MM8History_KO.txt": 3,
}

HEADER = "#\tText\tTime\tPage Title"


def contains_hangul(text: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def parse_records(text: str, path: Path) -> dict[int, tuple[str, str, str]]:
    if "\r" not in text:
        raise ValueError(
            f"{path}: no CR record separators; KoreanHistory.lua splits records on CR"
        )

    chunks = text.split("\r")
    if not chunks or chunks[0].lstrip("\ufeff\n") != HEADER:
        raise ValueError(f"{path}: unexpected header or record layout")

    records: dict[int, tuple[str, str, str]] = {}
    for raw in chunks[1:]:
        row = raw.lstrip("\n")
        if not row:
            continue
        parts = row.split("\t", 3)
        if len(parts) != 4 or not parts[0].isdigit():
            raise ValueError(f"{path}: malformed history record start: {row[:80]!r}")
        record_id = int(parts[0])
        if record_id in records:
            raise ValueError(f"{path}: duplicate history record id {record_id}")
        text_field, time_field, title = parts[1], parts[2], parts[3]
        if not text_field or not title:
            raise ValueError(f"{path}: record {record_id} has empty Text or Page Title")
        records[record_id] = (text_field, time_field, title)
    return records


def validate(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"{path}: empty file")

    # UTF-8 Hangul is unsafe here: KoreanHistory.lua performs no transcoding.
    try:
        utf8 = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        utf8 = None
    if utf8 is not None and contains_hangul(utf8):
        raise ValueError(
            f"{path}: Hangul is UTF-8; runtime history files must be EUC-KR bytes"
        )

    try:
        decoded = data.decode("euc_kr")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: invalid strict EUC-KR runtime bytes: {exc}") from exc

    if not contains_hangul(decoded):
        raise ValueError(f"{path}: decoded runtime file contains no Hangul")
    if decoded.encode("euc_kr") != data:
        raise ValueError(f"{path}: EUC-KR round-trip changed bytes")

    records = parse_records(decoded, path)
    minimum = MIN_RECORDS.get(path.name, 1)
    if len(records) < minimum:
        raise ValueError(
            f"{path}: only {len(records)} records; expected at least {minimum}"
        )

    return len(records), sum(1 for value in records.values() if "\n" in value[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()

    files = tuple(args.files) if args.files else DEFAULT_FILES
    failures: list[str] = []
    for path in files:
        try:
            records, multiline = validate(path)
            print(
                f"{path}: OK (strict euc-kr, records={records}, "
                f"multiline_text_records={multiline})"
            )
        except (OSError, ValueError) as exc:
            failures.append(str(exc))

    if failures:
        for failure in failures:
            print("ERROR:", failure)
        return 1

    print("Korean history runtime encoding: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
