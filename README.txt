============================================================
MMMerge 한국어 패치 v1.0.20
============================================================

이 패치는 Might and Magic 6·7·8 Merge(MMMerge)의 한국어 번역 패치입니다.
v1.0.20부터 Rodril MMMerge를 공식 호환 기준으로 명확히 하고,
한국어 패치는 기존 게임 위에 설치하는 localization overlay로 관리합니다.

공식 기준:
- 프로젝트: https://gitlab.com/letr.rod/mmmerge
- 브랜치: Rodril_nightly_build
- 현재 감사 기준 커밋:
  c0b6b4e9532e80413d1a3c27cbe25f57538c9a29 (2024-10-30)

Revamp, MAW, Waffle/커뮤니티 배포판 등은 기본 호환 기준에 포함하지 않습니다.
필요한 경우 별도 호환 레이어로 관리합니다.
자세한 upstream 정책은 UPSTREAM_BASELINE.md를 참조하십시오.

------------------------------------------------------------
1. 설치 방법
------------------------------------------------------------

새 설치:
1) 게임과 관련 도구를 모두 종료합니다.
2) 게임 폴더와 저장 파일을 백업합니다.
3) Rodril MMMerge를 먼저 설치합니다.
4) 한국어 패치 ZIP 안의 파일을 Might and Magic 8 / MMMerge 설치 폴더에
   그대로 복사하고 같은 이름의 파일은 모두 덮어씁니다.
5) 게임을 완전히 종료했다가 다시 실행합니다.

예시 설치 경로:
  D:\GOG\Might and Magic 8\

정상 설치 후 주요 파일:
  Data\zz LocKO.T.lod
  Data\LocalizeConf.ini
  Data\Text localization\KO_*.txt
  DataFiles\DBCS_*.fnt
  Scripts\General\FNT_DBCS.lua
  Scripts\General\KoreanFont.lua
  Scripts\General\KoreanFontText.lua
  Scripts\General\LocalizeTables.lua
  Scripts\General\ZZ_KoreanDaggerWoundHints.lua

------------------------------------------------------------
2. v1.0.19 이하에서 업데이트
------------------------------------------------------------

v1.0.19 이하 한국어 패치는 과거 다음 Rodril 지도 스크립트를 배포했습니다.

  Scripts\Maps\out01.lua

v1.0.20은 이 파일을 더 이상 포함하지 않습니다. 한국어 대포 힌트만
Scripts\General\ZZ_KoreanDaggerWoundHints.lua로 분리했으며,
Rodril이 원본 지도 게임플레이 스크립트를 온전히 소유하도록 변경했습니다.

따라서 기존 설치에서는 다음 순서를 지키십시오.

1) 저장 파일과 게임 폴더를 백업합니다.
2) Rodril MMMerge 원본/패치를 게임 폴더에 다시 적용합니다.
3) Rodril의 Scripts\Maps\out01.lua가 복원된 상태에서 v1.0.20을 덮어씁니다.
4) 게임을 완전히 종료했다가 다시 실행합니다.

중요:
- 기존 Scripts\Maps\out01.lua를 단순 삭제하지 마십시오.
  해당 파일에는 Dimension Door / Town Portal 등 원본 지도 로직이 들어 있습니다.
- v1.0.20 ZIP만 기존 v1.0.19 위에 바로 덮어쓰면 예전 out01.lua가 디스크에
  남을 수 있으므로 Rodril 원본을 먼저 재적용해야 합니다.
- 자세한 절차는 MIGRATION_v1.0.20.txt를 참조하십시오.

------------------------------------------------------------
3. 한국어 출력 구조
------------------------------------------------------------

현재 한글 출력은 upstream mm678-i18n의 native direct-blit DBCS 렌더러를
기반으로 합니다.

- upstream revision:
  aea1b22666ef556f34a71b4f3945904b04de1466
- MM8 GetLineWidth / WordWrap / Draw / DrawTextLimited 및 문자 draw loop를
  DBCS 대응으로 처리
- 한글 glyph를 MM8 원본 폰트 메모리에 임시로 덮어쓰지 않고 직접 blit
- DBCS page font reload/evict 시 stale pointer 검사 및 재취득
- 기존 저장/리소스의 옛 marker 문자열은 호환용으로 해석
- 새 런타임 한국어 문자열은 plain EUC-KR 유지
- 서로 다른 저수준 hook이 겹치지 않도록 설치 실패 시 fail-closed

Data\LocalizeConf.ini:
  encoding=euc_kr
  fontSizes=14,16,29
  specialFonts=Autonote:15b

------------------------------------------------------------
4. 번역 소스 구조
------------------------------------------------------------

핵심 번역 편집 원본:
  translations\ko\mmmerge.po

현재 검증 기준:
- PO 매핑 항목 25,051 / 25,051 번역
- untranslated 0
- fuzzy 0
- PO -> KO 번역 파일 byte-identical round trip
- PO -> mm8lang.ini CP949 round trip
- runtime-only 번역 소유권 0

