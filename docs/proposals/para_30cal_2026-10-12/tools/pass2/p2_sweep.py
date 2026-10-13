"""p2_sweep.py <map> - boot a map and ask the planner, at every AI actor's position (300u apart, up to 45) and four
facings, what COVER sites the ground has. One driver command; prints the mode A sites."""
import json, os, re, sys, time
import p2lib as G
R = G.R
MAP = sys.argv[1]
rundir = notes = None
OUT = {"map": MAP, "sites": [], "probes": []}
try:
    rundir, notes = G.boot("p2_sweep_" + MAP.replace("/", "_"), MAP)
    p0 = G.cmd("here")
    m = re.search(r"P2 here \(([^)]*)\)", R.read_log()[p0:])
    OUT["spawn"] = m.group(1)
    p0 = G.cmd("sweep", timeout=420)
    t = R.read_log()[p0:]
    probes = {m.group(1): m.group(2) for m in re.finditer(r"P2 PROBE (s\d+_\d+) from=([^\r\n]*)", t)}
    for m in re.finditer(r"P2 SITE (s\d+_\d+) ([^\r\n]*)", t):
        OUT["sites"].append({"tag": m.group(1), "from": probes.get(m.group(1), "")[:44], "site": m.group(2)})
    OUT["probes"] = probes
    G.log(MAP, "spawn", OUT["spawn"], "probes", len(probes), "sites", len(OUT["sites"]))
    seen = set()
    for s in OUT["sites"]:
        g = re.search(r"gun=\(([^)]*)\)", s["site"]).group(1)
        key = tuple(round(float(v) / 40) for v in g.split())
        if key in seen:
            continue
        seen.add(key)
        G.log("SITE", s["tag"], s["from"], s["site"][:200])
    tot = {}
    for line in probes.values():
        for k, v in re.findall(r"(\w+)=(\d+)", line.split("refused:")[-1]):
            tot[k] = tot.get(k, 0) + int(v)
    G.log("refusals over the map:", tot)
    G.log("script errors:", G.errors()[:8])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        G.log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    json.dump(OUT, open(os.path.join(G.HERE, "sweep_%s.json" % MAP.replace("/", "_")), "w"), indent=1)
    G.end(rundir, notes)
