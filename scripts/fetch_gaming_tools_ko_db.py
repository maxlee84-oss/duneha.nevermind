import json, re, time, hashlib, os
from datetime import datetime, timezone
from urllib.parse import urljoin
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from config import DATA, RAW

BASE = "https://dune.gaming.tools"
KO_BASE = f"{BASE}/ko"
ITEMS_URL = f"{KO_BASE}/items"
CRAFTING_URL = f"{KO_BASE}/crafting-calculator"

OUT = DATA / "equipment_db.json"
CRAFTING_OUT = DATA / "crafting_recipes.json"
UPDATE_LOG = DATA / "update_log.json"
RAW_OUT = RAW / "gaming_tools_ko_pages.json"

LIMIT = int(os.getenv("KO_DB_CRAWL_LIMIT", "0") or "0")
DELAY = float(os.getenv("KO_DB_CRAWL_DELAY", "0.05") or "0.05")
MIN_ITEMS = int(os.getenv("KO_DB_MIN_ITEMS", "50") or "50")

HEADERS = {
    "User-Agent": "Nevermind-DuneHa-KO-DB/1.0 (+GitHub Pages source check)",
    "Accept-Language": "ko-KR,ko;q=0.95,en-US;q=0.5,en;q=0.3",
}

CATEGORY_RULES = [
    ("vehicle", ["차량", "오니솝터", "샌드바이크", "버기", "엔진", "차대", "화물", "날개", "추진기"]),
    ("weapon", ["무기", "산탄총", "검", "더크", "레이피어", "권총", "소총", "벌컨", "카르포프", "라스건"]),
    ("armor", ["의복", "방어구", "재킷", "후드", "부츠", "장갑", "튜닉", "헬멧", "스틸슈트"]),
    ("tool", ["도구", "커터레이", "채취기", "혈액 추출기", "집수", "반중력 장치"]),
    ("placeable", ["설치물", "제작기", "정제기", "바람덫", "저장", "발전기"]),
    ("buildable", ["건설", "벽", "바닥", "지붕", "계단", "기둥", "문", "난간"]),
    ("component", ["구성 요소", "기계", "펌프", "축전기", "장갑판", "서보크", "조절기"]),
    ("refined_resource", ["정제된 자원", "주괴", "가루", "페이스트", "멜란지", "플래스틸", "플라스타늄"]),
    ("raw_resource", ["원자재", "광석", "섬유", "모래"])
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
    entry = {"time": now(), "type": "gaming-tools-ko-db", "status": status, "message": message}
    if extra:
        entry.update(extra)
    log["entries"].insert(0, entry)
    log["entries"] = log["entries"][:80]
    UPDATE_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()

    # gaming.tools can omit a charset in Content-Type. requests then assumes
    # ISO-8859-1 and corrupts Korean UTF-8 text into strings such as
    # "ì•„ì�´í…œ". Always decode the response bytes as UTF-8 first.
    try:
        text = r.content.decode("utf-8")
    except UnicodeDecodeError:
        r.encoding = r.apparent_encoding or "utf-8"
        text = r.text

    return repair_mojibake(text)


MOJIBAKE_MARKERS = (
    "Ã", "Â", "â€", "â€™", "â€œ", "â€\x9d", "ì", "ë", "ê", "í", "ðŸ", "�"
)

def mojibake_score(value):
    text = str(value or "")
    if not text:
        return 0
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)

def repair_mojibake(value):
    text = str(value or "")
    if mojibake_score(text) == 0:
        return text

    # Typical failure mode: UTF-8 bytes decoded as latin-1/cp1252.
    for source_encoding in ("latin1", "cp1252"):
        try:
            repaired = text.encode(source_encoding).decode("utf-8")
            if mojibake_score(repaired) < mojibake_score(text):
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text

def validate_korean_text(items):
    names = [str(item.get("name") or "") for item in items]
    if not names:
        return False, {"item_count": 0, "bad_names": 0, "korean_names": 0}

    bad = [name for name in names if mojibake_score(name) > 0]
    korean = [name for name in names if re.search(r"[가-힣]", name)]
    stats = {
        "item_count": len(names),
        "bad_names": len(bad),
        "korean_names": len(korean),
        "bad_ratio": round(len(bad) / len(names), 4),
        "korean_ratio": round(len(korean) / len(names), 4),
    }
    valid = stats["bad_ratio"] <= 0.02 and stats["korean_ratio"] >= 0.15
    return valid, stats

