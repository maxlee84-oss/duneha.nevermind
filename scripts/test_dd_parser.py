import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_dd_weekly as dd

HTML = """
<html><body>
<div>Updated for: 16th June > 23rd June</div>
<h4>All Schematics</h4>
<a>S Tools Adaptive Holtzman Shield</a>
<div>Testing Station (G3) - The Furnace 5%</div>
<a>S Weapons Perforator</a>
<div>Wreck (D2) - Deep Dark Wreck 7%</div>
<a>A Garments Power Harness</a>
<div>Testing Station (G4) - The Museum 5%</div>
<a>A Tools Compact Compactor Mk6</a>
<div>Loot Cave (H5) 8%</div>
<a>A Vehicle Components Focused Buggy Cutteray Mk6</a>
<div>Loot Cave (C3) 8%</div>
<a>A Weapons Replica Pulse-sword</a>
<div>Downed Ships 12%</div>
<a>A Weapons Replica Pulse-knife</a>
<div>Downed Ships 12%</div>
<a>A Garments Circuit Gauntlets</a>
<div>Testing Station (D3) - Circular Control Room 5%</div>
<h4>Row A (Mk5) Loot Tables</h4>
<h4>A1 - Wreck of the Eumenes</h4>
<a>Garments Advanced Suspensor Jacket</a>
<a>Tools Compact Compactor Mk5</a>
<a>Weapons Arhun K-28 Lasgun</a>
<a>Garments Mendek's Chestplate</a>
<a>Tools Focused Reaper Mk5</a>
<a>Vehicle Components Stormrider Boost Module Mk5</a>
<a>Tools Long Range Scanner</a>
<a>Garments Station Garb</a>
<h4>All Schematics</h4>
<a>S Weapons Black Market K-28 Lasgun</a>
<div>Testing Station (D3) - Circular Control Room 1%</div>
<a>S Garments Circuit Gauntlets</a>
<div>Testing Station (G3) - The Furnace 5%</div>
<a>A Weapons Plasma Cannon</a>
<div>Wreck (C4) - The Walkway 7%</div>
<a>A Weapons Dunewatcher</a>
<div>Downed Ships 9%</div>
<a>A Tools Impure Extractor Mk6</a>
<div>Loot Cave (C7) 8%</div>
<a>A Garments Pincushion Chestpiece</a>
<div>Testing Station (F6) - The Water Plant 7%</div>
<a>A Vehicle Components Stormrider Boost Module Mk6</a>
<div>Testing Station (G4) - The Museum 8%</div>
<a>A Weapons Cauterizer</a>
<div>Wreck (D6) - The Wrecked Wreck 7%</div>
<h4>Row A (Mk5) Loot Tables</h4>
</body></html>
"""

def localize(name, slug=""):
    return {"name": name, "url": dd.ko_search_url(name), "match": "test"}

def main():
    lines = dd.text_lines(HTML)
    sections = dd.locate_sections(lines)
    pve = dd.parse_mode(lines, *sections["pve"], "PvE", "pve", localize)
    pvp = dd.parse_mode(lines, *sections["pvp"], "PvP", "pvp", localize)
    rowa = dd.parse_rowa(lines, *sections["rowa"], localize)
    period = dd.parse_period(lines, __import__("datetime").date(2026,6,16), __import__("datetime").date(2026,6,23))
    assert len(pve) >= 8, len(pve)
    assert len(pvp) >= 8, len(pvp)
    assert len(rowa) >= 8, len(rowa)
    assert period["start"] == "2026-06-16"
    assert period["end"] == "2026-06-23"
    print(json.dumps({"pve":len(pve),"pvp":len(pvp),"rowa":len(rowa),"period":period}, ensure_ascii=False))

if __name__ == "__main__":
    main()
