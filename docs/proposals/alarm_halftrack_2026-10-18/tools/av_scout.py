"""av_scout.py <label> <map> <x,y,z;x,y,z..> [maxcells] - flood-fill the drivable (Opel hull) area of <map> in-engine from the given seeds
(+ the player spawn) and save the cells to scout/<label>_scf.txt (lines: ix iy z surfaceFlags, grid 128 u)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL, MAP, SEEDS = sys.argv[1], sys.argv[2], sys.argv[3]
MAXC = sys.argv[4] if len(sys.argv) > 4 else "7000"
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, MAP, extra=["set g_ai 0"])
    p0 = len(R.read_log())
    G.cmd("here")
    G.cmd("playerseed")
    for s in SEEDS.split(";"):
        if s.strip():
            x, y, z = s.split(",")
            G.cmd("fillseed", x=x, y=y, z=z)
    G.cmd("fill", lx=MAXC)
    m = R.wait_log(r"\^~\^~\^ SCF done (\d+)", 600, p0)
    txt = R.read_log()[p0:]
    cells = re.findall(r"\^~\^~\^ SCF (-?\d+) (-?\d+) (-?[\d.]+) (-?\d+)", txt)
    with open(os.path.join(A.HERE, "scout", LABEL + "_scf.txt"), "w") as f:
        for c in cells:
            f.write(" ".join(c) + "\n")
    G.log(LABEL, "cells", len(cells), "done" if m else "TIMEOUT", "errors", len(G.errors()), G.errors()[:3])
except Exception as e:
    import traceback
    G.log(LABEL, "FAILED", repr(e), traceback.format_exc()[-600:])
finally:
    G.end(rundir, notes)
