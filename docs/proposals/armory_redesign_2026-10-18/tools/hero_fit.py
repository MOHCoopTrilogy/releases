"""hero_fit.py - solve the Armory HERO transform (coop_loXfmHero) of every gun for the hero box, by measurement.

The hero box is wide (HERO_W x HERO_H menu units, gen_armory_urc.py): the slot-thumbnail fit (xfmt, solved for 92x50) cannot be reused, a rifle would be
a thin strip.  Same rule as the coordinator's gun-fit solver (fit3.py header): scale' = scale * max(w/0.88, h/0.80), centre the bounding box at 0.5/0.5,
clipped -> shrink >= 25 % and re-measure.  One probe frame per gun (y and z both +PR: cx depends only on y, cy only on z) gives the two slopes.

    python hero_fit.py init  <jobs_out.json>            state from armory_stats' xfmt scaled by the aspect ratio; round-0 jobs (base + probe per gun)
    python hero_fit.py solve <runDir> <jobs_out.json>   measure the frames of the run, one Newton step per gun, next jobs (guns not converged)
    python hero_fit.py apply                            write docs/tools/armory_hero_fit.tsv (id <TAB> xfm) from the state
    python hero_fit.py status

Frames: <runDir>\\shots\\hf_<name>.tga at 1920x1080 (run_hero_fit.py); name = <id> (base) | <id>p (probe); hf_000 = the empty hero box.
"""
import io, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "hero_fit_state.json")
TSV = r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv"
OUT = r"C:\mohaa-coop-dev\docs\tools\armory_hero_fit.tsv"
BOX = (144, 66, 332, 128)          # HERO_X, HERO_Y, HERO_W, HERO_H of gen_armory_urc.py (menu units)
T_ASPECT = 92.0 / 50.0
WT, HT = 0.92, 0.66                 # the gun fills 92 % of the width, at most 66 % of the height, centred at CY (the name / caliber sit over the lower left)
CY = 0.37
PR = 1.5
SKIP = {"66"}                      # the Mills bomb is a 2D icon
TOL_S, TOL_CX, TOL_CY = 0.05, 0.03, 0.05


def rows():
    out = {}
    hdr = None
    for l in io.open(TSV, encoding="utf-8"):
        if l.startswith("#") or not l.strip():
            continue
        f = l.rstrip("\r\n").split("\t")
        if hdr is None:
            hdr = f
            continue
        d = dict(zip(hdr, f))
        out.setdefault(d["id"], d)
    return out


def fmt(x):
    return " ".join("%g" % round(v, 3) for v in x)


def crop_box(im):
    W, H = im.size
    x0, y0 = int(BOX[0] * W / 640.0), int(BOX[1] * H / 480.0)
    x1, y1 = int((BOX[0] + BOX[2]) * W / 640.0), int((BOX[1] + BOX[3]) * H / 480.0)
    return np.asarray(im.convert("RGB").crop((x0, y0, x1, y1))).astype(int)


def measure(shots, name, base):
    p = os.path.join(shots, "hf_%s.tga" % name)
    if not os.path.isfile(p):
        return None
    a = crop_box(Image.open(p))
    m = np.abs(a - base).max(axis=2) > 18
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        return None
    h, w = m.shape
    bw, bh = (xs.max() - xs.min() + 1) / float(w), (ys.max() - ys.min() + 1) / float(h)
    cx, cy = (xs.min() + xs.max()) / 2.0 / w, (ys.min() + ys.max()) / 2.0 / h
    touch = xs.min() <= 1 or ys.min() <= 1 or xs.max() >= w - 2 or ys.max() >= h - 2
    return {"w": bw, "h": bh, "cx": cx, "cy": cy, "touch": bool(touch), "aspect_px": (w, h)}


def init(out):
    R = rows()
    st = {}
    r = 1.0     # the model is framed by the widget WIDTH (horizontal fov): a rifle fills the same fraction of any width at the same scale; tall guns are solved by Newton
    for i, d in R.items():
        if i in SKIP or d["tab"] == "":
            continue
        t = [float(v) for v in (d.get("xfmt") or d["xfm"]).split()]
        st[i] = {"x": [t[0] * r, t[1] * r, t[2] * r, t[3] * r, t[4], t[5], t[6]], "slope": None, "done": False, "round": 0}
    json.dump(st, open(STATE, "w"), indent=1)
    jobs(st, out, [i for i in st])


