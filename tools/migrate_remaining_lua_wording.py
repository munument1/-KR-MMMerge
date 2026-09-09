#!/usr/bin/env python3
"""One-time migration of remaining canonical Korean wording out of runtime Lua.

This moves player-facing text that already has (or should have) a static owner
into Data/Text localization, while leaving genuinely dynamic CustomUI wording
in Lua.  The migration is deliberately strict and fails if the expected old
structure is no longer present.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data" / "Text localization"
SCRIPTS = ROOT / "Scripts"

HIRELING_TEXT = {
    2324: "모든 캐릭터의 학습 기술에 +5 보너스를 주고 아이템을 무제한으로 식별합니다. 학습 숙련도 배율이 적용됩니다.",
    2333: "모든 캐릭터의 학습 기술에 +10 보너스를 줍니다. 학습 숙련도 배율이 적용됩니다.",
    2334: "모든 캐릭터의 학습 기술에 +15 보너스를 줍니다. 학습 숙련도 배율이 적용됩니다.",
}

MM6_HISTORY = (
    "#\tText\tTime\tPage Title\r"
    "1\t엔로스의 역사는 별똥별의 밤과 함께 시작됩니다. 아이언피스트 왕 롤랜드가 실종되고 "
    "크리건의 침공으로 스위트 워터가 파괴된 뒤, 여섯 영주가 왕국의 운명을 둘러싸고 대립합니다. "
    "여러분은 뉴 소피갈에서 여정을 시작해 여섯 영주의 승인을 얻고, 프리 헤이븐의 오라클을 복구하여 "
    "크리건을 물리칠 방법을 찾아야 합니다.\tForward\t엔로스 연대기\r"
)


def read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp949"), "cp949"


def write_text(path: Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def replace_regex(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one replacement, got {count}")
    return updated


def update_npc_text() -> None:
    path = DATA / "KO_NPCText.txt"
    text, encoding = read_text(path)
    for record_id, replacement in HIRELING_TEXT.items():
        pattern = rf"(?m)^(\t{record_id}\t\t)[^\r\n]*"
        text, count = re.subn(pattern, lambda m, r=replacement: m.group(1) + r, text, count=1)
        if count != 1:
            raise RuntimeError(f"KO_NPCText: could not replace NPCText[{record_id}]")
    write_text(path, text, encoding)


def update_runtime_manifest() -> None:
    path = ROOT / "config" / "runtime_override_keys.tsv"
    text, encoding = read_text(path)
    newline = "\r\n" if "\r\n" in text else "\n"
    additions = []
    for record_id in HIRELING_TEXT:
        marker = f"NPCText\t{record_id}\t\t"
        if marker not in text:
            additions.append(marker)
    if additions:
        if not text.endswith(("\n", "\r")):
            text += newline
        text += newline.join(additions) + newline
    write_text(path, text, encoding)


def update_reported_localization() -> None:
    path = SCRIPTS / "General" / "ZZ_KoreanReportedLocalization.lua"
    text, encoding = read_text(path)

    replacement = '''local HIRELING_LEARNING_DESCRIPTIONS = {
    [4] = 2324,
    [13] = 2333,
    [14] = 2334
}

local function applyHirelingLearningDescriptions()
    if not Game or not Game.NPCText or not Game.NPCProf then
        return
    end

    for profession, npcTextId in pairs(HIRELING_LEARNING_DESCRIPTIONS) do
        local localized = Game.NPCText[npcTextId]
        if type(localized) == "string" and localized ~= "" and Game.NPCProf[profession] then
            -- NPCProf.Description is a derived copy. Reuse the canonical
            -- NPCText wording instead of maintaining a second translation.
            Game.NPCProf[profession].Description = localized
        end
    end
end
'''
    text = replace_regex(
        text,
        r"local HIRELING_LEARNING_DESCRIPTIONS = \{.*?\nend\n(?=\n-- Experience/GlobalTxt)",
        replacement.rstrip("\n"),
        "hireling wording block",
        flags=re.S,
    )

    text = replace_regex(
        text,
        r"\n-- The compact MM7 history table embedded.*?(?=\nfunction events\.GameInitialized2)",
        "\n",
        "duplicate MM7 foreword block",
        flags=re.S,
    )
    text = text.replace("    applyMM7Foreword()\n", "")
    text = text.replace("KoreanReportedLocalization.ApplyMM7Foreword = applyMM7Foreword\n", "")

    if "MM7_FOREWORD" in text or "applyMM7Foreword" in text:
        raise RuntimeError("MM7 foreword duplicate still exists in reported localization")
    write_text(path, text, encoding)


def update_history() -> None:
    path = SCRIPTS / "General" / "KoreanHistory.lua"
    text, encoding = read_text(path)

    old_sources = '''\t[2] = {
\t\tLocalized = "Data/Text localization/MM7History_KO.txt",
\t\tFallback = "mm7history.txt"
\t}
}'''
    new_sources = '''\t[2] = {
\t\tLocalized = "Data/Text localization/MM7History_KO.txt",
\t\tFallback = "mm7history.txt"
\t},
\t[3] = {
\t\tLocalized = "Data/Text localization/MM6History_KO.txt"
\t}
}'''
    if old_sources not in text:
        raise RuntimeError("KoreanHistory: HistorySources structure changed")
    text = text.replace(old_sources, new_sources, 1)

    text = replace_regex(
        text,
        r"\nlocal MM6Introduction = \{.*?\n\}\n",
        "\n",
        "MM6Introduction literal block",
        flags=re.S,
    )
    text = text.replace(
        'if (not data or data == "") and Game.LoadTextFileFromLod then',
        'if (not data or data == "") and source.Fallback and Game.LoadTextFileFromLod then',
        1,
    )
    text = replace_regex(
        text,
        r"\n\tif continent == 3 then\n.*?\n\tend\n\n\tlocal records = loadHistoryRecords\(continent\)",
        "\n\tlocal records = loadHistoryRecords(continent)",
        "MM6 hard-coded history application",
        flags=re.S,
    )
    if "MM6Introduction" in text:
        raise RuntimeError("MM6Introduction literal still exists")
    write_text(path, text, encoding)

    history_path = DATA / "MM6History_KO.txt"
    history_path.write_bytes(MM6_HISTORY.encode("utf-8"))


def update_validator() -> None:
    path = SCRIPTS / "General" / "ZZ_KoreanLocalizationValidator.lua"
    text, encoding = read_text(path)

    replacement = r'''local function expectedRuntimeValue(TableName, Id, Field)
	local Localization = rawget(_G, "KoreanLocalization")
	if type(Localization) ~= "table" or type(Localization.GetExpectedRuntimeValues) ~= "function" then
		return nil
	end
	local Values = Localization.GetExpectedRuntimeValues()
	if type(Values) ~= "table" then
		return nil
	end
	local Key = tostring(TableName) .. "\31" .. tostring(Id) .. "\31" .. tostring(Field or "")
	local Entry = Values[Key]
	return type(Entry) == "table" and Entry.Value or nil
end

local function validateMergePromotionStrings(State)
	if not Game or not Game.GlobalTxt then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Game.GlobalTxt is unavailable for the Merge promotion-string check.")
		return
	end

	local Contracts = {
		[632] = 1,
		[633] = 1,
		[634] = 0
	}
	for Id, ExpectedPlaceholders in pairs(Contracts) do
		local Ok, Value = pcall(function() return Game.GlobalTxt[Id] end)
		if not Ok or type(Value) ~= "string" then
			addIssue(State, "ERROR", "<runtime>", nil,
				"Cannot read Game.GlobalTxt[" .. tostring(Id) .. "] for the Merge promotion-string check.")
		else
			local ActualPlaceholders = countLiteral(Value, "%s")
			if ActualPlaceholders ~= ExpectedPlaceholders then
				addIssue(State, "ERROR", "<runtime>", nil,
					"Game.GlobalTxt[" .. tostring(Id) .. "] has " ..
					tostring(ActualPlaceholders) .. " %s placeholder(s); Merge requires " ..
					tostring(ExpectedPlaceholders) .. ". GlobalTxt[634] is only the class-name separator.")
			end
		end
	end

	local ExpectedSeparator = expectedRuntimeValue("GlobalTxt", 634, "")
	local Ok, Separator = pcall(function() return Game.GlobalTxt[634] end)
	if type(ExpectedSeparator) ~= "string" then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Canonical runtime value for Game.GlobalTxt[634] is unavailable.")
	elseif Ok and type(Separator) == "string" and Separator ~= ExpectedSeparator then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Game.GlobalTxt[634] differs from its canonical Korean runtime value.")
	end
end

local function validateKoreanGlobalContracts(State)
	if not Game or not Game.GlobalTxt then
		addIssue(State, "ERROR", "<runtime>", nil,
			"Game.GlobalTxt is unavailable for the Korean terminology and training-string checks.")
		return
	end

	local ContractIds = {18, 34, 79, 168, 170, 172, 203, 433, 537, 538}
	for _, Id in ipairs(ContractIds) do
		local Expected = expectedRuntimeValue("GlobalTxt", Id, "")
		local Ok, Actual = pcall(function() return Game.GlobalTxt[Id] end)
		if type(Expected) ~= "string" then
			addIssue(State, "ERROR", "<runtime>", nil,
				"Canonical runtime value for Game.GlobalTxt[" .. tostring(Id) .. "] is unavailable.")
		elseif not Ok or type(Actual) ~= "string" then
			addIssue(State, "ERROR", "<runtime>", nil,
				"Cannot read Game.GlobalTxt[" .. tostring(Id) .. "] for the Korean contract check.")
		elseif Actual ~= Expected then
			addIssue(State, "ERROR", "<runtime>", nil,
				"Game.GlobalTxt[" .. tostring(Id) .. "] differs from the canonical Korean text or placeholder order.")
		end
	end
end
'''
    text = replace_regex(
        text,
        r"local function validateMergePromotionStrings\(State\).*?(?=\nlocal function validateTargetedMapHints\(State\))",
        replacement.rstrip("\n"),
        "validator canonical contract functions",
        flags=re.S,
    )
    text = replace_regex(
        text,
        r"\nlocal function validateTargetedMapHints\(State\).*?(?=\nlocal function validateGlobalFormatHook\(State\))",
        "\n",
        "retired targeted map hint validator",
        flags=re.S,
    )
    text = text.replace("\tvalidateTargetedMapHints(State)\n", "")
    if "TranslateTargetedMapHint" in text or "validateTargetedMapHints" in text:
        raise RuntimeError("retired map-hint validation still exists")

    if '"MM6History_KO.txt"' not in text:
        marker = '\t"MM7History_KO.txt",'
        if marker not in text:
            raise RuntimeError("validator expected-file list marker not found")
        text = text.replace(marker, '\t"MM6History_KO.txt",\n' + marker, 1)
    write_text(path, text, encoding)


def update_localize_tables() -> None:
    path = SCRIPTS / "General" / "LocalizeTables.lua"
    text, encoding = read_text(path)
    text = replace_regex(
        text,
        r"\nlocal function applyFixedOverrides\(\).*?\nend\n(?=\n-- First pass:)",
        "\n",
        "dead fixed NPCNews override",
        flags=re.S,
    )
    if "applyFixedOverrides" in text:
        raise RuntimeError("dead applyFixedOverrides block still exists")
    write_text(path, text, encoding)


def update_out01() -> None:
    path = SCRIPTS / "Maps" / "out01.lua"
    text, encoding = read_text(path)
    replacement = '''-- Dagger Wound Island cannon prompt fallback. The static STR translation is
-- canonical; reuse its localized string for map-script hint ids instead of
-- maintaining a second Korean literal here.
local KoreanCannonHint = evt.str[13]
if type(KoreanCannonHint) == "string" and KoreanCannonHint ~= "" then
	evt.hint[457] = KoreanCannonHint
	evt.hint[458] = KoreanCannonHint
end'''
    text = replace_regex(
        text,
        r"\A-- Dagger Wound Island cannon prompt fallback\..*?(?=\n\n-- Dimension door)",
        replacement,
        "out01 cannon hint fallback",
        flags=re.S,
    )
    write_text(path, text, encoding)


def verify() -> None:
    reported, _ = read_text(SCRIPTS / "General" / "ZZ_KoreanReportedLocalization.lua")
    validator, _ = read_text(SCRIPTS / "General" / "ZZ_KoreanLocalizationValidator.lua")
    history, _ = read_text(SCRIPTS / "General" / "KoreanHistory.lua")
    localize, _ = read_text(SCRIPTS / "General" / "LocalizeTables.lua")
    out01, _ = read_text(SCRIPTS / "Maps" / "out01.lua")
    forbidden = {
        "reported MM7 duplicate": "MM7_FOREWORD" in reported or "applyMM7Foreword" in reported,
        "reported hireling literal": "학습 숙련도 배율이 적용됩니다" in reported,
        "validator retired map hint": "TranslateTargetedMapHint" in validator,
        "history MM6 literal": "MM6Introduction" in history,
        "localize stale override": "applyFixedOverrides" in localize,
        "out01 Korean literal": "대포 발사" in out01,
    }
    bad = [name for name, present in forbidden.items() if present]
    if bad:
        raise RuntimeError("migration verification failed: " + ", ".join(bad))
    if not (DATA / "MM6History_KO.txt").is_file():
        raise RuntimeError("MM6History_KO.txt was not created")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="apply migration")
    args = parser.parse_args()
    if not args.write:
        parser.error("--write is required")

    update_npc_text()
    update_runtime_manifest()
    update_reported_localization()
    update_history()
    update_validator()
    update_localize_tables()
    update_out01()
    verify()
    print("remaining Lua wording migration: OK")
    print("  corrected canonical hireling NPCText: 3")
    print("  removed duplicate MM7 foreword owner: 1")
    print("  externalized MM6 history owner: 1")
    print("  retired validator literal contracts: 12")
    print("  removed dead NPCNews fixed literal: 1")
    print("  reused canonical OUT01 STR hint: 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
