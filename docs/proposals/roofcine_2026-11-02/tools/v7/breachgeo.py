"""breachgeo.py - small geometry helpers for the breach builder (numpy only): convex hull planes/faces of a point cloud, polygon utils,
affine texture/lightmap fit from a stock surface, hole-polygon generator, tileable scorch/ember TGA generator."""
import math, random, itertools
import numpy as np

def hull(points, eps=0.05):
    """brute-force convex hull of <= ~24 3D points. Returns list of faces: dict(n=(nx,ny,nz), d=float, idx=[vertex indices CCW seen from outside])."""
    P = np.array(points, float); n = len(P); planes = []
    for i, j, k in itertools.combinations(range(n), 3):
        nv = np.cross(P[j] - P[i], P[k] - P[i]); L = np.linalg.norm(nv)
        if L < 1e-6: continue
        nv /= L; d = nv @ P[i]; s = P @ nv - d
        if (s <= eps).all(): pass
        elif (s >= -eps).all(): nv = -nv; d = -d; s = -s
        else: continue
        if any(np.dot(nv, q[0]) > 0.99995 and abs(d - q[1]) < 0.3 for q in planes): continue
        planes.append((nv, d))
    faces = []
    for nv, d in planes:
        idx = [i for i in range(n) if abs(P[i] @ nv - d) <= eps]
        if len(idx) < 3: continue
        c = P[idx].mean(0)
        a = np.cross(nv, [1, 0, 0]) if abs(nv[0]) < 0.9 else np.cross(nv, [0, 1, 0]); a /= np.linalg.norm(a); bb = np.cross(nv, a)
        idx.sort(key=lambda i: math.atan2((P[i] - c) @ bb, (P[i] - c) @ a))
        faces.append(dict(n=tuple(nv), d=float(d), idx=idx))
    return faces

def fit_affine(src, dst):
    """least squares  dst = M @ [x y z 1]  for planar sources (uses lstsq, min-norm). src Nx3, dst Nx2 -> 2x4"""
    A = np.hstack([np.array(src, float), np.ones((len(src), 1))])
    M, *_ = np.linalg.lstsq(A, np.array(dst, float), rcond=None)
    return M.T

def apply_affine(M, p):
    v = M @ np.array([p[0], p[1], p[2], 1.0]); return float(v[0]), float(v[1])

def ray_rect(c, e, umin, umax, vmin, vmax):
    """first intersection of ray c + t e (t>0) with the rectangle boundary from inside; returns (u,v)."""
    best = 1e18
    for k, (lo, hi) in enumerate(((umin, umax), (vmin, vmax))):
        if abs(e[k]) < 1e-9: continue
        for bound in (lo, hi):
            t = (bound - c[k]) / e[k]
            if t > 1e-6 and t < best: best = t
    return (c[0] + e[0] * best, c[1] + e[1] * best)

def make_hole(cu, cv, base_r, K, seed, umin, umax, vmin, vmax, margin=24):
    """ragged star-shaped hole polygon: K vertices around (cu,cv). Returns list of (angle, r_front, r_back)."""
    rnd = random.Random(seed); out = []
    rmax = min(cu - umin, umax - cu, cv - vmin, vmax - cv) - margin
    for k in range(K):
        th = 2 * math.pi * (k + rnd.uniform(-0.28, 0.28)) / K
        r = base_r * rnd.choice((0.55, 0.7, 0.85, 1.0, 1.0, 1.15, 1.3, 1.4)) * rnd.uniform(0.9, 1.1)
        rb = r * rnd.uniform(1.12, 1.55)
        out.append((th, min(r, rmax * 0.8), min(rb, rmax)))
    out.sort(key=lambda a: a[0]); return out

def write_tga(path, w, h, rgba):
    import struct
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    a = np.asarray(rgba, np.uint8)[::-1]            # bottom-up
    bgra = a[:, :, [2, 1, 0, 3]]
    open(path, "wb").write(hdr + bgra.tobytes())

def noise2d(w, h, seed, octaves=5, wrapx=True):
    rnd = np.random.RandomState(seed); out = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(octaves):
        gh = 4 * 2 ** o; gw = 4 * 2 ** o
        g = rnd.rand(gh, gw)
        ys = np.linspace(0, gh, h, endpoint=False); xs = np.linspace(0, gw, w, endpoint=False)
        x0 = xs.astype(int) % gw; x1 = (x0 + 1) % gw; y0 = ys.astype(int) % gh; y1 = (y0 + 1) % gh
        fx = (xs - np.floor(xs))[None, :]; fy = (ys - np.floor(ys))[:, None]
        fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
        v = (g[np.ix_(y0, x0)] * (1 - fx) + g[np.ix_(y0, x1)] * fx) * (1 - fy) + (g[np.ix_(y1, x0)] * (1 - fx) + g[np.ix_(y1, x1)] * fx) * fy
        out += v * amp; tot += amp; amp *= 0.5
    return out / tot