def jobs(st, out, ids):
    R = rows()
    J = []
    for i in ids:
        x = st[i]["x"]
        J.append([i, R[i]["tik"], fmt(x)])
        if st[i]["slope"] is None:
            J.append([i + "p", R[i]["tik"], fmt([x[0], x[1] + PR, x[2] + PR] + x[3:])])
    json.dump(J, open(out, "w"))
    print("jobs", len(J), "for", len(ids), "guns ->", out)


def solve(run, out):
    st = json.load(open(STATE))
    shots = os.path.join(run, "shots")
    base = crop_box(Image.open(os.path.join(shots, "hf_000.tga")))
    todo, ok, miss = [], 0, []
    for i, s in st.items():
        if s["done"]:
            ok += 1
            continue
        m0 = measure(shots, i, base)
        if m0 is None:
            miss.append(i)
            todo.append(i)
            continue
        x = s["x"]
        ratio = max(m0["w"] / WT, m0["h"] / HT)
        if m0["touch"]:                                  # clipped: the bounding box is not the gun; shrink it and measure again (no slope yet)
            x[3] = x[3] * 1.6
            s["round"] += 1
            s["slope"] = None
            todo.append(i)
            continue
        if s["slope"] is None:
            mp = measure(shots, i + "p", base)
            if mp is None:
                miss.append(i)
                todo.append(i)
                continue
            # cx moves with y, cy with z; both probes were +PR; slopes in box-fraction per world unit at the CURRENT scale
            sy, sz = (mp["cx"] - m0["cx"]) / PR, (mp["cy"] - m0["cy"]) / PR
            if abs(sy) < 1e-4 or abs(sz) < 1e-4:
                miss.append(i)
                todo.append(i)
                continue
            s["slope"] = [sy, sz, s["x"][3]]
        sc = s["slope"][2] / x[3]                         # slope ~ 1 / scale
        sy, sz = s["slope"][0] * sc, s["slope"][1] * sc
        good = abs(ratio - 1) < TOL_S and abs(m0["cx"] - 0.5) < TOL_CX and abs(m0["cy"] - CY) < TOL_CY and not m0["touch"]
        s["last"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m0.items() if k != "aspect_px"}
        if good:
            s["done"] = True
            ok += 1
            continue
        # centre error is corrected in WORLD units (independent of the scale change); the size by the scale
        x[1] += -(m0["cx"] - 0.5) / sy
        x[2] += -(m0["cy"] - CY) / sz
        x[3] = x[3] * ratio
        s["round"] += 1
        todo.append(i)
    json.dump(st, open(STATE, "w"), indent=1)
    print("converged %d / %d ; todo %d ; unmeasured %s" % (ok, len(st), len(todo), miss[:10]))
    jobs(st, out, todo)


def reset(out):
    """keep the solved transforms as the starting point (the box is taller now) but measure everything again"""
    st = json.load(open(STATE))
    for s_ in st.values():
        s_["done"], s_["slope"], s_["round"] = False, None, 0
    json.dump(st, open(STATE, "w"), indent=1)
    jobs(st, out, [i for i in st])


def apply():
    st = json.load(open(STATE))
    L = ["# GENERATED by docs/proposals/armory_redesign_2026-10-18/tools/hero_fit.py from measured renders - the Armory hero box transform per gun", "id\txfmh"]
    for i in sorted(st):
        L.append("%s\t%s" % (i, fmt(st[i]["x"])))
    io.open(OUT, "w", encoding="latin-1", newline="\n").write("\n".join(L) + "\n")
    print("wrote", OUT, len(st), "guns, converged", sum(1 for s in st.values() if s["done"]))


def status():
    st = json.load(open(STATE))
    d = [i for i, s in st.items() if s["done"]]
    print("converged %d / %d" % (len(d), len(st)))
    for i, s in sorted(st.items()):
        if not s["done"]:
            print(i, s.get("last"), s["round"])


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "init":
        init(sys.argv[2])
    elif m == "reset":
        reset(sys.argv[2])
    elif m == "solve":
        solve(sys.argv[2], sys.argv[3])
    elif m == "apply":
        apply()
    else:
        status()
