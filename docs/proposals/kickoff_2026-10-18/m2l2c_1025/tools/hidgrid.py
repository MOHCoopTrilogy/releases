"""hidgrid.py <A|B> - candidate wave entries for a crane: floor, hidden from the panel (head + feet), path < 2600 u to the quay rally point"""
import os, sys, time, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
which = sys.argv[1]
cfg = {"A": dict(x=748, y=-3790, yaw=-300, pitch=-6000, k=19, s=46, z=748, s2=-3800),
       "B": dict(x=3190, y=-3590, yaw=2200, pitch=-6000, k=26, s=46, z=3190, s2=-3600)}[which]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_hg" + which, "m2l2c")
    G.cmd("god"); time.sleep(2); G.cmd("rgset", k=1); time.sleep(1)
    p0 = G.cmd("hidgrid", timeout=400, step=100, **cfg)
    time.sleep(1)
    rows = G.since(p0, r"\^~\^~\^ OX (HID [^\r\n]*)")
    json.dump(rows, open(os.path.join(G.HERE, "logs", "hid_%s.json" % which), "w"))
    G.log("hg", which, len(rows), "hidden cells with a path")
    for r in rows[:80]:
        G.log("hg", r)
finally:
    G.end(rundir, notes)
