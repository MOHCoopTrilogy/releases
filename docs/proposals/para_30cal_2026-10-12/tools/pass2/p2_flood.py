"""p2_flood.py <map> [x y z] - from the player's spawn (or from x y z, if he stays there) flood the ground a man can walk
to in 300u straight steps (up to 90 points) and list the COVER sites the planner finds at each (four facings)."""
import json, os, re, sys, time
import p2lib as G
R = G.R
MAP = sys.argv[1]
rundir = notes = None
try:
    rundir, notes = G.boot("p2_flood_" + MAP.replace("/", "_"), MAP)
    if len(sys.argv) > 4:
        G.cmd("tp", x=sys.argv[2], y=sys.argv[3], z=float(sys.argv[4]) + 20, yaw=0, pitch=0)
        time.sleep(1.0)
    p0 = G.cmd("here")
    G.log(MAP, "from", re.search(r"P2 here \(([^)]*)\)", R.read_log()[p0:]).group(1))
    p0 = G.cmd("flood", timeout=500)
    t = R.read_log()[p0:]
    pts = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r"P2 FPT (\d+) at=\(([^)]*)\) sky=(\d+)", t)}
    G.log("points", len(pts), "open sky (>900):", sum(1 for v in pts.values() if int(v[1]) > 900))
    seen = set()
    for m in re.finditer(r"P2 SITE f(\d+)_(\d+) ([^\r\n]*)", t):
        g = re.search(r"gun=\(([^)]*)\)", m.group(3)).group(1)
        key = tuple(round(float(v) / 30) for v in g.split())
        if key in seen:
            continue
        seen.add(key)
        G.log("SITE pt", m.group(1), "at", pts.get(m.group(1)), "yaw", m.group(2), m.group(3)[:200])
    tot = {}
    for m in re.finditer(r"P2 PROBE f\S+ [^\r\n]*refused:([^\r\n]*)", t):
        for k, v in re.findall(r"(\w+)=(\d+)", m.group(1)):
            tot[k] = tot.get(k, 0) + int(v)
    G.log("refusals:", tot)
    G.log("script errors:", G.errors()[:8])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
