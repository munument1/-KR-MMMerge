#!/usr/bin/env python3
"""Inventory Korean text literals still embedded in runtime Lua.

The scanner understands both Unicode Korean and legacy decimal byte escapes
(e.g. "\\184\\240...") that decode as CP949/EUC-KR.  It also builds a corpus
from Data/Text localization so exact wording duplicates can be distinguished
from genuinely runtime-only UI text.

This is an audit only: it never rewrites game scripts.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Scripts"
DATA = ROOT / "Data" / "Text localization"

HANGUL_RE = re.compile(r"[가-힣]")

GENERATED = {"KO_RuntimeOverrides.txt", "KO_StatsSkillsRuntime.txt"}


def read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def decode_lua_string(body: str) -> tuple[str | None, str]:
    """Return display text plus decoding mode, or (None, mode) if not Korean."""
    # First handle ordinary Lua escapes while preserving decimal bytes.
    raw = bytearray()
    chars: list[str] = []
    has_decimal = False
    i = 0
    while i < len(body):
        ch = body[i]
        if ch != "\\":
            chars.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(body):
            chars.append("\\")
            break
        esc = body[i]
        if esc.isdigit():
            if chars:
                # Literal ASCII/Unicode before bytes: encode it so one decoder
                # can reconstruct mixed strings such as prefixes/suffixes.
                raw.extend("".join(chars).encode("utf-8"))
                chars = []
            j = i
            while j < len(body) and j < i + 3 and body[j].isdigit():
                j += 1
            value = int(body[i:j], 10)
            if value > 255:
                return None, "invalid-decimal"
            raw.append(value)
            has_decimal = True
            i = j
            continue
        mapping = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
        chars.append(mapping.get(esc, esc))
        i += 1

    if has_decimal:
        if chars:
            # In the project these tails are normally ASCII.  CP949 contains
            # ASCII unchanged, so use CP949 for consistency with decimal bytes.
            tail = "".join(chars)
            try:
                raw.extend(tail.encode("cp949"))
            except UnicodeEncodeError:
                raw.extend(tail.encode("utf-8"))
        try:
            text = bytes(raw).decode("cp949")
            mode = "decimal-cp949"
        except UnicodeDecodeError:
            return None, "decimal-undecodable"
    else:
        text = "".join(chars)
        mode = "unicode"

    if not HANGUL_RE.search(text):
        return None, mode
    return text, mode


def iter_lua_strings(text: str):
    """Yield (body, start_offset, start_line) for quoted Lua strings in O(n).

    The previous regex scanner paired with text.count() for every match could
    become quadratic on the large generated/runtime Lua tree and stall CI for
    hours.  This deliberately mirrors the old audit's scope (single/double
    quoted strings, including strings found in comments) while advancing only
    once through each file.
    """
    i = 0
    line = 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch not in ("'", '"'):
            i += 1
            continue

        quote = ch
        start = i
        start_line = line
        i += 1
        body_start = i

        while i < n:
            ch = text[i]
            if ch == "\\":
                # A backslash escapes the next character for purposes of
                # locating the closing quote.  Keep the original body slice so
                # decode_lua_string() can interpret decimal and ordinary escapes.
                if i + 1 < n:
                    if text[i + 1] == "\n":
                        line += 1
                    i += 2
                else:
                    i += 1
                continue
            if ch == quote:
                yield text[body_start:i], start, start_line
                i += 1
                break
            if ch == "\n":
                line += 1
            i += 1
        else:
            # Unterminated quoted text cannot contain another independently
            # parseable quoted literal, so stop scanning this file.
            break


def iter_cells(path: Path):
    text, _ = read_text(path)
    # CSV parsing captures quoted tabs/newlines better than naive splitting.
    try:
        rows = csv.reader(io.StringIO(text, newline=""), delimiter="\t", quotechar='"', doublequote=True)
        for row in rows:
            for cell in row:
                cell = cell.strip()
                if cell and HANGUL_RE.search(cell):
                    yield cell
    except csv.Error:
        for line in text.splitlines():
            for cell in line.split("\t"):
                cell = cell.strip()
                if cell and HANGUL_RE.search(cell):
                    yield cell


def static_corpus():
    exact: dict[str, set[str]] = defaultdict(set)
    normalized: dict[str, set[str]] = defaultdict(set)
    file_counts = Counter()
    for path in sorted(DATA.glob("*")):
        if not path.is_file() or path.name in GENERATED:
            continue
        for cell in iter_cells(path):
            exact[cell].add(path.name)
            normalized[re.sub(r"\s+", " ", cell).strip()].add(path.name)
            file_counts[path.name] += 1
    return exact, normalized, file_counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--fail-static-duplicates", action="store_true")
    args = parser.parse_args()

    exact, normalized, source_counts = static_corpus()
    findings = []
    script_summary = {}

    for path in sorted(SCRIPTS.rglob("*.lua")):
        text, encoding = read_text(path)
        per_script = []
        for body, _start, literal_line in iter_lua_strings(text):
            decoded, mode = decode_lua_string(body)
            if not decoded:
                continue
            norm = re.sub(r"\s+", " ", decoded).strip()
            exact_sources = sorted(exact.get(decoded, ()), key=str.casefold)
            normalized_sources = sorted(normalized.get(norm, ()), key=str.casefold)
            finding = {
                "path": path.relative_to(ROOT).as_posix(),
                "line": literal_line,
                "script_encoding": encoding,
                "literal_encoding": mode,
                "text": decoded,
                "exact_static_sources": exact_sources,
                "normalized_static_sources": normalized_sources,
                "exact_static_match": bool(exact_sources),
                "normalized_static_match": bool(normalized_sources),
            }
            findings.append(finding)
            per_script.append(finding)
        if per_script:
            script_summary[path.relative_to(ROOT).as_posix()] = {
                "encoding": encoding,
                "korean_literals": len(per_script),
                "exact_static_matches": sum(x["exact_static_match"] for x in per_script),
                "normalized_static_matches": sum(x["normalized_static_match"] for x in per_script),
                "unique_texts": len({x["text"] for x in per_script}),
            }

    unique_texts = {f["text"] for f in findings}
    exact_duplicate_findings = [f for f in findings if f["exact_static_match"]]
    no_static_match = [f for f in findings if not f["normalized_static_match"]]

    report = {
        "schema": 1,
        "lua_files_with_korean": len(script_summary),
        "literal_occurrences": len(findings),
        "unique_korean_texts": len(unique_texts),
        "exact_static_duplicate_occurrences": len(exact_duplicate_findings),
        "no_static_match_occurrences": len(no_static_match),
        "scripts": script_summary,
        "findings": findings,
        "static_source_cell_counts": dict(sorted(source_counts.items(), key=lambda x: x[0].casefold())),
    }

    print("Lua Korean literal audit")
    print(f"  Lua files with Korean text:        {report['lua_files_with_korean']}")
    print(f"  Korean literal occurrences:       {report['literal_occurrences']}")
    print(f"  unique Korean texts:              {report['unique_korean_texts']}")
    print(f"  exact static duplicate literals:  {report['exact_static_duplicate_occurrences']}")
    print(f"  no static wording match:          {report['no_static_match_occurrences']}")
    print()
    for path, info in sorted(script_summary.items(), key=lambda x: (-x[1]["korean_literals"], x[0].casefold())):
        print(
            f"  {path}: literals={info['korean_literals']}, "
            f"exact_static={info['exact_static_matches']}, unique={info['unique_texts']}, "
            f"encoding={info['encoding']}"
        )

    if exact_duplicate_findings:
        print("\nExact canonical wording duplicates (first 80):")
        for item in exact_duplicate_findings[:80]:
            preview = item["text"].replace("\n", "\\n")
            if len(preview) > 100:
                preview = preview[:97] + "..."
            print(
                f"  {item['path']}:{item['line']} -> {item['exact_static_sources']}: {preview}"
            )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nJSON report: {args.json}")

    if args.fail_static_duplicates and exact_duplicate_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
