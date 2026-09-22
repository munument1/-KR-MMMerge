#!/usr/bin/env python3
"""Apply terminology fixes from RPG gallery report 66263.

The report targets player-facing terminology that still drifted after v1.0.33.
The canonical gettext catalog remains the source of truth.  Generic prose is
left alone unless the reported term is an unambiguous proper name or spell name.
"""
from __future__ import annotations

import pathlib
import re
import sys

import polib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
PO = ROOT / "translations" / "ko" / "mmmerge.po"

# Exact contexts that need a semantic fix rather than a safe global terminology
# replacement.
EXACT_REPLACEMENTS: tuple[tuple[str, str, str], ...] = (
    (
        "mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=25|field=<default>",
        "중립",
        "잔고",
    ),
    (
        "mmmerge/inherited/mm8/Skilldes.txt|table=SkillNames|id=18|field=<default>",
        "신체 마법",
        "육체 마법",
    ),
    (
        "mmmerge/inherited/mm8/Skilldes.txt|table=SkillDescriptions|id=18|field=<default>",
        "신체 계열 마법 숙련도입니다.",
        "육체 계열 마법 숙련도입니다.",
    ),
    (
        "mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=73|field=Description",
        "신체 속성 추가 피해",
        "육체 속성 추가 피해",
    ),
    (
        "mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=85|field=Description",
        "정신, 신체 보호 주문",
        "정신, 육체 보호 주문",
    ),
    (
        "mmmerge/Text localization/LANG_NPCText.txt|table=NPCText|id=1044|field=<default>",
        "우리 주문은 몸을 치유하기만 한다고 생각하지만, 상대의 몸에 피해를 주는 주문도 있습니다.",
        "우리 주문은 육체를 치유하기만 한다고 생각하지만, 상대의 육체에 피해를 주는 주문도 있습니다.",
    ),
    (
        "mmmerge/Text localization/LANG_StdItemsTxtNames.txt|table=StdItemsTxt|id=1|field=NameAdd",
        "[지력]",
        "[지능]",
    ),
    (
        "mmmerge/Text localization/LANG_SpcItemsTxtStats.txt|table=SpcItemsTxt|id=29|field=BonusStat",
        "모든 불 계열 주문의 효과가 증가합니다.",
        "모든 화염 계열 주문의 효과가 증가합니다.",
    ),
    (
        "mmmerge/Text localization/LANG_ItemsTxt.txt|id=223|field=NotIdentifiedName",
        "푸른색 물약",
        "파란색 물약",
    ),
    (
        "mmmerge/Text localization/LANG_ItemsTxt.txt|id=1767|field=NotIdentifiedName",
        "푸른색 물약",
        "파란색 물약",
    ),
)

# Already-correct v1.0.33 fixes mentioned again in the report.  Keep them as
# regression assertions so this pass cannot accidentally restore the old terms.
REQUIRED_EXISTING: tuple[tuple[str, str], ...] = (
    (
        "mmmerge/Text localization/LANG_StdItemsTxtStats.txt|table=StdItemsTxt|id=1|field=BonusStat",
        "지능",
    ),
    (
        "mmmerge/Text localization/LANG_SpcItemsTxtStats.txt|table=SpcItemsTxt|id=50|field=BonusStat",
        "민첩성",
    ),
    (
        "mmmerge/Text localization/LANG_SpcItemsTxtStats.txt|table=SpcItemsTxt|id=42|field=BonusStat",
        "인내력",
    ),
    (
        "mmmerge/Text localization/LANG_SpcItemsTxtNames.txt|table=SpcItemsTxt|id=29|field=NameAdd",
        "[화염 마법]",
    ),
)

PERSONALITY_RE = re.compile(r"인격(?!적|체)")


def context_map(po: polib.POFile) -> dict[str, polib.POEntry]:
    result: dict[str, polib.POEntry] = {}
    for entry in po:
        if not entry.msgctxt:
            continue
        if entry.msgctxt in result:
            raise SystemExit(f"duplicate PO context: {entry.msgctxt}")
        result[entry.msgctxt] = entry
    return result


def replace_exact(entry: polib.POEntry, old: str, new: str) -> int:
    if old in entry.msgstr:
        entry.msgstr = entry.msgstr.replace(old, new)
        return 1
    if new in entry.msgstr:
        return 0
    raise SystemExit(
        f"{entry.msgctxt}: expected old/new wording not found: {old!r} -> {new!r}; "
        f"actual={entry.msgstr!r}"
    )


