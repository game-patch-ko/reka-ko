"""Reader/writer for the serialized I2 LanguageSourceAsset MonoBehaviour.

Only mTerms and mLanguages are decoded. Everything before and after them is kept as raw bytes
so a rebuilt asset differs from the original only in what we changed.
"""
import struct


class Reader:
    def __init__(self, data, pos=0):
        self.b = data
        self.p = pos

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def align(self):
        self.p = (self.p + 3) & ~3

    def u8(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def string(self):
        n = self.i32()
        if n < 0 or self.p + n > len(self.b):
            raise ValueError(f"bad string length {n} at {self.p}")
        s = self.b[self.p : self.p + n].decode("utf-8")
        self.p += n
        self.align()
        return s

    def strings(self):
        n = self.i32()
        if n < 0 or n > 1000:
            raise ValueError(f"bad array length {n} at {self.p}")
        return [self.string() for _ in range(n)]

    def blob(self):
        n = self.i32()
        if n < 0 or n > 1000:
            raise ValueError(f"bad blob length {n} at {self.p}")
        v = self.b[self.p : self.p + n]
        self.p += n
        self.align()
        return v


class Writer:
    def __init__(self):
        self.parts = []
        self.n = 0

    def raw(self, b):
        self.parts.append(b)
        self.n += len(b)

    def i32(self, v):
        self.raw(struct.pack("<i", v))

    def align(self):
        pad = (-self.n) & 3
        if pad:
            self.raw(b"\0" * pad)

    def string(self, s):
        b = s.encode("utf-8")
        self.i32(len(b))
        self.raw(b)
        self.align()

    def strings(self, items):
        self.i32(len(items))
        for s in items:
            self.string(s)

    def blob(self, v):
        self.i32(len(v))
        self.raw(v)
        self.align()

    def bytes(self):
        return b"".join(self.parts)


def parse(raw):
    """Return dict with head (bytes), terms, tail_mid, languages, tail."""
    r = Reader(raw)
    r.p = 28
    name = r.string()
    r.p += 12  # three bools, an empty list and one more int ahead of mTerms in this build
    terms_at = r.p
    n = r.i32()
    terms = []
    for _ in range(n):
        t = {"Term": r.string(), "TermType": r.i32()}
        t["Languages"] = r.strings()
        t["Flags"] = r.blob()
        t["Touch"] = r.strings()
        terms.append(t)
    after_terms = r.p
    r.u8()  # CaseInsensitiveTerms
    r.align()
    r.i32()  # OnMissingTranslation
    r.string()  # mTerm_AppName
    langs_at = r.p
    n = r.i32()
    langs = []
    for _ in range(n):
        name_ = r.string()
        code = r.string()
        flags = r.u8()
        r.align()
        langs.append({"Name": name_, "Code": code, "Flags": flags})
    after_langs = r.p
    return {
        "name": name,
        "head": raw[:terms_at],
        "terms": terms,
        "mid": raw[after_terms:langs_at],
        "languages": langs,
        "tail": raw[after_langs:],
    }


def build(src):
    w = Writer()
    w.raw(src["head"])
    w.i32(len(src["terms"]))
    for t in src["terms"]:
        w.string(t["Term"])
        w.i32(t["TermType"])
        w.strings(t["Languages"])
        w.blob(t["Flags"])
        w.strings(t["Touch"])
    w.raw(src["mid"])
    w.i32(len(src["languages"]))
    for l in src["languages"]:
        w.string(l["Name"])
        w.string(l["Code"])
        w.raw(bytes([l["Flags"]]))
        w.align()
    w.raw(src["tail"])
    return w.bytes()
