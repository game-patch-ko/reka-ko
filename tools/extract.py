"""Extract the I2 localisation source of the game to work/i2_source.json.

The game carries two copies of I2Languages: Resources (resources.assets) and the
scriptableobjects Addressables bundle. Both are dumped and compared.
"""
import hashlib
import json
import os

import i2format
from common import AA, DATA, WORK, load_env


def find_i2(env):
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        raw = obj.get_raw_data()
        if raw[28:32] == (11).to_bytes(4, "little") and raw[32:43] == b"I2Languages":
            return obj
    return None


def main():
    copies = {
        "resources": os.path.join(DATA, "resources.assets"),
        "bundle": os.path.join(AA, "scriptableobjects_assets_all.bundle"),
    }
    sources = {}
    for key, path in copies.items():
        env = load_env(path)
        obj = find_i2(env)
        raw = obj.get_raw_data()
        src = i2format.parse(raw)
        if i2format.build(src) != raw:
            raise SystemExit(f"{key}: rebuild is not byte-identical")
        sources[key] = (src, hashlib.sha1(raw).hexdigest())
        print(key, obj.path_id, len(raw), sources[key][1])

    src = sources["resources"][0]
    print("copies identical:", sources["resources"][1] == sources["bundle"][1])
    terms, langs = src["terms"], src["languages"]
    print("terms:", len(terms), "mid:", src["mid"][:64], "tail:", src["tail"][:160])
    for i, l in enumerate(langs):
        filled = sum(1 for t in terms if i < len(t["Languages"]) and t["Languages"][i])
        chars = sum(len(t["Languages"][i]) for t in terms if i < len(t["Languages"]))
        print(i, l, filled, chars)

    dump = {
        "languages": langs,
        "terms": [
            {"term": t["Term"], "type": t["TermType"], "text": t["Languages"], "flags": list(t["Flags"])}
            for t in terms
        ],
    }
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "i2_source.json"), "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
