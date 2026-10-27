"""pathd3.py - path lengths between points on the quays / pens (hidden scout, gate open)"""
import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
rundir = notes = None
tests = [((748, -4560), (748, -5568)), ((748, -4560), (748, -3800)), ((748, -4560), (700, -3740)), ((748, -4560), (740, -3790)),
         ((748, -4560), (792, -3740)), ((748, -4560), (3615, -3850)), ((3204, -4520), (3188, -5648)), ((3204, -4520), (3180, -3600)),
         ((3412, -2952), (3180, -3600))]
if len(sys.argv) > 1:
    import json
    tests = [tuple(map(tuple, t)) for t in json.load(open(sys.argv[1]))]
try:
    rundir, notes = G.boot("m2_pd3", "m2l2c")
    G.cmd("god"); time.sleep(2); G.cmd("rgset", k=1); time.sleep(1)
    for (x, y), (gx, gy) in tests:
        p0 = G.cmd("pathd", x=x, y=y, z=-505, yaw=gx, pitch=gy, k=-512)
        for l in G.since(p0, r"\^~\^~\^ OX (PATHD[^\r\n]*)"):
            G.log("pd", l, "-> goal", gx, gy)
finally:
    G.end(rundir, notes)
