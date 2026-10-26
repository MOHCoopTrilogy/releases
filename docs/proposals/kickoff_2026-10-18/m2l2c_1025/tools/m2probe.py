import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
mp, x, y, z = sys.argv[1:5]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_pr_" + mp, mp, extra=["set coop_objxFailsafe 900"])
    G.cmd("god"); time.sleep(40)
    G.cmd("probe", x=x, y=y, z=z); time.sleep(7)
    for l in re.findall(r"\^~\^~\^ OX PROBE[^\r\n]*", G.R.read_log()): G.log(mp, l[:200])
    G.log(mp, "script errors:", len(G.errors()))
finally:
    if rundir: G.end(rundir, notes)
