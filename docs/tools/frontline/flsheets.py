#!/usr/bin/env python3
"""Blocked only by what you can see (our code; runs inside the converter on the player's PC).

Frontline wraps much of its town in a smooth, player-only collision layer (material 3 + the special-surface bit):
vertical sheets standing 16-128u in front of facades, rubble, carts and fences, often the ONLY collision those drawn
things have. Its player stopped at the sheet; in MOHAA, first person, that reads as an invisible wall an arm's length
before every wall (walk audit: 664 of the invisible contacts on the original's routes).

User rule (2026-11-10): you are only ever blocked by something you can see. So:
  1. every vertical sheet of the material is dropped, EXCEPT the ones on our reviewed keep list
     (fl_levels.json "clip_keep": [[chunk, triangle], ...] - indexes into the player's disc), which bound the playable
     area where nothing is drawn (side streets closed off, the level's edge): those stay, and flconvert draws a
     visible edge for them;
  2. the drawn geometry the dropped sheets stood in front of gets collision of its own: every drawn triangle near a
     dropped sheet, in the body band above its floor, that no remaining collision already covers, becomes a thin
     collision slab exactly on the drawn surface - the wall is where the player sees it.
Walkable sheets (Frontline's ramps over stairs and rubble, slope under 45 deg) and the tree / post columns (flfit)
are left alone.

The keep list is curated at dev time with the walk audit (docs/tools/byoaudit/geoaudit.py --cells): drop
everything, see where the walker gets out of the level, keep the sheets on that frontier, repeat
(docs/proposals/flpolish_2026-11-10/sheetiter.py writes nothing but the list).
"""
import math

import flgeom


def _normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    if ln < 1e-9:
        return None
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def _cen(t):
    return tuple((t[0][k] + t[1][k] + t[2][k]) / 3 for k in range(3))


def edges(kept, ground, height=64.0, snap=16.0):
    """The visible edge for the sheets that stay (they bound the level where nothing is drawn): one upright quad per
    distinct foot line, `height` tall from the floor at each end - flconvert draws it as a barbed-wire fence.
    Returns [((x0, y0, z0), (x1, y1, z1))] foot segments (deduplicated: a sheet is many stacked triangles)."""
    seen = set()
    out = []
    for t in kept:
        n = _normal(*t)
        if n is None:
            continue
        hd = math.hypot(n[0], n[1]) or 1.0
        tx, ty = -n[1] / hd, n[0] / hd
        proj = [(v[0] * tx + v[1] * ty, v) for v in t]
        a = min(proj)[1]
        b = max(proj)[1]
        zf = min(v[2] for v in t)
        key = tuple(sorted(((round(a[0] / snap), round(a[1] / snap)), (round(b[0] / snap), round(b[1] / snap)))))
        if key in seen or math.hypot(b[0] - a[0], b[1] - a[1]) < 8:
            continue
        seen.add(key)
        # the sheets run from well below the ground to 450u up: look for the floor under the whole sheet, not just
        # around its buried foot (most kept sheets got no fence that way)
        zt = max(v[2] for v in t)

        def low_floor(x, y):
            # the LOWEST floor from the buried foot upward: the highest one under the top was often a roof or an
            # upper storey, and the fence hung there instead of on the street
            h = zf + 48.0
            while h <= zt + 8.0:
                g = ground(x, y, h, zf - 256)
                if g is not None:
                    return g
                h += 48.0
            return None
        za = low_floor(a[0], a[1])
        zb = low_floor(b[0], b[1])
        if za is None and zb is None:
            continue
        za = zb if za is None else za
        zb = za if zb is None else zb
        out.append(((a[0], a[1], za), (b[0], b[1], zb)))
    return out


def replace(tris, tags, ids, is_sheet, rtris, keep=(), near=160.0, band=160.0, cover=6.0):
    """tris/tags/ids: wound collision, flag words, disc ids ((chunk, index) or None for our own collision).
    Returns (tris, tags, added_tris, report). added_tris carry no tag (the caller tags them)."""
    keep = {tuple(k) for k in keep}
    out_t, out_f, dropped, kept = [], [], [], []
    rep = {"sheets": 0, "dropped": 0, "kept": 0, "drawn_tris_near": 0, "drawn_tris_added": 0}
    for t, f, i in zip(tris, tags, ids):
        if is_sheet(f):
            n = _normal(*t)
            # every sheet a player cannot walk on (MOHAA walks up to 0.7): steep ones block exactly like walls
            if n is not None and abs(n[2]) < 0.7:
                rep["sheets"] += 1
                if i is not None and tuple(i) in keep:
                    rep["kept"] += 1
                    kept.append(t)
                else:
                    dropped.append((t, i))
                    rep["dropped"] += 1
                    continue
        out_t.append(t)
        out_f.append(f)
    rep["kept_tris"] = kept
    if not dropped:
        rep["dropped_list"] = []
        return out_t, out_f, [], rep
    # floors, for the body band (from the collision that stays)
    G = flgeom.TriGrid(out_t)
    D = flgeom.TriGrid([t for t, _i in dropped], cell=192.0)
    added = []
    h = (cover, cover, cover)
    for r in rtris:
        c = _cen(r)
        # near a dropped sheet (its footprint, in plan and height)
        cand = D.near(c[0], c[1], near)
        if not cand:
            continue
        zlo = min(min(v[2] for v in D.tris[j]) for j in cand)
        zhi = max(max(v[2] for v in D.tris[j]) for j in cand)
        if not (zlo - 32 <= min(v[2] for v in r) <= zhi):
            continue
        n = _normal(*r)
        if n is None or abs(n[2]) > 0.7:
            continue                                        # drawn floors keep the collision they have
        g = G.ground(c[0], c[1], c[2] + 8, c[2] - 512)
        base = g if g is not None else zlo
        if min(v[2] for v in r) > base + band:
            continue                                        # above anyone's head: eaves, upper storeys
        rep["drawn_tris_near"] += 1
        # already collides? sample the centroid and the three corner-ward points
        pts = [c] + [tuple(c[k] * 0.4 + v[k] * 0.6 for k in range(3)) for v in r]
        free = 0
        for p in pts:
            if not any(flgeom.tri_box(p, h, *G.tris[j]) for j in G.near(p[0], p[1], cover + 2)):
                free += 1
        if free >= 2:
            added.append(r)
    rep["drawn_tris_added"] = len(added)
    rep["dropped_list"] = [[list(i) if i is not None else None, [round(v) for v in _cen(t)]] for t, i in dropped]
    return out_t, out_f, added, rep
