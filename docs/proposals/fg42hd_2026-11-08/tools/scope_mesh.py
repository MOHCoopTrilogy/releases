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
RIM_UV = ((1536 + 128) / 2048.0, (1536 + 6 + 30) / 2048.0)  # its lighter lip rows (atlas.RIM_ROWS)
PX_PER_RAW = 30.0                    # ~ the body's texel density
LENS_UV = (0.5, 0.5)
# the eyepiece opening = the ocular glass radius, MEASURED against the lens pass's picture circle (gR, from the scope row's relief):
# glass 0.89 at x+0.5 drew 170 px where the circle was 238 px at 1080 (run z1080f), so 1.25 fills it; 1.20 keeps the lip just inside
# it, so the edge of the picture is the crisp rubber lip, never a band of bare glass (runs z1080c-e: the hazy grey band)
GLASS_R = 1.14   # 1.20 still left a sliver of bare glass where the circle is clipped square at the right (run z1080g)
CUP_R = 1.62                          # the eyecup's outside: barely over the 1.48 tube, so the ring round the picture is ~1/3 of it


def steel_uv(theta, x, x0=-8.0, x1=8.5):
    """a cylinder unwrap into the Scope tile at the body's texel density: u round the tube (one turn of the 1.48 tube = 9.3 raw),
    v along it (the tile's combed streaks run along v)"""
    tx, ty, ts, pad = SCOPE
    u = (tx + pad + 4 + (theta / (2 * math.pi)) * 2 * math.pi * 1.48 * PX_PER_RAW) / SHEET
    v = (ty + pad + 4 + (x - x0) * PX_PER_RAW) / SHEET
    return (u, v)


def _p(x, r, th, cy=AX_Y, cz=AX_Z):
    return np.array([x, cy + r * math.cos(th), cz - r * math.sin(th)])


def lathe(profile, mat, out, cap0=False, cap1=False, inward=False, uvc=None):
    """profile: [(x, r), ...] along +x; a revolved surface with outward normals (inward: facing the axis, a cup's inside wall);
    uvc: one fixed texel for the whole band"""
    for i in range(len(profile) - 1):
        (xa, ra), (xb, rb) = profile[i], profile[i + 1]
        # the profile's 2D normal (-dr, dx), so a band that runs backwards in x (the lip's face toward the eye) still faces out;
        # per-vertex (smooth round the tube): neighbouring quads share vertices, the band welds, and it shades as a turned part
        nx, nr = -(rb - ra), (xb - xa)
        ln = math.hypot(nx, nr) or 1.0
        nx, nr = nx / ln, nr / ln
        sg = -1.0 if inward else 1.0
        for k in range(N):
            t0, t1 = 2 * math.pi * k / N, 2 * math.pi * (k + 1) / N
            n0 = sg * np.array([nx, nr * math.cos(t0), -nr * math.sin(t0)])
            n1 = sg * np.array([nx, nr * math.cos(t1), -nr * math.sin(t1)])
            nn = [n0, n0, n1, n1]
            q = [_p(xa, ra, t0), _p(xb, rb, t0), _p(xb, rb, t1), _p(xa, ra, t1)]
            uv = [steel_uv(t0, xa), steel_uv(t0, xb), steel_uv(t1, xb), steel_uv(t1, xa)]
            if uvc is not None:
                uv = [uvc] * 4
            elif mat in ('rubber', 'cup'):
                uv = [DARK_UV] * 4
            for a, b, c in ((0, 1, 2), (0, 2, 3)):
                out.append((mat, [(q[a], nn[a], uv[a]), (q[b], nn[b], uv[b]), (q[c], nn[c], uv[c])]))
    for cap, (x, r), sgn in ((cap0, profile[0], -1), (cap1, profile[-1], 1)):
        if cap:
            disc(x, r, sgn, mat, out)


