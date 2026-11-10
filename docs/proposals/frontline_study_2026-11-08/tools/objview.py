#!/usr/bin/env python3
"""Quick-look renderer for cpt2obj output: top-down + oblique views, faces
shaded by their baked vertex colour. Our own code; numpy + matplotlib.
usage: objview.py <in.obj> <out.png> [elev azim]
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def load(fn):
    V, C, F = [], [], []
    for line in open(fn):
        if line.startswith("v "):
            t = line.split()
            V.append([float(t[1]), float(t[2]), float(t[3])])
            C.append([float(t[4]), float(t[5]), float(t[6])] if len(t) > 6 else [.7, .7, .7])
        elif line.startswith("f "):
            F.append([int(s.split("/")[0]) - 1 for s in line.split()[1:4]])
    return np.array(V), np.array(C), np.array(F)


def view(ax, V, C, F, R, title):
    P = V @ R.T
    tri = P[F]
    depth = tri[:, :, 2].mean(1)
    order = np.argsort(depth)
    col = np.clip(C[F].mean(1), 0, 1)
    pc = PolyCollection(tri[order][:, :, :2], facecolors=col[order], edgecolors="none")
    ax.add_collection(pc)
    ax.set_xlim(P[:, 0].min(), P[:, 0].max())
    ax.set_ylim(P[:, 1].min(), P[:, 1].max())
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.axis("off")


def rot(elev, azim):
    a, e = np.radians(azim), np.radians(elev)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return Rx @ Ry


def main(a):
    V, C, F = load(a[1])
    elev = float(a[3]) if len(a) > 3 else 35
    azim = float(a[4]) if len(a) > 4 else 30
    fig, axs = plt.subplots(1, 2, figsize=(20, 10), facecolor="#202020")
    # OBJ is Y-up; top-down = look down -Y
    top = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    view(axs[0], V, C, F, top, f"top-down  {len(F)} tris")
    view(axs[1], V, C, F, rot(elev, azim) @ np.diag([1, 1, 1]), f"oblique e{elev} a{azim}")
    for ax in axs:
        ax.title.set_color("w")
    fig.savefig(a[2], dpi=90, bbox_inches="tight")


if __name__ == "__main__":
    main(sys.argv)
