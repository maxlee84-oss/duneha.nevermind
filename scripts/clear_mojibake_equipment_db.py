import json
import re
from pathlib import Path
from config import DATA

DB = DATA / "equipment_db.json"
BAD = re.compile(r"(?:Ã|Â|â€|ì|ë|ê|í|ðŸ|�)")

def main():
    if not DB.exists():
        print("equipment_db.json not found")
        return

    data = json.loads(DB.read_text(encoding="utf-8"))
    items = data.get("items") or []
    bad = [item for item in items if BAD.search(str(item.get("name") or ""))]

    if not bad:
        print(json.dumps({"status":"clean","items":len(items)}, ensure_ascii=False))
        return

    # Do not try to salvage uncertain strings. Replace with an empty DB so the
    # next fetch must rebuild it rather than serving corrupted Korean text.
    backup = DATA / "equipment_db_mojibake_backup.json"
    backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    data["items"] = []
    data.setdefault("metadata", {})
    data["metadata"]["mode"] = "cleared_mojibake_waiting_refetch"
    data["metadata"]["warning"] = f"Removed {len(bad)} corrupted item names before refetch."
    DB.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status":"cleared","bad_items":len(bad),"backup":str(backup)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
