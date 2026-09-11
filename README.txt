============================================================
MMMerge 한국어 패치 v1.0.29
============================================================

이 패치는 Might and Magic 6·7·8 Merge(MMMerge)의 한국어 번역 패치입니다.
v1.0.20부터 Rodril MMMerge를 공식 호환 기준으로 사용하며,
한국어 패치는 기존 게임 위에 설치하는 localization overlay로 관리합니다.

v1.0.29 배포 파일은 플레이어 제보에 따라 hotfix refresh를 계속 갱신하고 있습니다.
같은 v1.0.29을 먼저 받은 사용자는 최신 ZIP을 다시 받아 덮어쓰십시오.

중요:
- MMMerge 컷신 자막 기능은 안정성 문제로 중단했습니다.
- 한국어 패치는 Bink/Smacker 영상 재생 루프, ShowMovie/PostRender 영상 자막 처리,
  CustomUI 영상 오버레이를 더 이상 건드리지 않습니다.
- 과거 v1.0.29 hotfix의 KoreanMovieSubtitles.lua가 설치되어 있을 수 있으므로,
  최신 패치에는 기존 파일을 덮어쓰기 위한 무동작 compatibility stub을 포함합니다.
- 하드서브 영상 파일도 배포하지 않습니다.

v1.0.29 최신 hotfix 핵심 변경:
- 스탯 우클릭 도움말 stats.txt를 native CP949 저장 방식으로 정리
- Game.StatsDescriptions 런타임 투영 범위를 안전한 0..6으로 유지
- Extra Settings의 Interface/General/Bolster/Keybinds 제목 번역 경로 수정
- 학자/교사/강사의 고용 효과를 +5%/+10%/+15% 평면 경험치 보너스로 보정
- MM7/Antagarich 민간인 공격 시 주변 민간인·경비 목격 적대 반응 호환 보정
- 던전/건물 입장 설명 TransTxt의 1-based 인덱스를 0-based로 적용하던 오류 수정
- 기존 v1.0.29 LOD도 KO_TransTxt의 실제 1-based ID로 런타임 재투영
- 컷신 자막 런타임 후킹 제거 및 원본 영상 재생 경로 보존
- 피낙시아 제국, 방패 주문, 율리시스 피해 속성 등 제보 용어/효과 교정

실게임 최종 확인이 필요한 항목:
- MM6/MM7/MM8 새 게임 및 컷신이 자막 후킹 없이 정상 재생되는지
- 던전/건물 입장 설명이 올바른 장소와 일치하는지
- 교사 포함 고용 NPC의 실제 경험치 획득량이 +5/+10/+15%로 적용되는지
- MM7 민간인 공격 시 주변 민간인·경비 적대 반응이 의도대로 작동하는지

자동 검증 통과와 실게임 확인은 구분합니다. 위 항목은 실제 플레이 확인 전까지
완전 해결로 단정하지 않습니다.

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

v1.0.20~v1.0.28에서 업데이트:
- 최신 v1.0.29 ZIP을 그대로 덮어쓴 뒤 게임을 완전히 종료했다가 다시 실행합니다.

기존 v1.0.29에서 hotfix refresh로 업데이트:
- 릴리즈 이름은 그대로 v1.0.29이지만 배포 ZIP이 교체될 수 있습니다.
- 최신 ZIP을 다시 내려받아 그대로 덮어쓰십시오.
- Scripts\General\KoreanMovieSubtitles.lua도 반드시 덮어써야 과거 자막 후킹 코드가 제거됩니다.
- SHA-256은 릴리즈에 함께 첨부된 .sha256 파일을 확인하십시오.

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
  Scripts\General\KoreanMovieSubtitles.lua   (무동작 compatibility stub)
  Scripts\General\LocalizeTables.lua
  Scripts\General\ZZZZ_KoreanTransTxtIndexFix.lua
  Scripts\General\ZZ_KoreanReportedLocalization.lua
  Scripts\Global\ZZZZ_KoreanHirelingExperienceFix.lua
  Scripts\Global\ZZZZ_KoreanMM7CivilianWitnessFix.lua

------------------------------------------------------------
2. v1.0.19 이하에서 업데이트
------------------------------------------------------------

v1.0.19 이하 한국어 패치는 과거 다음 Rodril 지도 스크립트를 배포했습니다.

  Scripts\Maps\out01.lua

v1.0.20부터 이 파일을 더 이상 포함하지 않습니다. 한국어 대포 힌트만
Scripts\General\ZZ_KoreanDaggerWoundHints.lua로 분리했으며,
Rodril이 원본 지도 게임플레이 스크립트를 온전히 소유하도록 변경했습니다.

따라서 기존 설치에서는 다음 순서를 지키십시오.
1) 저장 파일과 게임 폴더를 백업합니다.
2) Rodril MMMerge 원본/패치를 게임 폴더에 다시 적용합니다.
3) Rodril의 Scripts\Maps\out01.lua가 복원된 상태에서 최신 v1.0.29을 덮어씁니다.
4) 게임을 완전히 종료했다가 다시 실행합니다.

