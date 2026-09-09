# MMMerge 한국어 PO 작업 흐름

이 저장소의 일반 번역 편집 원본은 이제 GNU gettext 카탈로그인
`translations/ko/mmmerge.po`이다.

`Data/Text localization/KO_*.txt` / `KO_*.tsv`는 게임이 읽는 형식을 유지하기
위한 materialized runtime source이며, 일반 번역 문구를 직접 수정하는 원본으로
사용하지 않는다.

## 현재 상태

현재 카탈로그 기준:

- 활성 항목: **25,034**
- 번역 완료: **25,034 / 25,034 (100%)**
- 미번역: **0**
- fuzzy: **0**
- 중복 `(msgctxt, msgid)`: **0**
- Unicode replacement character: **0**
- PO가 관리하는 canonical Korean 파일: **30개**
- PO에서 직접 생성하지 않는 runtime projection:
  - `KO_RuntimeOverrides.txt`
  - `KO_StatsSkillsRuntime.txt`

영어 원문 기준은 다음 `mm678-i18n` revision에 고정되어 있다.

`aea1b22666ef556f34a71b4f3945904b04de1466`

## 번역 출처

`mm678-i18n`에서는 영어 원문 구조와 도구 아이디어만 사용한다.

**`mm678-i18n`의 한국어 `msgstr`은 가져오지 않는다.**

현재 PO의 한국어 번역은 이 저장소에 이미 존재하던 MMMerge 한국어 번역을
영어 원문과 구조적으로 대응시켜 최초 이식한 것이다. 초기 이식 과정에서도
LOD 역수확 결과는 인코딩 손상이 확인되어 폐기했고, 실제 `KO_*.txt` / TSV와
영어 원문을 직접 매칭했다.

## 정상적인 번역 편집 방법

1. `translations/ko/mmmerge.po`를 Poedit 등 gettext 편집기로 연다.
2. `msgid` 영어 원문과 `msgctxt` 문맥을 확인하고 `msgstr`만 수정한다.
3. 작업 브랜치에 PO 변경을 커밋한다.
4. `Sync Korean runtime sources from PO` workflow가 해당 브랜치에서 자동으로 다음 작업을 한다.
   - PO 완전성 검사
   - PO -> 30개 canonical `KO_*` 파일 materialize
   - `KO_RuntimeOverrides.txt` 재생성
   - `KO_StatsSkillsRuntime.txt` 재생성
   - Lua/runtime 번역 소유권 감사
   - PO -> KO byte round-trip 재검증
   - 변경된 runtime source 자동 커밋

일반 번역 수정에서 `KO_*.txt`를 먼저 수정하면 안 된다. 직접 수정된 KO 파일과
PO가 달라지면 `Validate PO round trip` CI가 drift로 실패한다.

## 문맥 충돌 방지

PO 항목은 영어 문장만으로 식별하지 않는다. 같은 영어 문장이 여러 위치에서
서로 다른 의미를 가질 수 있으므로 `msgctxt`에 구조적 위치를 넣는다.

예:

```text
mmmerge/Text localization/LANG_ItemsTxt.txt|id=123|field=Name
mmmerge/Text localization/LANG_NPCText.txt|table=NPCText|id=456|field=<default>
mmmerge/10LocLANG.T/7D12.STR|string=19
```

즉 같은 `msgid`라도 파일/테이블/ID/필드가 다르면 별도 번역으로 유지된다.

## PO -> KO materializer

`tools/build_korean_from_po.py`가 PO의 `msgstr`을 게임용 Korean source에 다시
주입한다.

기존 KO 파일은 다음 구조 정보만 template으로 사용한다.

- 레코드 ID와 순서
- 열 구조
- long overlay의 continuation-line 구조
- 기존 파일의 UTF-8/CP949 인코딩
- BOM 및 줄바꿈 형식
- 기존 quoted field 표현

현재 PO는 30개 canonical 파일을 **바이트 단위로 그대로 재생성**할 수 있음이
CI에서 검증되었다. CI는 long/wide/map/inherited/positional 형식의 대표 항목을
임시로 실제 변경하여 쓰기 경로와 재-materialize 안정성도 검사한다.

수동 확인 예:

```bash
python -m pip install polib
python tools/build_korean_from_po.py \
  --output-root build/po-preview \
  --require-byte-identical
```

PO의 변경 내용을 현재 runtime source에 직접 materialize하려면:

```bash
python tools/build_korean_from_po.py --write
python tools/rebuild_runtime_overrides.py --write
python tools/rebuild_stats_skills_runtime.py --write
```

보통은 CI가 이 작업을 수행하므로 직접 실행할 필요가 없다.

## RuntimeOverride 소유권

