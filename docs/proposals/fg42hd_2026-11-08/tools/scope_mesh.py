"""ZFG 42 scope + mount, modelled in-house for the scoped FG 42 on Shorty_Digitan's body (QA 2026-11-08: TastyTony's scope was rejected
as "too cartoon like"; the user said not to wait on a Sketchfab download).

The real ZFG 42 (Voigtlander / Ajack, 4x): a SHORT tube (about 15 cm), small objective and ocular bells, a rubber eyecup, elevation drum on
top, windage drum on the right, two rings on a claw base that clamps to the rail on the receiver's left side. Modelled as lathe profiles
and boxes in the FG42 bone's LOCAL frame (raw skd units: +x muzzle, +y right, -z up; 1 raw = 8.78 mm at the fit's 113.9 raw/m), on the
shipped scope's optical axis (y -0.02, z -6.91, ocular at x -7.49), so the scoped gun's ADS / PiP rows (cg_adssights_scope.h) stay valid.
Steel is textured from the sheet's Scope tile (atlas.py: the barrel's paint combed along the tube and blued, at the body's texel
density), the eyecup from its matte Rubber tile, the lenses are their own surface (coop_scope_glass_blue).
    import scope_mesh; tris = scope_mesh.build()   -> [(material, [(p, n, uv) x3]), ...]
"""
import math
import numpy as np

AX_Y, AX_Z = -0.02, -6.91           # optical axis (local raw)
X_EYE = -7.49                        # ocular face
N = 32                               # segments round the tube
SHEET = 2048.0
SCOPE = (1024, 1536, 512, 6)         # atlas.py's Scope tile: blued steel combed along the tube (x, y, size, pad)
DARK_UV = ((1536 + 128) / 2048.0, (1536 + 128) / 2048.0)   # the middle of atlas.py's matte Rubber tile
PX_PER_RAW = 30.0                    # ~ the body's texel density
LENS_UV = (0.5, 0.5)


def steel_uv(theta, x, x0=-8.0, x1=8.5):
    """a cylinder unwrap into the Scope tile at the body's texel density: u round the tube (one turn of the 1.48 tube = 9.3 raw),
    v along it (the tile's combed streaks run along v)"""
    tx, ty, ts, pad = SCOPE
    u = (tx + pad + 4 + (theta / (2 * math.pi)) * 2 * math.pi * 1.48 * PX_PER_RAW) / SHEET
    v = (ty + pad + 4 + (x - x0) * PX_PER_RAW) / SHEET
    return (u, v)


def _p(x, r, th, cy=AX_Y, cz=AX_Z):
    return np.array([x, cy + r * math.cos(th), cz - r * math.sin(th)])


def lathe(profile, mat, out, cap0=False, cap1=False):
    """profile: [(x, r), ...] front to back along +x; a revolved surface with outward normals"""
    for i in range(len(profile) - 1):
        (xa, ra), (xb, rb) = profile[i], profile[i + 1]
        slope = (ra - rb) / max(abs(xb - xa), 1e-6) * (1 if xb > xa else -1)
        for k in range(N):
            t0, t1 = 2 * math.pi * k / N, 2 * math.pi * (k + 1) / N
            tm = (t0 + t1) / 2
            n = np.array([slope, math.cos(tm), -math.sin(tm)]); n /= np.linalg.norm(n)
            q = [_p(xa, ra, t0), _p(xb, rb, t0), _p(xb, rb, t1), _p(xa, ra, t1)]
            uv = [steel_uv(t0, xa), steel_uv(t0, xb), steel_uv(t1, xb), steel_uv(t1, xa)]
            if mat == 'rubber':
                uv = [DARK_UV] * 4
            for a, b, c in ((0, 1, 2), (0, 2, 3)):
                out.append((mat, [(q[a], n, uv[a]), (q[b], n, uv[b]), (q[c], n, uv[c])]))
    for cap, (x, r), sgn in ((cap0, profile[0], -1), (cap1, profile[-1], 1)):
        if cap:
            disc(x, r, sgn, mat, out)


def disc(x, r, sgn, mat, out, cy=AX_Y, cz=AX_Z):
    n = np.array([sgn * 1.0, 0, 0])
    c = np.array([x, cy, cz])
    for k in range(N):
        t0, t1 = 2 * math.pi * k / N, 2 * math.pi * (k + 1) / N
        a, b = _p(x, r, t0, cy, cz), _p(x, r, t1, cy, cz)
        uv = LENS_UV if mat == 'lens' else (DARK_UV if mat == 'rubber' else steel_uv(t0, x))
        out.append((mat, [(c, n, uv), (a, n, uv), (b, n, uv)]))


