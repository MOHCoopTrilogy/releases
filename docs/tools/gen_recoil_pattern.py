"""gen_recoil_pattern.py - the per-gun recoil PATTERN table (coop_mod/recoil_pattern.txt) from tracked sources.

WHY. User 2026-11-10: "We can make recoil patterns realistic to their actual weapons." The engine
(fgame Weapon::CoopApplyPatternKick, coop_recoilPattern 1) kicks each round of a burst by a mostly deterministic
pattern; this script derives every number of that pattern from the real weapon, so nothing is hand-written into code.

INPUTS (all tracked, docs/tools/):
  recoil_research.tsv  one row per real gun: published specs (cartridge, bullet, velocity, charge, weight, rate, action,
                       stock layout, muzzle device, reputation) with per-row source URLs
  recoil_measured.tsv  one row per FIGURE with status MEASURED / DERIVED / ANECDOTAL and its own source. A MEASURED
                       numeric figure (rof_rpm, weight_kg, mv_mps, charge_g) overrides the research row - measurement
                       beats spec, spec beats estimate
  recoil_shape.tsv     the authored part: game stem -> physics row, class, carried magazine, stock line, device, hip
                       multiplier, drift / sway / jitter shape, with the basis of each shape ([M] measured, [D] derived)

PHYSICS (per round):
  impulse   I = m_b * v + m_c * 1.6 v        (bullet momentum + propellant gas; 1.6 v is the usual gas-velocity
                                               approximation - DERIVED, cross-checked against Chuck Hawks' tables)
  mass      M = spec weight + extra_kg + loaded magazine
  free recoil energy E = I^2 / 2M
  automatic, per round climb  = 0.88 * I / M^1.5 * stock * device * scale   (angular kick ~ impulse x lever / inertia,
            inertia ~ M * length^2 and length grows with mass: M^1.5. 0.88 sets the MP40 at ~0.30 deg)
  shoulder rifles / shotguns, the first round = 0.55 * sqrt(E) * stock * device * scale     (felt kick tracks energy)
  pistols, the flip           = 0.85 * sqrt(E) * device * scale
  rate of fire -> how fast the climb builds (no time to recover between rounds) and where it plateaus

    python docs/tools/gen_recoil_pattern.py build  [--mod DIR]   write <mod>/coop_mod/recoil_pattern.txt + derived.tsv
    python docs/tools/gen_recoil_pattern.py check  [--mod DIR]   exit 1 when the table is stale, or a roster gun /
                                                                 recoil_table.txt base has no pattern row
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


MOD = arg("--mod") or os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUT = os.path.join(MOD, "coop_mod", "recoil_pattern.txt")
DERIVED = os.path.join(ROOT, "docs", "proposals", "recoil_2026-11-10", "derived.tsv")

STOCK = {"drop": 1.0, "mid": 0.92, "inline": 0.82, "thompson": 1.45, "pistol": 1.0}
DEVICE = {"none": 1.0, "cutts": 0.88, "brake": 0.82, "jacket": 0.85, "suppressor": 0.88, "booster": 1.2}


def num(text):
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", text or "")
    return float(m.group(1)) if m else None


def read_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip("\r\n") for l in f if l.strip() and not l.startswith("#")]
    head = lines[0].split("\t")
    for l in lines[1:]:
        cells = l.split("\t")
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return rows


def physics():
    res = {r["key"]: r for r in read_tsv(os.path.join(HERE, "recoil_research.tsv"))}
    meas = read_tsv(os.path.join(HERE, "recoil_measured.tsv"))
    out = {}
    for k, r in res.items():
        p = {"name": r["real_name"], "action": r["action"]}
        for fld in ("bullet_g", "mv_mps", "charge_g", "weight_kg", "rof_rpm"):
            v = num(r[fld])
            est = "est" in (r[fld] or "")
            p[fld] = v
            p[fld + "_src"] = ("estimate" if est else "spec") + " (" + (r["sources"].split(",")[0].strip() or "?") + ")"
        out[k] = p
    for m in meas:
        k, fld = m["key"], m["field"]
        if k in out and fld in ("rof_rpm", "weight_kg", "mv_mps", "charge_g") and m["status"] == "MEASURED":
            v = num(m["value"])
            if v is not None and not out[k][fld + "_src"].startswith("MEASURED"):
                out[k][fld] = v
                out[k][fld + "_src"] = "MEASURED (" + m["source"] + ")"
    return out


def derive():
    phys = physics()
    shape = read_tsv(os.path.join(HERE, "recoil_shape.tsv"))
    rows, derived = [], []
    for s in shape:
        p = phys[s["phys"]]
        cls = s["cls"]
        mb, v, mc = p["bullet_g"] / 1000.0, p["mv_mps"], (p["charge_g"] or 0.0) / 1000.0
        M = p["weight_kg"] + float(s["extra_kg"]) + float(s["mag_kg"])
        I = mb * v + mc * 1.6 * v
        E = I * I / (2.0 * M)
        rof = p["rof_rpm"] or 0.0
        st, dv, sc = STOCK[s["layout"]], DEVICE[s["device"]], float(s["scale"])
        ob = "open-bolt" in p["action"] or "open bolt" in p["action"]
        if cls == "A":
            kick = 0.88 * I / M ** 1.5 * st * dv * sc
            kick1 = kick * (1.2 if ob else 1.05)       # an open bolt slams home before the first round fires
            grow = min(0.9, max(0.1, 0.15 + (rof - 450.0) / 900.0))
            growN = 6
            plateau = max(8, int(round(rof / 60.0 * 1.2)))   # ~1.2 s of fire: the stock is in the shoulder
            platMul = 0.55
            cap = 9.0 if M < 6.0 and kick < 0.5 else (12.0 if rof >= 1000 and M > 8 else 11.0)
            ret, rec, rmin, rmax = 0.90, 4.0, 8.0, 24.0
            settle = 0.30 + 0.03 * M
        elif cls in ("S", "B"):
            kick1 = 0.55 * math.sqrt(E) * st * dv * sc
            kick = kick1 * (1.15 if cls == "S" else 1.0)  # a rushed semi-auto follow-up climbs; a bolt cycle does not
            grow, growN = (0.30, 4) if cls == "S" else (0.0, 1)
            plateau, platMul = 0, 1.0
            cap = 10.0
            ret, rec, rmin, rmax = (0.97 if cls == "S" else 0.98), 5.0, 10.0, 30.0
            settle = 0.50 if cls == "S" else 0.60
        elif cls == "P":
            kick1 = 0.85 * math.sqrt(E) * dv * sc
            kick = kick1 * 1.2
            grow, growN, plateau, platMul = 0.30, 4, 0, 1.0
            cap = 7.0
            ret, rec, rmin, rmax = 0.97, 8.0, 14.0, 40.0
            settle = 0.35
        else:  # L
            kick1 = kick = 0.8 * sc
            grow, growN, plateau, platMul = 0.0, 1, 0, 1.0
            cap = 6.0
            ret, rec, rmin, rmax = 0.98, 4.0, 8.0, 20.0
            settle = 1.0
        yawcap = min(6.0, cap * 0.5)
        r = dict(name=s["stem"], kick1=kick1, kick=kick, grow=grow, growN=growN, plateau=plateau, platMul=platMul,
                 drift=float(s["drift"]), sway=float(s["sway"]), period=float(s["period"]), phase=0.0,
                 jitP=float(s["jitP"]), jitY=float(s["jitY"]), cap=cap, yawCap=yawcap, hip=float(s["hip"]), ret=ret,
                 recenter=rec, minDecay=rmin, maxDecay=rmax, settle=settle)
        rows.append(r)
        derived.append(dict(stem=s["stem"], phys=s["phys"], real=p["name"], cls=cls, M=M, I=I, E=E, rof=rof,
                            kick1=kick1, kick=kick, hip=r["hip"], basis=s["basis"],
                            rof_src=p["rof_rpm_src"], weight_src=p["weight_kg_src"], mv_src=p["mv_mps_src"],
                            charge_src=p["charge_g_src"]))
    return rows, derived


COLS = ["kick1", "kick", "grow", "growN", "plateau", "platMul", "drift", "sway", "period", "phase", "jitP", "jitY",
        "cap", "yawCap", "hip", "ret", "recenter", "minDecay", "maxDecay", "settle"]


def render(rows):
    out = ["// GENERATED by docs/tools/gen_recoil_pattern.py from recoil_research.tsv + recoil_measured.tsv +",
           "// recoil_shape.tsv - do not edit; edit a source and rerun. Read by fgame Weapon::CoopApplyPatternKick",
           "// (coop_recoilPattern 1). Finish variants <stem>_<finish> share their base row (trailing _segments dropped).",
           "// Degrees; drift + = right; climb is up. One row per game weapon stem.",
           "// name " + " ".join(COLS)]
    for r in rows:
        out.append(r["name"] + " " + " ".join(("%.3f" % r[c]).rstrip("0").rstrip(".") if isinstance(r[c], float)
                                              else str(r[c]) for c in COLS))
    return "\n".join(out) + "\n"


def render_derived(derived):
    head = ["stem", "phys", "real", "cls", "M", "I", "E", "rof", "kick1", "kick", "hip", "rof_src", "weight_src",
            "mv_src", "charge_src", "basis"]
    out = ["# GENERATED by docs/tools/gen_recoil_pattern.py - the derivation of every pattern row (M kg, I N s, E J)",
           "\t".join(head)]
    for d in derived:
        out.append("\t".join(("%.3f" % d[h]) if isinstance(d[h], float) else str(d[h]) for h in head))
    return "\n".join(out) + "\n"


def coverage_problems(rows):
    names = {r["name"] for r in rows}

    def resolves(stem):
        k = stem
        while True:
            if k in names:
                return True
            if "_" not in k:
                return False
            k = k.rsplit("_", 1)[0]

    bad = []
    lw = os.path.join(HERE, "loadout_weapons.tsv")
    for r in read_tsv(lw):
        stem = os.path.splitext(os.path.basename(r.get("tik", "")))[0]
        if stem and "grenade" not in stem and "handgranate" not in stem and stem != "it_w_bomba" and not resolves(stem):
            bad.append("roster " + r["id"] + " " + stem)
    rt = os.path.join(MOD, "coop_mod", "recoil_table.txt")
    if os.path.exists(rt):
        for l in open(rt, encoding="utf-8", errors="replace"):
            if l.strip() and not l.startswith("//"):
                stem = l.split()[0]
                if not resolves(stem) and not re.search(r"grenade|binocular|mine|bomba|handgranate", stem):
                    bad.append("recoil_table " + stem)
    return bad


def render_research():
    """the per-gun research table (markdown) - every figure with where it came from"""
    res = {r["key"]: r for r in read_tsv(os.path.join(HERE, "recoil_research.tsv"))}
    meas = read_tsv(os.path.join(HERE, "recoil_measured.tsv"))
    phys = physics()
    rows, derived = derive()
    by_phys = {}
    for d in derived:
        by_phys.setdefault(d["phys"], []).append(d)
    out = ["# Recoil research table (GENERATED by docs/tools/gen_recoil_pattern.py - do not edit)", "",
           "Figures: **M** = measured (a trial, test, chronograph or manual figure, from recoil_measured.tsv), "
           "**S** = published spec (recoil_research.tsv), **E** = estimate. Impulse I and free-recoil energy E are "
           "DERIVED (I = m_b v + m_c 1.6 v; E = I^2 / 2M with the loaded magazine). kick1 / kick = the pattern's "
           "first-round and sustained climb in degrees (aimed, standing).", "",
           "| gun | cartridge | bullet g | v m/s | charge g | weight kg | rpm | action | stock / device | I N s | E J | "
           "kick1 / kick | shape basis | sources |", "|" + "---|" * 14]

    def tag(src):
        return "M" if src.startswith("MEASURED") else ("E" if src.startswith("estimate") else "S")
    for k, r in res.items():
        p = phys[k]
        ds = by_phys.get(k, [])
        d0 = next((d for d in ds if d["stem"] == k), ds[0] if ds else None)
        src = sorted(set([r["sources"]] + [m["source"] for m in meas if m["key"] == k]))
        out.append("| %s | %s | %s | %s %s | %s %s | %s %s | %s %s | %s | %s / %s | %s | %s | %s | %s | %s |" % (
            r["real_name"], r["cartridge"], r["bullet_g"],
            p["mv_mps"], tag(p["mv_mps_src"]), p["charge_g"], tag(p["charge_g_src"]),
            p["weight_kg"], tag(p["weight_kg_src"]), int(p["rof_rpm"] or 0), tag(p["rof_rpm_src"]),
            r["action"], r["layout"], r["muzzle_device"],
            "%.1f" % d0["I"] if d0 else "-", "%.1f" % d0["E"] if d0 else "-",
            "%.2f / %.2f" % (d0["kick1"], d0["kick"]) if d0 else "-",
            (d0["basis"] if d0 else "").replace("|", "/"),
            " ".join(x.strip() for x in ",".join(src).split(",") if x.strip().startswith("http"))))
    out += ["", "## Measured figures (recoil_measured.tsv)", "", "| gun | field | value | status | range | source | note |",
            "|---|---|---|---|---|---|---|"]
    for m in meas:
        out.append("| %s | %s | %s %s | %s | %s | %s | %s |" % (m["key"], m["field"], m["value"], m["unit"], m["status"],
                                                            m["range"], m["source"], m["note"].replace("|", "/")))
    return "\n".join(out) + "\n"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    rows, derived = derive()
    text = render(rows)
    dtext = render_derived(derived)
    bad = coverage_problems(rows)
    if mode == "build":
        os.makedirs(os.path.dirname(DERIVED), exist_ok=True)
        with open(OUT, "w", newline="\n") as f:
            f.write(text)
        with open(DERIVED, "w", newline="\n") as f:
            f.write(dtext)
        with open(os.path.join(os.path.dirname(DERIVED), "RESEARCH.md"), "w", newline="\n", encoding="utf-8") as f:
            f.write(render_research())
        print("wrote %s (%d rows) and %s" % (OUT, len(rows), DERIVED))
    else:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        if cur != text:
            print("STALE: %s - run build" % OUT)
            sys.exit(1)
    for b in bad:
        print("NO PATTERN ROW: " + b)
    if bad:
        sys.exit(1)
    print("ok: %d rows, every roster gun and recoil_table base resolves" % len(rows))


if __name__ == "__main__":
    main()
