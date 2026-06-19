import json, urllib.parse
from config import DATA

EQUIPMENT = DATA / "equipment_db.json"
WEEKLY = DATA / "weekly.json"
GEAR = DATA / "gear_index.json"
ROUTES = DATA / "routes.json"
ALIASES = DATA / "item_aliases_ko.json"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def norm(s):
    return str(s or "").lower().replace("’","'").strip()

def ko_search_url(name):
    return "https://dune.gaming.tools/ko/items?search=" + urllib.parse.quote(str(name or ""))

def build_lookup(equipment, aliases):
    by_name = {norm(i.get("name")): i for i in equipment.get("items", []) if i.get("name")}
    for row in aliases.get("items", []):
        ko, original = row.get("ko"), row.get("original")
        if ko and original and norm(ko) in by_name:
            by_name[norm(original)] = by_name[norm(ko)]
    return by_name

def localize_str(s, aliases, route_map):
    if not isinstance(s, str): return s
    for row in aliases.get("items", []):
        s = s.replace(row["original"], row["ko"])
    for en, ko in route_map.items():
        s = s.replace(en, ko)
    return s

def walk(obj, aliases, route_map, lookup):
    if isinstance(obj, dict):
        if isinstance(obj.get("name"), str):
            original = obj["name"]
            found = lookup.get(norm(original)) or lookup.get(norm(localize_str(original, aliases, route_map)))
            if found:
                obj["original_name"] = original
                obj["name"] = found.get("name", original)
                obj["url"] = found.get("url", ko_search_url(obj["name"]))
                obj["db_source"] = "dune.gaming.tools/ko"
            else:
                obj["name"] = localize_str(original, aliases, route_map)
        for k,v in list(obj.items()):
            if isinstance(v, str):
                if "method.gg/dune-awakening/database" in v:
                    obj[k] = ko_search_url(obj.get("name",""))
                elif v.startswith("https://dune.gaming.tools/") and "/ko/" not in v:
                    obj[k] = v.replace("https://dune.gaming.tools/", "https://dune.gaming.tools/ko/")
                else:
                    obj[k] = localize_str(v, aliases, route_map)
            else:
                walk(v, aliases, route_map, lookup)
    elif isinstance(obj, list):
        for x in obj:
            walk(x, aliases, route_map, lookup)

def main():
    equipment = load(EQUIPMENT, {"items": []})
    aliases = load(ALIASES, {"items": [], "routes": {}})
    lookup = build_lookup(equipment, aliases)
    route_map = aliases.get("routes", {})

    if WEEKLY.exists():
        weekly = load(WEEKLY, {})
        if "week" in weekly and "regions" in weekly["week"]:
            asia = weekly["week"]["regions"].get("asia", "KST/JST")
            weekly["week"]["regions"] = {"asia": asia}
        weekly.setdefault("site", {})["db_source"] = "dune.gaming.tools/ko"
        walk(weekly, aliases, route_map, lookup)
        dump(WEEKLY, weekly)

    if GEAR.exists():
        gear = load(GEAR, [])
        for item in gear:
            original = item.get("original_name") or item.get("name")
            found = lookup.get(norm(original)) or lookup.get(norm(item.get("name")))
            if found:
                item["original_name"] = original
                item["name"] = found["name"]
                item["links"] = [{"label":"한글 DB", "url": found.get("url", ko_search_url(found["name"]))}]
            else:
                item["name"] = localize_str(item.get("name",""), aliases, route_map)
                item["links"] = [{"label":"한글 DB 검색", "url": ko_search_url(item.get("name",""))}]
            item["db_source"] = "dune.gaming.tools/ko"
        dump(GEAR, gear)

    if ROUTES.exists():
        routes = load(ROUTES, [])
        walk(routes, aliases, route_map, lookup)
        dump(ROUTES, routes)

if __name__ == "__main__":
    main()
