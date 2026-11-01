"""Validate translations against the source.

usage: check.py               check translations/ko.json
       check.py merge [GLOB]  first merge work/tr/*.json results (id -> text, per batch) into ko.json
Writes the problems to work/check.json.
"""
import glob
import json
import os
import re
import sys
from collections import Counter

from common import TRANSLATIONS, WORK
from mkbatches import source_entries

KO_PATH = os.path.join(TRANSLATIONS, "ko.json")
VAR = re.compile(r"\{[^{}]*\}|\$[A-Za-z_]+\$")
TAG = re.compile(r"</?[A-Za-z][^<>]*>")
HAN = re.compile(r"[一-鿿぀-ヿ]")
ALLOWED_LATIN = re.compile(
    r"\{[^{}]*\}|</?[A-Za-z][^<>]*>|\b(Steam|Discord|DLSS|FSR\d?|TAA|SMAA|FXAA|HDR|V-?Sync|VSync|FPS|Hz|UI|NVIDIA|AMD|"
    r"Emberstorm|Entertainment|REKA|Early|Access|QR|WASD|RGB|Xbox|PlayStation|ESC|Esc|Tab|Shift|Ctrl|Alt|Space|ID|FOV|MB|GB|ms|"
    r"LMB|RMB|DX\d+|DirectX|OK|CC|BY|TSR|XeSS|Vulkan|DualSense|Ultra)\b"
)


def load_ko():
    if os.path.exists(KO_PATH):
        with open(KO_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_ko(ko):
    with open(KO_PATH, "w", encoding="utf-8") as f:
        json.dump(ko, f, ensure_ascii=False, indent=0, sort_keys=False)


def merge(pattern):
    ko = load_ko()
    added = 0
    for path in sorted(glob.glob(os.path.join(WORK, "batches", pattern))):
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            batch = {str(e["id"]): e for e in json.load(f)}
        for part in sorted(glob.glob(os.path.join(WORK, "tr", name + "_*.json"))):
            with open(part, encoding="utf-8") as f:
                tr = json.load(f)
            for i, text in tr.items():
                if i in batch:
                    ko[batch[i]["key"]] = text
                    added += 1
                else:
                    print("unknown id", part, i)
    save_ko(ko)
    print("merged", added, "total", len(ko))


def check(entries, ko):
    problems = []

    def add(e, kind, detail=""):
        problems.append({"key": e["key"], "kind": kind, "detail": detail, "en": e["en"], "ko": ko.get(e["key"], "")})

    for e in entries:
        en = e["en"]
        if e["key"] not in ko:
            add(e, "missing")
            continue
        t = ko[e["key"]]
        if not t.strip():
            add(e, "empty")
            continue
        if Counter(VAR.findall(en)) != Counter(VAR.findall(t)):
            add(e, "variable", f"{VAR.findall(en)} -> {VAR.findall(t)}")
        if Counter(TAG.findall(en)) != Counter(TAG.findall(t)):
            add(e, "tag", f"{TAG.findall(en)} -> {TAG.findall(t)}")
        if en.count("\n") != t.count("\n"):
            add(e, "newline", f"{en.count(chr(10))} -> {t.count(chr(10))}")
        if (en[:1] == " ") != (t[:1] == " ") or (en[-1:] == " ") != (t[-1:] == " "):
            add(e, "edge_space")
        if HAN.search(t):
            add(e, "han", HAN.findall(t)[:5].__str__())
        rest = ALLOWED_LATIN.sub("", t)
        latin = re.findall(r"[A-Za-z]{2,}", rest)
        if latin and re.search(r"[A-Za-z]{3,}", en):
            add(e, "latin", " ".join(latin[:6]))
        if "을(를)" in t or "이(가)" in t or "은(는)" in t:
            add(e, "josa_paren")
        if len(en) > 12 and len(t) > len(en) * 1.5:
            add(e, "long", f"{len(en)} -> {len(t)}")
    return problems


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        merge(sys.argv[2] if len(sys.argv) > 2 else "*.json")
    entries = source_entries()
    ko = load_ko()
    problems = check(entries, ko)
    with open(os.path.join(WORK, "check.json"), "w", encoding="utf-8") as f:
        json.dump(problems, f, ensure_ascii=False, indent=0)
    print(len(entries), "entries,", len(ko), "translated")
    print(Counter(p["kind"] for p in problems).most_common())


if __name__ == "__main__":
    main()
