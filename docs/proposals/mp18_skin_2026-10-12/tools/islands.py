"""UV islands of mp18.skd, per surface: id, triangles, UV box, bone-space box, area-weighted mean normal, and the
texture direction of the gun's long axis (x). Also a labelled island map per surface (evidence/isl_<surface>.png).
usage: python islands.py
Importable: load() -> {surface: dict(uv, pos, nrm, tris, isl (per tri island id), n)}"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import skd
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
EVI = os.path.join(HERE, "..", "evidence")
SKD = os.path.join(MOD, "models/weapons/coop_mp18/mp18.skd")


def load():
    m = skd.read(open(SKD, "rb").read())
    out = {}
    for s in m["surfaces"]:
        uv = np.array([v["uv"] for v in s["verts"]], float)
        pos = np.array([v["pos"] for v in s["verts"]], float)
        nrm = np.array([v["n"] for v in s["verts"]], float)
        tris = np.array(s["tris"], int)
        # union-find over vertices that share a UV position (welds the per-normal splits inside an island)
        key = {}
        par = list(range(len(uv)))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for i, (u, v) in enumerate(uv):
            k = (round(u, 4), round(v, 4))
            if k in key:
                par[find(i)] = find(key[k])
            else:
                key[k] = i
        for t in tris:
            a, b, c = (find(int(x)) for x in t)
            par[b] = a; par[find(c)] = a
        roots = {}
        isl = np.zeros(len(tris), int)
        for ti, t in enumerate(tris):
            r = find(int(t[0]))
            isl[ti] = roots.setdefault(r, len(roots))
        out[s["name"]] = dict(uv=uv, pos=pos, nrm=nrm, tris=tris, isl=isl, n=len(roots))
    return out


def main():
    os.makedirs(EVI, exist_ok=True)
    S = load()
    rep = {}
    for name, s in S.items():
        W = 1024
        im = Image.new("RGB", (W, W), (20, 20, 20)); d = ImageDraw.Draw(im)
        rows = []
        for k in range(s["n"]):
            tt = s["tris"][s["isl"] == k]
            vi = np.unique(tt)
            uv = s["uv"][vi]; p = s["pos"][vi]
            fn = np.cross(s["pos"][tt[:, 1]] - s["pos"][tt[:, 0]], s["pos"][tt[:, 2]] - s["pos"][tt[:, 0]])
            area = np.linalg.norm(fn, axis=1).sum() / 2
            mn = fn.sum(0); mn = mn / (np.linalg.norm(mn) + 1e-9)
            # least squares: uv = A * pos + b ; the image of the x axis is A[:,0]
            X = np.c_[p, np.ones(len(p))]
            A, *_ = np.linalg.lstsq(X, uv, rcond=None)
            dx = A[0]; dz = A[2]; dy = A[1]
            col = tuple(int(c) for c in np.random.RandomState(k * 7 + 3).randint(70, 255, 3))
            for t in tt:
                d.polygon([tuple(s["uv"][i] * W) for i in t], fill=col, outline=(0, 0, 0))
            c = uv.mean(0) * W
            d.text((c[0] - 6, c[1] - 6), str(k), fill=(0, 0, 0))
            rows.append(dict(id=k, tris=len(tt), uv0=uv.min(0).round(3).tolist(), uv1=uv.max(0).round(3).tolist(),
                             p0=p.min(0).round(1).tolist(), p1=p.max(0).round(1).tolist(), area=round(area, 1),
                             n=mn.round(2).tolist(), x_in_uv=(dx * 100).round(2).tolist(),
                             y_in_uv=(dy * 100).round(2).tolist(), z_in_uv=(dz * 100).round(2).tolist()))
            print(name, json.dumps(rows[-1]))
        im.save(os.path.join(EVI, "isl_%s.png" % name))
        rep[name] = rows
    json.dump(rep, open(os.path.join(EVI, "islands.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