def main() -> None:
    po = polib.pofile(str(PO), encoding="utf-8")
    by_context = context_map(po)
    changed_entries = 0
    counts = {
        "tour": 0,
        "avlee": 0,
        "personality": 0,
        "stone_skin": 0,
        "exact": 0,
    }

    # Safe catalog-wide terminology replacements.
    for entry in po:
        original = entry.msgstr
        text = original

        if "관광" in text:
            counts["tour"] += text.count("관광")
            text = text.replace("관광", "안내")

        avlee_count = text.count("아블리") + text.count("애블리")
        if avlee_count:
            counts["avlee"] += avlee_count
            text = text.replace("아블리", "에이블리").replace("애블리", "에이블리")

        text, n = PERSONALITY_RE.subn("인성", text)
        counts["personality"] += n

        stone_count = text.count("돌가죽") + text.count("석피") + text.count("석화 피부")
        if stone_count:
            counts["stone_skin"] += stone_count
            text = text.replace("석화 피부", "석갑").replace("돌가죽", "석갑").replace("석피", "석갑")

        if text != original:
            entry.msgstr = text
            changed_entries += 1

    # Context-sensitive fixes.
    for ctx, old, new in EXACT_REPLACEMENTS:
        entry = by_context.get(ctx)
        if entry is None:
            raise SystemExit(f"missing PO context: {ctx}")
        before = entry.msgstr
        counts["exact"] += replace_exact(entry, old, new)
        if entry.msgstr != before and before == original if False else False:
            pass

    # The previous loop may have already counted an entry as changed.  Recount
    # directly to keep the printed number accurate and deterministic.
    changed_entries = sum(1 for entry in po if entry.msgstr != "")
    # changed_entries above is informational only; actual write is based on
    # whether the serialized catalog differs, so idempotent reruns are safe.

    # Final report-specific assertions.
    failures: list[str] = []
    for entry in po:
        text = entry.msgstr
        if "관광" in text:
            failures.append(f"{entry.msgctxt}: 관광 remains")
        if "아블리" in text or "애블리" in text:
            failures.append(f"{entry.msgctxt}: old Avlee transliteration remains")
        if PERSONALITY_RE.search(text):
            failures.append(f"{entry.msgctxt}: stat term 인격 remains")
        if "돌가죽" in text or "석피" in text or "석화 피부" in text:
            failures.append(f"{entry.msgctxt}: old Stone Skin term remains")

    # Protect unrelated Korean words that merely contain 인격.
    protected = [entry.msgstr for entry in po if "인격적" in entry.msgstr or "인격체" in entry.msgstr]
    if not any("인격적" in text for text in protected):
        failures.append("protected prose term 인격적 was lost")
    if not any("인격체" in text for text in protected):
        failures.append("protected noun 인격체 was lost")

    for ctx, expected in REQUIRED_EXISTING:
        entry = by_context.get(ctx)
        if entry is None or expected not in entry.msgstr:
            failures.append(f"{ctx}: expected regression guard {expected!r}")

    # Spot-check the new canonical forms.
    expected_exact = {
        "mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=25|field=<default>": "잔고",
        "mmmerge/inherited/mm8/Skilldes.txt|table=SkillNames|id=18|field=<default>": "육체 마법",
        "mmmerge/Text localization/LANG_StdItemsTxtNames.txt|table=StdItemsTxt|id=1|field=NameAdd": "[지능]",
        "mmmerge/Text localization/LANG_ItemsTxt.txt|id=223|field=NotIdentifiedName": "파란색 물약",
        "mmmerge/Text localization/LANG_ItemsTxt.txt|id=1767|field=NotIdentifiedName": "파란색 물약",
        "mmmerge/inherited/mm8/Spells.txt|table=SpellsTxt|id=38|field=Name": "석갑",
        "mmmerge/inherited/mm8/Global.txt|table=GlobalTxt|id=163|field=<default>": "인성",
    }
    for ctx, expected in expected_exact.items():
        entry = by_context.get(ctx)
        if entry is None or entry.msgstr != expected:
            failures.append(f"{ctx}: expected {expected!r}, got {None if entry is None else entry.msgstr!r}")

    if failures:
        raise SystemExit("report 66263 verification failed:\n" + "\n".join(failures[:50]))

    before = PO.read_text(encoding="utf-8")
    po.save(str(PO))
    after = PO.read_text(encoding="utf-8")
    if before == after:
        print("report 66263 terminology: already applied")
    else:
        print(
            "report 66263 terminology applied: "
            f"tour={counts['tour']}, avlee={counts['avlee']}, "
            f"personality={counts['personality']}, stone_skin={counts['stone_skin']}, "
            f"exact={counts['exact']}"
        )


if __name__ == "__main__":
    main()