기존 Scripts\Maps\out01.lua를 단순 삭제하지 마십시오.
해당 파일에는 Dimension Door / Town Portal 등 원본 지도 로직이 들어 있습니다.
자세한 절차는 MIGRATION_v1.0.20.txt를 참조하십시오.

------------------------------------------------------------
3. 한국어 출력 구조
------------------------------------------------------------

현재 한글 출력은 upstream mm678-i18n의 native direct-blit DBCS 렌더러를
기반으로 합니다.

- upstream revision: aea1b22666ef556f34a71b4f3945904b04de1466
- MM8 GetLineWidth / WordWrap / Draw / DrawTextLimited 및 문자 draw loop DBCS 대응
- 한글 glyph를 MM8 원본 폰트 메모리에 임시로 덮어쓰지 않고 직접 blit
- DBCS page font reload/evict 시 stale pointer 검사 및 재취득
- 기존 저장/리소스의 옛 marker 문자열은 호환용으로 해석
- 새 런타임 한국어 문자열은 plain EUC-KR/CP949 호환 바이트 사용
- 서로 다른 저수준 hook이 겹치지 않도록 설치 실패 시 fail-closed

Data\LocalizeConf.ini:
  encoding=euc_kr
  fontSizes=14,16,29
  specialFonts=Autonote:15b

스탯 도움말:
- 정적 stats.txt 26행은 native CP949로 저장
- Game.StatsDescriptions 런타임 투영은 엔진 배열 경계 때문에 0..6만 사용
- Condition(상태) 등 7번 이후 항목을 Game.StatsDescriptions에 직접 쓰지 않음

------------------------------------------------------------
4. 번역 소스 구조
------------------------------------------------------------

핵심 번역 편집 원본:
  translations\ko\mmmerge.po

v1.0.29 검증 기준:
- PO 매핑 항목 25,051 / 25,051 번역
- untranslated 0
- fuzzy 0
- PO -> KO 번역 파일 byte-identical round trip
- PO -> mm8lang.ini CP949 round trip
- runtime translation ownership audit 통과

게임에서 사용하는 형식:
- Data\Text localization\KO_*.txt
- Data\zz LocKO.T.lod
- mm8lang.ini
- Korean-only Lua runtime overlays

Rodril issue #17의 현지화 시스템 개편은 아직 완료된 upstream 계약이 아니므로,
현재 검증된 zz LocKO.T.lod 파이프라인을 임의로 제거하지 않습니다.

------------------------------------------------------------
5. 컷신 자막 정책
------------------------------------------------------------

MMMerge 한국어 패치에서는 컷신 자막을 지원하지 않습니다.

v1.0.29 개발 중 SRT를 ShowMovie/PostRender와 네이티브 Bink/Smacker 프레임에
실시간으로 합성하는 방식을 시험했으나, 실게임에서 MM6 새 게임은 영상 직후,
MM7은 영상 도중 튕기는 회귀가 제보되었습니다. MM8 영상이 정상 재생된 사례도
실제 자막 cue가 그려지지 않은 영상일 가능성을 배제할 수 없어 안전 근거로 사용하지 않습니다.

따라서 현재 정책은 다음과 같습니다.
- Bink/Smacker 네이티브 영상 draw 지점 후킹 금지
- events.ShowMovie / events.PostRender를 이용한 컷신 자막 오버레이 금지
- 영상 재생 중 CustomUI.ShowText 호출 금지
- 하드서브 영상 파일 배포 안 함
- Scripts\General\KoreanMovieSubtitles.lua는 과거 설치본을 덮어쓰기 위한 무동작 stub만 유지

Data\Korean Subtitles 아래 SRT는 번역 작업 기록용 소스 자산이며 현재 게임 런타임에서는
읽거나 표시하지 않습니다. 추후에도 MMMerge에서 별도 안전 경로가 확립되지 않는 한
자막 기능을 다시 활성화하지 않습니다.

------------------------------------------------------------
6. 고용 NPC 경험치 보너스
------------------------------------------------------------

Rodril의 기본 구현은 학자/교사/강사의 +5/+10/+15를 Learning 기술 등급에
더하는 방식이라 숙련도 배수의 영향을 다시 받을 수 있습니다.

한국어 패치 호환 오버레이는 다음 효과를 평면 경험치 보너스로 취급합니다.
- 학자(Scholar): +5%
- 교사(Teacher): +10%
- 강사(Instructor): +15%

런타임 오버레이:
  Scripts\Global\ZZZZ_KoreanHirelingExperienceFix.lua

학습 기술 창 표시만으로는 효과를 확정하기 어려우므로,
실제 경험치 획득량 비교로 최종 확인해야 합니다.

------------------------------------------------------------
7. MM7 민간인/경비 목격 적대 호환
------------------------------------------------------------

Antagarich에서 플레이어가 peasant NPC를 공격할 때,
기본 4096 게임 단위 반경 안의 살아 있는 민간인과 경비 그룹(38/55)을
적대화하는 좁은 호환 오버레이를 사용합니다.

런타임 오버레이:
  Scripts\Global\ZZZZ_KoreanMM7CivilianWitnessFix.lua

