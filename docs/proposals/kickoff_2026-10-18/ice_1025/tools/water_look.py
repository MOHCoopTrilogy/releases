"""water_look.py - offline look-dev for the COLD HARBOUR water of the Norway U-boat pens (m2l2a/b/c, co_lobby7) and the
open fjord of the m2l2b U-boat cutscene. BEFORE = what ships today (retail stages + the r_hzmWater pass, v1.10.3+),
AFTER = prototype of the proposed cold-harbour mode of that same pass. Not the final GLSL; the constants are its start.
usage: python water_look.py <view> [planar=1] [floes=1]   views in views.json -> $ICE_OUT/<view>_W_{BEFORE,AFTER,AB}.jpg
"""
import os, sys, json, math
import numpy as np
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WW = r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\tools"
sys.path.insert(0, WW)
import ww_look as L
import ww_stills as WS
from ww_fs import FS
import ice_look as IL

OUT = IL.OUT
VIEWS = IL.VIEWS
_C = {}


def swell_normal(x, y, t, amp=1.0):
    """slow heavy swell: 3 long crests (900/520/310 u), slopes 0.030/0.022/0.016 -> (nx, ny) = -gradient"""
    dirs = [(0.93, 0.37, 900.0, 0.030, 0.045), (-0.55, 0.83, 520.0, 0.022, 0.07), (0.20, -0.98, 310.0, 0.016, 0.10)]
    gx = np.zeros_like(x); gy = np.zeros_like(x)
    for dx, dy, lam, sl, om in dirs:
        k = 2 * math.pi / lam
        c = np.cos(k * (dx * x + dy * y) + om * t * 6.0) * sl * amp
        gx += c * dx; gy += c * dy
    return -gx, -gy


def chop_normal(x, y, t, calm):
    """oily chop detail: gradient of a 5-octave field at two scales; `calm` (0..1) flattens it into slicks"""
    e = 2.0
    out = []
    for sc, w, sp in ((120.0, 0.55, 1.0), (47.0, 0.35, -1.3)):
        f = lambda a, b: IL.fbm(a / sc + 0.02 * sp * t, b / sc - 0.013 * sp * t, 7 if sc > 100 else 19)
        gx = (f(x + e, y) - f(x - e, y)) / (2 * e) * sc * 0.55
        gy = (f(x, y + e) - f(x, y - e)) / (2 * e) * sc * 0.55
        out.append((-gx * w, -gy * w))
    nx = (out[0][0] + out[1][0]) * 0.26 * (1 - 0.6 * calm)
    ny = (out[0][1] + out[1][1]) * 0.26 * (1 - 0.6 * calm)
    return nx, ny


