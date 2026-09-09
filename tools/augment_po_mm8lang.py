#!/usr/bin/env python3
"""Add or refresh GrayFace MM8 mm8lang.ini strings in the Korean PO catalog."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import polib


TRANSLATABLE_KEYS = (
    "RecoveryTimeInfo",
    "PlayerNotActive",
    "DoubleSpeed",
    "NormalSpeed",
    "ArmorHalvedMessage",
    "ChooseAttackSpell",
    "SetAttackSpell",
    "SwitchAttackSpell",
    "RemoveAttackSpell",
    "Duration",
    "DurationYr",
    "DurationMo",
    "DurationDy",
    "DurationHr",
    "DurationMn",
    "Energy",
    "N/A",
)
PLACEHOLDER_RE = re.compile(r"%(?:\d+\$)?[sd]")


def decode_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode mm8lang source as UTF-8 or CP949: {path}")


def read_settings(path: Path) -> dict[str, str]:
    text, _encoding = decode_text(path)
    section = ""
    values: dict[str, str] = {}
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section != "Settings" or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value
    return values


def placeholders(value: str) -> tuple[str, ...]:
    return tuple(PLACEHOLDER_RE.findall(value.replace("%%", "")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--korean", type=Path, required=True)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--po", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    ko = read_settings(args.korean)
    en = read_settings(args.english)
    missing_ko = [key for key in TRANSLATABLE_KEYS if key not in ko]
    missing_en = [key for key in TRANSLATABLE_KEYS if key not in en]
    if missing_ko or missing_en:
        raise SystemExit(f"mm8lang keys missing: Korean={missing_ko}, English={missing_en}")

    po = polib.pofile(str(args.po))
    by_context = {entry.msgctxt: entry for entry in po if not entry.obsolete and entry.msgctxt}
    added = 0
    refreshed = 0
    for key in TRANSLATABLE_KEYS:
        msgid = en[key]
        msgstr = ko[key]
        if not msgid:
            raise SystemExit(f"English mm8lang value unexpectedly empty: {key}")
        if not msgstr:
            raise SystemExit(f"Korean mm8lang value unexpectedly empty: {key}")
        if placeholders(msgid) != placeholders(msgstr):
            raise SystemExit(
                f"placeholder mismatch for {key}: {placeholders(msgid)} != {placeholders(msgstr)}"
            )
        context = f"mm8/mm8lang.ini|section=Settings|key={key}"
        entry = by_context.get(context)
        if entry is None:
            entry = polib.POEntry(
                msgctxt=context,
                msgid=msgid,
                msgstr=msgstr,
                comment=(
                    "English: might-and-magic/mm678-i18n source/en/mm8/mm8lang.ini\n"
                    "KO-ROOT: mm8lang.ini"
                ),
            )
            po.append(entry)
            added += 1
        else:
            entry.msgid = msgid
            entry.msgstr = msgstr
            if "KO-ROOT: mm8lang.ini" not in (entry.comment or ""):
                entry.comment = ((entry.comment or "").rstrip() + "\nKO-ROOT: mm8lang.ini").lstrip()
            refreshed += 1

    po.save(str(args.po))

    report = json.loads(args.report.read_text(encoding="utf-8"))
    active = [entry for entry in po if not entry.obsolete]
    translated = [entry for entry in active if entry.msgstr]
    root_files = report.setdefault("root_files", {})
    root_files["mm8lang.ini"] = {
        "entries": len(TRANSLATABLE_KEYS),
        "format": "ini",
        "source": "source/en/mm8/mm8lang.ini",
    }
    report["root_mapped_files"] = sorted(root_files, key=str.casefold)
    report["root_entries_added"] = sum(int(spec.get("entries", 0)) for spec in root_files.values())
    report["entries"] = len(active)
    report["translated"] = len(translated)
    report["untranslated"] = len(active) - len(translated)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("mm8lang PO augmentation")
    print(f"  translatable keys: {len(TRANSLATABLE_KEYS)}")
    print(f"  added:             {added}")
    print(f"  refreshed:         {refreshed}")
    print(f"  catalog entries:   {len(active)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
