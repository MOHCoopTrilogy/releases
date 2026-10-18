"""fit3.py - gun-fit redo, continuation of fit2_solve.py. Fits BOTH the slot-card thumbnail (T, 92x50) and the inspect preview (W, 152x100).
    fit3.py jobs <out.json> [ids,...]    job list from fit2_state.json (all guns or the given ids)
    fit3.py probe <out.json>             W-view slope probes (8 guns: base, y+PR, z+PR)
    fit3.py slopew <runDir>              derive the W slopes from the probe run (median, per scale), store in the state
    fit3.py refine <runDir> [T|W|TW]     one Newton step per view from the renders in runDir; rewrites jobs for guns that moved
    fit3.py apply                        write the state into docs/tools/loadout_weapons.tsv (xfm = W, xfmt = T)
Rule (coordinator): scale' = scale * max(w/0.88, h/0.80); centre the BOUNDING BOX at 0.5/0.5; clipped -> shrink >=25% and re-measure."""
import io, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fit2_lib as L

ROOT = r"G:\claude_scratch_archive\loadout_review\fit2"
STATE = os.path.join(HERE, "fit2_state.json")
TSV = r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv"
WT, HT = 0.88, 0.80
PR = 4.0
rows = [l.rstrip("\n").split("\t") for l in io.open(TSV, encoding="utf-8") if not l.startswith("#")]
h = rows[0]
W = {r[0]: dict(zip(h, r)) for r in rows[1:]}
PROBE_IDS = ["01", "05", "24", "36", "44", "48", "53", "64"]


def fmt(x, y, z, s, yaw, roll):
    return " ".join("%g" % round(v, 3) for v in (x, y, z, s, 0, yaw, roll))


def xf(st, v, dy=0.0, dz=0.0):
    x, y, z, s = st[v]
    return fmt(x, y + dy, z + dz, s, st["yaw"], st["roll"])


def jobs(out, ids=None):
    st = json.load(open(STATE))
    ids = ids or sorted(st)
    J = [[i, W[i]["tik"], "", xf(st[i], "T"), xf(st[i], "W"), i] for i in ids]
    json.dump(J, open(out, "w"))
    print("jobs", len(J), "->", out)


def probe(out):
    st = json.load(open(STATE))
    J = []
    for i in PROBE_IDS:
        s = st[i]
        J.append([i + "0", W[i]["tik"], "", xf(s, "T"), xf(s, "W"), i])
        J.append([i + "y", W[i]["tik"], "", xf(s, "T"), xf(s, "W", dy=PR), i])
        J.append([i + "z", W[i]["tik"], "", xf(s, "T"), xf(s, "W", dz=PR), i])
    json.dump(J, open(out, "w"))
    print("probe jobs", len(J))


