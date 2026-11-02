"""v7b_ents.py <in.bsp> <out.bsp> - the v7 -> v7b step (2026-10-28): "svflags" "+broadcast" on every boom / collapse / cover / pclip entity
the finale moves or hides (so no PVS pop-out). The list is the exact v7 -> v7b entity diff; any entity that already carries svflags is left alone."""
import sys, re, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "v7"))
import bspedit as E
LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v7b_broadcast.txt")
b = E.Bsp(open(sys.argv[1], "rb").read())
names = set(open(LIST).read().split())
t = b.entities(); n = 0
def fix(m):
    global n
    blk = m.group(0)
    tn = re.search(r'"targetname" "([^"]*)"', blk)
    if tn and tn.group(1) in names and '"svflags"' not in blk:
        n += 1; return blk[:-1] + '"svflags" "+broadcast"\n}'
    return blk
t2 = re.sub(r'\{[^{}]*\}', fix, t)
b.lumps[E.IX["ents"]] = bytearray(t2.encode("latin1") + b"\x00")
open(sys.argv[2], "wb").write(b.tobytes())
print("broadcast added", n)