def water_after(S, V, mat, P, planar=True, floes=True, t=3.0):
    G = V.G; eye = V.eye; H, W = G["tid"].shape
    wm = V.wm
    ys, xs = np.nonzero(wm)
    pos = G["pos"][ys, xs]; dist = G["dist"][ys, xs]
    zw = float(np.median(pos[:, 2]))
    Vv = eye[None] - pos; Vv /= np.linalg.norm(Vv, axis=1, keepdims=True)
    # ---- slicks, swell, chop
    calm = np.clip((IL.fbm(pos[:, 0] / 700.0 + 3, pos[:, 1] / 700.0, 5) - 0.50) * 5.0, 0, 1)
    sx, sy = swell_normal(pos[:, 0], pos[:, 1], t, P["swell"])
    cx, cy = chop_normal(pos[:, 0], pos[:, 1], t, calm)
    fadeC = np.clip(1.0 - dist / 2600.0, 0.12, 1.0)               # chop fades with range (the anti-sparkle rule)
    nx = sx + cx * fadeC; ny = sy + cy * fadeC
    N = np.stack([nx, ny, np.ones_like(nx)], 1); N /= np.linalg.norm(N, axis=1, keepdims=True)
    # ---- floes + crust along the walls (distance to the nearest wall from the top-down occlusion grid)
    bank = None
    if floes:
        occ, ox, oy, cell = S.occ
        if "bd" not in _C or _C["bd_key"] != S.key:
            # distance to the nearest QUAY WALL: near-vertical faces that reach the waterline. (The top-down height grid
            # cannot be used: a covered pen is a roof everywhere.) Points are sampled over each such triangle.
            tri = S.xyz; nz = np.abs(S.nrm[:, 2])
            sel = (nz < 0.5) & (tri[:, :, 2].min(1) < zw + 160) & (tri[:, :, 2].max(1) > zw - 40) & (S.cls == 0)
            T = tri[sel]
            g = np.array([(a / 6.0, b / 6.0) for a in range(7) for b in range(7 - a)], np.float32)
            pts = (T[:, None, 0, :] * (1 - g[None, :, 0:1] - g[None, :, 1:2]) + T[:, None, 1, :] * g[None, :, 0:1] + T[:, None, 2, :] * g[None, :, 1:2]).reshape(-1, 3)
            wall = np.zeros(occ.shape, bool)
            ix = ((pts[:, 0] - ox) / cell).astype(int); iy = ((pts[:, 1] - oy) / cell).astype(int)
            ok = (ix >= 0) & (ix < occ.shape[1]) & (iy >= 0) & (iy < occ.shape[0])
            wall[iy[ok], ix[ok]] = True
            d = ndimage.distance_transform_edt(~wall) * cell
            _C["bd"], _C["bd_key"] = d, S.key
        d = _C["bd"]
        ix = np.clip(((pos[:, 0] - ox) / cell).astype(int), 0, d.shape[1] - 1); iy = np.clip(((pos[:, 1] - oy) / cell).astype(int), 0, d.shape[0] - 1)
        bank = d[iy, ix]
    # ---- depth tint: dark cold green-black, lighter at steep angles (scatter), never milky
    ndv = np.clip((N * Vv).sum(1), 0.02, 1)
    deep = np.array(P["deep"], np.float32); shallow = np.array(P["shallow"], np.float32)
    k = np.clip(ndv, 0, 1) ** 2.2
    body = deep[None] * (1 - k[:, None]) + shallow[None] * k[:, None]
    haze = S.sky_fog_frac(eye)
    sky_d = L.sky_sample(S.sky_blur[3], np.stack([np.zeros_like(nx), np.zeros_like(nx), np.ones_like(nx)], 1))
    body = body + sky_d * 0.025 * (1 - haze)
    lm = G["lmuv"]                                                # keep the baked lighting: bright lamp pools tint the body
    lmv = V.lmv[ys, xs]
    body = body * (0.55 + 0.45 * np.clip(lmv.mean(1, keepdims=True) / max(P["lmref"], 1e-3), 0, 1.6))
    # ---- ice crust / slush / floes: ambientCG cracked ice as thin white-blue plates, drifting with the swell
    ice_a = np.zeros(len(ys), np.float32); ice_c = np.zeros((len(ys), 3), np.float32)
    if floes:
        dr = P["drift"]
        edge = np.clip(1.0 - bank / dr, 0, 1) ** 1.2
        fx = pos[:, 0] + 18 * np.sin(t * 0.21 + pos[:, 1] / 260.0); fy = pos[:, 1] + 18 * np.cos(t * 0.17 + pos[:, 0] / 240.0)
        plate = IL.fbm(fx / 150.0 + 9, fy / 150.0 - 4, 23)
        cr = np.clip((plate - (0.64 - 0.26 * edge)) * 5.0, 0, 1)         # more, bigger plates at the wall
        cr = np.maximum(cr * (edge > 0.02), np.clip(edge - 0.85, 0, 1) * 4)  # a solid crust right at the wall
        slush = np.clip((IL.fbm(fx / 40.0, fy / 40.0, 31) - 0.55) * 4, 0, 1) * edge * 0.6
        u1, v1 = fx / 330.0, fy / 330.0
        wpp = dist / (W * 0.5 / math.tan(math.radians(40)))
        col = IL.samp(mat.c[0], u1, v1, np.log2(np.maximum(wpp / (330.0 / 1024.0), 1e-3)))
        lum = (col * np.array([.299, .587, .114], np.float32)).sum(1)
        kk = (np.clip((lum - 0.15) / 0.5, 0, 1))[:, None]
        icecol = np.array([0.07, 0.14, 0.2], np.float32)[None] * (1 - kk) + np.array([0.78, 0.88, 0.96], np.float32)[None] * kk
        icecol = icecol * (0.45 + 0.55 * np.clip(lmv.mean(1, keepdims=True) / max(P["lmref"], 1e-3), 0, 1.4))
        # plates have a dark thin edge: the water shows through where the mask is soft
        rim = (cr > 0.02) & (cr < 0.85)
        icecol = np.where(rim[:, None], icecol * 0.55, icecol)
        ice_a = np.clip(cr + slush, 0, 1).astype(np.float32); ice_c = icecol.astype(np.float32)
        # plates sit flat: their normal is the swell only, no chop, and they are matte
        N = np.where((ice_a > 0.5)[:, None], np.stack([sx, sy, np.ones_like(sx)], 1) / np.linalg.norm(np.stack([sx, sy, np.ones_like(sx)], 1), axis=1, keepdims=True), N)
    # ---- reflection: planar scene (pens/walls) + sky probe, Fresnel
    F0 = 0.02
    F = np.minimum(F0 + (1 - F0) * (1 - np.clip((N * Vv).sum(1), 0, 1)) ** 5, P["fmax"])
    R = 2 * (N * Vv).sum(1)[:, None] * N - Vv
    Rz = np.maximum(R[:, 2], 0.03); R = R / np.linalg.norm(R, axis=1, keepdims=True)
    env = L.sky_sample(S.sky_blur[2], R) * (1 - haze) + S.fogc[None] * haze
    refl = env
    if planar:
        Rimg = V.planar(zw)
        # screen-space lookup with ripple distortion; blur grows with range (rough water smears mirrors)
        bl = ndimage.gaussian_filter(Rimg, (1.5 * V.ss, 1.5 * V.ss, 0))
        px = np.clip(xs + (nx - 0.0) * -P["dist"] * V.RH * 0.5 * np.clip(1.0 - dist / 3000.0, 0.2, 1), 0, W - 1)
        py = np.clip(ys + (ny * 0) + (-nx * 0), 0, H - 1)
        # distortion mostly vertical on a mirror: use the slope component along the view pitch
        py = np.clip(ys + (sy + cy * fadeC) * -P["dist"] * V.RH * 0.5, 0, H - 1)
        sc_ = np.stack([ndimage.map_coordinates(bl[..., c], [py, px], order=1, mode="nearest") for c in range(3)], 1)
        hit = np.stack([ndimage.map_coordinates(V.planar_hit[...], [py, px], order=1, mode="nearest")], 1)[:, 0]
        refl = env * (1 - hit[:, None]) + sc_ * hit[:, None]
    # ---- sun / moon glint
    Hh = Vv + (-S.sun)[None]; Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
    nh = np.clip((N * Hh).sum(1), 0, 1); a2 = 0.05 ** 2 + 0.0 * nh
    D = a2 / (math.pi * ((nh * nh) * (a2 - 1) + 1) ** 2)
    nl = np.clip((N * (-S.sun)[None]).sum(1), 0, 1)
    glint = np.minimum(D * nl * F * 0.25, 2.0)[:, None] * S.sunc[None] * P["glint"] * fadeC[:, None]
    water = body * (1 - F[:, None]) + refl * F[:, None] * P["rgain"] + glint
    # ice over water: matte plate with a little fresnel sky sheen
    Fi = (0.04 + 0.96 * (1 - np.clip(Vv[:, 2], 0, 1)) ** 5)[:, None]
    icelit = ice_c * (1 - Fi) + env * Fi
    out = V.base.copy()
    out[ys, xs] = water * (1 - ice_a[:, None]) + icelit * ice_a[:, None]
    return out, wm


