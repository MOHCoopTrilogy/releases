"""gen_wallpins70.py <base menus pak> <out add dir> - v1.10.70: the attic's decorative push-pins come off the war map.

The attic blend came with ~40 chrome push-pin heads stuck into its wall map at random places (objects pin<N> / pinhead<N>, baked into
atc_chrome1 and the New Game cut atc_chromeng1). ng_bake.py has always left them out of the wall bake (no baked shadows), but the
models kept drawing them - over the old map they read as stray markers, and over the widened map (v1.10.70) they sit across the
U.S.S.R. where nothing happened. The map's real pins are the mission pins drawn into the map art (warmap.py) and the own-disc pins
(scene labels, make_ng3campaigns.py), so the decorative ones are cut: every triangle of the chrome models whose centre lies in the
slab in front of the map board (game x 352.4..354.05) inside the board's rectangle, taken by whole welded pieces under 3.6 u.
Nothing else is in that slab
(audited 2026-11-10: the heads in atc_chrome1, the
heads + shafts again in the desk groups atc_desk3-5 / atc_deskng3-5 - every welded piece in the slab is a pin under 3.6 u). Same writer as gen_ng_cut.py (skx.build_skd, tik surfaces of
fully emptied surfaces dropped)."""
import os, sys, zipfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

pak, out = sys.argv[1:3]
mdir = os.path.join(out, "models", "menu")
os.makedirs(mdir, exist_ok=True)
X0, X1, Y0, Y1, Z0, Z1 = 352.4, 354.05, -14.5, 150.8, 3.7, 145.7         # the slab in front of atc_wallmap1's board
PIN = 3.6                                                                  # a pin: a welded piece no wider than this (u)
MODELS = ("atc_chrome1", "atc_chromeng1", "atc_desk3", "atc_desk4", "atc_desk5", "atc_deskng3", "atc_deskng4", "atc_deskng5")


def pieces(P, T):
    """welded pieces (shared positions) of a surface: a component id per triangle"""
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
        a_ = fnd(t_[0])
        parent[fnd(t_[1])] = a_
        parent[fnd(t_[2])] = a_
    return np.array([fnd(t_[0]) for t_ in T])


z = zipfile.ZipFile(pak)
for nm in MODELS:
    if "models/menu/%s.skd" % nm not in z.namelist():
        continue
    d = R.read_skd(z.read("models/menu/%s.skd" % nm))
    surfs, cut, kept_big = [], 0, 0
    for s in d["surfaces"]:
        T = np.asarray(s["tris"])
        if not len(T):
            continue
        P = np.array([v[3] for v in s["verts"]])
        c = P[T].mean(1)
        slab = (c[:, 0] > X0) & (c[:, 0] < X1) & (c[:, 1] > Y0) & (c[:, 1] < Y1) & (c[:, 2] > Z0) & (c[:, 2] < Z1)
        pin = np.zeros(len(T), bool)
        if slab.any():
            comp = pieces(P, T)
            for cc in np.unique(comp[slab]):
                m_ = comp == cc
                ext = np.ptp(P[T[m_]].reshape(-1, 3), axis=0)
                if slab[m_].mean() >= 0.5 and ext.max() <= PIN:          # (its shaft runs on into the board)
                    pin |= m_
                else:
                    kept_big += int(m_.sum())
        cut += int(pin.sum())
        if (~pin).any():
            surfs.append((s["name"], T[~pin], s["verts"]))
    if not cut:
        print("%s: no push-pins" % nm)
        continue
    names = {sn for sn, _, _ in surfs}
    tik = z.read("models/menu/%s.tik" % nm).decode("latin-1")
    tik = "\n".join(l for l in tik.splitlines() if not (l.strip().startswith("surface ") and l.split()[1] not in names))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(tik + "\n")
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(d["name"], d["bones"], surfs))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(z.read("models/menu/%s.skc" % nm))
    print("%s: %d push-pin triangles cut (%d slab triangles of larger pieces kept), %d surfaces" % (nm, cut, kept_big, len(surfs)))
