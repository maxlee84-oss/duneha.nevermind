import copy
import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import DATA, RAW

ROUTES = [
    {
        "id": "route-the-old-quarry",
        "name": "올드 쿼리",
        "source_name": "The Old Quarry",
        "url": "https://www.method.gg/dune-awakening/testing-stations/testing-station-the-old-quarry",
    },
    {
        "id": "route-testing-station-24",
        "name": "테스팅 스테이션 #24",
        "source_name": "Testing Station 24",
        "url": "https://www.method.gg/dune-awakening/testing-stations/testing-station-24",
    },
    {
        "id": "route-testing-station-89",
        "name": "테스팅 스테이션 #89",
        "source_name": "Testing Station 89",
        "url": "https://www.method.gg/dune-awakening/testing-stations/testing-station-89",
    },
    {
        "id": "route-testing-station-136",
        "name": "테스팅 스테이션 #136",
        "source_name": "Testing Station 136",
        "url": "https://www.method.gg/dune-awakening/testing-stations/testing-station-136",
    },
    {
        "id": "route-testing-station-152",
        "name": "테스팅 스테이션 #152",
        "source_name": "Testing Station 152",
        "url": "https://www.method.gg/dune-awakening/testing-stations/testing-station-152",
    },
    {
        "id": "route-testing-station-195",
        "name": "테스팅 스테이션 #195",
        "source_name": "Testing Station 195",
        "url": "https://www.method.gg/dune-awakening/testing-stations/testing-station-195",
    },
]

WEEKLY = DATA / "weekly.json"
ROUTES_JSON = DATA / "routes.json"
EQUIPMENT = DATA / "equipment_db.json"
ALIASES = DATA / "item_aliases_ko.json"
UPDATE_LOG = DATA / "update_log.json"
REPORT = DATA / "dungeon_update_report.json"
PREVIOUS = DATA / "dungeon_previous.json"

HEADERS = {
    "User-Agent": "Nevermind-DuneHa-Dungeon-Updater/1.0 (+GitHub Actions fan utility)",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}

CATEGORY_MAP = {
    "Weapons": ("무기", "drop-chip type-weapon", "◆"),
    "Garments": ("방어구", "drop-chip type-armor", "⬟"),
    "Tools": ("도구", "drop-chip type-tool", "✦"),
    "Vehicle Components": ("차량 부품", "drop-chip type-vehicle", "▰"),
    "Augmentations": ("증강", "drop-chip type-misc", "◇"),
    "Resources": ("자원", "drop-chip type-misc", "◇"),
    "Consumables": ("소모품", "drop-chip type-misc", "◇"),
}

HAZARD_KO = {
    "Fire Damage": "화염 피해",
    "Radiation Damage": "방사능 피해",
    "Poison Damage": "독성 피해",
    "Electric Damage": "전기 피해",
    "Trap Damage": "함정 피해",
    "Explosive Barrel Damage": "폭발성 배럴 피해",
    "Quicksand Sinking Speed": "유사 침하 속도",
}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def slugify(value):
    value = clean(value).lower().replace("’", "'")
    return re.sub(r"[^a-z0-9가-힣]+", "-", value).strip("-") or "item"

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def ko_search_url(name):
    return "https://dune.gaming.tools/ko/items?search=" + urllib.parse.quote(clean(name))

def append_log(status, message, extra=None):
    log = load_json(UPDATE_LOG, {"entries":[]})
    log.setdefault("entries", [])
    row = {"time":now_iso(),"type":"dungeon-auto-update","status":status,"message":message}
    if extra:
        row.update(extra)
    log["entries"].insert(0,row)
    log["entries"] = log["entries"][:100]
    write_json(UPDATE_LOG, log)

def fetch(url, raw_path):
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    try:
        text = response.content.decode("utf-8")
    except UnicodeDecodeError:
        response.encoding = response.apparent_encoding or "utf-8"
        text = response.text
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text, encoding="utf-8", errors="ignore")
    return text

