"""gen_ng_cut.py <stage dir> <out add dir> <mod ui dir> - v1.10.67 the New Game war map's view without the desk props in front of the map.

User (2026-11-09): in the New Game war-map view the lamp, the drawer box, the blue folder, the papers and the legend card sat between
the camera and the map board, over its lower right. The room's bg / chrome were cut for that view long ago (make_newgame3d occ boxes,
atc_bgng / atc_chromeng), but the v1.10.66 desk regroup moved those props into their own atlases (props, blueprint, desk, desk2),
and the New Game scenes took the full models (bug-10647).

For each of those groups this writes atc_<group>ng<k> models: the same skd minus every triangle that lies between the New Game camera
and the map board AND projects onto the board (with a margin) - i.e. exactly what covers the map. Everything outside that cone stays.
Then every New Game scene (hzm_newgame3d.urc, hzm_ng3d_*.urc) is pointed at the ng copies.
"""
import os, re, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

stage, out, ui = sys.argv[1:4]
mdir = os.path.join(out, "models", "menu")
os.makedirs(mdir, exist_ok=True)
CAM = np.array([157.5, 68.1, 74.7])
MAPX = 354.1
MY0, MY1, MZ0, MZ1 = -14.5 - 45.0, 150.8 + 6.0, 3.7 - 30.0, 145.7 + 6.0      # the board (atc_wallmap1) + a margin
GROUPS = ("props", "blueprint", "desk", "desk2")
src = os.path.join(stage, "models", "menu")
renamed = {}
for g in GROUPS:
    k = 1
    while os.path.exists(os.path.join(src, "atc_%s%d.skd" % (g, k))):
        nm = "atc_%s%d" % (g, k)
        d = R.read_skd(open(os.path.join(src, nm + ".skd"), "rb").read())
        cut = 0
        surfs = []
        for s in d["surfaces"]:
            P = np.array([v[3] for v in s["verts"]])
            T = s["tris"]
            if not len(T):
                continue
            c = P[T].mean(1)
            t = (MAPX - CAM[0]) / np.maximum(c[:, 0] - CAM[0], 1e-3)
            hy = CAM[1] + (c[:, 1] - CAM[1]) * t
            hz = CAM[2] + (c[:, 2] - CAM[2]) * t
            cover = (c[:, 0] > CAM[0] + 4.0) & (c[:, 0] < MAPX - 2.0) & (hy > MY0) & (hy < MY1) & (hz > MZ0) & (hz < MZ1)
            # whole pieces, not ragged halves: a welded piece (shared positions) goes if a fifth of it covers the board
            parent = list(range(len(P)))

            def fnd(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i
            key = {}
            for i, pp in enumerate(np.round(P, 2)):
                kk = tuple(pp)
                if kk in key:
                    parent[fnd(i)] = fnd(key[kk])
                else:
                    key[kk] = i
            for t_ in T:
                a_, b_, c_ = fnd(t_[0]), fnd(t_[1]), fnd(t_[2])
                parent[b_] = a_
                parent[fnd(c_)] = a_
            comp = np.array([fnd(t_[0]) for t_ in T])
            # ... and pieces that touch (a phone's body, cradle and dial plate are separate pieces): one object, cut together
            uq = np.unique(comp)
            lo = {cc: P[T[comp == cc]].reshape(-1, 3).min(0) for cc in uq}
            hi = {cc: P[T[comp == cc]].reshape(-1, 3).max(0) for cc in uq}
            obj = {cc: cc for cc in uq}

            def ofd(c0):
                while obj[c0] != c0:
                    c0 = obj[c0]
                return c0
            ul = list(uq)
            for ia in range(len(ul)):
                for ib in range(ia + 1, len(ul)):
                    a1, b1 = ul[ia], ul[ib]
                    if np.all(lo[a1] - 1.0 <= hi[b1]) and np.all(lo[b1] - 1.0 <= hi[a1]):
                        obj[ofd(b1)] = ofd(a1)
            comp = np.array([ofd(cc) for cc in comp])
            for cc in np.unique(comp):
                m_ = comp == cc
                if cover[m_].mean() >= 0.05:
                    cover[m_] = True
                elif cover[m_].any() and m_.sum() > 0:
                    cover[m_] = cover[m_] if cover[m_].mean() >= 0.2 else False
            cut += int(cover.sum())
            keep = T[~cover]
            if len(keep):
                surfs.append((s["name"], keep, s["verts"]))
        ng = "atc_%sng%d" % (g, k)
        tik = open(os.path.join(src, nm + ".tik")).read()
        names = {sn for sn, _, _ in surfs}
        tik = "\n".join(l for l in tik.splitlines() if not (l.strip().startswith("surface ") and l.split()[1] not in names))
        tik = tik.replace("%s.skd" % nm, "%s.skd" % ng).replace("%s.skc" % nm, "%s.skc" % ng)
        open(os.path.join(mdir, ng + ".tik"), "w", newline="\n").write(tik + "\n")
        open(os.path.join(mdir, ng + ".skd"), "wb").write(X.build_skd(d["name"], d["bones"], surfs if surfs else [(d["surfaces"][0]["name"], np.zeros((0, 3), int), d["surfaces"][0]["verts"])]))
        open(os.path.join(mdir, ng + ".skc"), "wb").write(open(os.path.join(src, nm + ".skc"), "rb").read())
        renamed[nm] = ng
        print("%-14s -> %-16s cut %d triangles in front of the map" % (nm, ng, cut))
        k += 1
n = 0
for f in sorted(os.listdir(ui)):
    if not (f == "hzm_newgame3d.urc" or (f.startswith("hzm_ng3d_") and f.endswith(".urc"))):
        continue
    p = os.path.join(ui, f)
    t = open(p, encoding="latin-1", newline="").read()
    t2 = re.sub(r'models/menu/(atc_(?:props|blueprint|desk|desk2)\d+)\.tik', lambda m: "models/menu/%s.tik" % renamed.get(m.group(1), m.group(1)), t)
    if t2 != t:
        open(p, "w", encoding="latin-1", newline="").write(t2)
        n += 1
print("new game scenes pointed at the cut models:", n)
