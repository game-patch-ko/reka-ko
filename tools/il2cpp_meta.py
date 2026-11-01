"""Reader for global-metadata.dat v31 and method-address resolver for GameAssembly.dll.

usage: il2cpp_meta.py types REGEX        list matching types with fields and method addresses
       il2cpp_meta.py literals REGEX     list matching string literals
"""
import re
import struct
import sys

from common import DATA, GAME_ROOT

SEC_STRLIT, SEC_STRLITDATA, SEC_STRING, SEC_METHODS, SEC_FIELDS, SEC_TYPES, SEC_IMAGES = 0, 1, 2, 5, 11, 19, 20


class Meta:
    def __init__(self):
        with open(DATA + r"\il2cpp_data\Metadata\global-metadata.dat", "rb") as f:
            d = self.d = f.read()
        h = struct.unpack("<64i", d[:256])
        self.sec = [(h[i], h[i + 1]) for i in range(2, 64, 2)]
        o, n = self.sec[SEC_TYPES]
        self.T = [struct.unpack_from("<16i8H2I", d, o + i * 88) for i in range(n // 88)]
        o, n = self.sec[SEC_METHODS]
        self.M = [struct.unpack_from("<6iI4H", d, o + i * 36) for i in range(n // 36)]
        o, n = self.sec[SEC_FIELDS]
        self.F = [struct.unpack_from("<3i", d, o + i * 12) for i in range(n // 12)]

    def str(self, i):
        o = self.sec[SEC_STRING][0] + i
        return self.d[o : self.d.index(b"\0", o)].decode("utf8", "replace")

    def tname(self, t):
        ns, n = self.str(t[1]), self.str(t[0])
        return (ns + "." if ns else "") + n

    def methods(self, t):
        return self.M[t[9] : t[9] + t[16]] if t[9] >= 0 else []

    def fields(self, t):
        return self.F[t[8] : t[8] + t[18]] if t[8] >= 0 else []

    def find(self, pat):
        r = re.compile(pat)
        return [t for t in self.T if r.search(self.tname(t))]

    def literals(self):
        o, n = self.sec[SEC_STRLIT]
        base = self.sec[SEC_STRLITDATA][0]
        for i in range(n // 8):
            ln, off = struct.unpack_from("<2I", self.d, o + i * 8)
            yield i, self.d[base + off : base + off + ln].decode("utf8", "replace")


class PE:
    def __init__(self):
        with open(GAME_ROOT + r"\GameAssembly.dll", "rb") as f:
            b = self.b = f.read()
        p = struct.unpack_from("<I", b, 0x3C)[0]
        self.base = struct.unpack_from("<Q", b, p + 0x30)[0]
        ns = struct.unpack_from("<H", b, p + 6)[0]
        os_ = struct.unpack_from("<H", b, p + 20)[0]
        so = p + 24 + os_
        self.S = []
        for i in range(ns):
            nm = b[so + i * 40 : so + i * 40 + 8].rstrip(b"\0").decode()
            vs, va, rs, ro = struct.unpack_from("<4I", b, so + i * 40 + 8)
            self.S.append((nm, va, vs, ro, rs))

    def v2o(self, v):
        r = v - self.base
        for nm, va, vs, ro, rs in self.S:
            if va <= r < va + max(vs, rs):
                return r - va + ro

    def o2v(self, o):
        for nm, va, vs, ro, rs in self.S:
            if ro <= o < ro + rs:
                return self.base + va + o - ro

    def module(self, name):
        """Il2CppCodeGenModule: {char* name; u32 count; ptr* methodPointers; ...}"""
        needle = name.encode() + b"\0"
        i = -1
        while True:
            i = self.b.find(needle, i + 1)
            if i < 0:
                return None
            if self.b[i - 1] != 0:
                continue
            pk = struct.pack("<Q", self.o2v(i))
            j = -1
            while True:
                j = self.b.find(pk, j + 1)
                if j < 0:
                    break
                if j % 8:
                    continue
                c, _, mp = struct.unpack_from("<IIQ", self.b, j + 8)
                if 0 < c < 300000 and self.v2o(mp):
                    return c, mp


class Resolver:
    def __init__(self, meta, pe):
        self.m, self.pe = meta, pe
        o, n = meta.sec[SEC_IMAGES]
        self.images = []
        for i in range(n // 40):
            nm, asm, tstart, tcount = struct.unpack_from("<4i", meta.d, o + i * 40)
            self.images.append((meta.str(nm), tstart, tcount))
        self.mods = {}

    def module_of(self, tidx):
        for nm, s, c in self.images:
            if s <= tidx < s + c:
                if nm not in self.mods:
                    self.mods[nm] = self.pe.module(nm)
                return nm, self.mods[nm]
        return None, None

    def addr(self, tidx, method):
        nm, mod = self.module_of(tidx)
        rid = method[6] & 0xFFFFFF
        if not mod or rid == 0 or rid > mod[0]:
            return 0
        return struct.unpack_from("<Q", self.pe.b, self.pe.v2o(mod[1]) + (rid - 1) * 8)[0]


def main():
    m = Meta()
    if sys.argv[1] == "literals":
        r = re.compile(sys.argv[2])
        for i, s in m.literals():
            if r.search(s):
                print(i, repr(s[:200]))
        return
    pe = PE()
    rs = Resolver(m, pe)
    r = re.compile(sys.argv[2])
    for ti, t in enumerate(m.T):
        name = m.tname(t)
        if not r.search(name):
            continue
        print("==", name, "module", rs.module_of(ti)[0], "parent", t[4])
        for f in m.fields(t):
            print("   F", m.str(f[0]))
        for me in m.methods(t):
            print("   M", hex(rs.addr(ti, me)), m.str(me[0]), "params", me[10])


if __name__ == "__main__":
    main()