def text_lines(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    return [clean(x) for x in soup.get_text("\n").splitlines() if clean(x)]

def build_localizer():
    equipment = load_json(EQUIPMENT, {"items":[]})
    aliases = load_json(ALIASES, {"items":[]})
    by_name = {}
    by_slug = {}
    for item in equipment.get("items",[]):
        name = clean(item.get("name"))
        if name:
            by_name[name.lower()] = item
        for ident in (item.get("id"), item.get("slug"), str(item.get("url","")).rstrip("/").split("/")[-1]):
            if ident:
                by_slug[slugify(ident)] = item
    alias_by_en = {
        clean(x.get("original")).lower(): clean(x.get("ko"))
        for x in aliases.get("items",[])
        if clean(x.get("original")) and clean(x.get("ko"))
    }

    def localize(name):
        original = clean(name)
        alias = alias_by_en.get(original.lower())
        found = by_slug.get(slugify(original)) or (by_name.get(alias.lower()) if alias else None)
        if found:
            ko_name = clean(found.get("name")) or alias or original
            return ko_name, found.get("url") or ko_search_url(ko_name), "equipment_db"
        if alias:
            return alias, ko_search_url(alias), "alias"
        return original, ko_search_url(original), "search"
    return localize

def find_section(lines, start_label, end_labels):
    try:
        start = next(i for i,x in enumerate(lines) if x == start_label) + 1
    except StopIteration:
        return []
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i] in end_labels:
            end = i
            break
    return lines[start:end]

def parse_hazards(lines):
    raw = find_section(lines, "Testing Station Hazards", {"Testing Station Loot"})
    hazards = []
    for line in raw:
        if line in HAZARD_KO:
            hazards.append(HAZARD_KO[line])
        elif line.endswith("Damage") or "Sinking Speed" in line:
            hazards.append(line)
    return list(dict.fromkeys(hazards))

