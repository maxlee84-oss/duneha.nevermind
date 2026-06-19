from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from config import DATA

WEEKLY = DATA / "weekly.json"
KST = ZoneInfo("Asia/Seoul")

def current_window(now):
    # DuneHa Asia weekly window: Tuesday 04:00 KST/JST.
    weekday_delta = (now.weekday() - 1) % 7
    candidate = (now - timedelta(days=weekday_delta)).replace(hour=4, minute=0, second=0, microsecond=0)
    if now < candidate:
        candidate -= timedelta(days=7)
    return candidate, candidate + timedelta(days=7)

def main():
    data = json.loads(WEEKLY.read_text(encoding="utf-8"))
    now = datetime.now(KST)
    start, end = current_window(now)

    data["generated_at"] = now.astimezone(ZoneInfo("UTC")).replace(microsecond=0).isoformat().replace("+00:00","Z")
    data.setdefault("week", {})
    data["week"]["start"] = start.date().isoformat()
    data["week"]["end"] = end.date().isoformat()
    data["week"]["label"] = f"{start.date().isoformat()} to {end.date().isoformat()}"
    data["week"]["regions"] = {
        "asia": f"KST/JST · {start:%m/%d %H:%M} → {end:%m/%d %H:%M}"
    }

    status = data.setdefault("automation_status", {})
    status["render_mode"] = "weekly_json_single_source"
    status["checked_at"] = data["generated_at"]
    status["message"] = "DD/던전 화면은 data/weekly.json 단일 기준으로 표시됩니다. 외부 자동 수집은 다음 단계에서 연결합니다."

    WEEKLY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "start": data["week"]["start"],
        "end": data["week"]["end"],
        "asia": data["week"]["regions"]["asia"],
        "render_mode": status["render_mode"]
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