def cylinder(c, axis, r, h, mat, out, seg=20):
    """a closed cylinder centred at c, along unit axis (one of the frame axes), radius r, height h"""
    axis = np.asarray(axis, float)
    a1 = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(axis, a1); e1 /= np.linalg.norm(e1); e2 = np.cross(axis, e1)
    c0, c1 = c - axis * h / 2, c + axis * h / 2
    for k in range(seg):
        t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        d0 = e1 * math.cos(t0) + e2 * math.sin(t0); d1 = e1 * math.cos(t1) + e2 * math.sin(t1)
        nm = (d0 + d1) / np.linalg.norm(d0 + d1)
        uv = steel_uv(t0, c[0])
        q = [c0 + r * d0, c1 + r * d0, c1 + r * d1, c0 + r * d1]
        for a, b, cc in ((0, 1, 2), (0, 2, 3)):
            out.append((mat, [(q[a], nm, uv), (q[b], nm, uv), (q[cc], nm, uv)]))
        out.append((mat, [(c1, axis, uv), (c1 + r * d0, axis, uv), (c1 + r * d1, axis, uv)]))
        out.append((mat, [(c0, -axis, uv), (c0 + r * d1, -axis, uv), (c0 + r * d0, -axis, uv)]))


def box(lo, hi, mat, out):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    P = lambda i, j, k: np.array([(lo, hi)[i][0], (lo, hi)[j][1], (lo, hi)[k][2]])
    faces = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
             ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
             ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]
    for n, idx in faces:
        q = [P(*t) for t in idx]
        uv = [steel_uv(0.6 * j, p[0]) for j, p in enumerate(q)]
        for a, b, c in ((0, 1, 2), (0, 2, 3)):
            out.append((mat, [(q[a], np.array(n, float), uv[a]), (q[b], np.array(n, float), uv[b]), (q[c], np.array(n, float), uv[c])]))


def build(receiver_top_z):
    """receiver_top_z: the local z (raw, -z up) of the body's receiver top under the scope"""
    out = []
    x = X_EYE
    # eyecup (rubber), ocular bell, tube, objective bell, objective rim
    lathe([(x - 0.10, 1.90), (x + 0.15, 2.18), (x + 1.30, 2.10), (x + 1.45, 1.85)], 'rubber', out, cap0=False)
    lathe([(x + 1.45, 1.85), (x + 1.60, 1.80), (x + 3.00, 1.62), (x + 3.40, 1.48)], 'steel', out)
    lathe([(x + 3.40, 1.48), (x + 12.20, 1.48)], 'steel', out)
    lathe([(x + 12.20, 1.48), (x + 13.70, 1.70), (x + 14.60, 1.92), (x + 15.30, 1.98), (x + 15.45, 1.80)], 'steel', out)
    disc(x - 0.05, 1.70, -1, 'lens', out)                       # ocular glass (inside the eyecup)
    disc(x + 15.35, 1.78, 1, 'lens', out)                      # objective glass
    # turret block: a saddle on the tube, the elevation drum on top, the windage drum on the right
    tx = x + 7.6
    box((tx - 1.25, AX_Y - 1.15, AX_Z - 1.95), (tx + 1.25, AX_Y + 1.15, AX_Z - 0.6), 'steel', out)
    cylinder(np.array([tx, AX_Y, AX_Z - 2.45]), (0, 0, -1), 0.95, 1.0, 'steel', out)
    cylinder(np.array([tx, AX_Y, AX_Z - 3.02]), (0, 0, -1), 0.80, 0.18, 'steel', out)      # the drum's knurled cap
    cylinder(np.array([tx, AX_Y + 1.85, AX_Z]), (0, 1, 0), 0.85, 0.95, 'steel', out)
    # rings round the tube and the claw base: two posts down to a base rail on the receiver, clamped by a plate on its LEFT side
    for rx in (x + 4.6, x + 11.2):
        lathe([(rx - 0.45, 1.80), (rx + 0.45, 1.80)], 'steel', out, cap0=True, cap1=True)
        box((rx - 0.45, AX_Y - 0.85, AX_Z + 1.55), (rx + 0.45, AX_Y + 0.85, receiver_top_z - 0.95), 'steel', out)
    base_top = receiver_top_z - 0.95
    box((x + 3.6, AX_Y - 2.05, base_top), (x + 12.4, AX_Y + 1.25, receiver_top_z - 0.15), 'steel', out)
    box((x + 3.9, AX_Y - 2.45, base_top - 0.2), (x + 12.1, AX_Y - 2.03, receiver_top_z + 1.6), 'steel', out)   # side clamp plate
    for sx in (x + 5.2, x + 10.6):                                                                        # its two clamp screws
        cylinder(np.array([sx, AX_Y - 2.62, receiver_top_z + 0.5]), (0, -1, 0), 0.38, 0.36, 'steel', out, seg=12)
    return out


if __name__ == '__main__':
    t = build(-2.2)
    print(len(t), 'tris', {m: sum(1 for mm, _ in t if mm == m) for m in ('steel', 'rubber', 'lens')})
