"""propaudit.py <map> - boot a map, wait for the objectives2 props, collect the OBJX PROP lines"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
mp = sys.argv[1]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_pa_" + mp, mp, extra=["set coop_objxFailsafe 900", "set coop_objxPropLog 1"])
    G.cmd("god"); time.sleep(50)
    t = G.R.read_log()
    rows = re.findall(r"\^~\^~\^ (OBJX PROP[^\r\n]*)", t)
    open(os.path.join(G.HERE, "logs", "props_%s.txt" % mp), "w").write("\n".join(rows))
    G.log(mp, len(rows), "props", "errors", len(G.errors()))
finally:
    if rundir: G.end(rundir, notes)
