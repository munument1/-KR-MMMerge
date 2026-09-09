#!/usr/bin/env python3
"""Audit the staged Korean gettext catalog used by the MMMerge patch.

This intentionally checks completeness itself instead of treating an external
PO checker as proof that the catalog is complete.  The mm678-i18n checker skips
empty and fuzzy entries, which is useful for content QA but not for coverage.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

try:
    import polib
except ImportError as exc:  # pragma: no cover - dependency error is user-facing
    raise SystemExit("polib is required: python -m pip install polib") from exc


def collect_stats(po_path: Path, source_revision: str = "") -> dict:
    po = polib.pofile(str(po_path))
    active = [entry for entry in po if not entry.obsolete]
    obsolete = [entry for entry in po if entry.obsolete]

    fuzzy = [entry for entry in active if "fuzzy" in entry.flags]
    untranslated = [entry for entry in active if not entry.msgstr]
    reviewed = [
        entry for entry in active
        if entry.msgstr and "fuzzy" not in entry.flags
    ]
    translated_raw = [entry for entry in active if entry.msgstr]

    keys = [(entry.msgctxt or "", entry.msgid) for entry in active]
    duplicate_keys = sum(count - 1 for count in Counter(keys).values() if count > 1)
    replacement_chars = sum(entry.msgstr.count("\ufffd") for entry in active if entry.msgstr)
    contexts = Counter(entry.msgctxt or "<none>" for entry in active)

    total = len(active)
    return {
        "schema": 1,
        "language": po.metadata.get("Language", ""),
        "source_revision": source_revision,
        "total": total,
        "translated_raw": len(translated_raw),
        "reviewed_translated": len(reviewed),
        "untranslated": len(untranslated),
        "fuzzy": len(fuzzy),
        "obsolete": len(obsolete),
        "duplicate_keys": duplicate_keys,
        "replacement_chars": replacement_chars,
        "reviewed_percent": round((len(reviewed) * 100.0 / total), 3) if total else 0.0,
        "top_contexts": contexts.most_common(20),
    }


def print_stats(stats: dict) -> None:
    print("Korean gettext catalog")
    print(f"  language:            {stats['language'] or '<unset>'}")
    print(f"  active entries:      {stats['total']}")
    print(f"  reviewed translated: {stats['reviewed_translated']} ({stats['reviewed_percent']}%)")
    print(f"  untranslated:        {stats['untranslated']}")
    print(f"  fuzzy:               {stats['fuzzy']}")
    print(f"  obsolete:            {stats['obsolete']}")
    print(f"  duplicate keys:      {stats['duplicate_keys']}")
    print(f"  replacement chars:   {stats['replacement_chars']}")
    if stats.get("source_revision"):
        print(f"  source revision:     {stats['source_revision']}")


def compare_baseline(stats: dict, baseline: dict) -> list[str]:
    problems: list[str] = []
    if stats["total"] != baseline.get("total"):
        problems.append(
            f"active entry count changed: {baseline.get('total')} -> {stats['total']}"
        )
    if stats["reviewed_translated"] < baseline.get("reviewed_translated", 0):
        problems.append(
            "reviewed translations decreased: "
            f"{baseline.get('reviewed_translated')} -> {stats['reviewed_translated']}"
        )
    if stats["untranslated"] > baseline.get("untranslated", stats["untranslated"]):
        problems.append(
            f"untranslated entries increased: {baseline.get('untranslated')} -> {stats['untranslated']}"
        )
    if stats["fuzzy"] > baseline.get("fuzzy", stats["fuzzy"]):
        problems.append(f"fuzzy entries increased: {baseline.get('fuzzy')} -> {stats['fuzzy']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("po", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--no-regress", action="store_true")
    parser.add_argument("--fail-fuzzy", action="store_true")
    parser.add_argument("--min-translated", type=int, default=0)
    parser.add_argument("--source-revision", default="")
    args = parser.parse_args()

    if not args.po.is_file():
        print(f"missing PO: {args.po}", file=sys.stderr)
        return 2

    stats = collect_stats(args.po, args.source_revision)
    print_stats(stats)

    problems: list[str] = []
    if stats["language"] not in ("ko", "ko_KR"):
        problems.append(f"unexpected Language metadata: {stats['language']!r}")
    if stats["reviewed_translated"] < args.min_translated:
        problems.append(
            f"only {stats['reviewed_translated']} reviewed translations; "
            f"minimum is {args.min_translated}"
        )
    if stats["duplicate_keys"]:
        problems.append(f"duplicate (msgctxt, msgid) keys: {stats['duplicate_keys']}")
    if stats["replacement_chars"]:
        problems.append(f"Unicode replacement characters in translations: {stats['replacement_chars']}")
    if args.fail_fuzzy and stats["fuzzy"]:
        problems.append(f"fuzzy entries are not allowed: {stats['fuzzy']}")

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        if args.no_regress:
            problems.extend(compare_baseline(stats, baseline))

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if problems:
        print("\nPO audit failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("PO audit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
