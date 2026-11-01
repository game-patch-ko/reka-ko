"""Inventory the text-bearing assets of the game: I2 sources, fonts, MonoBehaviours.

Usage: python tools/scan_assets.py [game_dir]
Writes work/scan.json.
"""
import json
import os
import sys
from collections import Counter

import UnityPy

GAME = sys.argv[1] if len(sys.argv) > 1 else r"F:\SteamLibrary\steamapps\common\Reka"
DATA = os.path.join(GAME, "Reka_Data")
AA = os.path.join(DATA, "StreamingAssets", "aa", "StandaloneWindows64")
OUT = os.path.join(os.path.dirname(__file__), "..", "work", "scan.json")

TARGETS = [
    os.path.join(DATA, n)
    for n in ("globalgamemanagers", "globalgamemanagers.assets", "resources.assets", "sharedassets0.assets")
]
TARGETS += [
    os.path.join(AA, n)
    for n in sorted(os.listdir(AA))
    if not n.startswith("poigrassdata") and "poi_assets_all" not in n and "scenes_all" not in n
]

result = {}
for path in TARGETS:
    name = os.path.basename(path)
    size = os.path.getsize(path)
    print(f"[{name}] {size / 1e6:.1f} MB", flush=True)
    env = UnityPy.load(path)
    counts = Counter()
    fonts = []
    font_assets = []
    for obj in env.objects:
        t = obj.type.name
        counts[t] += 1
        if t == "Font":
            fonts.append(obj.peek_name() if hasattr(obj, "peek_name") else "?")
    result[name] = {"size": size, "types": counts.most_common(40), "fonts": fonts}
    print("   ", counts.most_common(12), flush=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1, ensure_ascii=False)
