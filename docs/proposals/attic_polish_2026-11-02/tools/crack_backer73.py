"""crack_backer73.py <menus pak> <add dir> <mod ui dir> <poses.json> <scene> <sweep.json> <model name> - v1.10.73: back the hairline
cracks a baked room leaks through (the attic's wing corner: the user's "white sliver" past the briefing-door room).

For every frame the sweep (voidraster.py --out) flagged, the void pixels' rays are re-cast at 4x density; each confirmed escaping ray
is followed to the point where it passes closest to the room's own surfaces (where it slips out between two of them). Those
points are clustered (30 u); each cluster gets a backing patch just outside, facing back along the mean ray, 1.6x the cluster's
spread (>= 16 u), textured with the texel of the room surface nearest to it - from inside, through the crack, it reads as that
wall. Weather layers (hzm_wx_*) never count as surfaces.
"""
import json, os, re, sys, zipfile
import numpy as np
from scipy.spatial import cKDTree      # before the tools path: tools/queue.py would shadow the stdlib queue scipy imports

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)                  # (tools/queue.py would shadow the stdlib queue scipy imports)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import voidtrace as V  # noqa: E402
import voidraster as VR  # noqa: E402
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

if sys.argv[1] == "--from":
    # rebuild the backer model from a saved patch list (crack_backer73.json beside this tool): no sweep needed
    _, _, pak, add, jf, NAME = sys.argv[:6]
    PATCHES = json.load(open(jf))[NAME]
else:
    pak, add, ui, poses_f, scene, sweep, NAME = sys.argv[1:8]
    PATCHES = None
