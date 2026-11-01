"""Targeted x64 disassembly of IL2CPP methods with names and string literals resolved.

usage: disasm.py Type::Method [Type::Method ...]
"""
import re
import struct
import sys

import capstone

from il2cpp_meta import Meta, PE, Resolver

sys.stdout.reconfigure(encoding="utf8")
m = Meta()
pe = PE()
rs = Resolver(m, pe)
names = {}
for ti, t in enumerate(m.T):
    mod = rs.module_of(ti)[0]
    if mod not in ("Assembly-CSharp.dll", "I2_Localisation.dll"):
        continue
    for me in m.methods(t):
        a = rs.addr(ti, me)
        if a:
            names.setdefault(a, m.tname(t) + "::" + m.str(me[0]))

DIS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)


def dis(a, limit=500):
    off = pe.v2o(a)
    code = pe.b[off : off + limit * 8]
    c = 0
    for i in DIS.disasm(code, a):
        s = f"{i.address:x} {i.mnemonic} {i.op_str}"
        if i.mnemonic in ("call", "jmp") and i.op_str.startswith("0x"):
            s += "   ; " + names.get(int(i.op_str, 16), "")
        mm = re.search(r"\[rip ([+-]) 0x([0-9a-f]+)\]", i.op_str)
        if mm:
            tgt = i.address + i.size + (int(mm[2], 16) if mm[1] == "+" else -int(mm[2], 16))
            s += f"   ; [{tgt:x}]"
        print(s)
        c += 1
        if i.mnemonic == "int3" or c >= limit:
            break


if __name__ == "__main__":
    for q in sys.argv[1:]:
        tn, mn = q.split("::")
        for ti, t in enumerate(m.T):
            if m.tname(t) == tn:
                for me in m.methods(t):
                    if m.str(me[0]) == mn:
                        a = rs.addr(ti, me)
                        print("=====", q, hex(a), "params", me[10])
                        dis(a)
