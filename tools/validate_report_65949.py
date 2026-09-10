#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"


def decode(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"cannot decode {path}")


def item_rows() -> dict[int, dict[str, str]]:
    text = decode(loc / "KO_ItemsTxt.txt")
    rows = csv.DictReader(io.StringIO(text), delimiter="\t")
    return {int(row["Id"]): row for row in rows if (row.get("Id") or "").isdigit()}


def note(rows, item_id: int) -> str:
    return rows[item_id].get("Notes", "")


rows = item_rows()

# Canonical player-facing stat / magic terminology.
global_text = decode(loc / "KO_GlobalTxt.txt")
for expected in [
    "\t1\t\t정확도", "\t75\t\t인내력", "\t136\t\t운", "\t211\t\t민첩성",
    "\t284\t\t공기 마법", "\t286\t\t대지 마법", "\t291\t\t육체 마법",
]:
    if expected not in global_text:
        raise SystemExit(f"missing canonical GlobalTxt row: {expected}")

stats = (loc / "KO_StatsDescriptions.tsv").read_text(encoding="utf-8-sig")
for expected in [
    "인내력은 캐릭터의 육체적 강인함",
    "정확도는 캐릭터의 조준 능력",
    "민첩성은 캐릭터가 얼마나 빠르고 민첩하게",
    "장착한 원거리 무기로 몬스터를",
    "육체 저항은 육체 계열 공격으로",
]:
    if expected not in stats:
        raise SystemExit(f"missing stats correction: {expected}")

# Item names/details directly covered by the report.
assert rows[506]["Name"] == "웜 스피터"  # Wyrm Spitter, not Wyrm Splitter.
assert rows[208]["Name"] == "흰독말풀"
assert rows[1016]["Name"] == "악마의 피 약병"
assert "황수정" in note(rows, 179) and "시트린" not in note(rows, 179)
assert "드래곤 터틀의 송곳니" in note(rows, 209)
assert "철깃털" in note(rows, 1303) and "아이언 페더" not in note(rows, 1303)
assert "명중 시 폭발" in note(rows, 1308)
assert "구울베인" in note(rows, 1309) and "구울스베인" not in note(rows, 1309)
assert "교수대" in note(rows, 1310) and "기벳" not in note(rows, 1310)
assert "제작된 샤렐" in note(rows, 1311) and "이 창은" in note(rows, 1311) and "에라시아" in note(rows, 1311)
assert "율리시스" in note(rows, 1312) and "울리세스" not in note(rows, 1312)
assert "(민첩성 +40, 물 마법)" in note(rows, 1314)
assert "(정신 마법, 어둠 마법)" in note(rows, 1315)
assert "매시" in note(rows, 1316) and "마쉬" not in note(rows, 1316)
assert "함정 해제 기술 +5" in note(rows, 1319)
assert "이 검의 날은 여전히 마법처럼 날카롭고" in note(rows, 1320)
assert "갑작스러운 죽음" in note(rows, 1323) and "부정적인 기운" in note(rows, 1323) and "불운하게" in note(rows, 1323)
assert "타이탄의 허리띠" in note(rows, 1326)
assert "활 기술 +5" in note(rows, 1328)
assert "원소와 연결되어 있어" in note(rows, 1330) and "원소 마법에 취약하지만" in note(rows, 1330)
assert "명중한 적을 밀쳐냄" in note(rows, 2021)
assert "공격 회복 속도 증가, 명중 시 폭발" in note(rows, 2025)
assert "피격 회복 속도 증가" in note(rows, 2027) and "휘청이는 시간을 줄여줍니다" in note(rows, 2027)
assert "생명력 지속 감소" in note(rows, 2035) and "재생력 +10" not in note(rows, 2035)
assert "가까운 크로노스" in note(rows, 2038)
assert "아르테미스" in note(rows, 2040) and "아르테무스" not in note(rows, 2040)
assert "석화 면역, 방패 주문 상시 유지, 운 +20, 민첩성 -20" in note(rows, 2043)
assert "아름다운 반지" in note(rows, 2047) and "불운의 저주" in note(rows, 2047)
assert "이 목걸이를 착용하는 동안" in note(rows, 2049)
assert "(모든 능력치 +10," in note(rows, 507)
assert "물 저항 +70, 화염 저항 -70" in note(rows, 528)
assert "공격 회복 속도 감소, 민첩성 -20" in note(rows, 525)

# Regression guard against the destructive "운" -> "행운" substring pass.
items_text = decode(loc / "KO_ItemsTxt.txt")
for bad in ["날카로행운", "아름다행운", "가까행운", "갑작스러행운", "기행운", "불행운"]:
    if bad in items_text:
        raise SystemExit(f"substring corruption remains: {bad}")

# Recovery-time text comes from mm8lang.ini, not stats.txt.
lang = (root / "mm8lang.ini").read_bytes().decode("cp949")
if "RecoveryTimeInfo=회복 시간: %d" not in lang:
    raise SystemExit("mm8lang.ini RecoveryTimeInfo is not localized")

print("report 65949 validation: OK")