if PATCHES is None:
    src = V.Src(pak, add)
    models = V.scene_models(ui, scene)
    T, W = V.load_tris(src, models)
    Troom = T[~W]
    # the room's uvs + shaders (shell models only: the backers borrow a wall's texel)
    Z = zipfile.ZipFile(pak)
    STRI, SUV, SSH = [], [], []
    for path, (ox, oy, oz, yaw) in models:
        nm = os.path.basename(path)[:-4]
        if not nm.startswith(("atc_bg", "hub_bg")):
            continue
        tik = Z.read(path).decode("latin-1")
        shmap = dict(re.findall(r"(?m)^\s*surface (\S+) shader (\S+)", tik))
        m = R.read_skd(Z.read("models/menu/%s.skd" % nm))
        for s in m["surfaces"]:
            P = np.array([v[3] for v in s["verts"]], float)
            U = np.array([v[1] for v in s["verts"]], float)
            STRI.append(P[s["tris"]])
            SUV.append(U[s["tris"]].mean(1))
            SSH += [shmap.get(s["name"], "")] * len(s["tris"])
    STRI, SUV, SSH = np.concatenate(STRI), np.concatenate(SUV), np.array(SSH)
    SC = STRI.mean(1)
    C = Troom.mean(1)
    KD = cKDTree(C)
    VR.TALL[0], VR.TALL[1] = T, W

    pts, dirs = [], []
    rep = [r for r in json.load(open(sweep)) if r["void"]]
    asp = {"16:9": 16 / 9, "21:9": 2.39, "4:3": 4 / 3}
    for r in rep:
        pose, a = r["pose"], asp[r["aspect"]]
        void = VR.frame(Troom.astype(float), T[W].astype(float), pose, a, 192)
        c = VR.cam(pose, a, 192)
        o, f, rr, u, tx, ty, w, h = c
        ys, xs = np.nonzero(void)
        for y0, x0 in zip(ys, xs):
            for dy in (0.25, 0.75):
                for dx in (0.25, 0.75):
                    xn, yn = (x0 + dx) / w * 2 - 1, 1 - (y0 + dy) / h * 2
                    d = f + xn * tx * rr + yn * ty * u
                    d = d / np.linalg.norm(d)
                    t, j = V.first_hit(o.astype(np.float32), d[None].astype(np.float32), T)
                    if np.isfinite(t[0]) and not W[j[0]]:
                        continue
                    if np.isfinite(t[0]) and V.through_opening(o.astype(np.float32), d[None].astype(np.float32), t)[0]:
                        continue
                    ss = np.arange(10, 900, 3.0)
                    q = o[None, :] + d[None, :] * ss[:, None]
                    dist, _ = KD.query(q)
                    k = int(dist.argmin())
                    pts.append(q[k])
                    dirs.append(d)
    pts, dirs = np.array(pts), np.array(dirs)
    print("%s: %d escaping rays from %d frames" % (scene, len(pts), len(rep)))
    if not len(pts):
        raise SystemExit(0)
    # cluster
    lab = -np.ones(len(pts), int)
    nc = 0
    for i in range(len(pts)):
        if lab[i] >= 0:
            continue
        lab[(np.linalg.norm(pts - pts[i], axis=1) < 30) & (lab < 0)] = nc
        nc += 1
    PATCHES = []
    for k in range(nc):
        P, D = pts[lab == k], dirs[lab == k]
        cpt, dm = P.mean(0), D.mean(0)
        dm /= np.linalg.norm(dm)
        spread = max(16.0, 1.6 * 2 * np.linalg.norm(P - cpt, axis=1).max())
        cen = cpt + dm * 6.0
        a1 = np.cross(dm, [0, 0, 1.0])
        if np.linalg.norm(a1) < 1e-3:
            a1 = np.array([1.0, 0, 0])
        a1 /= np.linalg.norm(a1)
        a2 = np.cross(a1, dm)
        j = int(np.linalg.norm(SC - cpt, axis=1).argmin())
        sh, uv = SSH[j], tuple(map(float, SUV[j]))
        PATCHES.append(dict(centre=cen.round(3).tolist(), normal=dm.round(5).tolist(), a1=a1.round(5).tolist(), a2=a2.round(5).tolist(),
                            size=round(float(spread), 2), shader=str(sh), uv=[round(v, 5) for v in uv], rays=int(len(P))))
        print("  crack %d: %d rays at %s, patch %.0f u, texel of %s" % (k, len(P), cpt.round(1).tolist(), spread, sh))
    jf = os.path.join(HERE, "crack_backer73.json")
    allp = json.load(open(jf)) if os.path.exists(jf) else {}
    allp[NAME] = PATCHES
    json.dump(allp, open(jf, "w"), indent=1)
parts = {}
for pt in PATCHES:
    cen, a1, a2, h_ = np.array(pt["centre"]), np.array(pt["a1"]), np.array(pt["a2"]), pt["size"] / 2
    Q = [cen - a1 * h_ - a2 * h_, cen + a1 * h_ - a2 * h_, cen + a1 * h_ + a2 * h_, cen - a1 * h_ + a2 * h_]
    for tr in ((0, 1, 2), (0, 2, 3)):
        parts.setdefault(pt["shader"], []).append([(0, tuple(map(float, Q[i])), tuple(pt["normal"]), tuple(pt["uv"])) for i in tr])
mdir = os.path.join(add, "models", "menu")
os.makedirs(mdir, exist_ok=True)
surfs, sl = [], []
for i, (sh, corners) in enumerate(sorted(parts.items())):
    ss = X.split_surfaces("k%d_" % i, corners)
    surfs += ss
    sl += ["\tsurface %s shader %s" % (q[0], sh) for q in ss]
Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
open(os.path.join(mdir, NAME + ".skd"), "wb").write(X.build_skd(NAME, [("root", "worldbone")], surfs))
open(os.path.join(mdir, NAME + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                 (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                 float(np.linalg.norm(Pv, axis=1).max()) + 1))
open(os.path.join(mdir, NAME + ".tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (NAME, "\n".join(sl), NAME))
print("%s: %d patches" % (NAME, len(PATCHES)))
