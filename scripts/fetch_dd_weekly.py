import copy
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from config import DATA, RAW

METHOD_URL = "https://www.method.gg/dune-awakening/deep-desert-companion"
GAMING_TOOLS_KO_URL = "https://dune.gaming.tools/ko/deep-desert"

WEEKLY = DATA / "weekly.json"
EQUIPMENT = DATA / "equipment_db.json"
ALIASES = DATA / "item_aliases_ko.json"
UPDATE_LOG = DATA / "update_log.json"
REPORT = DATA / "dd_update_report.json"
PREVIOUS = DATA / "dd_previous.json"
METHOD_RAW = RAW / "method_deep_desert.html"
GAMING_RAW = RAW / "dune_gaming_deep_desert.html"

KST = ZoneInfo("Asia/Seoul")

HEADERS = {
    "User-Agent": "Nevermind-DuneHa-DD-Updater/1.0 (+GitHub Actions fan utility)",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}

CATEGORY_LABELS = {
    "Weapons": ("무기", "◆ 무기"),
    "Garments": ("방어구", "⬟ 방어구"),
    "Tools": ("도구", "✦ 도구"),
    "Vehicle Components": ("차량 부품", "▰ 차량"),
    "Sidearms": ("사이드암", "⌁ 사이드암"),
}

RANKS = {"S", "A", "B", "C"}
LOCATION_WORDS = (
    "Testing Station", "Wreck", "Loot Cave", "Cave", "Downed Ships",
    "Ship", "Station", "Fallen Shipwreck"
)
SKIP_LINES = {
    "All Schematics", "Downed Ships", "Testing Stations", "Caves", "Wrecks",
    "PvE", "PvP", "Deep Desert POI Loot Tables", "Map Filters",
}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def slugify(value):
    s = clean(value).lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9가-힣]+", "-", s)
    return s.strip("-") or "item"

def ko_search_url(name):
    return "https://dune.gaming.tools/ko/items?search=" + urllib.parse.quote(clean(name))

def fetch_or_read(path, url):
    if path.exists() and path.stat().st_size > 5000:
        return path.read_text(encoding="utf-8", errors="ignore")
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(response.text, encoding="utf-8", errors="ignore")
    return response.text

def append_log(status, message, extra=None):
    log = load_json(UPDATE_LOG, {"entries": []})
    log.setdefault("entries", [])
    row = {
        "time": now_iso(),
        "type": "dd-weekly-auto-update",
        "status": status,
        "message": message,
    }
    if extra:
        row.update(extra)
    log["entries"].insert(0, row)
    log["entries"] = log["entries"][:100]
    write_json(UPDATE_LOG, log)

def build_localizer():
    equipment = load_json(EQUIPMENT, {"items": []})
    aliases = load_json(ALIASES, {"items": []})

    by_slug = {}
    by_name = {}
    for item in equipment.get("items", []):
        name = clean(item.get("name"))
        if name:
            by_name[name.lower()] = item
        identifiers = [
            item.get("id"),
            str(item.get("url", "")).rstrip("/").split("/")[-1],
            item.get("slug"),
        ]
        for ident in identifiers:
            if ident:
                by_slug[slugify(ident)] = item

    alias_by_en = {}
    for row in aliases.get("items", []):
        original = clean(row.get("original"))
        ko = clean(row.get("ko"))
        if original and ko:
            alias_by_en[original.lower()] = ko

    def localize(original_name, source_slug=""):
        original_name = clean(original_name)
        candidates = [
            by_slug.get(slugify(source_slug)),
            by_slug.get(slugify(original_name)),
        ]
        alias_name = alias_by_en.get(original_name.lower())
        if alias_name:
            candidates.append(by_name.get(alias_name.lower()))

        found = next((x for x in candidates if x), None)
        if found:
            return {
                "name": clean(found.get("name")) or alias_name or original_name,
                "url": found.get("url") or ko_search_url(found.get("name") or original_name),
                "match": "equipment_db",
            }
        if alias_name:
            return {"name": alias_name, "url": ko_search_url(alias_name), "match": "alias"}
        return {"name": original_name, "url": ko_search_url(original_name), "match": "search"}

    return localize

