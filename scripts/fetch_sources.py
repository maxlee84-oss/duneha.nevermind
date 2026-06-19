import json, re, time, hashlib
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from config import RAW, DATA, SOURCE_URLS, KEYWORDS

HEADERS = {
    "User-Agent": "NevermindGuildWeeklyOpsBot/1.0 (+GitHub Actions; Dune Awakening fan utility)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.6,en;q=0.5"
}

def safe_name(name):
    return re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")

def extract_page(name, url, html, status_code):
    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1","h2","h3"])][:120]
    links = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if text or href:
            links.append({"text": text[:180], "href": href[:350]})
    tables = []
    for table in soup.find_all("table")[:25]:
        rows = []
        for tr in table.find_all("tr")[:100]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th","td"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    # Remove heavy visual nodes after table extraction
    for tag in soup(["style", "noscript"]):
        tag.decompose()
    page_text = soup.get_text("\n", strip=True)
    keyword_hits = []
    for line in page_text.splitlines():
        if any(k.lower() in line.lower() for k in KEYWORDS):
            line = re.sub(r"\s+", " ", line).strip()
            if 5 <= len(line) <= 260 and line not in keyword_hits:
                keyword_hits.append(line)
        if len(keyword_hits) >= 500:
            break
    json_script_samples = []
    for s in soup.find_all("script"):
        txt = s.string or s.get_text() or ""
        if "__NEXT_DATA__" in str(s) or (txt.strip().startswith("{") and len(txt) > 200):
            json_script_samples.append(txt[:50000])
    return {
        "name": name,
        "url": url,
        "status_code": status_code,
        "title": title,
        "headings": headings,
        "links": links[:600],
        "tables": tables[:20],
        "keyword_hits": keyword_hits,
        "json_script_samples": json_script_samples[:6],
        "html_sha256": hashlib.sha256((html or "").encode("utf-8", errors="ignore")).hexdigest()
    }

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    bundle = {"fetched_at": datetime.now(timezone.utc).isoformat(), "sources": [], "errors": []}
    session = requests.Session()
    for name, url in SOURCE_URLS.items():
        try:
            resp = session.get(url, headers=HEADERS, timeout=40)
            html = resp.text
            raw_path = RAW / f"{safe_name(name)}.html"
            raw_path.write_text(html, encoding="utf-8", errors="ignore")
            item = extract_page(name, url, html, resp.status_code)
            item["raw_path"] = str(raw_path.relative_to(DATA.parent))
            bundle["sources"].append(item)
            time.sleep(1.5)
        except Exception as exc:
            bundle["errors"].append({"name": name, "url": url, "error": repr(exc)})
    (RAW / "source_bundle.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"source_count": len(bundle["sources"]), "errors": bundle["errors"]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