주의:
- 4096은 원작 MM7에서 확인된 정확한 수치가 아니라 현재 호환용 기본값입니다.
- 전역 평판 시스템을 켜거나 모든 경비를 적대화하지 않습니다.
- Enroth/Jadame에는 적용하지 않습니다.

------------------------------------------------------------
8. Rodril upstream 경계
------------------------------------------------------------

한국어 패치는 원칙적으로 localization overlay이며 게임플레이 코드를 광범위하게 포크하지 않습니다.

현재 정책:
- Scripts\Maps\*.lua 직접 배포 금지
- Scripts\Core / Modules / Structs vendoring 금지
- 한국어 전용 동작은 Korean* / ZZ_Korean* / ZZZZ_Korean* 오버레이를 우선 사용
- Timer, RefillTimer, RemoveTimer, Sleep, Sleep2 같은 게임플레이 전역 함수 교체 금지
- 의도적인 Rodril 동일 경로 스크립트 교체는 Scripts\General\LocalizeTables.lua 1개
- 실제 호환성 결손을 보정하는 좁은 runtime compatibility overlay만 별도 검사 후 허용

현재 호환성 예외:
- ZZZZ_KoreanHirelingExperienceFix.lua
- ZZZZ_KoreanMM7CivilianWitnessFix.lua

개발자용 검사:
  python tools\validate_rodril_overlay_boundary.py

------------------------------------------------------------
9. 검증
------------------------------------------------------------

주요 자동 검사:
- gettext PO 완전성/placeholder/중복 검사
- PO -> KO/mm8lang byte round trip
- runtime translation ownership audit
- Lua Korean literal audit
- native DBCS 통합 검사
- native CP949 stats.txt 26행 검사
- Game.StatsDescriptions 0..6 엔진 경계 검사
- Rodril overlay boundary 검사
- 제보 65949 / 65960 / 65992 회귀 검사
- Extra Settings 리소스 검사
- TransTxt 1-based 인덱스 회귀 검사
- 학자/교사/강사 경험치 계산 회귀 검사
- MM7 민간인 목격 적대 로직 검사
- 컷신 자막 비활성화 회귀 검사
  (ShowMovie/PostRender/CustomUI/native movie hook 재도입 금지)

자동 검증은 코드/데이터 계약을 검사하는 것이며 실제 게임 플레이 확인을 대신하지 않습니다.

------------------------------------------------------------
10. UI 소실 문제 제보 시 확인할 항목
------------------------------------------------------------

장시간 플레이 중 HUD/ESC/상점 UI 등 2D 인터페이스가 사라지는 문제가 다시 발생하면
발생 직전 행동, F4 전환 복구 여부, 보이지 않는 메뉴 클릭 동작 여부,
Hardware Accelerated 3D / Software 3D, dgVoodoo 사용 여부,
MMMerge/한국어 패치 버전과 가능한 경우 저장 파일을 함께 제보해 주십시오.

F4 전환으로 즉시 UI가 복구된다면 한국어 텍스트 데이터보다
DirectDraw/2D surface 복구 계층을 우선 의심할 수 있습니다.

------------------------------------------------------------
11. 의도적으로 영문을 유지하는 항목
------------------------------------------------------------

저장 슬롯/퀵세이브 처리에 민감한 표기:
  Empty
  Quick Save

지도 STR에서도 판정용 데이터일 수 있는 수수께끼 정답, 암호 조각,
한 글자 스위치 코드, 삭제 문자열, 개발용 자리표시자는 영문을 유지할 수 있습니다.

------------------------------------------------------------
12. 파일 안내
------------------------------------------------------------

README.txt                         설치와 사용 안내
MIGRATION_v1.0.20.txt              v1.0.19 이하 업데이트 절차
UPSTREAM_BASELINE.md               Rodril 기준판/오버레이 경계 정책
CHANGELOG.txt                      이전 변경 이력
NATIVE_DBCS_MIGRATION_AUDIT.txt    native DBCS 렌더러 분석/검증
UI_RENDER_CORRUPTION_AUDIT.txt     UI 소실 원인 분석
STR_TRANSLATION_COVERAGE.txt       지도 STR 번역 범위와 제외 기준
RUNTIME_LOCALIZATION_AUDIT.txt     런타임 번역 소유권 감사
FONT_LICENSES.md                   포함 글꼴 라이선스 안내
Data\Text localization\           게임용 번역 테이블
Data\Korean Subtitles\            보관용 SRT 소스(런타임 미사용)
Data\zz LocKO.T.lod               정적 한국어 리소스
DataFiles\                         한글 출력용 DBCS 페이지 폰트
Scripts\General\FNT_DBCS.lua      native direct-blit DBCS 렌더러
Scripts\General\KoreanMovieSubtitles.lua
                                   과거 자막 후킹 파일을 덮어쓰기 위한 무동작 stub
Scripts\Global\ZZZZ_KoreanHirelingExperienceFix.lua
                                   고용 NPC 경험치 호환 보정
Scripts\Global\ZZZZ_KoreanMM7CivilianWitnessFix.lua
                                   MM7 민간인 목격 적대 호환 보정

저장소:
  https://github.com/munument1/-KR-MMMerge

============================================================