def build_planar(V, S, zw):
    if getattr(V, "_pl", None) is not None:
        return V._pl
    eye = V.eye.copy(); e2 = eye.copy(); e2[2] = 2 * zw - eye[2]
    tgt = V.tgt.copy(); t2 = tgt.copy(); t2[2] = 2 * zw - tgt[2]
    cam, yaw, el = L.look_camera(e2, t2, V.RW, V.RH)
    z, tid, bary = L.render_geometry(S, e2, cam, V.RW, V.RH, include_water=False)
    G2 = L.gbuf(S, e2, cam, V.RW, V.RH, tid, bary)
    b2, _, lm2 = L.shade_base(S, G2, V.RW, V.RH)
    # nothing under the surface is mirrored: geometry below the plane is the real floor, drop it; sky counts as a miss
    below = G2["pos"][..., 2] < zw - 1.0
    hit = ((tid >= 0) & (~below)).astype(np.float32)
    img = L.fog_and_sky(S, b2, G2, cam, V.RW, V.RH, e2)
    img = img[::-1]; hit = ndimage.gaussian_filter(hit[::-1], 1.2)
    V._pl = img.astype(np.float32); V.planar_hit = hit
    return V._pl


def run(view, W=1280, H=720, ss=2, planar=True, floes=True, tag="", P=None):
    mp, eye, tgt = VIEWS[view]
    key = mp
    if key not in _C:
        fs = FS(); S = L.Scene(fs, "maps/%s.bsp" % mp); S.build_occlusion(); A = L.Assets(); _C[key] = (fs, S, A)
    fs, S, A = _C[key]
    P0 = dict(swell=1.0, deep=[0.012, 0.034, 0.036], shallow=[0.045, 0.100, 0.095], fmax=0.80, rgain=1.0, glint=1.0,
              drift=240.0, lmref=0.35, dist=0.9)
    P0.update(P or {})
    V = WS.View(S, A, eye, tgt, W, H, ss)
    V.tgt = np.asarray(tgt, float)
    V.planar = lambda zw: build_planar(V, S, zw)
    b, lb = V.frame(4.0, "after")                          # TODAY: retail stages + the shipped r_hzmWater pass
    if "mat" not in _C:
        _C["mat"] = IL.IceMat()
    out, wm = water_after(S, V, _C["mat"], P0, planar, floes)
    img = L.fog_and_sky(S, out, V.G, V.cam, V.RW, V.RH, V.eye)
    la = lambda x: float(np.exp(np.mean(np.log(x.mean(-1) + 1e-4))))
    a8 = L.to8(L.downsample(L.grade(img, 1.0), ss))
    b8 = L.to8(b)
    Image.fromarray(b8).save(f"{OUT}/{view}_W{tag}_BEFORE.jpg", quality=93)
    Image.fromarray(a8).save(f"{OUT}/{view}_W{tag}_AFTER.jpg", quality=93)
    ab = np.concatenate([L.label(b8, "BEFORE (shipped today: retail water + r_hzmWater)"), np.zeros((6, W, 3), np.uint8),
                         L.label(a8, "AFTER (prototype cold-harbour water, offline)")], 0)
    Image.fromarray(ab).save(f"{OUT}/{view}_W{tag}_AB.jpg", quality=90)
    print(view, "water frac", float(V.wm.mean()), flush=True)


if __name__ == "__main__":
    run(sys.argv[1], planar=(len(sys.argv) < 3 or sys.argv[2] != "0"), floes=(len(sys.argv) < 4 or sys.argv[3] != "0"))
