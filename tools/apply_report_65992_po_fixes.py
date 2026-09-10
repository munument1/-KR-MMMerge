#!/usr/bin/env python3
"""Apply source-scoped Korean wording corrections from player report 65992.

The gettext catalog is the translation source of truth.  Every edit below is
restricted to the canonical KO source file (and, for record-specific fixes, to
its structural msgctxt suffix) so unrelated prose is never changed by a broad
repository-wide replacement.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polib


ITEM_FIXES: dict[int, list[tuple[str, str]]] = {
    837: [
        ("대침묵의 사건 12년 전에", "침묵의 시대 12년 전에"),
        ("패디쉬 총독", "파디쉬 총독"),
    ],
    894: [
        ("피낙스 제국", "피낙시아 제국"),
        ("피낙스 용기병", "피낙시아 용기병"),
    ],
    1306: [
        ("원거리 공격 피해 절반", "방패 주문 상시 유지"),
    ],
    1312: [
        ("물 속성 피해 9-12", "냉기 피해 9-12"),
    ],
    1322: [
        ("원거리 공격 피해 절반", "방패 주문 상시 유지"),
    ],
    1325: [
        ("피낙스 제국", "피낙시아 제국"),
    ],
    1333: [
        ("원거리 공격 피해 절반", "방패 주문 상시 유지"),
    ],
    2026: [
        (
            "(특수 능력: 모든 저항력 +10, 생명력 +25)",
            "(특수 능력: 방패 주문 상시 유지, 돌가죽 주문 상시 유지, 생명력 +25)",
        ),
    ],
    2028: [
        ("원거리 공격 피해 절반", "방패 주문 상시 유지"),
    ],
    2043: [
        ("방패 주문 효과 상시 유지", "방패 주문 상시 유지"),
    ],
}

CLASS_FIXES: dict[int, list[tuple[str, str]]] = {
    4: [
        (
            "강력한 빛 마법을 사용할 수 있는 유일한 직업입니다.",
            "강력한 빛 마법도 사용할 수 있습니다.",
        ),
    ],
    30: [("성직 마법", "성직자 마법")],
    42: [
        (
            "빛과 어둠으로 갈라지는 거울의 길에도 접근할 수 있습니다.",
            "빛과 어둠으로 이루어진 거울의 길에도 접근할 수 있습니다.",
        ),
    ],
    44: [
        (
            "강력한 어둠 마법을 사용할 수 있는 유일한 직업입니다.",
            "강력한 어둠 마법도 사용할 수 있습니다.",
        ),
    ],
}

SKILL_REPLACEMENTS: list[tuple[str, str]] = [
    ("방어력(AC)", "방어력"),
    ("공격 회복 시간(딜레이)", "공격 회복 시간"),
    ("최대 생명력(HP)", "최대 생명력"),
    ("최대 주문력(SP)", "최대 주문력"),
    ("방패 주문 효과 자동 부여", "방패 주문 상시 유지"),
    ("매혹(Glamour)", "매혹"),
    ("여행자의 축복(Travelers' Boon)", "여행자의 축복"),
    ("실명(Blind)", "실명"),
    ("암흑 화염(Darkfire Bolt)", "암흑 화염"),
    ("생명력 흡수(Lifedrain)", "생명력 흡수"),
    ("공중 부양(Levitate)", "공중 부양"),
    ("유혹(Charm)", "유혹"),
    ("안개 형태(Mistform)", "안개 형태"),
    ("공포(Fear)", "공포"),
    ("폭발성 브레스(Breath Weapon)", "폭발성 브레스"),
    ("비행(Flight)", "비행"),
    ("날개 치기(Wing Buffet)", "날개 치기"),
    ("스킬", "기술"),
    ("(+기술당 ", "(+기술 레벨당 "),
]

STATS_REPLACEMENTS: list[tuple[str, str]] = [
    ("스킬", "기술"),
]


def source_notes(entry: polib.POEntry) -> str:
    return "\n".join(filter(None, (entry.comment, entry.tcomment)))


def belongs_to(entry: polib.POEntry, filename: str) -> bool:
    return f"KO: Data/Text localization/{filename}" in source_notes(entry)


def find_record(po: polib.POFile, filename: str, record_id: int, field: str) -> polib.POEntry:
    suffix = f"|id={record_id}|field={field}"
    matches = [
        entry
        for entry in po
        if belongs_to(entry, filename) and (entry.msgctxt or "").endswith(suffix)
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one {filename} record {record_id}/{field}; found {len(matches)}"
        )
    return matches[0]


def replace_required(entry: polib.POEntry, old: str, new: str, label: str) -> int:
    if old in entry.msgstr:
        count = entry.msgstr.count(old)
        entry.msgstr = entry.msgstr.replace(old, new)
        return count
    if new in entry.msgstr:
        return 0
    raise SystemExit(f"{label}: neither old nor corrected text found: {old!r}")


def replace_in_source(
    po: polib.POFile,
    filename: str,
    replacements: list[tuple[str, str]],
) -> int:
    entries = [entry for entry in po if belongs_to(entry, filename)]
    if not entries:
        raise SystemExit(f"no PO entries found for {filename}")
    changed = 0
    for entry in entries:
        for old, new in replacements:
            if old in entry.msgstr:
                count = entry.msgstr.count(old)
                entry.msgstr = entry.msgstr.replace(old, new)
                changed += count
    return changed


def validate_final(po: polib.POFile) -> None:
    expected_items = {
        837: ("침묵의 시대 12년 전에", "파디쉬 총독"),
        894: ("피낙시아 제국", "피낙시아 용기병"),
        1306: ("방패 주문 상시 유지",),
        1312: ("냉기 피해 9-12",),
        1322: ("방패 주문 상시 유지",),
        1325: ("피낙시아 제국",),
        1333: ("방패 주문 상시 유지",),
        2026: ("방패 주문 상시 유지", "돌가죽 주문 상시 유지", "생명력 +25"),
        2028: ("방패 주문 상시 유지",),
        2043: ("방패 주문 상시 유지",),
    }
    for record_id, needles in expected_items.items():
        entry = find_record(po, "KO_ItemsTxt.txt", record_id, "Notes")
        for needle in needles:
            if needle not in entry.msgstr:
                raise SystemExit(f"item {record_id}: missing corrected wording {needle!r}")

    forbidden_items = {
        894: ("피낙스 제국", "피낙스 용기병"),
        1306: ("원거리 공격 피해 절반",),
        1312: ("물 속성 피해 9-12",),
        1322: ("원거리 공격 피해 절반",),
        1325: ("피낙스 제국",),
        1333: ("원거리 공격 피해 절반",),
        2026: ("모든 저항력 +10",),
        2028: ("원거리 공격 피해 절반",),
        2043: ("방패 주문 효과 상시 유지",),
    }
    for record_id, needles in forbidden_items.items():
        entry = find_record(po, "KO_ItemsTxt.txt", record_id, "Notes")
        for needle in needles:
            if needle in entry.msgstr:
                raise SystemExit(f"item {record_id}: stale wording remains: {needle!r}")

    expected_classes = {
        4: "강력한 빛 마법도 사용할 수 있습니다.",
        30: "성직자 마법",
        42: "빛과 어둠으로 이루어진 거울의 길",
        44: "강력한 어둠 마법도 사용할 수 있습니다.",
    }
    for record_id, needle in expected_classes.items():
        entry = find_record(po, "KO_ClassDescriptions.txt", record_id, "<default>")
        if needle not in entry.msgstr:
            raise SystemExit(f"class {record_id}: missing corrected wording {needle!r}")

    skill_entries = [entry for entry in po if belongs_to(entry, "KO_Skilldes.txt")]
    stats_entries = [entry for entry in po if belongs_to(entry, "KO_StatsDescriptions.tsv")]
    if any("스킬" in entry.msgstr for entry in skill_entries + stats_entries):
        raise SystemExit("스킬 remains in canonical stats/skill descriptions")
    for stale in ("(AC)", "(HP)", "(SP)", "(딜레이)"):
        if any(stale in entry.msgstr for entry in skill_entries):
            raise SystemExit(f"stale skill parenthetical remains: {stale}")
    for stale in (
        "(Glamour)", "(Travelers' Boon)", "(Blind)", "(Darkfire Bolt)",
        "(Lifedrain)", "(Levitate)", "(Charm)", "(Mistform)",
        "(Fear)", "(Breath Weapon)", "(Flight)", "(Wing Buffet)",
    ):
        if any(stale in entry.msgstr for entry in skill_entries):
            raise SystemExit(f"stale racial-skill English gloss remains: {stale}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("po", nargs="?", type=Path, default=Path("translations/ko/mmmerge.po"))
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()

    po = polib.pofile(str(args.po))
    changed = 0

    for record_id, replacements in ITEM_FIXES.items():
        entry = find_record(po, "KO_ItemsTxt.txt", record_id, "Notes")
        for old, new in replacements:
            changed += replace_required(entry, old, new, f"item {record_id}")

    for record_id, replacements in CLASS_FIXES.items():
        entry = find_record(po, "KO_ClassDescriptions.txt", record_id, "<default>")
        for old, new in replacements:
            changed += replace_required(entry, old, new, f"class {record_id}")

    changed += replace_in_source(po, "KO_Skilldes.txt", SKILL_REPLACEMENTS)
    changed += replace_in_source(po, "KO_StatsDescriptions.tsv", STATS_REPLACEMENTS)

    validate_final(po)

    if not args.check and changed:
        po.save(str(args.po))
    print(f"report 65992 PO corrections: {changed} replacements; validation OK")


if __name__ == "__main__":
    main()