def scorch_ring_tga(path, size=256):
    """u axis (x) = radial 0 inner -> 1 outer, v axis (y) = angle (wraps). Black-brown soot, ragged alpha."""
    n = noise2d(size, size, 7); n2 = noise2d(size, size, 11, 6)
    u = np.linspace(0, 1, size)[None, :].repeat(size, 0)
    a = np.clip(1.15 - u * (0.9 + 0.9 * n), 0, 1) ** 1.3          # dense at the hole edge, ragged fade outward
    a = np.clip(a + (n2 - 0.5) * 0.35 * (1 - u), 0, 1)
    a[:, :6] = 1.0                                                # solid at the hole lip
    r = (14 + 22 * n2 + 20 * u).clip(0, 255); g = (11 + 17 * n2 + 15 * u).clip(0, 255); b = (9 + 14 * n2 + 12 * u).clip(0, 255)
    rgba = np.dstack([r, g, b, a * 235]); write_tga(path, size, size, rgba)

def ember_glow_tga(path, size=128):
    """soft orange radial glow (additive)."""
    y, x = np.mgrid[0:size, 0:size]; d = np.hypot(x - size / 2 + 0.5, y - size / 2 + 0.5) / (size / 2)
    a = np.clip(1 - d, 0, 1) ** 2.2; n = noise2d(size, size, 5, 4)
    a = a * (0.75 + 0.5 * n)
    rgba = np.dstack([255 * a, 120 * a, 30 * a, 255 * np.ones_like(a)]); write_tga(path, size, size, rgba)


def make_hole2(cu, cv, base_r, K0, seed, umin, umax, vmin, vmax, margin=22):
    """v7 ragged hole: low-frequency blast lobes, per-vertex +-25-40 % radius jitter, 2-4 deep narrow cracks, 3-5 outward rim chips,
    per-vertex back radius / depth fraction (spalled-back edges).  Returns sorted list of (angle, r_front, r_back, depth_frac)."""
    rnd = random.Random(seed)
    rmax = min(cu - umin, umax - cu, cv - vmin, vmax - cv) - margin
    rcap = rmax - 4
    base_r = min(base_r, rcap * 0.62)
    ph = rnd.uniform(0, 2 * math.pi); a2 = rnd.uniform(0.05, 0.25); p2 = rnd.uniform(0, 6.28); a3 = rnd.uniform(0.03, 0.18); p3 = rnd.uniform(0, 6.28)
    jit = rnd.uniform(0.25, 0.40)
    base = []
    for k in range(K0):
        th = ph + 2 * math.pi * (k + rnd.uniform(-0.3, 0.3)) / K0
        rf = base_r * (1 + a2 * math.cos(2 * th + p2) + a3 * math.cos(3 * th + p3)) * (1 + rnd.uniform(-jit, jit))
        base.append([th, rf, 0])
    idx = list(range(K0)); rnd.shuffle(idx)
    ncr = rnd.randint(2, 4); nch = rnd.randint(3, 5)
    cracks = set(idx[:ncr]); chips = set(idx[ncr:ncr + nch])
    pts = []
    for k, (th, rf, _) in enumerate(base):
        if k in cracks:
            d = rnd.uniform(0.025, 0.055)
            pts += [[th - d, rf * 0.85, 1], [th, rf * rnd.uniform(1.7, 2.5), 2], [th + d, rf * 0.85, 1]]      # type 2 = crack tip
        elif k in chips:
            d = rnd.uniform(0.07, 0.12)
            pts += [[th - d, rf, 0], [th, rf * rnd.uniform(1.25, 1.5), 3], [th + d, rf, 0]]                    # type 3 = rim chip
        else:
            pts.append([th, rf, 0])
    pts.sort(key=lambda p: p[0])
    for i in range(1, len(pts)):
        if pts[i][0] - pts[i - 1][0] < 0.012: pts[i][0] = pts[i - 1][0] + 0.012
    while pts[-1][0] - pts[0][0] > 2 * math.pi - 0.02: pts[-1][0] -= 0.003
    out = []
    for th, rf, typ in pts:
        rf = max(34.0, min(rf, rcap))
        room = max(2.0, rmax - rf)
        if typ in (1, 2):
            fr = rnd.uniform(0.04, 0.14); dep = 1.0
        elif rnd.random() < 0.38:
            fr = rnd.uniform(0.55, 1.0); dep = rnd.uniform(0.3, 0.7)
        else:
            fr = rnd.uniform(0.08, 0.5); dep = rnd.choice([1.0, 1.0, rnd.uniform(0.7, 1.0)])
        rb = rf + max(1.0, room * fr)
        out.append((th, rf, rb, dep))
    return out


def streak_tga(path, w=64, h=256):
    """soot streak: u across the width (gaussian), v along the length (1 at the root, fading out); ragged."""
    n = noise2d(w, h, 21, 5); n2 = noise2d(w, h, 33, 6)
    u = np.linspace(-1, 1, w)[None, :].repeat(h, 0); v = np.linspace(0, 1, h)[:, None].repeat(w, 1)
    wid = 0.55 + 0.35 * n2
    a = np.exp(-(u / wid) ** 2 * 2.4) * np.clip(1.0 - v * (0.85 + 0.5 * n), 0, 1) ** 1.35
    a = np.clip(a * (0.55 + 0.9 * n2), 0, 1)
    a[:3, :] *= np.linspace(0.4, 1, 3)[:, None]
    r = 12 + 20 * n2; g = 10 + 16 * n2; b = 8 + 13 * n2
    write_tga(path, w, h, np.dstack([r, g, b, a * 225]))
