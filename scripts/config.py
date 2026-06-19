from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"

SOURCE_URLS = {
    "dune_gaming_deep_desert": "https://dune.gaming.tools/deep-desert",
    "method_deep_desert": "https://www.method.gg/dune-awakening/deep-desert-companion",
    "method_overland": "https://www.method.gg/dune-awakening/overland-companion",
    "method_database": "https://www.method.gg/dune-awakening/database",
    "official_news": "https://duneawakening.com/en/news"
}

KEYWORDS = [
    "Deep Desert", "PvE", "PvP", "Row A", "Mk5", "Testing Station", "Old Quarry",
    "Power Harness", "Cutteray", "Kynes", "Hummingbird", "Vehicle", "Armor", "Weapon",
    "schematic", "unique", "drop", "POI", "loot", "Landsraad", "Augment"
]
