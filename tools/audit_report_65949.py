#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
loc = root / "Data" / "Text localization"

TERMS = [
    "지능", "지력", "적중률", "정확도", "운", "행운", "육체", "신체",
    "저항력", "대기 마법", "흙 마법", "물건", "날카로행운", "아름다행운",
    "가까행운", "기행운", "불행운", "불행운하게", "이동 속도",
]

ITEMS = {
    "종결", "교수대", "구울베인", "철깃털", "아르테미스", "샤렐", "황수정",
    "타이탄의 허리띠", "매시", "어먹", "파쇄자", "율리시스", "웜 스피터",
    "통치자의 반지", "융합의 반지", "칠 리그 장화", "올드 닉", "아이기스",
    "통치의 삼지창", "하데스", "메코리그의 망치", "헤라", "아니아 셀빙",
    "롱시커", "펠리노어", "수호자", "아프로디테", "크로노스", "탈레돈의 투구",
    "토르", "퍼시벌", "최상급 판금 갑옷", "전령의 장화", "드래곤 터틀의 송곳니",
    "데빌 체액 약병", "현자의 돌", "피르나 뿌리", "다투라",
}


def decode(path: pathlib.Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("unknown", b"", 0, 1, str(path))


def source_occurrences() -> None:
    print("== term counts by localization source ==")
    for path in sorted(loc.glob("KO_*.txt")):
        try:
            text = decode(path)
        except UnicodeDecodeError:
            continue
        counts = [(t, text.count(t)) for t in TERMS if text.count(t)]
        if counts:
            print(path.name + ": " + ", ".join(f"{t}={n}" for t, n in counts))

    print("\n== suspicious substring corruption ==")
    suspicious = ["날카로행운", "아름다행운", "가까행운", "기행운", "불행운"]
    for path in sorted(loc.glob("KO_*.txt")):
        try:
            text = decode(path)
        except UnicodeDecodeError:
            continue
        for no, line in enumerate(text.splitlines(), 1):
            if any(t in line for t in suspicious):
                print(f"{path.name}:{no}: {line}")


def item_rows() -> None:
    path = loc / "KO_ItemsTxt.txt"
    text = decode(path)
    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    print("\n== reported item rows ==")
    found = set()
    for row in rows:
        name = (row.get("Name") or "").strip()
        if name in ITEMS:
            found.add(name)
            print(f"ID={row.get('Id','')} NAME={name}")
            print("  NotIdentifiedName=" + (row.get("NotIdentifiedName ") or row.get("NotIdentifiedName") or ""))
            print("  Notes=" + (row.get("Notes") or ""))
    missing = sorted(ITEMS - found)
    if missing:
        print("\nNOT FOUND BY CURRENT KOREAN NAME: " + ", ".join(missing))


if __name__ == "__main__":
    source_occurrences()
    item_rows()
