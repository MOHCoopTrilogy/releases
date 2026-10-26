import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
rundir = notes = None
try:
    rundir, notes = G.boot("m2_bd", "m2l2c")
    G.cmd("god"); time.sleep(2)
    for m in sys.argv[1:]:
        p0 = G.cmd("bounds", s=m)
        for l in G.since(p0, r"\^~\^~\^ OX (BOUNDS[^\r\n]*)"): G.log("bd", l)
finally:
    G.end(rundir, notes)
