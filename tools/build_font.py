"""Subset Noto Sans CJK KR down to what the Korean fallback font needs: all Hangul syllables,
jamo, Korean/CJK punctuation and every character used by the translation.
The result lands in work/NotoSansKR-subset.otf and is embedded in resources.assets by patch.py.
"""
import os

from fontTools import subset
from fontTools.ttLib import TTFont

from common import ROOT, WORK

SRC = os.path.join(ROOT, "fonts", "NotoSansCJKkr-Regular.otf")
OUT = os.path.join(WORK, "NotoSansKR-subset.otf")


def codepoints(extra=""):
    cp = set(range(0xAC00, 0xD7A4)) | set(range(0x3131, 0x3164)) | set(range(0x3000, 0x3020))
    cp |= set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | set(range(0x2010, 0x2040)) | set(range(0x2190, 0x2194))
    cp |= {0x2605, 0x2606, 0x25CB, 0x25CF, 0x2666, 0x2665, 0x301C, 0xFF5E, 0xFF01, 0xFF1F}
    cp |= {ord(c) for c in extra if ord(c) >= 0x20}
    return cp


def build(extra=""):
    font = TTFont(SRC, recalcTimestamp=False)  # keep builds byte-identical
    opts = subset.Options()
    opts.layout_features = []
    opts.hinting = False
    opts.notdef_outline = True
    opts.name_IDs = [1, 2, 4, 6]
    s = subset.Subsetter(opts)
    s.populate(unicodes=codepoints(extra))
    s.subset(font)
    font.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(path, os.path.getsize(path))
