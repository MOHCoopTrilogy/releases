#!/usr/bin/env python3
"""POC still: top-down + oblique render of a level with textures resolved
(face colour = mean texel under its UVs x baked vertex colour), entities and
navpoints overlaid. Writes PNGs to an out dir (never into the repo).
usage: poc_render.py <image.iso> <level> <outdir>"""
import os, sys, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flcore


def main(img, level, out):
    os.makedirs(out, exist_ok=True)
    L = flcore.Level(flcore.Disc(img), level)
    tri_xy, tri_z, tri_col = [], [], []
    stats = collections.Counter()
    texmean = {}
    for m in L.meshes():
        tex = L.texture(m["tex"]) if m["tex"] else None
        if tex and tex["rgba"]:
            if m["tex"] not in texmean:
                a = np.frombuffer(tex["rgba"], np.uint8).reshape(tex["h"], tex["w"], 4).astype(float) / 255
                texmean[m["tex"]] = a
            arr = texmean[m["tex"]]
        else:
            arr = None
        V = np.array(m["verts"]); C = np.array(m["cols"], float)[:, :3] / 255; UV = np.array(m["uvs"])
        for a, b, c in m["tris"]:
            stats["tex" if arr is not None else "untex"] += 1
            if arr is not None:
                uv = UV[[a, b, c]].mean(0)
                tx = int((uv[0] % 1) * arr.shape[1]) % arr.shape[1]
                ty = int((uv[1] % 1) * arr.shape[0]) % arr.shape[0]
                base = arr[max(0, ty - 2):ty + 3, max(0, tx - 2):tx + 3, :3].reshape(-1, 3).mean(0)
            else:
                base = np.array([1.0, 0.0, 1.0])
            col = np.clip(base * C[[a, b, c]].mean(0) * 2.0, 0, 1)
            tri_xy.append(V[[a, b, c]]); tri_col.append(col)
    T = np.array(tri_xy); Ccol = np.array(tri_col)
    ents = L.entities(); navs = L.navpoints()
    print(f"{level}: tris {sum(stats.values())}  textured {100*stats['tex']/max(1,sum(stats.values())):.1f}%  "
          f"textures {len(texmean)}  entities {len(ents)}  navpoints {len(navs)}")
    fig, ax = plt.subplots(figsize=(22, 16), facecolor="#151515")
    order = np.argsort(T[:, :, 2].mean(1))
    ax.add_collection(PolyCollection(T[order][:, :, :2], facecolors=Ccol[order], edgecolors="none"))
    N = np.array([n["pos"] for n in navs])
    ax.scatter(N[:, 0], N[:, 1], s=2, c="#00e5ff", label="navpoints")
    groups = {"Soldier": "#ff3030", "Allied": "#40ff40", "Health": "#ffffff", "Ammo": "#ffe040",
              "Objective": "#ff40ff", "Trigger": "#ff9000"}
    for g, c in groups.items():
        P = np.array([e["pos"] for e in ents if any(g.lower() in s.lower() for s in e["strs"])] or np.zeros((0, 3)))
        if len(P):
            ax.scatter(P[:, 0], P[:, 1], s=40, c=c, edgecolors="k", label=f"{g} ({len(P)})")
    ax.set_aspect("equal"); ax.autoscale(); ax.axis("off")
    leg = ax.legend(loc="lower left", facecolor="#222", labelcolor="w")
    ax.set_title(f"Frontline {level} - converted top-down (textures resolved, baked light), entities from .bpd", color="w")
    fig.savefig(os.path.join(out, f"{level}_poc_top.png"), dpi=70, bbox_inches="tight")


if __name__ == "__main__":
    main(*sys.argv[1:4])