def clean(s):
    s = repair_mojibake(s)
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = re.sub(r"^Image:\s*", "", s)
    # remove duplicated token sequences commonly produced by img alt + text
    parts = s.split()
    if len(parts) >= 2 and len(parts) % 2 == 0:
        half = len(parts)//2
        if parts[:half] == parts[half:]:
            s = " ".join(parts[:half])
    return s.strip()

def slug_from_url(url):
    return re.sub(r"[^a-zA-Z0-9가-힣_-]+", "-", url.rstrip("/").split("/")[-1]).strip("-")

def guess_category(label, name=""):
    hay = f"{label} {name}"
    for cat, keys in CATEGORY_RULES:
        if any(k in hay for k in keys):
            return cat
    return "unknown"

def parse_links_from_page(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        text = clean(a.get_text(" "))
        if not text:
            continue
        if "/ko/items/" in href or href.startswith("/ko/items/"):
            url = urljoin(BASE, href)
            links[url] = text
    return [{"id": slug_from_url(url), "name": name, "url": url} for url, name in links.items()]

def split_item_line(text):
    # Example: "스파이스 멜란지 기타 - 정제된 자원"
    m = re.match(r"(.+?)\s+([가-힣A-Za-z ]+\s-\s[가-힣A-Za-z0-9 #]+)(?:\s+Tier\s+\d+.*)?$", text)
    if m:
        return clean(m.group(1)), clean(m.group(2))
    return clean(text), ""

def parse_material_line(line):
    line = clean(line)
    # Korean page still often has "재료명 | x10" style from calculator/page text extraction
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
    if qty.is_integer():
        qty = int(qty)
    if not name or name in {"제작", "Crafting", "Time", "시간"}:
        return None
    return {"name": name, "qty": qty, **({"unit": unit} if unit else {})}

def parse_stats(lines):
    stats = []
    skip = {"제작", "Crafting", "Home", "Database", "Tools", "COPY", "Add", "Sign In"}
    for idx, line in enumerate(lines):
        if line in skip:
            continue
        # key: value
        if ":" in line and len(line) < 90:
            k, v = [clean(x) for x in line.split(":", 1)]
            if (
                k and v and len(k) <= 32
                and k.lower() not in {"http", "https", "url", "image", "link"}
                and not v.startswith("//")
                and "dune.gaming.tools/" not in v
            ):
                stats.append({"label": k, "value": v})
        # common labels followed by value
        elif line in {"피해 유형", "발사 방식", "발당 피해", "고유 효과", "방어도", "내구도", "전력 소비", "제작대", "Tier", "Rarity", "희귀도"} and idx + 1 < len(lines):
            v = clean(lines[idx+1])
            if v and v not in skip:
                stats.append({"label": line, "value": v})
    # dedup, cap
    out, seen = [], set()
    for s in stats:
        key = (s["label"], s["value"])
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:24]

def parse_recipe(lines):
    recipes = []
    i = 0
    while i < len(lines):
        if lines[i].lower() in {"crafting", "제작"}:
            station = ""
            mats = []
            j = i + 1
            while j < min(len(lines), i + 55):
                line = lines[j]
                low = line.lower()
                if j > i + 1 and low in {"crafting", "제작"}:
                    break
                if not station and any(k in line for k in ["제작기", "정제기", "Refinery", "Fabricator", "Assembler", "Processor", "데스스틸"]):
                    station = line
                mat = parse_material_line(line)
                if mat:
                    mats.append(mat)
                j += 1
            if mats:
                # dedup
                seen, dedup = set(), []
                for m in mats:
                    key = (m["name"], str(m["qty"]), m.get("unit",""))
                    if key not in seen:
                        seen.add(key)
                        dedup.append(m)
                recipes.append({"station": station or "제작대 정보 확인 중", "materials": dedup})
            i = j
        else:
            i += 1
    return recipes

