import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
rundir = notes = None
cands = [(4020,-4136),(4244,-4376),(4020,-4888),(4000,-5600),(4450,-5650),(4450,-4900),(4000,-5300),(4500,-5200),(4000,-5000),(4450,-4500),(4500,-3900),(4050,-3500)]
try:
    rundir, notes = G.boot("m2_pd", "m2l2c")
    G.cmd("god"); time.sleep(2); G.cmd("rgset", k=1); time.sleep(1)
    for x, y in cands:
        p0 = G.cmd("pathd", x=x, y=y, z=-505, yaw=3540, pitch=-3300, k=-512)
        for l in G.since(p0, r"\^~\^~\^ OX (PATHD[^\r\n]*)"): G.log("pd", l)
finally:
    G.end(rundir, notes)
