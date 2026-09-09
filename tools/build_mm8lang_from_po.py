#!/usr/bin/env python3
"""Materialize root mm8lang.ini from Korean gettext PO entries."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import polib


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PO = ROOT / "translations/ko/mmmerge.po"
DEFAULT_SOURCE = ROOT / "mm8lang.ini"
CONTEXT_RE = re.compile(r"^mm8/mm8lang\.ini\|section=(?P<section>[^|]+)\|key=(?P<key>.+)$")
PLACEHOLDER_RE = re.compile(r"%(?:\d+\$)?[sd]")


def placeholders(value: str) -> tuple[str, ...]:
    return tuple(PLACEHOLDER_RE.findall(value.replace("%%", "")))


def read_text(path: Path) -> tuple[str, str, bool, str]:
    data = path.read_bytes()
    bom = data.startswith(b"\xef\xbb\xbf")
    payload = data[3:] if bom else data
    encoding = "utf-8"
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        if bom:
            raise ValueError(f"UTF-8 BOM file is not valid UTF-8: {path}")
        encoding = "cp949"
        text = payload.decode("cp949")
    crlf = text.count("\r\n")
    bare_lf = text.count("\n") - crlf
    newline = "\r\n" if crlf > bare_lf else "\n"
    return text, encoding, bom, newline


def encode_text(text: str, encoding: str, bom: bool) -> bytes:
    data = text.encode(encoding)
    return (b"\xef\xbb\xbf" + data) if bom and encoding == "utf-8" else data


def load_entries(po_path: Path) -> dict[tuple[str, str], polib.POEntry]:
    po = polib.pofile(str(po_path))
    out: dict[tuple[str, str], polib.POEntry] = {}
    for entry in po:
        if entry.obsolete or "KO-ROOT: mm8lang.ini" not in (entry.comment or ""):
            continue
        match = CONTEXT_RE.match(entry.msgctxt or "")
        if not match:
            raise ValueError(f"invalid mm8lang context: {entry.msgctxt!r}")
        key = (match.group("section"), match.group("key"))
        if key in out:
            raise ValueError(f"duplicate mm8lang key: {key}")
        if not entry.msgstr:
            raise ValueError(f"untranslated mm8lang key: {key}")
        if placeholders(entry.msgid) != placeholders(entry.msgstr):
            raise ValueError(
                f"placeholder mismatch for {key}: {placeholders(entry.msgid)} != {placeholders(entry.msgstr)}"
            )
        out[key] = entry
    if not out:
        raise ValueError("PO contains no KO-ROOT mm8lang entries")
    return out


def materialize(source: Path, entries: dict[tuple[str, str], polib.POEntry]) -> tuple[bytes, int, int, str]:
    text, encoding, bom, newline = read_text(source)
    trailing = text.endswith(("\n", "\r"))
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if trailing and lines and lines[-1] == "":
        lines = lines[:-1]

    section = ""
    used: set[tuple[str, str]] = set()
    changes = 0
    output: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            output.append(raw)
            continue
        if "=" not in raw or stripped.startswith((";", "#")):
            output.append(raw)
            continue
        key_raw, current = raw.split("=", 1)
        key = (section, key_raw.strip())
        entry = entries.get(key)
        if entry is None:
            output.append(raw)
            continue
        used.add(key)
        desired = entry.msgstr
        if current != desired:
            changes += 1
        output.append(f"{key_raw}={desired}")

    missing = sorted(set(entries) - used)
    if missing:
        raise ValueError(f"PO mm8lang keys missing from template: {missing}")

    result = newline.join(output)
    if trailing:
        result += newline
    return encode_text(result, encoding, bom), changes, len(used), encoding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--po", type=Path, default=DEFAULT_PO)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-byte-identical", action="store_true")
    args = parser.parse_args()

    if args.write and args.output:
        raise SystemExit("--write and --output are mutually exclusive")
    if not args.write and not args.output:
        raise SystemExit("provide --output or --write")

    entries = load_entries(args.po)
    output, changes, applied, encoding = materialize(args.source, entries)
    original = args.source.read_bytes()
    drift = output != original

    if args.require_byte_identical and drift:
        raise SystemExit("current PO does not byte-round-trip mm8lang.ini")

    destination = args.source if args.write else args.output
    assert destination is not None
    destination.parent.mkdir(parents=True, exist_ok=True)
    if args.write:
        if drift:
            destination.write_bytes(output)
    else:
        destination.write_bytes(output)

    print("PO -> mm8lang.ini materialization")
    print(f"  PO entries applied: {applied}")
    print(f"  source encoding:    {encoding}")
    print(f"  text values changed: {changes}")
    print(f"  byte drift:          {drift}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
