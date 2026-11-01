"""Consistency QA over translations/ko.json. Writes work/qa_*.json and prints a summary.

  glossary  source mentions a glossary term but the translation lacks its Korean form
  samesrc   identical source text translated differently
  tone      speaker/register rules from translations/GUIDE.md, judged from the key path
  variants  spelling variants of names that should not exist
"""
import json
import os
import re
from collections import Counter, defaultdict

from common import TRANSLATIONS, WORK
from mkbatches import source_entries

SKIP_GLOSSARY = {"Merchant", "Tile", "Roof", "Trim", "Pine", "Birch", "Beech", "Spruce", "Sage", "Quest", "Furniture"}
HANGUL_END = re.compile(r"[가-힣]+[.!?…]*\s*$")
POLITE = re.compile(r"(요|니다|세요|까요|네요|군요)[.!?…~]*\s*$")
FORMAL = re.compile(r"(습니다|십시오|합니다|입니까)[.!?…~]*\s*$")
VARIANTS = {
    "바바야가": "바바 야가", "바바 야카": "바바 야가", "바바 이아가": "바바 야가", "바바 자가": "바바 야가",
    "르시": "레시", "레쉬": "레시", "레시이": "레시", "렉카": "레카", "루트크": "루트키", "룻키": "루트키",
    "블루트니크": "블루드니크", "블루드닉": "블루드니크", "블루트닉": "블루드니크", "나위아": "나비아", "나비야": "나비아",
    "자위아": "야비아", "자비아": "야비아", "드지아디": "지아디", "지아디들": "지아디", "지아디이": "지아디",
    "벨레즈": "벨레스", "페런": "페룬", "즐리던": "즐리덴", "즐라이든": "즐리덴", "보그단이": None,
}


def load():
    with open(os.path.join(TRANSLATIONS, "ko.json"), encoding="utf-8") as f:
        ko = json.load(f)
    with open(os.path.join(TRANSLATIONS, "glossary.json"), encoding="utf-8") as f:
        g = json.load(f)
    gloss = {k: v for sec in g.values() for k, v in sec.items()}
    return source_entries(), ko, gloss


def check_glossary(entries, ko, gloss):
    out = []
    names = sorted(gloss, key=len, reverse=True)
    for e in entries:
        t = ko.get(e["key"], "")
        en = e["en"].replace("’", "'")
        taken = en
        for name in names:
            if name in SKIP_GLOSSARY:
                continue
            n = name.replace("’", "'")
            flags = 0 if name[0].isupper() else re.I
            if not re.search(rf"\b{re.escape(n)}", taken, flags):
                continue
            taken = re.sub(rf"\b{re.escape(n)}", " ", taken, flags=flags)
            if gloss[name] not in t:
                out.append({"key": e["key"], "term": name, "want": gloss[name], "en": e["en"][:200], "ko": t[:200]})
    return out


def check_same(entries, ko):
    by = defaultdict(set)
    for e in entries:
        if e["key"] in ko:
            by[e["en"].strip()].add(ko[e["key"]].strip())
    return [{"en": en, "ko": sorted(v)} for en, v in by.items() if len(v) > 1]


def lines(t):
    return [x for x in re.split(r"\r?\n", t) if x.strip()]


def check_tone(entries, ko):
    out = []
    for e in entries:
        key, t = e["key"], ko.get(e["key"], "")
        rule = None
        if "/Log/" in key or key.endswith("/Log") or "CleanseLog" in key:
            if any(FORMAL.search(x) for x in lines(t)):
                rule = "log_formal"
        elif re.search(r"/BabaJaga/.*(Response|Rumor|Answer)$", key) or "BabaJagaLying" in key:
            if any(POLITE.search(x) for x in lines(t)):
                rule = "babajaga_polite"
        elif key.endswith("_Prompt") or key.endswith("/Prompt"):
            if lines(t) and not POLITE.search(lines(t)[-1]) and re.search(r"[.?!]\s*$", t) and len(t) > 12 and "BabaJaga" in key:
                rule = "reka_to_bj_plain"
        elif key.startswith("UI/MainMenu/Settings/Explanation") or "/Explanation/" in key:
            if t and not FORMAL.search(lines(t)[-1]) and len(t) > 25:
                rule = "explain_not_formal"
        if rule:
            out.append({"key": key, "rule": rule, "en": e["en"][:200], "ko": t[:200]})
    return out


def check_variants(ko):
    out = []
    for k, t in ko.items():
        for bad, good in VARIANTS.items():
            if good and bad in t:
                out.append({"key": k, "bad": bad, "good": good, "ko": t[:160]})
    return out


def main():
    entries, ko, gloss = load()
    res = {
        "glossary": check_glossary(entries, ko, gloss),
        "samesrc": check_same(entries, ko),
        "tone": check_tone(entries, ko),
        "variants": check_variants(ko),
    }
    for name, data in res.items():
        with open(os.path.join(WORK, f"qa_{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
        print(name, len(data))
    print(Counter(x["term"] for x in res["glossary"]).most_common(30))
    print(Counter(x["rule"] for x in res["tone"]).most_common())
    print(Counter(x["bad"] for x in res["variants"]).most_common())


if __name__ == "__main__":
    main()
