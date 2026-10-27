import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
rundir = notes = None
try:
    rundir, notes = G.boot("m2_bz", "m2l2c", extra=["set coop_objx 0"])
    G.cmd("god"); time.sleep(3)
    for x, y in ((3656, -3540), (3640, -3550), (3700, -3560), (3600, -3550), (3740, -3550)):
        p0 = G.cmd("benchz", x=x, y=y)
        for l in G.since(p0, r"\^~\^~\^ OX (BENCHZ[^\r\n]*)"): G.log("bz", l)
finally:
    G.end(rundir, notes)
