"""p2_probe.py <map> [bags] - boot a map, list its AI actors, and at the player's spawn and at up to 14 actor
positions ask the planner what gun sites the ground has (8 facings each, an enemy 700u ahead). Prints the sites."""
import json, os, re, sys, time
import p2lib as G
R = G.R
MAP = sys.argv[1]
BAGS = sys.argv[2] if len(sys.argv) > 2 else "0"
rundir = notes = None
OUT = {"map": MAP, "sites": [], "probes": []}
try:
    rundir, notes = G.boot("p2_probe_" + MAP.replace("/", "_"), MAP)
    p0 = G.cmd("here")
    m = re.search(r"P2 here \(([^)]*)\)", R.read_log()[p0:])
    spawn = [float(v) for v in m.group(1).split()]
    p0 = G.cmd("ents", timeout=60)
    ents = [[float(v) for v in e.split()] for e in G.since(p0, r"P2 ENT \d+ at=\(([^)]*)\)")]
    G.log("spawn", spawn, "actors", len(ents))
    # spread: the spawn, then actors at least 500u from anything already chosen
    pts = [spawn]
    for e in ents:
        if all((e[0] - q[0]) ** 2 + (e[1] - q[1]) ** 2 > 500 ** 2 for q in pts):
            pts.append(e)
        if len(pts) >= 15:
            break
    for i, q in enumerate(pts):
        G.cmd("tp", x=q[0], y=q[1], z=q[2] + 8, yaw=0, pitch=0)
        time.sleep(0.5)
        for yaw in range(0, 360, 45):
            tag = "p%d_y%d" % (i, yaw)
            p0 = G.cmd("probe", timeout=60, yaw=yaw, n=700, tag=tag, pitch=BAGS)
            t = R.read_log()[p0:]
            for s in re.findall(r"P2 SITE %s ([^\r\n]*)" % tag, t):
                OUT["sites"].append({"pt": q, "yaw": yaw, "site": s})
                if " mode=A" in " " + s:
                    G.log("SITE", [round(v) for v in q], yaw, s[:190])
            pr = re.search(r"P2 PROBE %s ([^\r\n]*)" % tag, t)
            OUT["probes"].append({"pt": q, "yaw": yaw, "line": pr.group(1) if pr else None})
            if pr and yaw == 0:
                G.log("probe", i, pr.group(1)[:230])
    G.log("script errors:", G.errors()[:8])
    G.log("sites A:", sum(1 for s in OUT["sites"] if "mode=A" in s["site"]), "C:", sum(1 for s in OUT["sites"] if "mode=C" in s["site"]))
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        G.log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    json.dump(OUT, open(os.path.join(G.HERE, "probe_%s.json" % MAP.replace("/", "_")), "w"), indent=1)
    G.end(rundir, notes)
