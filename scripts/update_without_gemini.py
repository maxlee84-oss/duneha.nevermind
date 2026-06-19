import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
from config import DATA, RAW

WEEKLY = DATA / "weekly.json"
UPDATE_LOG = DATA / "update_log.json"
BUNDLE = RAW / "source_bundle.json"
SIGNATURES = DATA / "source_signatures.json"
REPORT = DATA / "validation_report.json"

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    weekly = load_json(WEEKLY, {})
    bundle = load_json(BUNDLE, {"sources": [], "errors": []})
    old_signatures = load_json(SIGNATURES, {"sources": {}})

    new_signatures = {}
    changed_sources = []
    checked_sources = []

    for src in bundle.get("sources", []):
        name = src.get("name")
        url = src.get("url")
        sha = src.get("html_sha256")
        key = name or url
        new_signatures[key] = {
            "url": url,
            "sha256": sha,
            "status_code": src.get("status_code"),
            "title": src.get("title")
        }
        checked_sources.append(key)
        old_sha = (old_signatures.get("sources") or {}).get(key, {}).get("sha256")
        if old_sha and old_sha != sha:
            changed_sources.append({"name": key, "url": url, "old": old_sha, "new": sha})
        elif not old_sha:
            changed_sources.append({"name": key, "url": url, "old": None, "new": sha, "reason": "new source signature"})

    # Preserve stable weekly data. Without Gemini/AI we do not rewrite DD/drop data automatically.
    status = {
        "mode": "no_gemini_source_check",
        "confidence": "verified_static_data",
        "message": (
            "Gemini 제거 버전: 소스 페이지를 매일 확인하고 변경 감지만 기록합니다. "
            "DD/던전 데이터는 마지막 검증본을 유지합니다."
        ),
        "checked_at": now(),
        "checked_sources": checked_sources,
        "changed_source_count": len(changed_sources),
        "source_errors": bundle.get("errors", [])
    }
    weekly["generated_at"] = now()
    weekly["automation_status"] = status
    WEEKLY.write_text(json.dumps(weekly, ensure_ascii=False, indent=2), encoding="utf-8")

    # Persist signatures
    SIGNATURES.write_text(json.dumps({
        "updated_at": now(),
        "sources": new_signatures
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Update log
    log = load_json(UPDATE_LOG, {"entries": []})
    log.setdefault("entries", [])
    if changed_sources:
        msg = f"소스 변경 감지: {len(changed_sources)}개. 데이터는 마지막 검증본을 유지합니다."
        status_text = "source-changed"
    else:
        msg = "소스 확인 완료. 변경사항 없음."
        status_text = "no-change"

    log["entries"].insert(0, {
        "time": now(),
        "type": "daily-source-check",
        "status": status_text,
        "message": msg,
        "changed_sources": changed_sources[:10],
        "errors": bundle.get("errors", [])
    })
    log["entries"] = log["entries"][:40]
    UPDATE_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "ok": True,
        "mode": "no_gemini_source_check",
        "checked_sources": checked_sources,
        "changed_sources": changed_sources,
        "source_errors": bundle.get("errors", [])
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
