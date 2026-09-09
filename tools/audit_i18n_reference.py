#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import re
import sys
import urllib.request
from collections import defaultdict
from dataclasses import dataclass

REFERENCE_REV = "aea1b22666ef556f34a71b4f3945904b04de1466"
REFERENCE_URL = (
    "https://raw.githubusercontent.com/might-and-magic/mm678-i18n/"
    f"{REFERENCE_REV}/references/glossary/ko/glossary.jsonl"
)
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
LATIN_RE = re.compile(r"[A-Za-z]")
SAFE_EXTENSIONS = {".txt", ".tsv", ".utf8"}
STRUCT_HEADER = ["Table (of Game struct)", "Id", "Field", "New text"]
HEADER_WORDS = {
    "id", "name", "notes", "description", "text", "field", "new text",
    "notidentifiedname", "notidentifiedname ", "type", "picture", "value",
}


@dataclass(frozen=True)
class Reference:
    context: str
    msgid: str
    msgstr: str


@dataclass(frozen=True)
class Occurrence:
    path: str
    line: int
    column: int
    value: str


def decode(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(enc).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("unknown", b"", 0, 1, str(path))


def load_reference(reference_file: pathlib.Path | None, reference_url: str) -> list[Reference]:
    if reference_file:
        raw = reference_file.read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(
            reference_url,
            headers={"User-Agent": "KR-MMMerge-i18n-reference-audit/1.0"},
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8")

    rows: list[Reference] = []
    for no, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid reference JSONL at line {no}: {exc}") from exc
        msgid = str(obj.get("msgid") or "").strip()
        msgstr = str(obj.get("msgstr") or "").strip()
        context = str(obj.get("msgctxt") or "").strip()
        # Only Korean reference material is useful for this audit.
        if not msgid or not msgstr or not LATIN_RE.search(msgid) or not HANGUL_RE.search(msgstr):
            continue
        rows.append(Reference(context=context, msgid=msgid, msgstr=msgstr))
    return rows


def parse_cells(line: str) -> list[str]:
    if "\t" not in line:
        return [line.strip()]
    try:
        return next(csv.reader([line], delimiter="\t"))
    except csv.Error:
        return line.split("\t")


def clean_cell(cell: str) -> str:
    return cell.strip().strip('"')


def looks_like_header(cells: list[str]) -> bool:
    cleaned = [clean_cell(c).lower() for c in cells if clean_cell(c)]
    if not cleaned:
        return False
    known = sum(1 for c in cleaned if c in HEADER_WORDS)
    return known >= 2 and known >= len(cleaned) // 2


def iter_localization_cells(root: pathlib.Path):
    loc = root / "Data" / "Text localization"
    if not loc.is_dir():
        raise SystemExit(f"localization directory not found: {loc}")
    for path in sorted(
        p for p in loc.iterdir() if p.is_file() and p.suffix.lower() in SAFE_EXTENSIONS
    ):
        try:
            text = decode(path)
        except UnicodeDecodeError as exc:
            print(f"warning: skipped undecodable file: {path}: {exc}", file=sys.stderr)
            continue
        rel = path.relative_to(root).as_posix()
        lines = text.splitlines()
        first_cells = parse_cells(lines[0]) if lines else []
        structured = [clean_cell(c) for c in first_cells[:4]] == STRUCT_HEADER

        for line_no, line in enumerate(lines, 1):
            if not line or line.lstrip().startswith("#"):
                continue
            cells = parse_cells(line)
            if line_no == 1 and (structured or looks_like_header(cells)):
                continue

            # The bulk of KR-MMMerge runtime override tables intentionally keep
            # English metadata in columns 1-3 (table/id/field). Only column 4 is
            # displayed text. Scanning metadata created thousands of fake hits
            # such as Name/Master, so never treat those columns as translations.
            if structured:
                selected = [(4, cells[3])] if len(cells) >= 4 else []
            else:
                selected = list(enumerate(cells, 1))

            for col_no, cell in selected:
                value = clean_cell(cell)
                if value:
                    yield Occurrence(rel, line_no, col_no, value)


def build_report(root: pathlib.Path, refs: list[Reference], reference_label: str) -> str:
    by_msgid: dict[str, list[Reference]] = defaultdict(list)
    by_msgstr: dict[str, set[str]] = defaultdict(set)
    for ref in refs:
        by_msgid[ref.msgid].append(ref)
        by_msgstr[ref.msgstr].add(ref.msgid)

    occurrences = list(iter_localization_cells(root))
    exact_english: list[tuple[Occurrence, list[Reference]]] = []
    legacy_in_use: list[tuple[Occurrence, set[str]]] = []

    for occ in occurrences:
        if occ.value in by_msgid:
            exact_english.append((occ, by_msgid[occ.value]))
        if occ.value in by_msgstr:
            legacy_in_use.append((occ, by_msgstr[occ.value]))

    # Context/era conflicts are informative, not errors. Restrict the section to
    # msgids that are actually relevant to text currently found in our payload.
    relevant_msgids = {occ.value for occ, _ in exact_english}
    for _, msgids in legacy_in_use:
        relevant_msgids.update(msgids)

    conflicts: dict[str, list[Reference]] = {}
    for msgid in sorted(relevant_msgids):
        options = by_msgid.get(msgid, [])
        if len({r.msgstr for r in options}) > 1:
            conflicts[msgid] = options

    out = io.StringIO()
    print("MMMERGE KOREAN OFFICIAL/LEGACY REFERENCE AUDIT", file=out)
    print("==============================================", file=out)
    print(f"Reference: {reference_label}", file=out)
    print("Reference policy: mm678-i18n Korean data is advisory only; never auto-applied.", file=out)
    print(f"Usable Korean reference rows: {len(refs)}", file=out)
    print(f"Unique English msgids: {len(by_msgid)}", file=out)
    print(f"Displayed/localized cells scanned: {len(occurrences)}", file=out)
    print(f"Exact English residual candidates: {len(exact_english)}", file=out)
    print(f"Legacy-reference Korean cells already in use: {len(legacy_in_use)}", file=out)
    print(f"Relevant legacy translation conflicts: {len(conflicts)}", file=out)
    print("", file=out)

    print("[A] EXACT ENGLISH RESIDUAL CANDIDATES", file=out)
    print("-------------------------------------", file=out)
    print(
        "These are displayed/localized cells in the Korean payload that exactly equal an "
        "English msgid for which mm678-i18n has a Korean legacy/retail-derived reference. "
        "Review manually; proper names and intentionally untranslated tokens can be false positives.",
        file=out,
    )
    if not exact_english:
        print("(none)", file=out)
    for occ, options in exact_english:
        refs_text = " | ".join(
            f"{r.context or '(no context)'} => {r.msgstr}"
            for r in sorted(set(options), key=lambda x: (x.context, x.msgstr))
        )
        print(
            f"{occ.path}:{occ.line}:col{occ.column}\tEN={occ.value}\tREF={refs_text}",
            file=out,
        )
    print("", file=out)

    print("[B] LEGACY REFERENCE TERMS ALREADY PRESENT", file=out)
    print("------------------------------------------", file=out)
    print(
        "Exact Korean displayed/localized cells that also occur in the legacy reference. "
        "This is not a problem by itself; it helps identify where old official terminology "
        "is already inherited.",
        file=out,
    )
    if not legacy_in_use:
        print("(none)", file=out)
    for occ, msgids in legacy_in_use:
        mids = " | ".join(sorted(msgids))
        print(f"{occ.path}:{occ.line}:col{occ.column}\tKO={occ.value}\tEN={mids}", file=out)
    print("", file=out)

    print("[C] RELEVANT LEGACY TRANSLATION CONFLICTS", file=out)
    print("-----------------------------------------", file=out)
    print(
        "Same English msgid has multiple Korean renderings in mm678-i18n. These are "
        "reference warnings only and must never be resolved by automatic replacement.",
        file=out,
    )
    if not conflicts:
        print("(none)", file=out)
    for msgid, options in conflicts.items():
        grouped: dict[str, set[str]] = defaultdict(set)
        for ref in options:
            grouped[ref.msgstr].add(ref.context or "(no context)")
        variants = " | ".join(
            f"{ko} [{', '.join(sorted(ctxs))}]" for ko, ctxs in sorted(grouped.items())
        )
        print(f"EN={msgid}\t{variants}", file=out)

    return out.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit KR-MMMerge against mm678-i18n's Korean legacy/retail-derived reference."
    )
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument(
        "--reference-file", type=pathlib.Path, help="local glossary.jsonl for offline runs"
    )
    parser.add_argument("--reference-url", default=REFERENCE_URL, help="reference JSONL URL")
    parser.add_argument("--output", type=pathlib.Path, help="write report to this path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    refs = load_reference(args.reference_file, args.reference_url)
    label = str(args.reference_file) if args.reference_file else args.reference_url
    report = build_report(root, refs, label)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(report, end="")
        print(f"\nReport written: {args.output}")
    else:
        print(report, end="")
    # Advisory by design: findings do not fail CI.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
