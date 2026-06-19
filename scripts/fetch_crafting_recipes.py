import json, re, time, hashlib, os
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from config import DATA, RAW

BASE = "https://dune.gaming.tools"
CALCULATOR = f"{BASE}/crafting-calculator"
OUT = DATA / "crafting_recipes.json"
UPDATE_LOG = DATA / "update_log.json"
RAW_OUT = RAW / "crafting_source_pages.json"

LIMIT = int(os.getenv("CRAFTING_CRAWL_LIMIT", "0") or "0")
DELAY = float(os.getenv("CRAFTING_CRAWL_DELAY", "0.06") or "0.06")
MIN_RECIPE_ITEMS = int(os.getenv("CRAFTING_MIN_RECIPE_ITEMS", "50") or "50")

HEADERS = {
    "User-Agent": "Nevermind-DuneHa-Guild-Helper/1.0 (+GitHub Pages source check)",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}

CATEGORY_HINTS = [
    ("vehicle", ["vehicle", "ornithopter", "sandbike", "buggy", "carrier", "engine", "wing", "thruster", "chassis", "cockpit", "cabin", "storage"]),
    ("weapon", ["weapon", "rifle", "lasgun", "pistol", "sword", "knife", "blade", "cannon", "drillshot", "rapier", "maula", "vulcan", "karpov"]),
    ("armor", ["garment", "armor", "chestpiece", "helmet", "pants", "boots", "gloves", "stillsuit", "jacket", "gauntlets", "leggings"]),
    ("tool", ["tool", "cutteray", "compactor", "reaper", "scanner", "suspensor", "extractor", "dew"]),
    ("placeable", ["placeable", "fabricator", "refinery", "windtrap", "storage", "generator"]),
    ("buildable", ["wall", "roof", "floor", "door", "foundation", "stairs", "arch"]),
    ("component", ["component", "machinery", "capacitor", "pump", "servok", "regulator", "plating"]),
    ("refined_resource", ["ingot", "paste", "dust", "refined", "plasteel", "plastanium", "duraluminum"]),
]

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_log(status, message, extra=None):
    log = load_json(UPDATE_LOG, {"entries": []})
    log.setdefault("entries", [])
    entry = {"time": now(), "type": "crafting-db", "status": status, "message": message}
    if extra:
        entry.update(extra)
    log["entries"].insert(0, entry)
    log["entries"] = log["entries"][:60]
    UPDATE_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.text

def clean(s):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = re.sub(r"^Image:\s*", "", s).strip()
    parts = s.split()
    if len(parts) >= 2 and len(parts) % 2 == 0:
        half = len(parts)//2
        if parts[:half] == parts[half:]:
            s = " ".join(parts[:half])
    return s

def slug_from_url(url):
    return url.rstrip("/").split("/")[-1]

def guess_category(name, page_text, url):
    hay = f"{name} {page_text} {url}".lower()
    for cat, keys in CATEGORY_HINTS:
        if any(k in hay for k in keys):
            return cat
    return "unknown"

def parse_item_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = clean(a.get_text(" "))
        if not text or text.lower() in {"home", "discord", "database", "tools"}:
            continue
        if "/items/" in href or href.startswith("/items/"):
            url = urljoin(BASE, href)
            links[url] = text
    return [{"name": name, "url": url, "id": slug_from_url(url)} for url, name in links.items()]

def parse_material_line(line):
    line = clean(line)
    m = re.search(r"(.+?)\s*\|\s*x?([\d,.]+)\s*([A-Za-z가-힣/]+)?$", line)
    if not m:
        m = re.search(r"(.+?)\s+x([\d,.]+)\s*([A-Za-z가-힣/]+)?$", line)
    if not m:
        return None
    name = clean(m.group(1))
    qty = float(m.group(2).replace(",", ""))
    unit = m.group(3) or ""
    if unit.lower() == "x":
        unit = ""
    words = name.split()
    if len(words) >= 2 and len(words) % 2 == 0:
        half = len(words)//2
        if words[:half] == words[half:]:
            name = " ".join(words[:half])
    if not name or name.lower() in {"ingredients", "time", "station"}:
        return None
    if qty.is_integer():
        qty = int(qty)
    return {"name": name, "qty": qty, **({"unit": unit} if unit else {})}