def text_lines(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return [clean(x) for x in soup.get_text("\n").splitlines() if clean(x)]

def parse_period(lines, expected_start, expected_end):
    joined = "\n".join(lines[:1000])
    match = re.search(
        r"Updated for:\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s*>\s*"
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)",
        joined,
        re.I,
    )
    if not match:
        return None

    d1, m1, d2, m2 = match.groups()
    m1_num = MONTHS.get(m1.lower())
    m2_num = MONTHS.get(m2.lower())
    if not m1_num or not m2_num:
        return None

    year = expected_start.year
    start = datetime(year, m1_num, int(d1), tzinfo=KST).date()
    end_year = year + 1 if m2_num < m1_num else year
    end = datetime(end_year, m2_num, int(d2), tzinfo=KST).date()
    return {"start": start.isoformat(), "end": end.isoformat(), "label": match.group(0)}

def is_location(line):
    return (
        ("%" in line or "<1%" in line)
        and any(word.lower() in line.lower() for word in LOCATION_WORDS)
    )

def parse_item_at(lines, index):
    line = lines[index]

    combined = re.match(
        r"^(?:(S|A|B|C)\s+)?(Weapons|Garments|Tools|Vehicle Components|Sidearms)\s+(.+)$",
        line,
        re.I,
    )
    if combined:
        rank, category, name = combined.groups()
        category = next((x for x in CATEGORY_LABELS if x.lower() == category.lower()), category)
        return {
            "rank": (rank or "").upper(),
            "category_en": category,
            "name": clean(name),
            "consumed": 1,
        }

    if line in RANKS and index + 2 < len(lines):
        category = lines[index + 1]
        if category in CATEGORY_LABELS:
            name = lines[index + 2]
            if name not in SKIP_LINES and not is_location(name):
                return {
                    "rank": line,
                    "category_en": category,
                    "name": clean(name),
                    "consumed": 3,
                }

    if line in CATEGORY_LABELS and index + 1 < len(lines):
        name = lines[index + 1]
        if name not in SKIP_LINES and not is_location(name):
            return {
                "rank": "",
                "category_en": line,
                "name": clean(name),
                "consumed": 2,
            }

    return None

def locate_sections(lines):
    all_indices = [i for i, line in enumerate(lines) if line.strip() == "All Schematics"]
    row_indices = [i for i, line in enumerate(lines) if "Row A (Mk5) Loot Tables" in line]
    if len(all_indices) < 2 or len(row_indices) < 2:
        raise ValueError(
            f"Method DD section markers incomplete: all={len(all_indices)}, rowA={len(row_indices)}"
        )
    pve_start, pvp_start = all_indices[0], all_indices[1]
    pve_row = next(i for i in row_indices if i > pve_start)
    pvp_row = next(i for i in row_indices if i > pvp_start)
    return {
        "pve": (pve_start + 1, pve_row),
        "pvp": (pvp_start + 1, pvp_row),
        "rowa": (pve_row + 1, pvp_start),
    }

def translate_location(text):
    replacements = [
        ("Testing Station", "테스팅 스테이션"),
        ("Loot Cave", "루트 동굴"),
        ("Downed Ships", "추락선"),
        ("Wreck", "잔해"),
        ("Cave", "동굴"),
        ("The Furnace", "용광로"),
        ("The Museum", "박물관"),
        ("The Water Plant", "정수 시설"),
        ("Circular Control Room", "원형 제어실"),
        ("Deep Dark Wreck", "깊은 어둠의 잔해"),
        ("The Walkway", "통로"),
        ("The Wrecked Wreck", "파손된 잔해"),
    ]
    result = clean(text)
    for en, ko in replacements:
        result = result.replace(en, ko)
    return result