def slopew(run):
    st = json.load(open(STATE))
    M = L.run(os.path.join(ROOT, run), ("T", "W"))
    sy, sz = [], []
    for i in PROBE_IDS:
        a, b, c = M.get(i + "0"), M.get(i + "y"), M.get(i + "z")
        if not (a and b and c and a["W"] and b["W"] and c["W"]):
            print("probe miss", i)
            continue
        s = st[i]["W"][3]
        sy.append((b["W"]["cx"] - a["W"]["cx"]) / PR * s)
        sz.append((c["W"]["cy"] - a["W"]["cy"]) / PR * s)
        print(i, round(sy[-1], 4), round(sz[-1], 4), "T slope", [round(v, 4) for v in st[i]["slope"]["T"]], "(T at its own scale)")
    sy.sort(); sz.sort()
    med = [sy[len(sy) // 2], sz[len(sz) // 2]]
    for i in st:
        st[i]["slope"]["W"] = med
    json.dump(st, open(STATE, "w"), indent=0)
    print("W slope", med)


def refine(run, views="TW"):
    st = json.load(open(STATE))
    d = os.path.join(ROOT, run)
    M = L.run(d, ("T", "W"))
    changed, rep = [], {}
    for i, s in st.items():
        m = M.get(i)
        if not m:
            continue
        ch = False
        for v in views:
            b = m[v]
            if not b:
                # nothing visible: zoom in around the centre
                s[v][3] *= 0.6
                ch = True
                rep[i + v] = "none"
                continue
            x, y, z, sc = s[v]
            sy, sz = s["slope"][v][0] / sc, s["slope"][v][1] / sc
            k = max(b["w"] / WT, b["h"] / HT)
            dy = -(b["cx"] - 0.5) / sy if abs(sy) > 1e-5 else 0
            dz = -(b["cy"] - 0.5) / sz if abs(sz) > 1e-5 else 0
            if L.clipped(b):
                k, dy, dz = max(k, 1.25), 0, 0
            rep[i + v] = (round(b["cx"], 2), round(b["cy"], 2), round(b["w"], 2), round(b["h"], 2))
            if abs(b["cx"] - 0.5) > 0.02 or abs(b["cy"] - 0.5) > 0.03 or abs(k - 1) > 0.04:
                s[v] = [0, y + dy, z + dz, sc * k]
                ch = True
            else:
                rep[i + v] = rep[i + v] + ("ok",)
        if ch:
            changed.append(i)
    json.dump(st, open(STATE, "w"), indent=0)
    nxt = os.path.join(HERE, "fit2_jobs_next.json")
    J = [[i, W[i]["tik"], "", xf(st[i], "T"), xf(st[i], "W"), i] for i in changed]
    json.dump(J, open(nxt, "w"))
    nok = sum(1 for v in rep.values() if isinstance(v, tuple) and v[-1] == "ok")
    print("refine: changed", len(changed), "of", len(st), "views ok", nok, "of", len(rep))
    return changed


PRJ = os.path.join(HERE, "fit3_pr.json")


def probe3(out, ids=None):
    """3 shots per gun: base, y-shifted, z-shifted. Shift per gun/view so the move is ~0.12 of the rect (slope guess from the state)."""
    st = json.load(open(STATE))
    ids = ids or sorted(st)
    J, PRs = [], {}
    for i in ids:
        s = st[i]
        pr = {}
        for v in "TW":
            g = s["slope"].get(v) or s["slope"]["T"]
            pr[v] = [min(12.0, max(0.3, 0.12 * s[v][3] / max(abs(g[0]), 0.012))), min(12.0, max(0.3, 0.12 * s[v][3] / max(abs(g[1]), 0.012)))]
        PRs[i] = pr
        J.append([i + "0", W[i]["tik"], "", xf(s, "T"), xf(s, "W"), i])
        J.append([i + "y", W[i]["tik"], "", xf(s, "T", dy=pr["T"][0]), xf(s, "W", dy=pr["W"][0]), i])
        J.append([i + "z", W[i]["tik"], "", xf(s, "T", dz=pr["T"][1]), xf(s, "W", dz=pr["W"][1]), i])
    json.dump(J, open(out, "w"))
    json.dump(PRs, open(PRJ, "w"))
    print("probe3 jobs", len(J))


def refine3(run, views="TW"):
    st = json.load(open(STATE))
    PRs = json.load(open(PRJ))
    M = L.run(os.path.join(ROOT, run), ("T", "W"))
    ok, rep = 0, {}
    for i, s in st.items():
        m0, my, mz = M.get(i + "0"), M.get(i + "y"), M.get(i + "z")
        if not m0:
            continue
        for v in views:
            b = m0[v]
            sc = s[v][3]
            if not b:
                s[v][3] *= 1.6
                rep[i + v] = "none"
                continue
            by, bz = (my or {}).get(v), (mz or {}).get(v)
            sl = list(s["slope"].get(v) or s["slope"]["T"])
            if by and not L.clipped(by) and not L.clipped(b):
                d = (by["cx"] - b["cx"]) / PRs[i][v][0] * sc
                if abs(d) > 0.004:
                    sl[0] = d
            if bz and not L.clipped(bz) and not L.clipped(b):
                d = (bz["cy"] - b["cy"]) / PRs[i][v][1] * sc
                if abs(d) > 0.004:
                    sl[1] = d
            s["slope"][v] = sl
            x, y, z, _ = s[v]
            sy, sz = sl[0] / sc, sl[1] / sc
            k = max(b["w"] / WT, b["h"] / HT)  # apparent size ~ 1/scale (r1-r7: the "grows with scale" reading was a clipped mask)
            dy = -(b["cx"] - 0.5) / sy if abs(sy) > 1e-5 else 0
            dz = -(b["cy"] - 0.5) / sz if abs(sz) > 1e-5 else 0
            if L.clipped(b):
                k, dy, dz = max(k, 1.3), 0, 0
            conv = abs(b["cx"] - 0.5) <= 0.02 and abs(b["cy"] - 0.5) <= 0.03 and abs(k - 1) <= 0.04
            rep[i + v] = (round(b["cx"], 2), round(b["cy"], 2), round(b["w"], 2), round(b["h"], 2), "ok" if conv else "")
            if conv:
                ok += 1
            else:
                s[v] = [0, y + dy, z + dz, sc * k]
    json.dump(st, open(STATE, "w"), indent=0)
    bad = {k: v for k, v in rep.items() if not (isinstance(v, tuple) and v[-1] == "ok")}
    print("refine3: converged views", ok, "of", len(rep), "| not converged:", len(bad))
    print(" ".join("%s%s" % (k, v[:4] if isinstance(v, tuple) else v) for k, v in list(bad.items())[:24]))


ORI = {"A": (90, 180), "B": (270, 180), "C": (90, 0), "D": (270, 0)}
SYM = {"64", "65", "66", "67", "68", "69"}   # grenades: no meaningful muzzle/up


def orient_jobs(out):
    st = json.load(open(STATE))
    J = []
    for i, s in sorted(st.items()):
        for k, (yaw, roll) in ORI.items():
            a = dict(s); a["yaw"], a["roll"] = yaw, roll
            J.append([i + k, W[i]["tik"], "", xf(a, "T"), xf(a, "W"), i])
    json.dump(J, open(out, "w"))
    print("orient jobs", len(J))


def _prof(img, base):
    import numpy as np
    m = L.mask(img, base)
    ys, xs = np.nonzero(m)
    if len(xs) < 30:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    Hh = y1 - y0
    cols = m[:, x0:x1]
    top = np.array([np.nonzero(c)[0].min() if c.any() else np.nan for c in cols.T])
    bot = np.array([np.nonzero(c)[0].max() if c.any() else np.nan for c in cols.T])
    mid = (top + bot) / 2
    n = len(mid)
    ax = np.nanmedian(mid[n // 4: 3 * n // 4])
    up = ax - np.nanmin(top)
    down = np.nanmax(bot) - ax
    my = ys.mean()
    q = max(1, n // 4)
    cm = cols.sum(axis=0)
    tl, tr = cm[:q].mean(), cm[-q:].mean()
    return dict(u=((down - up) / Hh) + 0.5 * ((my - ax) / Hh), m=(tl - tr) / max(tl + tr, 1), n=int(m.sum()))


def orient(run):
    st = json.load(open(STATE))
    d = os.path.join(ROOT, run)
    base = L.load(os.path.join(d, "fit_000.jpg"), "T")
    flips = []
    for i, s in st.items():
        if i in SYM:
            continue
        P = {k: _prof(L.load(os.path.join(d, "fit_%s%s.jpg" % (i, k)), "T"), base) for k in ORI}
        if not all(P.values()):
            print("orient: unusable", i, {k: bool(v) for k, v in P.items()})
            continue
        # roll: 0 vs 180 at the same yaw -> pick higher u (hangs below); yaw: 90 vs 270 -> pick higher m (thick end left = muzzle right)
        ur = {r: (P["C" if r == 0 else "A"]["u"] + P["D" if r == 0 else "B"]["u"]) / 2 for r in (0, 180)}
        my = {y: (P["C" if y == 90 else "D"]["m"] + P["A" if y == 90 else "B"]["m"]) / 2 for y in (90, 270)}
        roll = 0 if ur[0] >= ur[180] else 180
        yaw = 90 if my[90] >= my[270] else 270
        conf = (round(abs(ur[0] - ur[180]), 2), round(abs(my[90] - my[270]), 2))
        if (yaw, roll) != (s["yaw"], s["roll"]):
            flips.append((i, (s["yaw"], s["roll"]), (yaw, roll), conf))
            for v in "TW":
                if yaw != s["yaw"]:
                    s[v][1] = -s[v][1]
                if roll != s["roll"]:
                    s[v][2] = -s[v][2]
            s["yaw"], s["roll"] = yaw, roll
        s["oconf"] = conf
    json.dump(st, open(STATE, "w"), indent=0)
    print("orientation flips:", len(flips))
    for f in flips:
        print(" ", f)
    low = sorted((v["oconf"], i) for i, v in st.items() if "oconf" in v)[:12]
    print("lowest confidence (u,m):", low)


def apply():
    st = json.load(open(STATE))
    lines = io.open(TSV, encoding="utf-8").read().split("\n")
    out = []
    hdr_done = False
    for ln in lines:
        if ln.startswith("id\t"):
            if "xfmt" not in ln.split("\t"):
                ln = ln + "\txfmt"
            hdr_done = True
            out.append(ln)
            continue
        if not hdr_done or not ln.strip() or ln.startswith("#"):
            out.append(ln)
            continue
        c = ln.split("\t")
        i = c[0]
        if i in st:
            c[3] = xf(st[i], "T")   # inspect preview widget is dormant in the stock menu (coop_loPvC*=0): not fitted, shares the thumb fit
            while len(c) < 18:
                c.append("")
            c[17] = xf(st[i], "T")
        out.append("\t".join(c))
    io.open(TSV, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("applied", len(st))


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "jobs":
        jobs(a[2], a[3].split(",") if len(a) > 3 else None)
    elif a[1] == "probe":
        probe(a[2])
    elif a[1] == "ojobs":
        orient_jobs(a[2])
    elif a[1] == "orient":
        orient(a[2])
    elif a[1] == "probe3":
        probe3(a[2], a[3].split(",") if len(a) > 3 else None)
    elif a[1] == "refine3":
        refine3(a[2], a[3] if len(a) > 3 else "TW")
    elif a[1] == "slopew":
        slopew(a[2])
    elif a[1] == "refine":
        refine(a[2], a[3] if len(a) > 3 else "TW")
    elif a[1] == "apply":
        apply()
