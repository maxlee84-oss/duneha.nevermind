import json, sys
from config import DATA

WEEKLY = DATA / "weekly.json"
CRAFTING = DATA / "crafting_recipes.json"
EQUIPMENT = DATA / "equipment_db.json"
REPORT = DATA / "validation_report.json"
DD_REPORT = DATA / "dd_update_report.json"
DUNGEON_REPORT = DATA / "dungeon_update_report.json"

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def count_data(data):
    dd_counts = {}
    for k, bundle in (data.get("dd") or {}).items():
        items = bundle if isinstance(bundle, list) else bundle.get("items", [])
        dd_counts[k] = len(items or [])
    dungeon_counts = {k: len((v or {}).get("drops") or []) for k, v in (data.get("dungeons") or {}).items()}
    return dd_counts, dungeon_counts

def main():
    if not WEEKLY.exists():
        raise SystemExit("weekly.json missing")

    data = load_json(WEEKLY, {})
    crafting = load_json(CRAFTING, {"items": [], "metadata": {}})
    dd_report = load_json(DD_REPORT, {})
    dungeon_report = load_json(DUNGEON_REPORT, {})
    equipment = load_json(EQUIPMENT, {"items": [], "metadata": {}})
    errors, warnings = [], []

    for key in ["schema_version", "site", "week", "dd", "dungeons", "sources"]:
        if key not in data:
            errors.append(f"missing key: {key}")

    dd_counts, dungeon_counts = count_data(data)
    render_mode = (data.get("automation_status") or {}).get("render_mode")
    if render_mode != "weekly_json_single_source":
        warnings.append("weekly.json single-source render mode not set")
    if sum(dd_counts.values()) < 10:
        errors.append("too few DD items")
    if sum(dungeon_counts.values()) < 10:
        warnings.append("few dungeon drops")
    if len(dungeon_counts) < 3:
        warnings.append("few dungeon route groups")

    crafting_items = len(crafting.get("items") or [])
    equipment_items = len(equipment.get("items") or [])
    if crafting_items < 2:
        warnings.append("crafting DB has very few items")
    if equipment_items < 2:
        warnings.append("equipment KO DB has very few items")

    report = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "dd_counts": dd_counts,
        "dungeon_counts": dungeon_counts,
        "automation_status": data.get("automation_status", {}),
        "weekly_render_mode": render_mode,
        "dd_update_status": dd_report.get("status"),
        "dungeon_update_status": dungeon_report.get("status"),
        "crafting_items": crafting_items,
        "crafting_mode": (crafting.get("metadata") or {}).get("mode"),
        "equipment_items": equipment_items,
        "equipment_mode": (equipment.get("metadata") or {}).get("mode")
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
