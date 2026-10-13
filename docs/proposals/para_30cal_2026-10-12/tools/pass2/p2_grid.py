"""p2_grid.py <map> <cx> <cy> <cz> [step=350] [n=5] - probe an n x n grid of points round a place for COVER sites
(four facings each, an enemy 700u ahead). The player is put at each point first, so only ground he stays on counts."""
import json, os, re, sys, time
import p2lib as G
R = G.R
MAP = sys.argv[1]
CX, CY, CZ = [float(v) for v in sys.argv[2:5]]
STEP = float(sys.argv[5]) if len(sys.argv) > 5 else 350.0
N = int(sys.argv[6]) if len(sys.argv) > 6 else 5
rundir = notes = None
try:
    rundir, notes = G.boot("p2_grid_" + MAP.replace("/", "_"), MAP)
    seen = set()
    for i in range(N):
        for j in range(N):
            x = CX + (i - (N - 1) / 2.0) * STEP
            y = CY + (j - (N - 1) / 2.0) * STEP
            p0 = G.cmd("tp", x=x, y=y, z=CZ + 30, yaw=0, pitch=0)
            time.sleep(0.7)
            p0 = G.cmd("here")
            m = re.search(r"P2 here \(([^)]*)\)", R.read_log()[p0:])
            at = [float(v) for v in m.group(1).split()]
            if abs(at[0] - x) > 40 or abs(at[1] - y) > 40:
                G.log("pt", i, j, "player did not stay", at)
                continue
            for yaw in (0, 90, 180, 270):
                tag = "g%d_%d_%d" % (i, j, yaw)
                p0 = G.cmd("probe", timeout=60, yaw=yaw, n=700, tag=tag, pitch=0)
                t = R.read_log()[p0:]
                for s in re.findall(r"P2 SITE %s ([^\r\n]*)" % tag, t):
                    g = re.search(r"gun=\(([^)]*)\)", s).group(1)
                    key = tuple(round(float(v) / 30) for v in g.split())
                    if key in seen:
                        continue
                    seen.add(key)
                    G.log("SITE from", [round(v) for v in at], "yaw", yaw, s[:210])
    G.log("script errors:", G.errors()[:8])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
