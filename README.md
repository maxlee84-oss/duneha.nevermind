# 듄하 — Dune Awakening Nevermind 길드 도우미

이 패키지는 사용자가 업로드한 마지막 v7.5 브리핑 HTML의 디자인을 기준으로 만든 **Visual Match / No Gemini** 배포본입니다.

## 핵심 변경

- 현재 배포본의 별도 SPA 디자인을 제거
- 업로드된 마지막 브리핑 HTML 디자인을 `index.html`로 복원
- 제목: `듄하`
- 소제목: `Dune Awakening Nevermind 길드 도우미`
- Gemini 완전 제거
- AI 검색 섹션 없음
- 매일 오전 8시 KST 소스 변경 감지만 수행

## GitHub 업로드 구조

repository root에 아래가 바로 보여야 합니다.

```text
.github
assets
data
docs
scripts
index.html
README.md
requirements.txt
```

## 운영 방식

이 버전은 `index.html` 자체가 완성형 브리핑 페이지입니다.

자동화는 아래만 수행합니다.

```text
fetch_sources.py
→ update_without_gemini.py
→ validate_data.py
→ build_discord_message.py
→ commit if changed
→ deploy
```

Gemini를 제거했으므로 외부 소스를 자동 해석해 브리핑 내용을 바꾸지는 않습니다.  
대신 기존 검증된 페이지 디자인/콘텐츠를 안정적으로 유지합니다.

## 디자인 기준

업로드된 v7.5 자료의 주요 구조를 유지합니다.

- spice gold / dark brown Dune tone
- 상단 sticky icon nav
- 이번 주 브리핑 dashboard
- Favorites accordion
- DD 브리핑 tab
- 던전 브리핑 route card
- mobile quick return nav
- v7.5 detail summary arrow alignment


## v7.5.2 Design Polish

반영 사항:

- Asia 전용 주간 기준으로 정리
- 제목/소제목/설명문 정돈
- Favorites → 목표 장비 보드
- PvE 우선 / PvP 참고 톤 반영
- 설명 문구 한글화
- 출처 영역 간소화
- 전체 디자인 polish 적용

미반영 사항:

- 홈 대시보드의 이번 주 추천 루트 추가
- No Gemini 운영 상태 별도 노출


## v7.5.3 제작 재료 조회기

추가 사항:

- `이번 주 브리핑` 섹션 삭제
- 상단 첫 기능으로 `제작 재료 조회기` 추가
- 아이템명 / 재료명 검색
- 카테고리 필터
- 제작 수량에 따른 총 필요 재료 표시
- 선택 재료 복사
- `data/crafting_recipes.json` 기반 정적 조회
- GitHub Actions에서 `scripts/fetch_crafting_recipes.py` 실행

데이터 기준:

- 1차: dune.gaming.tools Crafting Calculator / Items DB
- 보조: Questlog.gg Recipes / awakening.wiki
- Gemini 사용 없음

주의:

- 전체 제작 DB는 GitHub Actions 실행 후 `data/crafting_recipes.json`으로 갱신됩니다.
- 최초 프리뷰에서는 기본 seed 데이터가 표시될 수 있습니다.


## v7.5.4 Pretendard Typography Pass

반영 사항:

- Pretendard Variable 웹폰트 적용
- 본문 / 버튼 / 입력창 / 카드 / 드롭칩 전체 폰트 통일
- 한글 자간과 굵기 조정
- 모바일 카드 제목 가독성 개선

폰트 파일은 배포 ZIP에 포함하지 않고 CDN 방식으로 로드합니다.


## v7.5.5 안정화 패치

반영 사항:

- 남아 있던 지역 시간 선택 스크립트 제거
- Asia 시간은 정적 텍스트로만 유지
- 제작 재료 조회기에 직접 재료 기준 안내 추가
- 검색 결과 300개 제한 안내 추가
- 제작 DB 상태 표시 개선
- 제작 DB 크롤러 실패 시 기존 DB 유지
- 수집 레시피가 50개 미만이면 새 DB로 덮어쓰지 않음
- 제작 DB 변경/보존 결과를 update_log.json에 기록


## v7.5.6 gaming.tools/ko 한글 DB 전환

