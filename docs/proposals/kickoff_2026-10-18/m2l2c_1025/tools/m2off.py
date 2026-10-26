"""m2off.py <map> - REAL officer, 2 full officer waves: spawn point + visible flag + per-man arrival (global routing)"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
mp = sys.argv[1]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_f_" + mp, mp, extra=["set coop_objxFailsafe 900", "set coop_reinfMg 0"])
    G.cmd("god"); G.cmd("notgt") if os.environ.get("NOTGT") else None
    ok = G.R.wait_log(r"OFFICER SPAWNED", 150, 0)
    G.log(mp, "officer spawned:", bool(ok))
    time.sleep(5)
    for k in range(2):
        G.cmd("offwave"); time.sleep(60)
    t = G.R.read_log()
    for l in re.findall(r"\^~\^~\^ (?:OFFICER wave|REINF)[^\r\n]*", t): G.log(mp, l[:200])
    G.log(mp, "script errors:", len(G.errors()))
finally:
    if rundir: G.end(rundir, notes)
