"""Split the source text into translation batches: work/batches/<name>.json.

usage: mkbatches.py poc              three small mixed sample batches (dialogue, UI, items)
       mkbatches.py main [N=20]      everything not translated yet, in N batches of similar weight
"""
import json
import os
import sys

from common import TRANSLATIONS, WORK

SKIP_PREFIX = ("TECHNICAL_DO_NOT_TRANSLATE",)
# Autonyms stay in their own language, and the fixed dropdown label is set by patch.py.
KEEP_AUTONYM = "UI/MainMenu/Settings/Language/"
TRANSLATE_IN_AUTONYMS = {"UI/MainMenu/Settings/Language/Language"}


def source_entries():
    with open(os.path.join(WORK, "i2_source.json"), encoding="utf-8") as f:
        terms = json.load(f)["terms"]
    out = []
    for t in terms:
        key, text = t["term"], t["text"]
        en = text[0]
        if not en or key.startswith(SKIP_PREFIX):
            continue
        if key.startswith(KEEP_AUTONYM) and key not in TRANSLATE_IN_AUTONYMS:
            continue
        e = {"key": key, "en": en}
        ctx = {k: v for k, v in (("desc", text[13]), ("emotion", text[14]), ("comment", text[15])) if v}
        if ctx:
            e["ctx"] = ctx
        out.append(e)
    return out


def done_keys():
    path = os.path.join(TRANSLATIONS, "ko.json")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return set(json.load(f))


def write(name, entries):
    d = os.path.join(WORK, "batches")
    os.makedirs(d, exist_ok=True)
    for i, e in enumerate(entries):
        e["id"] = i
    with open(os.path.join(d, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=0)
    print(name, len(entries), sum(len(e["en"]) for e in entries))


def weight(e):
    return len(e["en"]) + 30


def main():
    entries = source_entries()
    if sys.argv[1] == "poc":
        groups = {
            "poc_dialogue": [e for e in entries if e["key"].startswith("Chapter_BJD/")][:60],
            "poc_ui": [e for e in entries if e["key"].startswith(("UI/MainMenu", "Tutorial/C00", "Patients/"))][::9][:60],
            "poc_items": [e for e in entries if e["key"].startswith(("Item/", "Plants/"))][:60],
        }
        for name, g in groups.items():
            write(name, g)
        return
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    done = done_keys()
    todo = [e for e in entries if e["key"] not in done]
    total = sum(weight(e) for e in todo)
    print("todo", len(todo), "of", len(entries))
    per = total / n
    idx, cur, w = 1, [], 0
    for e in todo:
        cur.append(e)
        w += weight(e)
        if w >= per and idx < n:
            write(f"b{idx:02d}", cur)
            idx, cur, w = idx + 1, [], 0
    write(f"b{idx:02d}", cur)


if __name__ == "__main__":
    main()