`KO_RuntimeOverrides.txt`의 번역 문구는 독립적으로 관리하지 않는다.
`config/runtime_override_keys.tsv`에는 Merge 초기화 뒤 다시 적용해야 하는
**키**만 기록하고, 문구는 canonical Korean source에서 자동으로 가져온다.

현재 runtime override는 **160개**이며 전부 canonical 번역에서 자동 생성된다.

- canonical 번역에서 자동 생성: **160개**
- runtime-only: **0개**

기존 runtime-only였던 `Houses[45].Name` (`니혼 터널`)과
`Houses[48].Name` (`이오폴로 가는 터널`)도 이제 `KO_2DEvents.txt`의
canonical Name 필드와 PO에서 관리한다.

이 구조 때문에 오래된 Lua/override 문구가 최신 번역을 다시 덮어쓰는 일을
CI가 탐지할 수 있다.

## 능력치 / 기술 번역

기존 `KoreanStatsAndSkills.lua`에 있던 번역 하드코딩은 canonical source로
이동했다.

- 능력치 이름: `KO_GlobalTxt.txt`
- 능력치 설명: `KO_StatsDescriptions.tsv`
- 기술 이름/설명/숙련도 설명: `KO_Skilldes.txt`
- 런타임 재적용 파일: `KO_StatsSkillsRuntime.txt` (자동 생성, 267개)

Lua는 번역 원본을 따로 보유하지 않고 런타임 동작만 담당한다.

## Lua에 남아 있는 한국어

정적 번역과 겹치는 Lua 한국어 리터럴은 허용하지 않는다.
현재 한국어 리터럴을 보유하도록 허용된 파일은 동적 UI를 만드는 다음 두 개뿐이다.

- `Scripts/General/ZZ_KoreanReportedLocalization.lua`
- `Scripts/General/ZZZ_KoreanExtraSettingsOverlay.lua`

`Audit runtime translation ownership` workflow는 다른 Lua에 한국어 리터럴이
새로 생기거나 정적 번역과 정확히 중복되면 실패한다.

## 역사 파일은 별도 runtime asset

MM6/MM7/MM8 역사 파일은 현재 PO 25,034개 카탈로그와 별도로 관리한다.

- `MM6History_KO.txt`
- `MM7History_KO.txt`
- `MM8History_KO.txt`

`KoreanHistory.lua`가 이 파일의 raw bytes를 직접 게임에 넣기 때문에 세 파일은
**strict EUC-KR**이어야 한다. UTF-8 한글이면 native DBCS renderer에서 정상적인
게임 문자열이 아니다.

`Validate Korean history runtime` workflow가 다음을 검사한다.

- UTF-8 한글 오염 금지
- strict EUC-KR decode/round-trip
- CR 레코드 구분 구조
- 역사 레코드 수/내용
- Lua 5.1 문법
- MM6/MM7/MM8 역사 적용 회귀 테스트

## 역방향 legacy import

`.github/workflows/bootstrap-po-catalog.yml`의 현재 이름은
`Import Korean gettext catalog from legacy tables`이며 **수동 실행 전용**이다.

이 workflow는 복구나 영어 원문 구조 재이식처럼 특별한 경우에 기존 KO 파일에서
PO를 다시 만드는 역방향 작업이다. 정상 번역 작업에는 사용하지 않는다.
실행하면 현재 KO runtime source를 기준으로 PO를 다시 생성할 수 있으므로,
PO에만 존재하는 미반영 변경이 있는 상태에서 실행해서는 안 된다.

## 주요 CI

- `Validate Korean gettext catalog`
  - 25,034개 coverage 기준
  - untranslated/fuzzy/duplicate/replacement character 회귀 검사
- `Sync Korean runtime sources from PO`
  - 모든 저장소 작업 브랜치에서 정상적인 PO -> KO 생성 경로
  - PO 변경 뒤 생성된 KO/runtime projection을 같은 브랜치에 자동 커밋
- `Validate PO round trip`
  - PO와 canonical KO의 byte equivalence
  - 각 파일 형식의 실제 쓰기 경로 테스트
- `Audit runtime translation ownership`
  - runtime override / stats-skill projection / Lua 중복 검사
- `Validate Korean history runtime`
  - 역사 파일 EUC-KR 및 Lua 적용 회귀 검사

## 원칙

번역 문구의 단일 원본은 PO로 유지한다.

```text
translations/ko/mmmerge.po
        ↓
canonical KO text tables
        ↓
RuntimeOverrides / StatsSkillsRuntime
        ↓
기존 MMMerge LocalizeTables / LOD / runtime hooks
        ↓
게임
```

게임 런타임은 PO 파일 자체를 읽지 않는다. PO는 번역 관리 원본이고, 게임에는
기존 MMMerge가 이해하는 TXT/TSV/LOD/Lua 구조가 계속 제공된다. 따라서 gettext
도입 때문에 기존 렌더러나 Merge 런타임 로더를 새 방식으로 교체하지 않는다.