게임에서 사용하는 형식은 MMMerge/GrayFace 호환성을 위해 기존 구조를 유지합니다.

- Data\Text localization\KO_*.txt
- Data\zz LocKO.T.lod
- mm8lang.ini
- Korean-only Lua runtime overlays

Rodril issue #17의 현지화 시스템 개편은 아직 완료된 upstream 계약이 아니므로,
현재 검증된 zz LocKO.T.lod 파이프라인을 임의로 제거하지 않습니다.

------------------------------------------------------------
5. Rodril upstream 경계
------------------------------------------------------------

한국어 패치는 게임플레이 포크가 아닙니다.

현재 정책:
- Scripts\Maps\*.lua 직접 배포 금지
- Scripts\Core / Modules / Structs vendoring 금지
- 한국어 전용 동작은 Korean* / ZZ_Korean* 오버레이를 우선 사용
- 의도적인 Rodril 동일 경로 스크립트 교체는 현재 1개:
  Scripts\General\LocalizeTables.lua

LocalizeTables.lua는 한국어 인코딩, 런타임 번역 소유권, 캐시 보정 등 때문에
유지하는 예외입니다. Rodril upstream이 이 파일을 변경하면 반드시 diff/rebase
검토 후 기준 커밋을 갱신합니다.

개발자용 검사:
  python tools\validate_rodril_overlay_boundary.py

------------------------------------------------------------
6. 검증
------------------------------------------------------------

주요 자동 검사:
- gettext PO 완전성/placeholder/중복 검사
- PO -> KO/mm8lang byte round trip
- runtime translation ownership audit
- Lua Korean literal audit
- native DBCS 통합 검사
- Rodril overlay boundary 검사
- Dagger Wound 한국어 힌트 Lua 5.1 문법/동작 검사
- MM6/MM7/MM8 역사/NEW GAME 회귀 검사
- 제보 65949 / 65960 회귀 검사
- Extra Settings 리소스 검사

native DBCS upstream MM8 page-font 오프라인 하네스:
  53 passed / 0 failed

------------------------------------------------------------
7. UI 소실 문제 제보 시 확인할 항목
------------------------------------------------------------

장시간 플레이 중 HUD/ESC/상점 UI 등 2D 인터페이스가 사라지는 문제가
다시 발생하면 다음 정보를 함께 제보해 주십시오.

- 발생 직전 행동: NPC 대화, 상점 진입, 지역 이동, Alt+Tab 등
- F4 창모드/전체화면 전환으로 UI가 복구되는지
- HUD뿐 아니라 ESC 메뉴도 보이지 않는지
- 보이지 않는 메뉴 위치 클릭 시 기능은 동작하는지
- 게임 완전 재실행 후 정상화되는지
- Hardware Accelerated 3D / Software 3D 여부
- dgVoodoo 사용 여부
- MMMerge 버전과 한국어 패치 버전
- 가능하면 문제 화면과 재현 가능한 저장 파일

F4 전환으로 즉시 UI가 복구된다면 한국어 텍스트 데이터보다
DirectDraw/2D surface 복구 계층을 우선 의심할 수 있습니다.

------------------------------------------------------------
8. 의도적으로 영문을 유지하는 항목
------------------------------------------------------------

저장 슬롯/퀵세이브 처리에 민감한 표기:
  Empty
  Quick Save

지도 STR에서도 다음 항목은 판정용 데이터일 수 있어 영문을 유지합니다.
- 수수께끼 정답과 암호 입력값
- 오벨리스크 암호 조각
- 한 글자 스위치 코드
- (removed) 삭제 문자열
- 개발용 자리표시자와 디버그 문자열

------------------------------------------------------------
9. 파일 안내
------------------------------------------------------------

README.txt                         설치와 사용 안내
MIGRATION_v1.0.20.txt              구버전 -> v1.0.20 업데이트 절차
UPSTREAM_BASELINE.md              Rodril 기준판/오버레이 경계 정책
CHANGELOG.txt                      이전 변경 이력
NATIVE_DBCS_MIGRATION_AUDIT.txt    native DBCS 렌더러 분석/검증
UI_RENDER_CORRUPTION_AUDIT.txt     UI 소실 원인 분석
STR_TRANSLATION_COVERAGE.txt       지도 STR 번역 범위와 제외 기준
RUNTIME_LOCALIZATION_AUDIT.txt     런타임 번역 소유권 감사
FONT_LICENSES.md                   포함 글꼴 라이선스 안내
Data\Text localization\          게임용 번역 테이블
Data\zz LocKO.T.lod               정적 한국어 리소스
DataFiles\                        한글 출력용 DBCS 페이지 폰트
Scripts\General\FNT_DBCS.lua     native direct-blit DBCS 렌더러
Scripts\General\KoreanFont.lua    한국어 호환 API

저장소:
  https://github.com/munument1/-KR-MMMerge

============================================================
