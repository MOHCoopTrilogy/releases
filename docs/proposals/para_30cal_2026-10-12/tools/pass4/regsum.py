"""regsum.py <label> ... - one line a regression run from logs/run_<label>.txt and its qconsole.log: script errors,
teleports (meter), rescues, men alive, health, how far the men are from the hold point at the end, landings off level."""
import json, math, os, re, sys
H = os.path.dirname(os.path.abspath(__file__))
for lab in sys.argv[1:]:
    t = open(os.path.join(H, "logs", "run_%s.txt" % lab), encoding="latin-1").read()
    j = json.load(open(os.path.join(H, "logs", "run_%s.json" % lab)))
    at = j.get("at", [0, 0, 0, 0])
    er = re.search(r"script errors: (\d+)", t)
    mt = re.findall(r"P3 METER t=(\d+) landed=(\d+) alive=(\d+) hp=(\d+).*?tele=(\d+).*?farAvg=(\d+) farMax=(\d+)", t)
    sq = re.findall(r"P3 SQ k=(\d) alive=(\d) hp=([\d.]+) at=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \)", t)
    d = ["%s:%d" % (k, math.hypot(float(x) - at[0], float(y) - at[1])) if a == "1" else "%s:dead" % k for k, a, hp, x, y, z in sq]
    land = [int(v) for v in re.findall(r"P3 LAND k=\d at=\([^)]*\) dref=\d+ dz=(-?\d+)", t)]
    kinds = dict(re.findall(r"\('([a-z]+ [a-z0-9=]+)', (\d+)\)", t))
    pick = {k: v for k, v in kinds.items() if k.split()[0] in ("rescue", "walkout", "clear", "nade") or k in ("mg setup", "mg nade", "mg seat", "mg suppress", "mg track", "mg newbelt", "tac mandown")}
    print(lab, j.get("map"), "errors=%s" % (er.group(1) if er else "?"), "FAILED" if "FAILED" in t else "",
          "meter(t,landed,alive,hp,tele,farAvg,farMax)=%s" % (mt[-1],) if mt else "no meter", "dist_from_hold=%s" % d,
          "landing_dz=%s" % land, "rescue_lines=%d" % len(re.findall(r"PSQ t=[\d.]+ rescue", t)), pick)
