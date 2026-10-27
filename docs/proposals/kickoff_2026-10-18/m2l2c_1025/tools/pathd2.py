import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
rundir = notes = None
cands = [(748,-5568),(748,-4560),(756,-2352),(748,-2936),(700,-3300),(700,-4200),(3204,-4520),(3188,-5648),(3412,-2952),(3196,-3040),(10,-6984),(-469,-5664)]
try:
    rundir, notes = G.boot("m2_pd", "m2l2c")
    G.cmd("god"); time.sleep(2); G.cmd("rgset", k=1); time.sleep(1)
    for gx0, gy0, (x, y) in [(702,-3740,c) for c in cands[:6]] + [(3155,-3600,c) for c in cands[6:10]]:
        GX, GY = gx0, gy0
        p0 = G.cmd("pathd", x=x, y=y, z=-505, yaw=GX, pitch=GY, k=-512)
        for l in G.since(p0, r"\^~\^~\^ OX (PATHD[^\r\n]*)"): G.log("pd", l)
finally:
    G.end(rundir, notes)
