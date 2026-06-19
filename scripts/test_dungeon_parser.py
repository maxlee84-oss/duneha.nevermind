import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_dungeons as d

HTML = """
<html><body>
<div>Element: Fire Party Size: 4 Loot Grades: 0-5</div>
<h2>Testing Station Hazards</h2>
<div>Fire Damage</div><div>Trap Damage</div>
<h2>Testing Station Loot</h2>
<div>24% S Weapons Replica Pulse-sword</div>
<div>10% S Weapons Replica Pulse-knife</div>
<div>3% S Weapons The Ancient Way</div>
<div>&lt;1% S Weapons Black Market K-28 Lasgun</div>
<div>10% A Weapons Cauterizer</div>
<div>10% B Garments Executor's Boots</div>
<div>10% B Garments Executor's Chestpiece</div>
<div>5% C Garments Desert Garb</div>
<div>10% A Tools Compact Compactor Mk6</div>
<div>5% C Resources Plastanium Ingot</div>
<div>Looking for a Build or Guide?</div>
</body></html>
"""

def localize(name):
    return name, d.ko_search_url(name), "test"

def main():
    lines = d.text_lines(HTML)
    drops = d.parse_loot(lines, localize)
    hazards = d.parse_hazards(lines)
    info = d.parse_info(lines)
    assert len(drops) == 10, len(drops)
    assert hazards == ["화염 피해","함정 피해"], hazards
    assert info.get("party_size") == "4", info
    print(json.dumps({"drops":len(drops),"hazards":hazards,"info":info}, ensure_ascii=False))

if __name__ == "__main__":
    main()