def parse_info(lines):
    info = {}
    joined = " ".join(lines[:300])
    patterns = {
        "element": r"Element:\s*([^|]+?)(?:Party Size:|Loot Grades:|$)",
        "party_size": r"Party Size:\s*(\d+)",
        "loot_grades": r"Loot Grades:\s*([0-9\-–]+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, joined, re.I)
        if m:
            info[key] = clean(m.group(1))
    return info

def parse_loot(lines, localize):
    try:
        start = next(i for i,x in enumerate(lines) if x == "Testing Station Loot") + 1
    except StopIteration:
        raise ValueError("Testing Station Loot marker missing")

    end_markers = {
        "Looking for a Build or Guide?", "Best Build Video & Written Guide",
        "Return to Index", "Enjoying Dune?"
    }
    loot_lines = []
    for line in lines[start:]:
        if line in end_markers:
            break
        loot_lines.append(line)

    drops = []
    # Common Method text form: 10% S Weapons Perforator
    pattern = re.compile(
        r"^(<1%|\d+(?:\.\d+)?%)\s+([SABC])\s+"
        r"(Weapons|Garments|Tools|Vehicle Components|Augmentations|Resources|Consumables)\s+(.+)$"
    )
    for line in loot_lines:
        match = pattern.match(line)
        if not match:
            continue
        chance, rank, category_en, original = match.groups()
        original = clean(original)
        if not original or original.lower() in {"items", "augments"}:
            continue
        ko_name, url, match_state = localize(original)
        category_ko, type_class, icon = CATEGORY_MAP[category_en]
        drops.append({
            "id": slugify(original),
            "slug": slugify(original),
            "original_name": original,
            "name": ko_name,
            "display_name": f"{icon} {ko_name}",
            "url": url,
            "category": category_ko,
            "category_en": category_en,
            "rank": rank,
            "chance": chance,
            "type_class": type_class,
            "source_match": match_state,
            "confidence": "auto_parsed_method",
            "image": None,
        })

    dedup = {}
    for drop in drops:
        key = (drop["slug"], drop["rank"], drop["chance"])
        dedup.setdefault(key, drop)
    return list(dedup.values())

def make_subtitle(route, hazards, info, drops):
    parts = []
    if route["id"] == "route-the-old-quarry":
        parts.append("채석장")
    if hazards:
        parts.append(" · ".join(hazards[:2]))
    if info.get("party_size"):
        parts.append(f"권장 인원 표기 {info['party_size']}명")
    parts.append(f"드랍 {len(drops)}종")
    return " · ".join(parts)

def parse_route(route, localize):
    raw_path = RAW / f"dungeon_{route['id']}.html"
    html = fetch(route["url"], raw_path)
    lines = text_lines(html)
    drops = parse_loot(lines, localize)
    hazards = parse_hazards(lines)
    info = parse_info(lines)

    return {
        "id": route["id"],
        "name": route["name"],
        "source_name": route["source_name"],
        "subtitle": make_subtitle(route, hazards, info, drops),
        "hazards": hazards,
        "info": info,
        "drop_count": len(drops),
        "drops": drops,
        "source": "Method Testing Stations",
        "source_url": route["url"],
        "updated_at": now_iso(),
        "confidence": "auto_parsed_method",
    }

def validate_candidate(candidate):
    errors = []
    if set(candidate.keys()) != {x["id"] for x in ROUTES}:
        errors.append("route set incomplete")
    per_route = {}
    for route in ROUTES:
        row = candidate.get(route["id"], {})
        count = len(row.get("drops",[]))
        per_route[route["id"]] = count
        # Old Quarry and station pages should expose a meaningful loot table.
        if count < 6:
            errors.append(f"{route['id']} drop count {count} < 6")
        names = [x.get("slug") for x in row.get("drops",[])]
        if names and len(set(names)) / len(names) < 0.75:
            errors.append(f"{route['id']} duplicate ratio too high")
    return errors, per_route

def preserve(weekly, reason, extra=None):
    weekly["dungeon_update"] = {
        "status":"preserved",
        "source":"Method Testing Stations",
        "checked_at":now_iso(),
        "reason":reason,
    }
    status = weekly.setdefault("automation_status",{})
    status.update({
        "dungeon_mode":"previous_preserved",
        "checked_at":now_iso(),
        "message":"던전 자동 수집 검증에 실패하여 마지막 검증본을 유지합니다.",
    })
    write_json(WEEKLY, weekly)
    report = {"ok":False,"status":"preserved","reason":reason,"checked_at":now_iso()}
    if extra:
        report.update(extra)
    write_json(REPORT, report)
    append_log("preserved", reason, extra)
    print(json.dumps(report, ensure_ascii=False, indent=2))

def main():
    weekly = load_json(WEEKLY, None)
    if not weekly:
        raise SystemExit("weekly.json missing")

    try:
        localize = build_localizer()
        candidate = {}
        for route in ROUTES:
            candidate[route["id"]] = parse_route(route, localize)

        errors, counts = validate_candidate(candidate)
        if errors:
            preserve(weekly, "; ".join(errors), {"counts":counts})
            return

        write_json(PREVIOUS, {
            "saved_at":now_iso(),
            "dungeons":weekly.get("dungeons",{}),
            "dungeon_update":weekly.get("dungeon_update"),
        })

        weekly["dungeons"] = candidate
        weekly["generated_at"] = now_iso()
        weekly["dungeon_update"] = {
            "status":"updated",
            "source":"Method Testing Stations",
            "source_url":"https://www.method.gg/dune-awakening/testing-stations",
            "secondary_source":"dune.gaming.tools/ko",
            "counts":counts,
            "updated_at":now_iso(),
        }
        status = weekly.setdefault("automation_status",{})
        status.update({
            "dungeon_mode":"auto_updated",
            "checked_at":now_iso(),
            "message":"DD와 던전 데이터가 외부 소스 검증 후 자동 갱신되었습니다.",
            "render_mode":"weekly_json_single_source",
        })
        write_json(WEEKLY, weekly)

        # routes.json stores generic route metadata only. No user/guild recommendations.
        route_index = []
        for route in ROUTES:
            parsed = candidate[route["id"]]
            route_index.append({
                "id":parsed["id"],
                "name":parsed["name"],
                "subtitle":parsed["subtitle"],
                "hazards":parsed["hazards"],
                "info":parsed["info"],
                "drop_count":parsed["drop_count"],
                "tags":["dungeon","overland"],
                "source_url":parsed["source_url"],
                "updated_at":parsed["updated_at"],
            })
        write_json(ROUTES_JSON, route_index)

        report = {
            "ok":True,"status":"updated","counts":counts,
            "updated_at":now_iso()
        }
        write_json(REPORT, report)
        append_log("updated","Dungeon data updated",report)
        print(json.dumps(report, ensure_ascii=False, indent=2))

    except Exception as exc:
        preserve(weekly, f"parser error: {repr(exc)[:400]}")
        if isinstance(exc,(ValueError,RuntimeError)):
            return
        raise


def parse_loot_flexible(html, lines, localize):
    drops = parse_loot(lines, localize) if "Testing Station Loot" in lines else []
    if drops:
        return drops

    # Fallback 1: visible text without exact section markers.
    joined_lines = lines
    pattern = re.compile(
        r"(?:(<1%|\d+(?:\.\d+)?%)\s*)?([SABC])\s+"
        r"(Weapons|Garments|Tools|Vehicle Components|Augmentations|Resources|Consumables)\s+"
        r"([^|]{2,100})$"
    )
    for line in joined_lines:
        m = pattern.search(line)
        if not m:
            continue
        chance, rank, category_en, original = m.groups()
        original = clean(original)
        if any(x in original.lower() for x in ("looking for", "build guide", "return to")):
            continue
        ko_name, url, match_state = localize(original)
        category_ko, type_class, icon = CATEGORY_MAP[category_en]
        drops.append({
            "id":slugify(original),"slug":slugify(original),
            "original_name":original,"name":ko_name,
            "display_name":f"{icon} {ko_name}","url":url,
            "category":category_ko,"category_en":category_en,
            "rank":rank,"chance":chance or "확률 미표기",
            "type_class":type_class,"source_match":match_state,
            "confidence":"auto_parsed_method_flexible","image":None,
        })

    # Fallback 2: embedded JSON blobs such as __NEXT_DATA__.
    if len(drops) < 6:
        soup = BeautifulSoup(html, "html.parser")
        blob_text = "\n".join(
            s.get_text(" ", strip=True) for s in soup.find_all("script")
            if s.get_text(strip=True)
        )
        json_pattern = re.compile(
            r'"(?:name|title)"\s*:\s*"([^"]{2,100})".{0,300}?'
            r'"(?:grade|rank|rarity)"\s*:\s*"([SABC])".{0,300}?'
            r'"(?:chance|dropChance|probability)"\s*:\s*"?([0-9.]+%?|<1%)"?',
            re.I|re.S
        )
        for m in json_pattern.finditer(blob_text):
            original, rank, chance = m.groups()
            if slugify(original) in {x["slug"] for x in drops}:
                continue
            ko_name, url, match_state = localize(original)
            drops.append({
                "id":slugify(original),"slug":slugify(original),
                "original_name":original,"name":ko_name,
                "display_name":f"◇ {ko_name}","url":url,
                "category":"기타","category_en":"Unknown",
                "rank":rank.upper(),"chance":chance if "%" in chance else chance+"%",
                "type_class":"drop-chip type-misc","source_match":match_state,
                "confidence":"auto_parsed_embedded_json","image":None,
            })

    dedup = {}
    for d in drops:
        dedup.setdefault((d["slug"],d.get("rank"),d.get("chance")),d)
    return list(dedup.values())

_original_parse_route = parse_route
def parse_route(route, localize):
    raw_path = RAW / f"dungeon_{route['id']}.html"
    html = fetch(route["url"], raw_path)
    lines = text_lines(html)
    drops = parse_loot_flexible(html, lines, localize)
    hazards = parse_hazards(lines)
    info = parse_info(lines)
    return {
        "id":route["id"],"name":route["name"],"source_name":route["source_name"],
        "subtitle":make_subtitle(route,hazards,info,drops),
        "hazards":hazards,"info":info,"drop_count":len(drops),"drops":drops,
        "source":"Method Testing Stations","source_url":route["url"],
        "updated_at":now_iso(),"confidence":"auto_parsed_method",
    }

_original_main = main
def main():
    weekly = load_json(WEEKLY,None)
    if not weekly:
        raise SystemExit("weekly.json missing")
    localize = build_localizer()
    previous = copy.deepcopy(weekly.get("dungeons",{}))
    merged = copy.deepcopy(previous)
    route_results = {}
    updated, preserved = [], []

    for route in ROUTES:
        try:
            parsed = parse_route(route,localize)
            names = [x.get("slug") for x in parsed.get("drops",[]) if x.get("slug")]
            unique_ratio = len(set(names))/len(names) if names else 0
            valid = len(names) >= 6 and unique_ratio >= 0.75
            route_results[route["id"]] = {
                "valid":valid,"drop_count":len(names),
                "unique_ratio":round(unique_ratio,4)
            }
            if valid:
                merged[route["id"]] = parsed
                updated.append(route["id"])
            else:
                preserved.append(route["id"])
        except Exception as exc:
            route_results[route["id"]] = {"valid":False,"error":repr(exc)[:240]}
            preserved.append(route["id"])

    if not updated:
        preserve(weekly,"all dungeon routes failed validation",{"routes":route_results})
        return

    write_json(PREVIOUS,{
        "saved_at":now_iso(),"dungeons":previous,
        "dungeon_update":weekly.get("dungeon_update")
    })
    weekly["dungeons"] = merged
    weekly["generated_at"] = now_iso()
    status_name = "updated" if not preserved else "partial"
    weekly["dungeon_update"] = {
        "status":status_name,"source":"Method Testing Stations",
        "source_url":"https://www.method.gg/dune-awakening/testing-stations",
        "secondary_source":"dune.gaming.tools/ko",
        "routes":route_results,"updated_routes":updated,
        "preserved_routes":preserved,"updated_at":now_iso(),
    }
    weekly.setdefault("automation_status",{}).update({
        "dungeon_mode":"auto_updated" if status_name=="updated" else "partial_updated",
        "checked_at":now_iso(),
        "message":"던전 데이터를 루트별 검증 후 갱신했습니다. 실패 루트는 마지막 검증본을 유지합니다.",
        "render_mode":"weekly_json_single_source",
    })
    write_json(WEEKLY,weekly)

    route_index=[]
    for route in ROUTES:
        parsed=merged.get(route["id"],{})
        route_index.append({
            "id":route["id"],"name":parsed.get("name",route["name"]),
            "subtitle":parsed.get("subtitle",""),
            "hazards":parsed.get("hazards",[]),"info":parsed.get("info",{}),
            "drop_count":len(parsed.get("drops",[])),
            "tags":["dungeon","overland"],
            "source_url":parsed.get("source_url",route["url"]),
            "updated_at":parsed.get("updated_at"),
        })
    write_json(ROUTES_JSON,route_index)
    report={
        "ok":True,"status":status_name,"routes":route_results,
        "updated_routes":updated,"preserved_routes":preserved,
        "updated_at":now_iso()
    }
    write_json(REPORT,report)
    append_log(status_name,"Dungeon route-level update",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
