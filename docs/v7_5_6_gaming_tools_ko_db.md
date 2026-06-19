# v7.5.6 gaming.tools/ko 한글 DB 전환

## 목적

장비 정보, 검색 기능, 스펙, 제작 재료를 `https://dune.gaming.tools/ko`의 한글 DB 기준으로 통합합니다.

## 데이터 파일

- `data/equipment_db.json`: 한글 아이템명 / 분류 / 스펙 / 제작 재료
- `data/crafting_recipes.json`: 제작 재료가 있는 항목만 파생 저장

## 수집 스크립트

- `scripts/fetch_gaming_tools_ko_db.py`

## 수집 소스

- `https://dune.gaming.tools/ko/items`
- `https://dune.gaming.tools/ko/crafting-calculator`

## 유지 정책

- 수집 결과가 기준 미만이면 기존 DB 유지
- 실패 결과는 `data/update_log.json` 기록
- Gemini / AI 자동 해석은 사용하지 않음
