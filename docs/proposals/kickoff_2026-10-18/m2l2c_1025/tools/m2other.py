"""m2other.py <map> - global officer-wave check on another map: spawn point + visible flag per call (3 calls)"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
mp = sys.argv[1]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_o_" + mp, mp, extra=["set coop_objxFailsafe 900"])
    G.cmd("god"); time.sleep(45)
    for k in range(3):
        G.cmd("rnftest"); time.sleep(3)
    t = G.R.read_log()
    for l in re.findall(r"\^~\^~\^ OX RNFTEST[^\r\n]*", t): G.log(mp, l[:200])
    G.log(mp, "script errors:", len(G.errors()))
finally:
    if rundir: G.end(rundir, notes)
