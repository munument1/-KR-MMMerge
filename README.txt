[현재 작업 브랜치: UI investigation test1 / v1.0.15 기반 테스트본]
버퍼 경계·캐시 수명 수정과 선택적 UI 상태 진단을 추가했습니다.
설치/시험: UI_TEST1_README.txt
변경·검증 범위: UI_TEST1_NOTES.md
원래 UI 소실의 장시간 게임 내 해결은 아직 확인하지 못했습니다.
아래는 수정 전 v1.0.15 배포 설명을 보존한 기록입니다.
------------------------------------------------------------------

============================================================
MMMerge 한국어 패치 v1.0.15
============================================================

이 패치는 Might and Magic 6·7·8 Merge(MMMerge)의 한국어 번역 패치입니다.
v1.0.15는 장시간 플레이 중 HUD·ESC·상점 UI 등 2D 인터페이스가
간헐적으로 사라진다는 제보를 계속 추적하면서 한글 출력 구조 자체를
교체한 렌더링 안정화 버전입니다. v1.0.14 및 v1.0.13c까지의 모든
번역·안정화 변경을 포함합니다.

중요:
- v1.0.14의 stale font pointer 방어는 실제 위험 경로를 제거했지만,
  제보자의 동일 증상이 계속 발생해 그것만으로는 원인이 아니었음을 확인했습니다.
- v1.0.15는 구식 glyph-7 임시 덮어쓰기 렌더러를 완전히 폐기하고
  upstream의 native direct-blit DBCS 렌더러로 교체했습니다.
- 실제 장시간 플레이 재현 환경이 없으므로 UI 소실 문제가 완전히 해결됐다고
  단정하지 않습니다. 이번 버전은 남아 있던 저수준 렌더러 구조 자체를 제거한
  근본적인 안정화 변경입니다.

1. 설치 방법
------------------------------------------------------------
1) 게임과 관련 도구를 모두 종료합니다.
2) 기존 게임 폴더와 저장 파일을 백업합니다.
3) 압축 파일 안의 Data, DataFiles, Scripts 폴더를
   Might and Magic 8 설치 폴더에 그대로 복사합니다.
4) 같은 이름의 파일이 나오면 모두 덮어씁니다.
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

2. 기존 버전에서 업데이트
------------------------------------------------------------
- 변경 파일만 골라 넣지 말고 전체 설치본을 다시 덮어쓰는 것을 권장합니다.
- 구버전의 KoreanFont.lua를 따로 백업해 두었다가 다시 복사하지 마십시오.
- v1.0.15는 예전 glyph-7 scratch renderer와 동시에 사용할 수 없습니다.
- 구버전에서 남은 ZZ_KoreanGameplayFeedbackFixes.lua도 최신 무동작 파일로
  반드시 덮어써야 지도 이동 중 반복 evt.str/evt.hint 수정이 사라집니다.
- 업데이트 전 저장 파일 백업을 권장합니다.

3. v1.0.15 native DBCS 렌더러
------------------------------------------------------------
기존 한글 출력 방식은 한글 한 글자를 표시할 때 MM8 원본 폰트의 glyph 7을
임시 버퍼처럼 덮어쓰고 엔진이 그린 뒤 다시 복구하는 구조였습니다.

v1.0.15에서는 이 방식을 사용하지 않습니다.

- upstream mm678-i18n의 FNT_DBCS.lua native renderer 이식
- upstream revision:
  aea1b22666ef556f34a71b4f3945904b04de1466
- MM8 GetLineWidth / WordWrap / Draw / DrawTextLimited 및 문자 draw loop를
  DBCS 대응으로 처리
- 한글 glyph를 원본 MM8 폰트 메모리에 복사하지 않고 화면 버퍼로 직접 blit
- DBCS page font가 reload/evict된 경우 stale pointer를 검사하고 재취득
- 기존 세이브나 리소스에 남아 있는 옛 marker 문자열은 그리는 순간 자동 해석
- 새 런타임 한국어 문자열은 plain EUC-KR 상태로 유지
- native renderer가 설치되지 못한 경우 구식 renderer를 자동 재활성화하지 않음
  (서로 다른 저수준 hook이 겹치지 않도록 fail-closed)

현재 한국어 폰트 자산에 맞춰 Data\LocalizeConf.ini에 다음을 명시합니다.
  encoding=euc_kr
  fontSizes=14,16,29
  specialFonts=Autonote:15b

4. 지도 이동 중 runtime rewrite 제거
------------------------------------------------------------
과거 화로(brazier) 표시 보정을 위해 ZZ_KoreanGameplayFeedbackFixes.lua가
다음 시점마다 evt.str / evt.hint를 반복 순회·수정하고 있었습니다.

- BeforeLoadMapScripts
- LoadMapScripts
- LoadMap
- AfterLoadMap
- 이후 8 Tick