def disc(x, r, sgn, mat, out, cy=AX_Y, cz=AX_Z):
    n = np.array([sgn * 1.0, 0, 0])
    c = np.array([x, cy, cz])
    for k in range(N):
        t0, t1 = 2 * math.pi * k / N, 2 * math.pi * (k + 1) / N
        a, b = _p(x, r, t0, cy, cz), _p(x, r, t1, cy, cz)
        uv = LENS_UV if mat in ('lens', 'glass') else (DARK_UV if mat in ('rubber', 'cup') else steel_uv(t0, x))
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
    # [QA 2026-11-08 #2] the eyecup is a real CUP: an outer wall to a rolled lip in lighter, worn rubber (the lit rim), a straight
    # inside wall down to the ocular glass recessed 0.9 inside it. The Kar98k's recipe at the eye: the eyepiece itself is the dark ring
    # round the picture - so the lip's opening matches the lens pass's picture circle (GLASS_R) and the cup is barely wider than the tube.
    # The first cup (2.18 outside, glass 1.70) read as a thick black double ring round a hazy grey band of bare glass; hiding it
    # (coop_scopeEyeHide, the ZF4 route) left a small scope floating inside the pass's own ring (runs z1080c-f) - not used.
    lathe([(x - 0.22, CUP_R), (x + 0.20, CUP_R), (x + 1.10, 1.56), (x + 1.45, 1.48)], 'cup', out)
    lathe([(x - 0.40, CUP_R - 0.10), (x - 0.30, CUP_R), (x - 0.22, CUP_R)], 'cup', out, uvc=RIM_UV)
    lathe([(x - 0.40, GLASS_R), (x - 0.43, (GLASS_R + CUP_R) / 2 - 0.05), (x - 0.40, CUP_R - 0.10)], 'cup', out, uvc=RIM_UV)
    lathe([(x - 0.40, GLASS_R), (x + 0.50, GLASS_R)], 'cup', out, inward=True)
    disc(x + 0.50, GLASS_R, -1, 'glass', out)                   # ocular glass, recessed in the cup
    lathe([(x + 1.45, 1.48), (x + 3.40, 1.48)], 'steel', out)
    # the tube's INSIDE, dark: the gun layer is drawn over the lens picture, so through the hollow tube the turret block showed as a
    # notch in the top of the eyepiece (run z1080d / e). A real tube is a closed dark bore.
    lathe([(x + 0.50, GLASS_R), (x + 1.45, 1.30), (x + 15.20, 1.30)], 'steel', out, inward=True, uvc=DARK_UV)
    lathe([(x + 3.40, 1.48), (x + 12.20, 1.48)], 'steel', out)
    lathe([(x + 12.20, 1.48), (x + 13.70, 1.70), (x + 14.60, 1.92), (x + 15.30, 1.98), (x + 15.45, 1.80)], 'steel', out)
    disc(x + 15.35, 1.78, 1, 'lens', out)                      # objective glass
    # turret block: a saddle on the tube, the elevation drum on top, the windage drum on the right
    tx = x + 7.6
    box((tx - 1.25, AX_Y - 1.15, AX_Z - 1.95), (tx + 1.25, AX_Y + 1.15, AX_Z - 1.30), 'steel', out)   # stays OUTSIDE the tube (r 1.48): it showed as a notch in the eyepiece
    cylinder(np.array([tx, AX_Y, AX_Z - 2.45]), (0, 0, -1), 0.95, 1.0, 'steel', out)
    cylinder(np.array([tx, AX_Y, AX_Z - 3.02]), (0, 0, -1), 0.80, 0.18, 'steel', out)      # the drum's knurled cap
    cylinder(np.array([tx, AX_Y + 2.00, AX_Z]), (0, 1, 0), 0.85, 0.95, 'steel', out)
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
    print(len(t), 'tris', {m: sum(1 for mm, _ in t if mm == m) for m in ('steel', 'cup', 'glass', 'lens')})
