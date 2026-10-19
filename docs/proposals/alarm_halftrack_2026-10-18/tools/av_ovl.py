"""av_ovl.py - score candidate halftrack stops (rotation-safe fill cells round Nebelwerfer 1) by how much of the church->Nebelwerfer line they overlook."""
import os, re, sys, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
import av_route as RT
G = A.G; R = A.R
cells, adj = RT.load("m3l3g")
NEB = (-1834, -5160)
cand = []
for c in cells:
    x, y, z, f = cells[c]
    d = math.hypot(x - NEB[0], y - NEB[1])
    if 600 <= d <= 2400 and RT.fat(cells, c):
        if all(math.hypot(x - q[0], y - q[1]) >= 200 for q in cand):
            cand.append((x, y, z))
cand = cand[:150]
rundir = notes = None
try:
    rundir, notes = G.boot("av_ovl", "m3l3", extra=["set g_ai 0"])
    p0 = len(R.read_log())
    for (x, y, z) in cand:
        G.cmd("ovlc", x=x, y=y, z=z + 6)
    rows = re.findall(r"\^~\^~\^ OVL (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (\d+)", R.read_log()[p0:])
    with open(os.path.join(A.HERE, "scout", "m3l3_ovl.txt"), "w") as f:
        for r in rows:
            f.write(" ".join(r) + "\n")
    G.log("ovl", "scored", len(rows), "of", len(cand))
except Exception as e:
    import traceback
    G.log("ovl", "FAILED", repr(e), traceback.format_exc()[-500:])
finally:
    G.end(rundir, notes)
