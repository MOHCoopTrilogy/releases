"""mkjobs4.py <modDir> <out.json> - verify jobs for run_fit4.py, read from the GENERATED cfgs (thumb xfm from w<id>_s<slot>.cfg), plus 3 finishes on the base gun's framing."""
import io, json, re, sys, os
mod, out = sys.argv[1], sys.argv[2]
UI = os.path.join(mod, "ui", "loadout")
rows = [l.rstrip("\n").split("\t") for l in io.open(r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv", encoding="utf-8") if not l.startswith("#")]
h = rows[0]
J = []
base = {}
for r in rows[1:]:
    d = dict(zip(h, r))
    sl = d["slots"][0]
    t = io.open(os.path.join(UI, "w%s_s%s.cfg" % (d["id"], sl)), encoding="latin-1").read()
    xt = re.search(r'(?m)^set coop_loXfmT\d "([^"]*)"', t).group(1)
    base[d["id"]] = (d["tik"], d["name"], xt, sl)
    J.append([d["id"], d["tik"], d["name"], xt, "", d["id"], sl])
for pid, suf, nm in (("01", "gold", "M1 GARAND GOLD"), ("48", "chrome", "COLT 45 CHROME"), ("24", "gold", "THOMPSON GOLD")):
    tik, _, xt, sl = base[pid]
    J.append(["f" + pid + suf, tik.replace(".tik", "_%s.tik" % suf), nm, xt, "", pid, sl])
json.dump(J, open(out, "w"))
print(len(J))
