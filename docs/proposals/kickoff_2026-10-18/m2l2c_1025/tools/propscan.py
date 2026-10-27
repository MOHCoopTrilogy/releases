import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
mp = sys.argv[1]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_ps_" + mp, mp, extra=["set coop_objxFailsafe 900"])
    G.cmd("god"); time.sleep(45)
    G.cmd("objact", timeout=60); time.sleep(10)
    p0 = G.cmd("propscan", timeout=60)
    rows = G.since(p0, r"\^~\^~\^ OX (PROPSCAN[^\r\n]*)")
    open(os.path.join(G.HERE, "logs", "propscan_%s.txt" % mp), "w").write("\n".join(rows))
    G.log(mp, len(rows), "rows; errors", len(G.errors()))
finally:
    if rundir: G.end(rundir, notes)
