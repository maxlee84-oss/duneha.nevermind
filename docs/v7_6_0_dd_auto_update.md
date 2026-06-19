# v7.6.0 DD 자동 갱신

## 대상

- DD 희귀 드랍
- DD PvE
- DD PvP
- DD 상시 / Row A
- 주간 기간 검증
- 한글 장비명과 한글 DB 링크

## 소스

1. Method Deep Desert Companion: 주간 드랍 원본
2. dune.gaming.tools/ko: 한글 장비명/링크 정규화
3. 기존 weekly.json: 수집 실패 시 fallback

## 반영 조건

- Method의 `Updated for` 기간이 Asia 주간 창과 일치
- 희귀 4개 이상
- PvE 8개 이상
- PvP 8개 이상
- Row A 8개 이상
- 중복률 검증 통과

## 실패 시

새 데이터로 덮어쓰지 않고 기존 DD 데이터를 유지합니다.

## 제외

던전 루트 자동 갱신은 v7.6.1에서 진행합니다.
