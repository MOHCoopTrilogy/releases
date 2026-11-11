#!/usr/bin/env python3
"""Fit Frontline's invisible blocker COLUMNS to what is drawn (our code; runs inside the converter on the player's PC).

Frontline wraps trees, posts and some props in tall special-surface boxes (.cdb material 3, flag bit 23: up to 524u
high, 20-250u across, buried 150u+ in the ground). In Frontline the tree/prop stands inside the box, so the box reads as
the object. Converted, the box is usually much fatter than the drawn trunk or post, and where the drawn object is a
billboard or was not converted at all there is nothing visible inside it: an invisible wall the player snags on
(user playtest 2026-11-10: "you get caught on objects while moving", "a lot of invisible walls everywhere").

Each column is rebuilt as an axis-aligned box around the drawn geometry inside its footprint between floor+8 and
floor+110 (the body band), padded 2u; a column with nothing drawn in that band is dropped.
"""
import collections

import numpy as np

MAT_SPECIAL = 3


def components(tris, idx):
    par = {i: i for i in idx}

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    vm = {}
    for i in idx:
        for p in tris[i]:
            k = (round(p[0]), round(p[1]), round(p[2]))
            if k in vm:
                par[f(i)] = f(vm[k])
            else:
                vm[k] = i
    out = collections.defaultdict(list)
    for i in idx:
        out[f(i)].append(i)
    return list(out.values())


def fit_columns(tris, tags, render_tris, ground, opts=None):
    """tris: wound collision [(a, b, c)], tags: flag words; render_tris: [(a, b, c)] drawn geometry (MOHAA units);
    ground(x, y, ztop, zbot) -> floor z or None. Returns (tris, tags, boxes[(lo, hi)], report)."""
    o = {"min_h": 250.0, "max_w": 260.0, "band_lo": 8.0, "band_hi": 110.0, "pad": 2.0}
    o.update(opts or {})
    idx = [i for i, f in enumerate(tags) if (f & 0x7FF) == MAT_SPECIAL]
    comps = components(tris, idx)
    R = np.asarray(render_tris, dtype=np.float64) if render_tris else np.zeros((0, 3, 3))
    rlo, rhi = R.min(1), R.max(1)
    drop, boxes = set(), []
    rep = {"columns": 0, "fitted": 0, "dropped": 0, "area_before": 0.0, "area_after": 0.0}
    for ts in comps:
        P = np.asarray([p for i in ts for p in tris[i]])
        lo, hi = P.min(0), P.max(0)
        ext = hi - lo
        if ext[2] < o["min_h"] or max(ext[0], ext[1]) > o["max_w"]:
            continue
        rep["columns"] += 1
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        fz = ground(cx, cy, hi[2], lo[2])
        if fz is None:
            continue                       # cannot tell its floor: leave Frontline's column as it is
        z0, z1 = fz + o["band_lo"], fz + o["band_hi"]
        m = (rhi[:, 0] > lo[0]) & (rlo[:, 0] < hi[0]) & (rhi[:, 1] > lo[1]) & (rlo[:, 1] < hi[1]) & \
            (rhi[:, 2] > z0) & (rlo[:, 2] < z1)
        drop.update(ts)
        rep["area_before"] += float(ext[0] * ext[1])
        # [flpolish] the drawn POINTS inside the footprint and the body band, from non-floor triangles: a big wall or
        # ground triangle merely overlapping the footprint kept the box as fat as Frontline's (walk audit: 83 column
        # contacts on the routes with the trunk 16-128u away)
        Rm = R[m]
        nz = np.abs(np.cross(Rm[:, 1] - Rm[:, 0], Rm[:, 2] - Rm[:, 0])[:, 2]) / (
            np.linalg.norm(np.cross(Rm[:, 1] - Rm[:, 0], Rm[:, 2] - Rm[:, 0]), axis=1) + 1e-9)
        Vw = Rm[nz < 0.7].reshape(-1, 3)
        Vw = Vw[(Vw[:, 0] >= lo[0]) & (Vw[:, 0] <= hi[0]) & (Vw[:, 1] >= lo[1]) & (Vw[:, 1] <= hi[1])]
        # the trunk/post at body height only: low branches and the canopy's lower cards widened the box (walk audit:
        # 38 column contacts on the routes with the drawn trunk 16-128u away)
        Vt = Vw[(Vw[:, 2] >= z0) & (Vw[:, 2] <= z0 + 70.0)]
        if len(Vt) >= 3:
            Vw = Vt
        if not m.any() or len(Vw) < 3:
            rep["dropped"] += 1
            continue
        blo = np.maximum(Vw.min(0), lo)
        bhi = np.minimum(Vw.max(0), hi)
        pad = o["pad"]
        boxes.append(((float(blo[0] - pad), float(blo[1] - pad), float(fz - 8.0)),
                      (float(bhi[0] + pad), float(bhi[1] + pad), float(hi[2]))))
        rep["area_after"] += float((bhi[0] - blo[0] + 2 * pad) * (bhi[1] - blo[1] + 2 * pad))
        rep["fitted"] += 1
    keep = [i for i in range(len(tris)) if i not in drop]
    rep["area_before"] = round(rep["area_before"])
    rep["area_after"] = round(rep["area_after"])
    return [tris[i] for i in keep], [tags[i] for i in keep], boxes, rep
