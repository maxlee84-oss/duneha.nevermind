# v7.5.9 weekly.json 단일 기준

## 목적

DD 및 던전 화면과 데이터 파일의 이중 관리를 제거합니다.

## 동작

1. 브라우저가 `data/weekly.json`을 불러옵니다.
2. DD 희귀/PvE/PvP/Row A와 던전 루트를 동적으로 렌더링합니다.
3. JSON 로드 실패 시 기존 검증 HTML을 fallback으로 표시합니다.
4. 즐겨찾기 ID는 기존 구조를 유지합니다.

## Asia 기간

`scripts/update_week_window.py`가 매일 Asia/Seoul 기준 화요일 04:00 주간 창을 계산합니다.

## 다음 단계

DD 희귀 드랍과 PvE/PvP 로테이션의 외부 자동 수집은 v7.6.0에서 연결합니다.
