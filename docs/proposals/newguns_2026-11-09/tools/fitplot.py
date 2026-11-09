"""side/top silhouettes: the shipped donor (red) under the new gun (black outline fill), gun frame. python fitplot.py <donor pkl> <new npz-in-gun-frame> <out.png>"""
import sys, pickle, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def draw(ax, tris2d, col, alpha):
    ax.add_collection(PolyCollection(tris2d, facecolors=col, edgecolors='none', alpha=alpha))


def plot(donor, new, out, marks=()):
    fig, ax = plt.subplots(2, 1, figsize=(18, 10))
    for k, (i, j, sg, title) in enumerate(((0, 2, -1, 'side (up)'), (0, 1, 1, 'top (+y right)'))):
        for nm, P, T in donor:
            draw(ax[k], np.stack([P[T][:, :, i], sg * P[T][:, :, j]], -1), 'red', 0.35)
        draw(ax[k], np.stack([new[:, :, i], sg * new[:, :, j]], -1), 'black', 0.35)
        for (lab, p) in marks:
            ax[k].plot(p[i], sg * p[j], 'b+', ms=14); ax[k].annotate(lab, (p[i], sg * p[j]), color='b')
        ax[k].autoscale(); ax[k].set_aspect('equal'); ax[k].grid(True); ax[k].set_title(title + ': red = shipped, black = new')
    plt.tight_layout(); plt.savefig(out, dpi=70); plt.close(fig)