현재 지도 STR 번역은 zz LocKO.T.lod의 정적 리소스가 담당하므로 이 반복
수정 경로를 퇴역시켰습니다. v1.0.15의 해당 파일은 구버전 설치를 덮어쓰기
위한 무동작 stub입니다.

5. 검증
------------------------------------------------------------
upstream MM8 page-font 오프라인 하네스:
  53 passed / 0 failed

검증 범위:
- native hook 설치
- GetLineWidth
- WordWrap / WordWrap2
- DBCS pair 경계 줄바꿈
- legacy marker decode
- main / limited / scroll / centered direct glyph blit
- stale DBCS page eviction 및 self-heal
- buffer 길이 제한

한국어 패치 통합 검사:
- FNT_DBCS.lua / KoreanFont.lua / KoreanFontText.lua Lua 5.1 문법 검사
- KoreanFont.lua에 mem.hook / asmpatch / asmhook / mem.copy 없음
- 구식 KoreanFontLegacy.lua 미포함 확인
- FNT_DBCS.lua가 지정한 upstream blob과 일치하는지 검사
- DBCS_14 / 15b / 16 / 29의 A1 및 B0-C8 페이지 존재 확인
- map-load / Tick runtime rewrite가 퇴역 상태인지 검사

개발자용 검사:
  python tools\validate_native_dbcs_integration.py .

자세한 분석:
  NATIVE_DBCS_MIGRATION_AUDIT.txt
  UI_RENDER_CORRUPTION_AUDIT.txt

6. UI 소실 문제 제보 시 확인할 항목
------------------------------------------------------------
문제가 다시 발생하면 가능하면 다음을 확인해 주십시오.

- 발생 직전 행동: NPC 대화, 상점 진입, 지역 이동, Alt+Tab 등
- 문제가 난 상태에서 F4로 창모드/전체화면 전환했을 때 UI가 살아나는지
- HUD뿐 아니라 ESC 메뉴도 보이지 않는지
- 보이지 않는 메뉴 위치를 클릭했을 때 기능은 계속 동작하는지
- 키보드 저장 후 게임을 완전히 재실행하면 정상화되는지
- Hardware Accelerated 3D / Software 3D 여부
- dgVoodoo 사용 여부
- 사용 중인 MMMerge 버전과 한국어 패치 버전
- 가능하면 문제 화면과 재현 가능한 저장 파일

F4 전환으로 즉시 UI가 복구된다면 한글 텍스트 데이터보다는
DirectDraw/2D surface 복구 계층을 더 우선적으로 의심할 수 있습니다.

7. 기존 번역 범위
------------------------------------------------------------
v1.0.13c까지 다음 항목을 포함해 지도·던전·시설·오브젝트 및 상호작용
문구를 대규모로 정리했습니다.

- 71개 지도 파일의 표시 항목 181개 추가 한국어화
- 209개 STR 리소스 검토
- 163개 지도 파일의 사용자 표시 문구 658개 한국어화
- KO_MapStrings 오버레이 852개
- MM8 기본 주문 99개 명칭/짧은 이름 통일
- 성소·길드·시설·지역명·던전명 용어 통일
- 수수께끼 정답, 암호 조각, 내부 코드 등 판정용 문자열은 의도적으로 보존

자세한 이전 버전 내역은 CHANGELOG.txt를 확인하십시오.

8. 의도적으로 영문을 유지하는 항목
------------------------------------------------------------
저장 슬롯과 퀵세이브 처리에 민감한 다음 표기는 영문으로 유지합니다.
  Empty
  Quick Save

지도 STR에서도 다음 항목은 판정용 데이터일 수 있어 유지합니다.
- 수수께끼 정답과 암호 입력값
- 오벨리스크 암호 조각
- 한 글자 스위치 코드
- (removed) 삭제 문자열
- 개발용 자리표시자와 디버그 문자열

9. 파일 안내
------------------------------------------------------------
README.txt                         설치와 사용 안내
CHANGELOG.txt                      전체 변경 이력
NATIVE_DBCS_MIGRATION_AUDIT.txt    v1.0.15 렌더러 교체 분석/검증
UI_RENDER_CORRUPTION_AUDIT.txt     v1.0.14 UI 소실 원인 분석
STR_TRANSLATION_COVERAGE.txt       지도 STR 번역 범위와 제외 기준
FONT_LICENSES.md                   포함 글꼴 라이선스 안내
Data\Text localization\          번역 원본 테이블
Data\zz LocKO.T.lod               게임에서 읽는 정적 한국어 리소스
DataFiles\                        한글 출력용 DBCS 페이지 폰트
Scripts\General\FNT_DBCS.lua     native direct-blit DBCS 렌더러
Scripts\General\KoreanFont.lua    한국어 호환 API(저수준 hook 없음)
tools\                            빌드·검사·번역 감사용 개발 도구

저장소:
  https://github.com/munument1/-KR-MMMerge

============================================================