def parse_item_page(link):
    html = fetch(link["url"])
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = clean(h1.get_text(" ")) if h1 else link["name"]
    title, inline_label = split_item_line(title)

    lines = [clean(x) for x in soup.get_text("\n").splitlines()]
    lines = [x for x in lines if x]

    category_label = inline_label
    for h in soup.find_all(["h2", "h3"]):
        t = clean(h.get_text(" "))
        if " - " in t or any(k in t for k in ["무기", "차량", "의복", "기타", "설치물", "건설"]):
            category_label = category_label or t
            break

    recipes = parse_recipe(lines)
    stats = parse_stats(lines)
    station = recipes[0]["station"] if recipes else ""
    materials = recipes[0]["materials"] if recipes else []

    return {
        "id": link["id"],
        "name": title,
        "category": guess_category(category_label, title),
        "category_label": category_label,
        "station": station,
        "status": "ko_source_detected" if (stats or materials) else "ko_source_listed",
        "source": "dune.gaming.tools/ko",
        "url": link["url"],
        "note": "dune.gaming.tools/ko 한글 DB에서 수집",
        "stats": stats,
        "materials": materials,
        "variants": recipes
    }, {"url": link["url"], "title": title, "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(), "stats": len(stats), "materials": len(materials)}

def preserve_previous(reason, extra=None):
    prev = load_json(OUT, None)
    if prev and prev.get("items"):
        prev.setdefault("metadata", {})
        prev["metadata"]["mode"] = "previous_ko_db_preserved"
        prev["metadata"]["checked_at"] = now()
        prev["metadata"]["warning"] = reason
        OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
        write_log("preserved", reason, extra)
        print(json.dumps({"mode": "previous_ko_db_preserved", "reason": reason}, ensure_ascii=False, indent=2))
        return True
    return False

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    try:
        items_html = fetch(ITEMS_URL)
        craft_html = fetch(CRAFTING_URL)
        links = {}
        for l in parse_links_from_page(items_html, ITEMS_URL) + parse_links_from_page(craft_html, CRAFTING_URL):
            links[l["url"]] = l
        links = list(links.values())

        if LIMIT > 0:
            links = links[:LIMIT]

        if len(links) < MIN_ITEMS:
            if preserve_previous(f"한글 아이템 링크 수가 {len(links)}개로 기준({MIN_ITEMS}) 미만입니다.", {"link_count": len(links)}):
                return

        parsed, raw_pages, failures = [], [], 0
        for idx, link in enumerate(links, 1):
            try:
                item, meta = parse_item_page(link)
                parsed.append(item)
                raw_pages.append(meta)
                print(json.dumps({"idx": idx, "total": len(links), "name": item["name"], "stats": len(item.get("stats", [])), "materials": len(item.get("materials", []))}, ensure_ascii=False))
                time.sleep(DELAY)
            except Exception as exc:
                failures += 1
                raw_pages.append({"url": link["url"], "error": repr(exc)[:240]})
                print(json.dumps({"warning": "ko item fetch failed", "url": link["url"], "error": repr(exc)[:180]}, ensure_ascii=False))

        if len(parsed) < MIN_ITEMS:
            if preserve_previous(f"수집된 한글 아이템이 {len(parsed)}개로 기준({MIN_ITEMS}) 미만입니다.", {"link_count": len(links), "item_count": len(parsed), "failures": failures}):
                return

        ko_valid, ko_stats = validate_korean_text(parsed)
        if not ko_valid:
            if preserve_previous(
                "한글 DB 인코딩 검증 실패. 깨진 문자열을 저장하지 않고 기존 DB를 유지합니다.",
                {"item_count": len(parsed), "failures": failures, "korean_text": ko_stats},
            ):
                return
            raise RuntimeError(f"Korean text validation failed: {ko_stats}")

        data = {
            "metadata": {
                "schema_version": "2.0",
                "mode": "full_ko_crawl_from_gaming_tools",
                "primary_source": "dune.gaming.tools/ko",
                "items_url": ITEMS_URL,
                "crafting_url": CRAFTING_URL,
                "updated_at": now(),
                "link_count": len(links),
                "item_count": len(parsed),
                "failures": failures,
                "encoding": "utf-8",
                "korean_text_validation": ko_stats,
                "note": "dune.gaming.tools/ko의 한글 아이템명, 장비 스펙, 제작 재료를 수집했습니다."
            },
            "items": sorted(parsed, key=lambda x: x.get("name",""))
        }
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Backward compatibility for old crafting UI consumers.
        CRAFTING_OUT.write_text(json.dumps({
            "metadata": {**data["metadata"], "mode": "derived_from_equipment_db"},
            "items": [i for i in data["items"] if i.get("materials")]
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        RAW_OUT.write_text(json.dumps({"items": raw_pages}, ensure_ascii=False, indent=2), encoding="utf-8")
        write_log("updated", f"한글 장비/제작 DB 갱신 완료: {len(parsed)}개", {"link_count": len(links), "item_count": len(parsed), "failures": failures})
        print(json.dumps(data["metadata"], ensure_ascii=False, indent=2))

    except Exception as exc:
        reason = f"한글 장비/제작 DB 수집 실패. 기존 DB를 유지합니다. 오류: {repr(exc)[:240]}"
        if not preserve_previous(reason):
            OUT.write_text(json.dumps({"metadata": {"mode": "ko_crawl_failed_empty", "updated_at": now(), "warning": reason}, "items": []}, ensure_ascii=False, indent=2), encoding="utf-8")
            write_log("failed_empty", reason)
        print(json.dumps({"warning": reason}, ensure_ascii=False))


def discover_item_links():
    """Collect item detail links from the Korean item index and pagination pages."""
    queue = [ITEMS_URL]
    seen_pages = set()
    links = {}
    max_pages = int(os.getenv("KO_DB_MAX_PAGES", "40") or "40")

    while queue and len(seen_pages) < max_pages:
        page_url = queue.pop(0)
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        html = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")

        for row in parse_links_from_page(html, page_url):
            links[row["url"]] = row

        for a in soup.find_all("a", href=True):
            href = urljoin(BASE, a.get("href") or "")
            if not href.startswith(ITEMS_URL):
                continue
            if href in seen_pages or href in queue:
                continue
            # Follow explicit page/pagination links only.
            if re.search(r"(?:[?&](?:page|p)=\d+|/page/\d+)", href):
                queue.append(href)

    return list(links.values()), sorted(seen_pages)

_original_main = main

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    try:
        links, crawled_pages = discover_item_links()
        if LIMIT > 0:
            links = links[:LIMIT]

        # 50 is the absolute safety floor, not a claim that this is the full DB.
        if len(links) < MIN_ITEMS:
            if preserve_previous(
                f"한글 아이템 링크 수가 {len(links)}개로 기준({MIN_ITEMS}) 미만입니다.",
                {"link_count": len(links), "pages": crawled_pages},
            ):
                return

        parsed, raw_pages, failures = [], [], 0
        for idx, link in enumerate(links, 1):
            try:
                item, meta = parse_item_page(link)
                parsed.append(item)
                raw_pages.append(meta)
                print(json.dumps({
                    "idx": idx, "total": len(links), "name": item["name"],
                    "stats": len(item.get("stats", [])),
                    "materials": len(item.get("materials", []))
                }, ensure_ascii=False))
                time.sleep(DELAY)
            except Exception as exc:
                failures += 1
                raw_pages.append({"url": link["url"], "error": repr(exc)[:240]})

        ko_valid, ko_stats = validate_korean_text(parsed)
        if not ko_valid:
            if preserve_previous(
                "한글 DB 인코딩 검증 실패. 깨진 문자열을 저장하지 않고 기존 DB를 유지합니다.",
                {"item_count": len(parsed), "failures": failures, "korean_text": ko_stats},
            ):
                return
            raise RuntimeError(f"Korean text validation failed: {ko_stats}")

        mode = "full_ko_crawl_from_gaming_tools"
        if len(parsed) < 200:
            mode = "partial_ko_crawl_from_gaming_tools"

        data = {
            "metadata": {
                "schema_version": "2.1",
                "mode": mode,
                "primary_source": "dune.gaming.tools/ko",
                "items_url": ITEMS_URL,
                "crafting_url": CRAFTING_URL,
                "updated_at": now(),
                "page_count": len(crawled_pages),
                "link_count": len(links),
                "item_count": len(parsed),
                "failures": failures,
                "encoding": "utf-8",
                "korean_text_validation": ko_stats,
                "note": "한글 아이템명·스펙·직접 제작 재료. 전체성은 item_count와 mode로 판단합니다."
            },
            "items": sorted(parsed, key=lambda x: x.get("name", ""))
        }
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        CRAFTING_OUT.write_text(json.dumps({
            "metadata": {**data["metadata"], "mode": "derived_from_equipment_db"},
            "items": [i for i in data["items"] if i.get("materials")]
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        RAW_OUT.write_text(json.dumps({"pages": crawled_pages, "items": raw_pages}, ensure_ascii=False, indent=2), encoding="utf-8")
        write_log("updated", f"한글 장비 DB 갱신: {len(parsed)}개", {
            "page_count": len(crawled_pages), "item_count": len(parsed),
            "failures": failures, "mode": mode
        })
        print(json.dumps(data["metadata"], ensure_ascii=False, indent=2))
    except Exception as exc:
        reason = f"한글 장비 DB 수집 실패. 기존 DB 유지: {repr(exc)[:240]}"
        if not preserve_previous(reason):
            OUT.write_text(json.dumps({
                "metadata": {"mode": "ko_crawl_failed_empty", "updated_at": now(), "warning": reason},
                "items": []
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            write_log("failed_empty", reason)
        print(json.dumps({"warning": reason}, ensure_ascii=False))


if __name__ == "__main__":
    main()