반영 사항:

- DB 기준을 `https://dune.gaming.tools/ko`로 전환
- 아이템명 / 분류 / 장비 스펙 / 제작 재료를 한글 DB 기준으로 수집
- `data/equipment_db.json` 추가
- 기존 `crafting_recipes.json`은 equipment DB에서 재료가 있는 항목만 파생 생성
- 사이트 검색은 `equipment_db.json`을 우선 로드
- GitHub Actions에서 `scripts/fetch_gaming_tools_ko_db.py` 실행
- Gemini 사용 없음


## v7.5.7 전체 한글 DB 전환

- DD / 던전 루트의 장비 링크를 `dune.gaming.tools/ko/items` 기준으로 전환
- Method.gg DB 링크 제거
- 현재 정적 브리핑 내 주요 장비 표기를 한글화
- `data/item_aliases_ko.json` 추가
- GitHub Actions에서 한글 장비 DB 수집 후 `localize_weekly_with_ko_db.py` 실행
- `weekly.json`, `gear_index.json`, `routes.json`의 이름/링크를 한글 DB 기준으로 정리


## v7.5.8 Dune 타이포그래피 / 검색 UX 개선

- `듄하` 제목을 Dune에서 영감받은 로고형 타이포그래피로 변경
- 강한 세리프/네온 대신 넓은 자간, 얇은 기하학적 실루엣, 절제된 골드 그라디언트 적용
- `/ko/ko`, `/ko/ko/ko` 중복 경로 오류 제거
- `즐겨찾기s` 표시를 `목표 장비 보드`로 정리
- SVG `viewbox`를 표준 `viewBox`로 수정
- 제작/장비 검색 입력부는 항상 노출
- 결과/상세 영역만 접힘 처리
- 한글 DB 직접 연결은 `KO`, 검색 링크는 `검색` 배지로 구분
- 사이트 설명을 장비/제작/DD/던전 통합 정보로 변경


## v7.5.8.2 로고 크기 통일

- `듄`과 `하`의 글자 크기를 동일하게 조정
- 투명도와 세로 위치 차이 제거
- 기존 골드 그라디언트와 넓은 자간은 유지


## v7.5.9 weekly.json 단일 기준 구조

이번 버전은 자동 수집을 붙이기 전의 1단계 구조 통합입니다.

- DD 및 던전 화면을 `data/weekly.json`에서 동적으로 렌더링
- 기존 정적 DD/던전 HTML은 JSON 로드 실패 시 fallback으로만 사용
- Asia 주간 기간을 매일 자동 계산
- 마지막 데이터 생성 시각과 데이터 상태 표시
- 즐겨찾기 기능은 동적 카드에서도 유지
- GitHub Actions에 `scripts/update_week_window.py` 추가
- 외부 DD/던전 자동 수집은 아직 적용하지 않음


## v7.6.0 DD 주간 자동 갱신

이번 버전은 DD 자동 갱신 단계입니다.

- Method Deep Desert Companion의 현재 주차를 파싱
- DD 희귀 / PvE / PvP / Row A를 `weekly.json`에 반영
- `dune.gaming.tools/ko` 장비 DB로 한글명/링크 정규화
- 소스 주차와 Asia 주간 창이 일치할 때만 반영
- 항목 수/중복률 검증 실패 시 기존 DD 데이터 유지
- 이전 DD 데이터는 `data/dd_previous.json`에 백업
- 결과는 `data/dd_update_report.json` 및 `data/update_log.json`에 기록
- 던전 데이터는 이번 버전에서 변경하지 않음


## v7.6.1 던전 자동 갱신

- 올드 쿼리와 테스팅 스테이션 #24 / #89 / #136 / #152 / #195 자동 수집
- 위험 속성, 기본 정보, 드랍 확률·등급·종류 수집
- `dune.gaming.tools/ko` 기준 한글명과 아이템 링크 정규화
- 6개 루트 및 루트별 최소 드랍 수 검증
- 실패 시 기존 던전 데이터 유지
- `routes.json`에는 범용 루트 메타데이터만 저장
- 사용자별 추천 우선순위와 길드 파밍 목표는 완전히 제외
