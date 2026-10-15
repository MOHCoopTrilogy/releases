import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
rundir = notes = None
try:
    rundir, notes = G.boot("cn_probe", "m1l1", extra=[])
    p0 = len(R.read_log())
    G.cmd("probe", timeout=60)
    for l in re.findall(r"\^~\^~\^ CN PROBE[^\r\n]*", R.read_log()[p0:]):
        G.log("probe", l[:200])
    G.log("probe errors", len(G.errors()), G.errors()[:3])
finally:
    G.end(rundir, notes)
