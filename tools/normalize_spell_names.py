#!/usr/bin/env python3
"""Normalize Korean spell names across the localization overlays.

The spell table, scrolls, spellbooks and dialogue were translated in separate
passes, so the same spell could appear with different transliterations or
translations. KO_SpellsTxt is treated as the canonical owner after applying
SPELL_TERMINOLOGY.tsv.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SpellTerm:
    spell_id: int
    canonical: str
    aliases: tuple[str, ...]


def load_terms(path: Path) -> dict[int, SpellTerm]:
    terms: dict[int, SpellTerm] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line_no == 1 or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            raise ValueError(f"{path}:{line_no}: expected 3 tab-separated columns")
        spell_id = int(parts[0])
        canonical = parts[1]
        aliases = tuple(item for item in parts[2].split("|") if item)
        terms[spell_id] = SpellTerm(spell_id, canonical, aliases)
    expected = set(range(1, 100))
    if set(terms) != expected:
        missing = sorted(expected - set(terms))
        extra = sorted(set(terms) - expected)
        raise ValueError(f"terminology IDs mismatch; missing={missing}, extra={extra}")
    return terms


# Only phrases unambiguous enough to normalize in arbitrary localization prose.
SAFE_GLOBAL_REPLACEMENTS = {
    "파이어 볼트": "화염 화살",
    "파이어볼": "화염구",
    "불 저항": "화염 저항",
    "파이어 스파이크": "화염 가시",
    "이몰레이션": "화염의 장막",
    "메테오 샤워": "유성우",
    "인페르노": "지옥불",
    "인시너레이트": "소각",
    "점프": "도약",
    "대기 저항": "공기 저항",
    "라이트닝 볼트": "번개 화살",
    "인비저빌리티": "투명화",
    "스타버스트": "별 폭발",
    "물 저항력": "물 저항",
    "물 걷기": "수면 보행",
    "마을 귀환": "도시 귀환",
    "로이드의 신호기": "로이드의 봉화",
    "석화 피부": "돌가죽",
    "데스 블로섬": "죽음의 꽃",
    "대규모 왜곡": "질량 왜곡",
    "생명 감지": "생명체 감지",
    "죽은 자 소생": "소생",
    "죽은 자 되살리기": "소생",
    "공포 제거": "공포 해제",
    "마인드 블래스트": "정신 폭발",
    "사이킥 쇼크": "정신 충격",
    "엔슬레이브": "노예화",
    "큐어 위크니스": "약화 치료",
    "신체 저항": "육체 저항",
    "망치 손": "망치손",
    "해머핸즈": "망치손",
    "강력 치료": "대치유",
    "위습 소환": "위스프 소환",
    "신의 날": "신들의 날",
    "프리즘 빛": "프리즘 광선",
    "신의 개입": "신성한 개입",
    "파편 금속": "금속 파편",
    "언데드 조종": "언데드 지배",
    "드래곤 브레스": "용의 숨결",
    "드래곤의 숨결": "용의 숨결",
}

# This is a distinct racial spell and must not be partially rewritten by the
# Fire Bolt alias rule.
PROTECTED_PHRASES = ("다크파이어 볼트",)



# Spell-specific wording fixes required after replacing a transliterated name
# with a Korean canonical name. These are intentionally narrow so generic
# words such as the one-syllable alias "해" are never rewritten globally.
SPELL_FIELD_REPLACEMENTS: dict[tuple[int, str], tuple[tuple[str, str], ...]] = {
    (50, "Description"): (("주문 효과가 끝날 때 보존 상태인", "주문 효과가 끝날 때 생명 보존 상태인"),),
    (70, "Description"): (("해는 8의 기본 피해", "고통은 8의 기본 피해"),),
}


def has_final_consonant(text: str) -> tuple[bool, bool]:
    """Return (has_jongseong, jongseong_is_rieul) for the last Hangul syllable."""
    for char in reversed(text):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            jong = (code - 0xAC00) % 28
            return jong != 0, jong == 8
        if char.isalnum():
            break
    return False, False


def correct_canonical_josa(text: str, canonicals: tuple[str, ...]) -> str:
    """Correct common Korean particles immediately following canonical names."""
    for name in sorted(canonicals, key=len, reverse=True):
        has_jong, rieul = has_final_consonant(name)
        correct = {
            "은": "은" if has_jong else "는",
            "는": "은" if has_jong else "는",
            "을": "을" if has_jong else "를",
            "를": "을" if has_jong else "를",
            "과": "과" if has_jong else "와",
            "와": "과" if has_jong else "와",
            "으로": "로" if (not has_jong or rieul) else "으로",
            "로": "로" if (not has_jong or rieul) else "으로",
        }
        # Require a word boundary after the particle. This avoids corrupting
        # copular forms or longer words that merely begin with the same glyph.
        for particle in ("으로", "은", "는", "을", "를", "과", "와", "로"):
            replacement = correct[particle]
            if particle != replacement:
                pattern = re.escape(name + particle) + r"(?=$|[^가-힣])"
                text = re.sub(pattern, name + replacement, text)
    return text


GLOBALTXT_CANONICAL_BY_ID = {
    6: "공기 저항",
    202: "공기 저항",
    228: "망치손",
    233: "생명 보존",
}


def replace_safe_phrases(text: str) -> str:
    protected: dict[str, str] = {}
    for index, phrase in enumerate(PROTECTED_PHRASES):
        token = f"\x00SPELL_PROTECTED_{index}\x00"
        if phrase in text:
            text = text.replace(phrase, token)
            protected[token] = phrase
    for old, new in sorted(SAFE_GLOBAL_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(old, new)
    # Explicit potion/spell references where bare "보존" is otherwise generic.
    # Negative lookbehind keeps repeated runs idempotent.
    text = re.sub(r"(?<!생명 )보존 \(", "생명 보존 (", text)
    text = re.sub(r"\+ (?<!생명 )보존", "+ 생명 보존", text)
    for token, phrase in protected.items():
        text = text.replace(token, phrase)
    canonicals = tuple(sorted(set(SAFE_GLOBAL_REPLACEMENTS.values()) | {"생명 보존"}))
    return correct_canonical_josa(text, canonicals)


def normalize_spells_overlay(path: Path, terms: dict[int, SpellTerm]) -> int:
    text = path.read_bytes().decode("cp949")
    output: list[str] = []
    changed = 0
    for line in text.splitlines(keepends=True):
        newline = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
        body = line[:-len(newline)] if newline else line
        parts = body.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            spell_id = int(parts[1].strip())
            field = parts[2].strip()
            value = parts[3]
            original = value
            term = terms.get(spell_id)
            if term and field in {"Name", "ShortName"}:
                value = term.canonical
            elif term:
                value = replace_safe_phrases(value)
                # Aliases specific to this spell are safe only when they are
                # not a substring of the canonical name and not one character.
                for alias in sorted(term.aliases, key=len, reverse=True):
                    if len(alias) > 1 and alias not in term.canonical:
                        value = value.replace(alias, term.canonical)
            # MM8 racial ability text explicitly compares itself to two spells.
            if spell_id == 123 and field == "Description":
                value = value.replace("파이어볼", "화염구").replace("드래곤 브레스", "용의 숨결")
            for old_text, new_text in SPELL_FIELD_REPLACEMENTS.get((spell_id, field), ()):
                value = value.replace(old_text, new_text)
            value = correct_canonical_josa(value, tuple(item.canonical for item in terms.values()))
            if value != original:
                changed += 1
            parts[3] = value
            body = "\t".join(parts)
        output.append(body + newline)
    path.write_bytes("".join(output).encode("cp949"))
    return changed


def normalize_items(path: Path, terms: dict[int, SpellTerm]) -> int:
    text = path.read_bytes().decode("cp949")
    alias_to_canonical: dict[str, str] = {}
    for term in terms.values():
        alias_to_canonical[term.canonical] = term.canonical
        for alias in term.aliases:
            alias_to_canonical[alias] = term.canonical

    output: list[str] = []
    changed = 0
    for line in text.splitlines(keepends=True):
        newline = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
        body = line[:-len(newline)] if newline else line
        parts = body.split("\t", 3)
        if len(parts) >= 4 and parts[0].isdigit():
            name = parts[1]
            kind = parts[2].strip()
            original_parts = tuple(parts)
            if kind in {"두루마리", "주문서", "마법서"} and name in alias_to_canonical:
                parts[1] = alias_to_canonical[name]
            parts[1] = replace_safe_phrases(parts[1])
            parts[2] = replace_safe_phrases(parts[2])
            parts[3] = replace_safe_phrases(parts[3])
            if tuple(parts) != original_parts:
                changed += 1
            body = "\t".join(parts)
        output.append(body + newline)
    path.write_bytes("".join(output).encode("cp949"))
    return changed


def normalize_globaltxt(path: Path) -> int:
    text = path.read_bytes().decode("cp949")
    output: list[str] = []
    changed = 0
    for line in text.splitlines(keepends=True):
        newline = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
        body = line[:-len(newline)] if newline else line
        parts = body.split("\t", 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            record_id = int(parts[1].strip())
            original = parts[3]
            parts[3] = GLOBALTXT_CANONICAL_BY_ID.get(record_id, replace_safe_phrases(parts[3]))
            if parts[3] != original:
                changed += 1
            body = "\t".join(parts)
        output.append(body + newline)
    path.write_bytes("".join(output).encode("cp949"))
    return changed


def normalize_other_overlays(folder: Path, excluded: set[str]) -> dict[str, int]:
    reports: dict[str, int] = {}
    for path in sorted(folder.glob("KO_*.txt")):
        if path.name in excluded:
            continue
        try:
            text = path.read_bytes().decode("cp949")
        except UnicodeDecodeError:
            continue
        normalized = replace_safe_phrases(text)
        if normalized != text:
            reports[path.name] = sum(text.count(old) for old in SAFE_GLOBAL_REPLACEMENTS)
            path.write_bytes(normalized.encode("cp949"))
    return reports


def normalize_lua_global_terms(path: Path) -> int:
    data = path.read_bytes()
    changed = 0
    for old, new in SAFE_GLOBAL_REPLACEMENTS.items():
        old_bytes = old.encode("cp949")
        new_bytes = new.encode("cp949")
        count = data.count(old_bytes)
        if count:
            data = data.replace(old_bytes, new_bytes)
            changed += count
    path.write_bytes(data)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--terms", type=Path, default=Path(__file__).with_name("SPELL_TERMINOLOGY.tsv"))
    args = parser.parse_args()
    terms = load_terms(args.terms)
    translations = args.translations

    reports: dict[str, int] = {}
    reports["KO_SpellsTxt.txt"] = normalize_spells_overlay(translations / "KO_SpellsTxt.txt", terms)
    reports["KO_ItemsTxt.txt"] = normalize_items(translations / "KO_ItemsTxt.txt", terms)
    reports["KO_GlobalTxt.txt"] = normalize_globaltxt(translations / "KO_GlobalTxt.txt")
    reports.update(normalize_other_overlays(
        translations, {"KO_SpellsTxt.txt", "KO_ItemsTxt.txt", "KO_GlobalTxt.txt"}
    ))
    root = translations.parent.parent
    lua_path = root / "Scripts/General/KoreanStatsAndSkills.lua"
    if lua_path.exists():
        reports["KoreanStatsAndSkills.lua"] = normalize_lua_global_terms(lua_path)
    for name, count in reports.items():
        print(f"{name}: {count} normalized rows/occurrences")


if __name__ == "__main__":
    main()
