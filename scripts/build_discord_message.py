import json
from config import DATA

weekly = json.loads((DATA / "weekly.json").read_text(encoding="utf-8"))
report_path = DATA / "validation_report.json"
report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
week = weekly.get("week", {})
status = weekly.get("automation_status", {})

dd_counts = report.get("dd_counts", {})
dungeon_counts = report.get("dungeon_counts", {})

message = f"""@everyone

이번 주 **듄하 — Dune Awakening Nevermind 길드 도우미** 소스 확인 완료.

기간: **{week.get('label', '')}**
Asia 기준: **{week.get('regions', {}).get('asia', '')}**

주요 내용
- Deep Desert: 희귀 / PvE / PvP / Row A
- Overland 던전: Old Quarry / Testing Station
- Gear Finder / Favorites / Route Planner
- 출처 및 업데이트 로그 확인 가능

업데이트 상태
- Mode: `{status.get('mode', 'unknown')}`
- Confidence: `{status.get('confidence', 'unknown')}`

DD 항목 수: {sum(dd_counts.values()) if dd_counts else "확인 전"}
던전 드랍 수: {sum(dungeon_counts.values()) if dungeon_counts else "확인 전"}

페이지 링크:
https://<github-id>.github.io/<repo-name>/
"""
(DATA / "discord_announcement.md").write_text(message, encoding="utf-8")
print(message)
