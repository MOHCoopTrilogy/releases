"""Grease gun layout probe: per UV island of greaser.skd - 3D area, texel density at 2048, stretch (ratio of the
two scales of the UV map), and which triangles are thrown across the sheet. Writes work/gg_cover.png: sound
triangles filled (one colour per surface, label <surface letter><island>), thrown triangles outlined in red, and
work/gg_probe.json.

    python gg_probe.py
"""
import os, json
import numpy as np
from PIL import Image, ImageDraw
import rplib as L
SKD = "models/weapons/greasegun/greaser.skd"
N = 2048
LET = {"Clip": "C", "bool_mesh": "B", "skin1": "S", "Mesh_MultiAttached4": "E", "Mesh_MultiAttached": "M"}
COL = {"C": (90, 140, 220), "B": (220, 200, 90), "S": (110, 200, 110), "E": (230, 130, 60), "M": (190, 110, 200)}


def tri_stats(s):
    """per triangle: 3D area, uv px area, the two singular values (px per unit) of the 3D->UV map."""
    P = s["pos"][s["tris"]]; U = s["uv"][s["tris"]] * N
    e1 = P[:, 1] - P[:, 0]; e2 = P[:, 2] - P[:, 0]
    n = np.cross(e1, e2); a3 = np.linalg.norm(n, axis=1) / 2
    # local 2D frame of the triangle
    x = e1 / (np.linalg.norm(e1, axis=1, keepdims=True) + 1e-12)
    nn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    y = np.cross(nn, x)
    A = np.stack([np.stack([(e1 * x).sum(1), (e2 * x).sum(1)], 1), np.stack([(e1 * y).sum(1), (e2 * y).sum(1)], 1)], 1)
    B = np.stack([U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]], 2)       # columns = uv edges
    sv = np.zeros((len(P), 2))
    for i in range(len(P)):
        if a3[i] < 1e-9:
            continue
        J = B[i] @ np.linalg.inv(A[i])
        sv[i] = np.linalg.svd(J, compute_uv=False)
    au = np.abs(np.cross(U[:, 1] - U[:, 0], U[:, 2] - U[:, 0])) / 2
    ext = np.maximum(np.ptp(U[..., 0], axis=1), np.ptp(U[..., 1], axis=1)) / N
    return a3, au, sv, ext


def main():
    S = L.load_skd(SKD)
    im = Image.new("RGB", (N, N), (16, 16, 16)); d = ImageDraw.Draw(im)
    rep = {}
    thrown_all = []
    for name, s in S.items():
        a3, au, sv, ext = tri_stats(s)
        ratio = sv[:, 0] / np.maximum(sv[:, 1], 1e-6)
        thrown = (ext > 0.30) & (ratio > 6) | (ratio > 25) & (ext > 0.12)
        for k in range(s["n"]):
            m = s["isl"] == k
            ok = m & ~thrown
            tt = s["tris"][m]
            p = s["pos"][np.unique(tt)]
            row = dict(tris=int(m.sum()), thrown=int((m & thrown).sum()), area=round(float(a3[m].sum()), 1),
                       px_per_unit=[round(float(np.median(sv[ok, 0])), 1), round(float(np.median(sv[ok, 1])), 1)] if ok.any() else None,
                       p0=p.min(0).round(1).tolist(), p1=p.max(0).round(1).tolist(),
                       uv0=s["uv"][np.unique(tt)].min(0).round(3).tolist(), uv1=s["uv"][np.unique(tt)].max(0).round(3).tolist())
            rep["%s%d" % (LET[name], k)] = row
            print("%s%-3d" % (LET[name], k), json.dumps(row))
        for ti, t in enumerate(s["tris"]):
            pts = [tuple(s["uv"][i] * N) for i in t]
            if thrown[ti]:
                thrown_all.append(pts)
            else:
                c = COL[LET[name]]
                kk = int(s["isl"][ti])
                c = tuple(int(np.clip(v + ((kk * 37) % 60) - 30, 0, 255)) for v in c)
                d.polygon(pts, fill=c, outline=(0, 0, 0))
        for k in range(s["n"]):
            tt = s["tris"][(s["isl"] == k) & ~thrown]
            if len(tt):
                c = s["uv"][np.unique(tt)].mean(0) * N
                d.text((c[0] - 10, c[1] - 6), "%s%d" % (LET[name], k), fill=(255, 255, 255))
    for pts in thrown_all:
        d.line(pts + [pts[0]], fill=(255, 40, 40), width=2)
    os.makedirs(L.WORK, exist_ok=True)
    im.resize((1280, 1280), Image.LANCZOS).save(os.path.join(L.WORK, "gg_cover.png"))
    json.dump(rep, open(os.path.join(L.WORK, "gg_probe.json"), "w"), indent=1)
    print("thrown triangles:", len(thrown_all))


if __name__ == "__main__":
    main()
