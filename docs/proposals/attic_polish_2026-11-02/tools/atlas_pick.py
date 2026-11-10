"""atlas_pick.py - screen -> baked-atlas picking for the attic (which atlas texels does this patch of the home view come from?).

Rasterises the baked groups (bake dir *.npz: world tris in Blender units + atlas uv) from a Scene3D camera with a painter's ID
buffer (PIL polygons, far to near), so a screen mask can be turned into (group, triangle ids) and then into a UV mask on that
group's atlas.  Used by retouch.py.  Camera / projection = the engine's (mphub_run.hot_px / scene_params.axes_from_angles)."""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import scene_params as SP  # noqa: E402

BAKE = os.environ.get("ATTIC_BAKE", r"G:\mohaa-hudfeed3\menus3d\bake_s5")
SCALE = 52.5
GROUPS = ["bg", "chrome", "radio", "nook", "projector", "fan", "chalk", "wallmap"]
HOME = [-36.7, 21.0, 102.4, 7.01, 0.0, 0.0, 55.11]


def load(g):
    d = np.load(os.path.join(BAKE, g + ".npz"))
    return d["pos"].astype(np.float64), d["uv"].astype(np.float64)


def project(P, cam, w, h):
    org, ang, fovy = np.array(cam[:3]), cam[3:6], cam[6]
    f, left, up = SP.axes_from_angles(*ang)
    Q = np.stack([P[..., 1], -P[..., 0], P[..., 2]], -1) * SCALE - org
    x, y, z = Q @ f, Q @ left, Q @ up
    F = (h / 2) / math.tan(math.radians(fovy) / 2)
    xs = np.where(x > 1e-3, x, 1e-3)
    return np.stack([w / 2 - y / xs * F, h / 2 - z / xs * F], -1), x


def idbuffer(cam, w, h, groups=GROUPS):
    """-> int32 [h, w] of (group index << 20 | tri index) + 1, 0 = nothing"""
    items = []
    for gi, g in enumerate(groups):
        if not os.path.exists(os.path.join(BAKE, g + ".npz")):
            continue
        P, _ = load(g)
        S, dep = project(P, cam, w, h)
        ok = (dep > 1.0).all(1)
        lo, hi = S.min(1), S.max(1)
        ok &= (hi[:, 0] >= 0) & (lo[:, 0] < w) & (hi[:, 1] >= 0) & (lo[:, 1] < h)
        for t in np.nonzero(ok)[0]:
            items.append((dep[t].mean(), gi, t, S[t]))
    items.sort(key=lambda r: -r[0])
    im = Image.new("RGB", (w, h), 0)
    d = ImageDraw.Draw(im)
    for _, gi, t, s in items:
        v = (gi << 20 | t) + 1
        d.polygon([tuple(p) for p in s], fill=(v & 255, (v >> 8) & 255, (v >> 16) & 255))
    a = np.asarray(im).astype(np.int32)
    return a[..., 0] | (a[..., 1] << 8) | (a[..., 2] << 16)


def zpick(cam, w, h, roi, g="bg"):
    """exact per-pixel z-buffer of one group inside roi (x0, y0, x1, y1): -> (tri index map, atlas uv map [.., 2]) - every screen pixel
    of the roi mapped to the atlas texel it shows (perspective-correct barycentrics), so a defect seen on screen can be painted out
    of the atlas exactly where it is"""
    P, UV = load(g)
    S, dep = project(P, cam, w, h)
    x0, y0, x1, y1 = roi
    ok = (dep > 1).all(1)
    lo, hi = S.min(1), S.max(1)
    ok &= (hi[:, 0] >= x0) & (lo[:, 0] < x1) & (hi[:, 1] >= y0) & (lo[:, 1] < y1)
    Z = np.full((y1 - y0, x1 - x0), 1e9)
    I = np.full((y1 - y0, x1 - x0), -1)
    U = np.zeros((y1 - y0, x1 - x0, 2))
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    for t in np.nonzero(ok)[0]:
        a, b, c = S[t]
        iz = 1.0 / dep[t]
        bx0, bx1 = max(x0, int(min(a[0], b[0], c[0]))), min(x1, int(max(a[0], b[0], c[0])) + 1)
        by0, by1 = max(y0, int(min(a[1], b[1], c[1]))), min(y1, int(max(a[1], b[1], c[1])) + 1)
        if bx0 >= bx1 or by0 >= by1:
            continue
        sl = (slice(by0 - y0, by1 - y0), slice(bx0 - x0, bx1 - x0))
        X, Y = xx[sl], yy[sl]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        l3 = 1 - l1 - l2
        inside = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        w1, w2, w3 = l1 * iz[0], l2 * iz[1], l3 * iz[2]
        s = w1 + w2 + w3
        z = 1.0 / np.maximum(s, 1e-12)
        upd = inside & (z < Z[sl])
        Z[sl][upd] = z[upd]
        I[sl][upd] = t
        uv = (w1[..., None] * UV[t, 0] + w2[..., None] * UV[t, 1] + w3[..., None] * UV[t, 2]) / s[..., None]
        U[sl][upd] = uv[upd]
    return I, U


def tris_in(ids, mask, groups=GROUPS, min_px=1):
    """screen mask -> {group: sorted tri ids} (a triangle counts when >= min_px of its pixels are in the mask)"""
    v = ids[mask & (ids > 0)] - 1
    u, c = np.unique(v, return_counts=True)
    out = {}
    for val, n in zip(u, c):
        if n >= min_px:
            out.setdefault(groups[val >> 20], []).append(int(val & 0xFFFFF))
    return out


def uv_mask(g, tris, size, grow=2):
    """the atlas texels of those triangles (+ a few px so the bake's edge padding goes with them)"""
    _, UV = load(g)
    W, H = size
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for t in tris:
        d.polygon([(u * W, (1 - v) * H) for u, v in UV[t]], fill=255)
    if grow:
        from PIL import ImageFilter
        m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    return np.asarray(m) > 0


def raycast(cam, w, h, pixels, g="bg"):
    """exact nearest hit for screen pixels (no near-plane culling, unlike zpick): -> list of (tri, uv) or (None, None)"""
    P, UV = load(g)
    Q = np.stack([P[..., 1], -P[..., 0], P[..., 2]], -1) * SCALE           # game units
    org, ang, fovy = np.array(cam[:3]), cam[3:6], cam[6]
    f, left, up = SP.axes_from_angles(*ang)
    F = (h / 2) / math.tan(math.radians(fovy) / 2)
    v0, e1, e2 = Q[:, 0], Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]
    out = []
    for sx, sy in pixels:
        d = f + left * (-(sx + 0.5 - w / 2) / F) + up * (-(sy + 0.5 - h / 2) / F)
        p = np.cross(d, e2)
        det = (e1 * p).sum(1)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
        tv = org - v0
        u = (tv * p).sum(1) * inv
        q = np.cross(tv, e1)
        v = (d * q).sum(1) * inv
        t = (e2 * q).sum(1) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-3)
        if not hit.any():
            out.append((None, None))
            continue
        i = np.nonzero(hit)[0][np.argmin(t[hit])]
        out.append((int(i), (1 - u[i] - v[i]) * UV[i, 0] + u[i] * UV[i, 1] + v[i] * UV[i, 2]))
    return out