def make_item(parsed, mode, locations, localize, section):
    original = parsed["name"]
    source_slug = slugify(original)
    localized = localize(original, source_slug)
    category_ko, category_badge = CATEGORY_LABELS.get(
        parsed["category_en"], ("기타", "◇ 기타")
    )
    rank = parsed.get("rank") or ""
    tier = "Mk5" if section == "rowa" else ("Mk6" if "Mk6" in original else "유니크")
    badges = [mode, category_badge]
    if rank:
        badges.append(rank)
    if tier:
        badges.append(tier)

    loc_text = " / ".join(translate_location(x) for x in locations[:14])
    details = f"드랍 위치 {mode} · {loc_text}" if loc_text else f"{mode} 드랍 위치 확인 중"

    return {
        "id": f"{section}-{slugify(original)}",
        "slug": slugify(original),
        "original_name": original,
        "name": localized["name"],
        "category": category_ko,
        "section": section,
        "rank": rank,
        "badges": list(dict.fromkeys(badges)),
        "source_url": localized["url"],
        "source_match": localized["match"],
        "details": details,
        "links": [],
        "image": None,
        "confidence": "auto_parsed_method",
    }

def parse_mode(lines, start, end, mode, section, localize):
    results = []
    current = None
    locations = []
    i = start

    def flush():
        nonlocal current, locations
        if current:
            results.append(make_item(current, mode, locations, localize, section))
        current = None
        locations = []

    while i < end:
        line = lines[i]
        item = parse_item_at(lines, i)
        if item:
            flush()
            current = item
            i += item["consumed"]
            continue
        if current and is_location(line):
            locations.append(line)
        i += 1
    flush()

    dedup = {}
    for item in results:
        key = item["slug"]
        if key not in dedup:
            dedup[key] = item
        else:
            existing = dedup[key]
            if item["details"] not in existing["details"]:
                existing["details"] += " / " + item["details"].replace("드랍 위치 ", "")
    return list(dedup.values())

def parse_rowa(lines, start, end, localize):
    results = {}
    current_poi = "Row A"
    i = start
    while i < end:
        line = lines[i]
        if re.match(r"^A\d+\s*-\s*", line):
            current_poi = line
            i += 1
            continue
        item = parse_item_at(lines, i)
        if item:
            built = make_item(item, "Row A", [current_poi], localize, "rowa")
            key = built["slug"]
            if key not in results:
                results[key] = built
            else:
                poi = translate_location(current_poi)
                if poi not in results[key]["details"]:
                    results[key]["details"] += " / " + poi
            i += item["consumed"]
            continue
        i += 1
    return list(results.values())

def notable_items(pve_items, pvp_items):
    selected = []
    seen = set()
    for item in pve_items + pvp_items:
        if item.get("rank") == "S" or any(
            key in item.get("name", "")
            for key in ("파워 하네스", "커터레이", "건틀릿", "컴팩터")
        ):
            key = item["slug"]
            if key not in seen:
                copy_item = copy.deepcopy(item)
                copy_item["id"] = "notable-" + key
                copy_item["section"] = "notable"
                selected.append(copy_item)
                seen.add(key)
        if len(selected) >= 12:
            break
    return selected

def validate_candidate(candidate, period, expected):
    errors = []
    counts = {
        key: len(candidate.get(key, {}).get("items", []))
        for key in ("notable", "pve", "pvp", "rowa")
    }
    minimums = {"notable": 4, "pve": 8, "pvp": 8, "rowa": 8}
    for key, minimum in minimums.items():
        if counts[key] < minimum:
            errors.append(f"{key} count {counts[key]} < {minimum}")

    if period is None:
        errors.append("Method updated period not found")
    else:
        if period["start"] != expected["start"] or period["end"] != expected["end"]:
            errors.append(
                f"period mismatch source={period['start']}..{period['end']} "
                f"expected={expected['start']}..{expected['end']}"
            )

    for key in ("pve", "pvp"):
        names = [x.get("slug") for x in candidate[key]["items"]]
        if names and len(set(names)) / len(names) < 0.65:
            errors.append(f"{key} duplicate ratio too high")

    return errors, counts