def parse_item_page(url, fallback_name):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    title = clean((soup.find("h1").get_text(" ") if soup.find("h1") else fallback_name))
    text_lines = [clean(x) for x in soup.get_text("\n").splitlines()]
    text_lines = [x for x in text_lines if x]

    category_label = ""
    for h in soup.find_all(["h2", "h3"]):
        t = clean(h.get_text(" "))
        if " - " in t or t.startswith(("Misc", "Vehicles", "Weapons", "Garments", "Tools")):
            category_label = t
            break

    recipes = []
    i = 0
    while i < len(text_lines):
        if text_lines[i].lower() == "crafting":
            station = ""
            time_value = ""
            mats = []
            j = i + 1
            while j < min(len(text_lines), i + 48):
                line = text_lines[j]
                low = line.lower()
                if j > i + 1 and low == "crafting":
                    break
                if not station and ("refinery" in low or "fabricator" in low or "processor" in low or "assembler" in low or "deathstill" in low):
                    station = line
                if not time_value and re.fullmatch(r"[\d:.]+\s*[smh]?", line.lower() or ""):
                    time_value = line
                mat = parse_material_line(line)
                if mat:
                    mats.append(mat)
                j += 1
            seen = set()
            dedup = []
            for m in mats:
                key = (m["name"], m.get("unit",""), str(m["qty"]))
                if key not in seen:
                    seen.add(key)
                    dedup.append(m)
            if dedup:
                recipes.append({"station": station or "Crafting Station", "time": time_value, "materials": dedup})
            i = j
        else:
            i += 1

    if recipes:
        default = recipes[0]
        materials = default["materials"]
        station = default["station"]
        status = "source_detected"
    else:
        materials = []
        station = ""
        status = "no_recipe_detected"

    return {
        "id": slug_from_url(url),
        "name": title or fallback_name,
        "category": guess_category(title or fallback_name, category_label, url),
        "category_label": category_label,
        "station": station,
        "status": status,
        "source": "dune.gaming.tools",
        "url": url,
        "materials": materials,
        "variants": recipes
    }, {"url": url, "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(), "title": title, "recipe_count": len(recipes)}

def preserve_previous(reason, extra=None):
    previous = load_json(OUT, None)
    if previous:
        meta = previous.setdefault("metadata", {})
        meta["mode"] = "previous_db_preserved"
        meta["checked_at"] = now()
        meta["warning"] = reason
        OUT.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")
        write_log("preserved", reason, extra)
        print(json.dumps({"ok": True, "mode": "previous_db_preserved", "reason": reason}, ensure_ascii=False, indent=2))
        return True
    return False

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    try:
        calc_html = fetch(CALCULATOR)
        links = parse_item_links(calc_html)
        if LIMIT > 0:
            links = links[:LIMIT]

        if not links:
            if preserve_previous("제작 계산기 소스에서 아이템 링크를 찾지 못했습니다.", {"item_link_count": 0}):
                return

        items, raw_pages, failures = [], {
            "calculator": {
                "url": CALCULATOR,
                "sha256": hashlib.sha256(calc_html.encode("utf-8")).hexdigest(),
                "item_link_count": len(links)
            },
            "pages": []
        }, 0

        for idx, link in enumerate(links, start=1):
            try:
                item, meta = parse_item_page(link["url"], link["name"])
                if item.get("materials"):
                    items.append(item)
                raw_pages["pages"].append(meta)
                print(json.dumps({"idx": idx, "total": len(links), "name": item.get("name"), "materials": len(item.get("materials", []))}, ensure_ascii=False))
                time.sleep(DELAY)
            except Exception as exc:
                failures += 1
                raw_pages["pages"].append({"url": link["url"], "error": repr(exc)[:300]})
                print(json.dumps({"warning": "item fetch failed", "url": link["url"], "error": repr(exc)[:200]}, ensure_ascii=False))

        RAW_OUT.write_text(json.dumps(raw_pages, ensure_ascii=False, indent=2), encoding="utf-8")

        if len(items) < MIN_RECIPE_ITEMS:
            reason = f"수집된 제작 레시피가 {len(items)}개로 기준({MIN_RECIPE_ITEMS}개) 미만입니다. 기존 DB를 유지합니다."
            if preserve_previous(reason, {"item_link_count": len(links), "recipe_item_count": len(items), "failures": failures}):
                return

        data = {
            "metadata": {
                "schema_version": "1.0",
                "mode": "full_crawl_from_dune_gaming_tools",
                "primary_source": "dune.gaming.tools/crafting-calculator",
                "secondary_sources": ["questlog.gg recipes", "awakening.wiki"],
                "updated_at": now(),
                "item_link_count": len(links),
                "recipe_item_count": len(items),
                "failures": failures,
                "note": "전체 제작 가능 아이템을 gaming.tools에서 수집했습니다. 페이지 구조 변경 시 일부 항목은 누락될 수 있습니다."
            },
            "items": sorted(items, key=lambda x: x.get("name",""))
        }

        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        write_log("updated", f"제작 DB 갱신 완료: {len(items)}개 레시피", {"item_link_count": len(links), "recipe_item_count": len(items), "failures": failures})
        print(json.dumps(data["metadata"], ensure_ascii=False, indent=2))

    except Exception as exc:
        reason = f"제작 DB 수집 실패. 기존 DB를 유지합니다. 오류: {repr(exc)[:240]}"
        if not preserve_previous(reason):
            OUT.write_text(json.dumps({"metadata": {"mode": "crawl_failed_empty", "updated_at": now(), "warning": reason}, "items": []}, ensure_ascii=False, indent=2), encoding="utf-8")
            write_log("failed_empty", reason)
        print(json.dumps({"warning": reason}, ensure_ascii=False))

if __name__ == "__main__":
    main()
