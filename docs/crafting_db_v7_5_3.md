# v7.5.3 제작 재료 조회기

## 목적

전체 제작 가능 아이템을 검색하여 제작에 필요한 재료를 빠르게 확인합니다.

## 제외

- 보유 수량 입력
- 부족분 계산
- Gemini 자동 해석

## 포함

- 아이템/재료 검색
- 카테고리 필터
- 제작 수량 곱셈
- 재료 목록 복사
- 전체 레시피 DB 수집 스크립트

## 데이터 소스

1. dune.gaming.tools Crafting Calculator
2. dune.gaming.tools Items DB
3. Questlog.gg Recipes
4. awakening.wiki

## 자동화

GitHub Actions에서 `scripts/fetch_crafting_recipes.py`가 실행되어 `data/crafting_recipes.json`을 갱신합니다.