def preserve_previous(weekly, reason, report_extra=None):
    status = weekly.setdefault("automation_status", {})
    status.update({
        "mode": "dd_previous_preserved",
        "confidence": "last_verified_data",
        "checked_at": now_iso(),
        "message": "DD 자동 수집 검증에 실패하여 마지막 검증본을 유지합니다.",
    })
    weekly["dd_update"] = {
        "status": "preserved",
        "source": "Method Deep Desert Companion",
        "source_url": METHOD_URL,
        "checked_at": now_iso(),
        "reason": reason,
    }
    write_json(WEEKLY, weekly)
    report = {
        "ok": False,
        "status": "preserved",
        "reason": reason,
        "checked_at": now_iso(),
    }
    if report_extra:
        report.update(report_extra)
    write_json(REPORT, report)
    append_log("preserved", reason, report_extra)
    print(json.dumps(report, ensure_ascii=False, indent=2))

def main():
    weekly = load_json(WEEKLY, None)
    if not weekly:
        raise SystemExit("weekly.json missing or invalid")

    expected = {
        "start": weekly.get("week", {}).get("start"),
        "end": weekly.get("week", {}).get("end"),
    }
    if not expected["start"] or not expected["end"]:
        raise SystemExit("weekly window missing; run update_week_window.py first")

    expected_start = datetime.fromisoformat(expected["start"]).date()
    expected_end = datetime.fromisoformat(expected["end"]).date()

    try:
        method_html = fetch_or_read(METHOD_RAW, METHOD_URL)
        lines = text_lines(method_html)
        period = parse_period(lines, expected_start, expected_end)
        sections = locate_sections(lines)
        localize = build_localizer()

        pve_items = parse_mode(lines, *sections["pve"], "PvE", "pve", localize)
        pvp_items = parse_mode(lines, *sections["pvp"], "PvP", "pvp", localize)
        rowa_items = parse_rowa(lines, *sections["rowa"], localize)
        notable = notable_items(pve_items, pvp_items)

        candidate = {
            "notable": {"id": "notable", "label": "희귀", "items": notable},
            "pve": {"id": "pve", "label": "PvE", "items": pve_items},
            "pvp": {"id": "pvp", "label": "PvP", "items": pvp_items},
            "rowa": {"id": "rowa", "label": "Row A", "items": rowa_items},
        }

        errors, counts = validate_candidate(candidate, period, expected)
        if errors:
            preserve_previous(
                weekly,
                "; ".join(errors),
                {"counts": counts, "source_period": period, "expected_period": expected},
            )
            return

        write_json(PREVIOUS, {
            "saved_at": now_iso(),
            "week": weekly.get("week"),
            "dd": weekly.get("dd"),
            "dd_update": weekly.get("dd_update"),
        })

        weekly["dd"] = candidate
        weekly["generated_at"] = now_iso()
        weekly["dd_update"] = {
            "status": "updated",
            "source": "Method Deep Desert Companion",
            "source_url": METHOD_URL,
            "secondary_source": "dune.gaming.tools/ko/deep-desert",
            "secondary_source_url": GAMING_TOOLS_KO_URL,
            "source_period": period,
            "counts": counts,
            "updated_at": now_iso(),
        }
        status = weekly.setdefault("automation_status", {})
        status.update({
            "mode": "dd_auto_updated",
            "confidence": "validated_external_data",
            "checked_at": now_iso(),
            "message": "DD 희귀/PvE/PvP/Row A 데이터를 외부 소스에서 검증 후 자동 갱신했습니다.",
            "render_mode": "weekly_json_single_source",
        })
        write_json(WEEKLY, weekly)

        report = {
            "ok": True,
            "status": "updated",
            "counts": counts,
            "source_period": period,
            "expected_period": expected,
            "updated_at": now_iso(),
        }
        write_json(REPORT, report)
        append_log("updated", "DD weekly data updated", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))

    except Exception as exc:
        preserve_previous(weekly, f"parser error: {repr(exc)[:400]}")
        if isinstance(exc, (ValueError, RuntimeError)):
            return
        raise

if __name__ == "__main__":
    main()
