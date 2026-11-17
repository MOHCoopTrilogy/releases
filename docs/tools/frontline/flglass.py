#!/usr/bin/env python3
"""Frontline's window glass (our code; runs inside the converter on the player's PC).

Frontline's glass panes are not in the level meshes: each pane exists only as collision of material 13 (+ the
special-surface bit) in the .cdb chunks, one pane per flag word (the pane's index sits in the high bits, 0x80000d,
0x80080d, ...), and the game draws it itself. Unconverted, every window of the level showed straight through to the
room behind (the Bazar de Varzy shop on 1_1: the inner door and crates instead of the original's dark glass).

panes() groups those triangles into panes (one per chunk + flag word; a pane two chunks both carry is kept once) and
leaves out the panes a drawn card already covers (a mesh triangle of one of `cover_tex`, coplanar within 2u, holding
the pane's centre): that card is the disc's own drawing of the pane. Gate: fl_levels.json "glass" per level.
"""
import math


def _normal(a, b, c):
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(sum(x * x for x in n))
    return None if ln < 1e-9 else tuple(x / ln for x in n)


def _inside(p, t, n, slack=1.0):
    def cr(o, x):
        u = [x[k] - o[k] for k in range(3)]
        v = [p[k] - o[k] for k in range(3)]
        w = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        return sum(w[k] * n[k] for k in range(3))
    s = (cr(t[0], t[1]), cr(t[1], t[2]), cr(t[2], t[0]))
    return all(x >= -slack for x in s) or all(x <= slack for x in s)


def panes(coll, X, cards, mat=13, special=1 << 23):
    """coll: [(chunk name, verts, [(a, b, c, flags)])] (disc); X: disc -> map; cards: drawn triangles (map units) of
    the textures that already draw a pane. Returns ([[tri, ...] per pane], report)."""
    groups = {}
    for name, vs, ts in coll:
        P = None
        for a, b, c, f in ts:
            if (f & 0x7FF) != mat or not (f & special):
                continue
            if P is None:
                P = [X(v) for v in vs]
            groups.setdefault((name, f), []).append((P[a], P[b], P[c]))
    seen = set()
    out = []
    rep = {"groups": len(groups), "panes": 0, "duplicates": 0, "covered": 0}
    cn = [(t, _normal(*t)) for t in cards]
    cn = [(t, n) for t, n in cn if n is not None]
    for key in sorted(groups):
        tris = groups[key]
        sig = tuple(sorted({tuple(round(q) for q in p) for t in tris for p in t}))
        if sig in seen:
            rep["duplicates"] += 1
            continue
        seen.add(sig)
        pts = [p for t in tris for p in t]
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        if any(abs(sum((c[k] - t[0][k]) * n[k] for k in range(3))) <= 2.0 and _inside(c, t, n) for t, n in cn):
            rep["covered"] += 1
            continue
        out.append(tris)
    rep["panes"] = len(out)
    return out, rep


def surface(tris, light):
    """one pane -> (verts, indexes) for flbsp.add_soup: planar st over the pane's own extent (0..1 on its two longest
    in-plane axes), so a pane texture maps once per pane."""
    n = None
    for t in tris:
        n = _normal(*t)
        if n:
            break
    n = n or (0.0, 0.0, 1.0)
    ax = sorted(range(3), key=lambda k: abs(n[k]))[:2]       # the two axes the plane spreads along
    if ax[0] == 2:
        ax = [ax[1], 2]                                       # upright panes: s across, t up
    pts = [p for t in tris for p in t]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    verts, idx = [], []
    for t in tris:
        for p in t:
            s = (p[ax[0]] - lo[ax[0]]) / max(1e-6, hi[ax[0]] - lo[ax[0]])
            tt = 1.0 - (p[ax[1]] - lo[ax[1]]) / max(1e-6, hi[ax[1]] - lo[ax[1]])
            idx.append(len(verts))
            verts.append((tuple(p), (s, tt), n, tuple(light) + (255,)))
    return verts, idx
