"""cgrid.py <label> x0 y0 z0 step nx ny - ceiling-underside grid on m2l2c (edited map)"""
import os, sys, time, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
label, x0, y0, z0, step, nx, ny = sys.argv[1:8]
span = sys.argv[8] if len(sys.argv) > 8 else "900"
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + label, "m2l2c")
    G.cmd("god"); time.sleep(3)
    p0 = G.cmd("ceilgrid", timeout=120, x=x0, y=y0, z=z0, step=step, k=nx, s=ny, yaw=span)
    time.sleep(2)
    rows = G.since(p0, r"\^~\^~\^ OX (CG y=[^\r\n]*)")
    json.dump(rows, open(os.path.join(G.HERE, "logs", "cg_%s.json" % label), "w"))
    G.log(label, len(rows), "rows", G.errors()[:2])
finally:
    G.end(rundir, notes)
