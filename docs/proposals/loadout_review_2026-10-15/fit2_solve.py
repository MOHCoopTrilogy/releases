"""fit2_solve.py init <runDir>      boot-1 renders (6 per gun) -> orientation (muzzle right, upright) + first fit for thumb and preview
   fit2_solve.py refine <runDir>   one Newton step from the latest renders of the CURRENT state (fit2_state.json), writes the next job list
Rule (coordinator): scale so the gun fills the frame: scale' = scale * max(w/0.88, h/0.80); centre the BOUNDING BOX (not the pivot) at 0.5/0.5.
Offsets y (screen horizontal) / z (vertical) are world units independent of scale; the view distance ~ scale, so slopes ~ 1/scale."""
import io, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fit2_lib as L

ROOT = r"H:\hzm_archive\loadout_review\fit2"
LATEST = os.path.join(ROOT, "latest")
WT, HT = 0.88, 0.80
S0, PR = 3.0, 8.0
STATE = os.path.join(HERE, "fit2_state.json")
rows = [l.rstrip("\n").split("\t") for l in io.open(r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv", encoding="latin-1") if not l.startswith("#")]
h = rows[0]
W = {r[0]: dict(zip(h, r)) for r in rows[1:]}


def fmt(x, y, z, s, yaw, roll):
    return " ".join("%g" % round(v, 3) for v in (x, y, z, s, 0, yaw, roll))


def jobs_from(state, ids):
    out = []
    for i in ids:
        st = state[i]
        x = fmt(0, st["T"][1], st["T"][2], st["T"][3], st["yaw"], st["roll"])
        out.append([i, W[i]["tik"], "", x, x, i])
    return out


ORI = {"A": (90, 180), "B": (270, 180), "C": (90, 0), "D": (270, 0)}


def init(run):
    """boot-1 -> first fit from orientation A (slopes + centre + scale); jobs for boot 2 = all four orientations at that fit (big masks)."""
    M = L.run(os.path.join(ROOT, run))
    state, flags = {}, {}
    for i in W:
        a, ay, az = M.get(i + "A"), M.get(i + "Ay"), M.get(i + "Az")
        if not (a and ay and az and a["T"] and ay["T"] and az["T"]):
            flags[i] = "missing"
            continue
        st = {"yaw": 90, "roll": 180, "orient": "A", "slope": {}}
        sy = (ay["T"]["cx"] - a["T"]["cx"]) / PR * S0
        sz = (az["T"]["cy"] - a["T"]["cy"]) / PR * S0
        st["slope"]["T"] = [sy, sz]
        b = a["T"]
        y = -(b["cx"] - 0.5) / (sy / S0) if abs(sy) > 1e-5 else 0.0
        z = -(b["cy"] - 0.5) / (sz / S0) if abs(sz) > 1e-5 else 0.0
        st["T"] = [0, y, z, S0 * max(b["w"] / WT, b["h"] / HT)]
        st["W"] = st["T"]
        state[i] = st
    if state:
        import statistics as _st
        med = [_st.median(v["slope"]["T"][0] for v in state.values()), _st.median(v["slope"]["T"][1] for v in state.values())]
        for i in flags:   # no usable mask at S0 (tiny / invisible): start from a zoomed-in guess with the median slopes, refine fixes it
            state[i] = {"yaw": 90, "roll": 180, "orient": "A", "slope": {"T": med}, "T": [0, 0, 0, 1.8], "W": [0, 0, 0, 1.8]}
    json.dump(state, open(STATE, "w"), indent=0)
    jobs = []
    for i, st in state.items():
        for k, (yaw, roll) in ORI.items():
            x = fmt(0, st["T"][1], st["T"][2], st["T"][3], yaw, roll)
            jobs.append([i + k, W[i]["tik"], "", x, x, i])
    json.dump(jobs, open(os.path.join(HERE, "fit2_jobs_next.json"), "w"))
    print("init", len(state), "flags", flags, "jobs", len(jobs))


def orient(run):
    """boot-2 (4 orientations per gun at a fitted scale, plenty of pixels) -> pick upright + muzzle-right, then continue with refine."""
    state = json.load(open(STATE))
    M = L.run(os.path.join(ROOT, run))
    cnt = {k: 0 for k in ORI}
    for i, st in state.items():
        best, bs = "A", -9
        for k in ORI:
            m = (M.get(i + k) or {}).get("T")
            if not m:
                continue
            upright = 1 if m["my"] > (m["y0"] + m["y1"]) / 2 else 0
            sym = abs(m["tl"] - m["tr"]) <= 0.12 * max(m["tl"], m["tr"], 1)
            muzzle = 0.5 if sym else (1 if m["tl"] > m["tr"] else 0)
            sc = upright * 2 + muzzle + (0.2 if k == "A" else 0)
            if sc > bs:
                best, bs = k, sc
        st["orient"] = best
        st["yaw"], st["roll"] = ORI[best]
        cnt[best] += 1
    json.dump(state, open(STATE, "w"), indent=0)
    os.makedirs(LATEST, exist_ok=True)
    for i, st in state.items():
        f = os.path.join(ROOT, run, "fit_%s%s.jpg" % (i, st["orient"]))
        if os.path.isfile(f):
            shutil.copy(f, os.path.join(LATEST, "fit_%s.jpg" % i))
    shutil.copy(os.path.join(ROOT, run, "fit_000.jpg"), os.path.join(LATEST, "fit_000.jpg"))
    print("orientation picks", cnt)
    # now a normal refine step on the chosen orientation's render
    refine(None)


def refine(run):
    state = json.load(open(STATE))
    os.makedirs(LATEST, exist_ok=True)
    if run:
        rd = os.path.join(ROOT, run)
        for f in os.listdir(rd):
            if f.startswith("fit_"):
                shutil.copy(os.path.join(rd, f), os.path.join(LATEST, f))
    M = L.run(LATEST)
    changed, bad = [], {}
    for i, st in state.items():
        m = M.get(i)
        if not m:
            continue
        ch = False
        for v in ("T",):
            b = m[v]
            if not b:
                continue
            x, y, z, s = st[v]
            sy, sz = st["slope"][v][0] / s, st["slope"][v][1] / s
            k = max(b["w"] / WT, b["h"] / HT)
            dy = -(b["cx"] - 0.5) / sy if abs(sy) > 1e-5 else 0
            dz = -(b["cy"] - 0.5) / sz if abs(sz) > 1e-5 else 0
            if L.clipped(b):
                k, dy, dz = max(k, 1.25), 0, 0
            if abs(b["cx"] - 0.5) > 0.02 or abs(b["cy"] - 0.5) > 0.03 or abs(k - 1) > 0.04:
                st[v] = [0, y + dy, z + dz, s * k]
                ch = True
                bad[i + v] = (round(b["cx"], 2), round(b["cy"], 2), round(b["w"], 2), round(b["h"], 2))
        if ch:
            changed.append(i)
    json.dump(state, open(STATE, "w"), indent=0)
    json.dump(jobs_from(state, changed), open(os.path.join(HERE, "fit2_jobs_next.json"), "w"))
    print("refine: changed", len(changed), "of", len(state))
    return state


if __name__ == "__main__":
    {"init": init, "orient": orient, "refine": refine}[sys.argv[1]](sys.argv[2])
