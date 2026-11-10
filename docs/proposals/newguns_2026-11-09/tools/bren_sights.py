"""The Bren Mk I's sights, rebuilt on the model (newguns2 2026-11-09, BREN_SIGHTS.md part A).

A real Bren aims along a line offset LEFT of the top magazine: the rear sight is a range DRUM on the left of the body with an
ARM running back to an APERTURE LEAF above the butt, the front sight a BLADE between two protecting ears on a BRACKET off the
left of the barrel. The source mesh has the drum in the right place (part 32 + its knob 33, centred y -1.93 = the line) but its
arm / leaf (34), aperture disc (49) and front blade / ears (55 / 16) sit 0.7 u further right, and part 35 (a ring on the
magazine catch, right of the line) is not a Bren sight. Those are removed (build_bren.py) and rebuilt here as proper parts, in
the GUN frame (+x muzzle, +y right, +z DOWN, game units), on one line of sight:

    LOS: y = Y_L, z = Z_L, level with the bore. F = the blade tip, R = the aperture centre (cg_adssights.h row, relief RELIEF).

Sizes (BREN_SIGHTS.md A): leaf plate 0.06 u thick, disc radius 0.45 (at the 3 u eye relief: ~1/3 of the screen height), hole
radius HOLE; the arm / drum / bracket tops stay >= 0.55 u under the line so nothing below shows through the hole at 3 u.

    python bren_sights.py         prints the parts and the sight row (build_bren.py imports parts() / row())
"""
import math
import numpy as np

Y_L, Z_L = -1.94, -5.85          # the line of sight (gun frame): over the drum centre, 0.55 u above the drum / arm tops
X_LEAF = -9.60                   # the aperture leaf (where the source leaf stood, above the body / butt joint)
X_BLADE = 34.83                  # the front blade tip (the source blade's x)
LEAF_T, LEAF_R, HOLE = 0.06, 0.45, 0.21
HOLE_BEV = 0.035                 # [newguns2 polish] the hole is chamfered on the eye side: r HOLE + HOLE_BEV there, HOLE (the sight) at the front
ARM_X0, ARM_X1, ARM_W, ARM_TOP, ARM_H = -9.75, -3.40, 0.22, -5.30, 0.14
BLADE_W, BLADE_L, BLADE_H = 0.10, 0.45, 0.55
EAR_DY, EAR_T, EAR_L, EAR_UP = 0.32, 0.08, 0.62, 0.10   # ears stand EAR_UP above the blade tip
BR_X0, BR_X1, BR_BASE = 34.45, 35.20, -4.98                # bracket: a base under the blade + ears, and a strut down into the
BR_STRUT = [(-2.12, -4.98), (-1.60, -4.98), (-0.30, -4.20), (-0.55, -3.90)]   # barrel's left side ((y, z) quad, extruded along x)
DRUMBR = (-5.10, -3.45, -1.62, -0.95, -4.55, -3.05)      # the drum's bracket onto the body (x0, x1, y0, y1, z0, z1)
RELIEF = 3.0


def _quad(out, a, b, c, d, n):
    for t in ((a, b, c), (a, c, d)):
        out.append((np.array(t, float), np.array(n, float)))


def box(x0, x1, y0, y1, z0, z1):
    out = []
    P = lambda i, j, k: (x1 if i else x0, y1 if j else y0, z1 if k else z0)
    _quad(out, P(0, 0, 0), P(0, 1, 0), P(0, 1, 1), P(0, 0, 1), (-1, 0, 0))
    _quad(out, P(1, 0, 0), P(1, 0, 1), P(1, 1, 1), P(1, 1, 0), (1, 0, 0))
    _quad(out, P(0, 0, 0), P(0, 0, 1), P(1, 0, 1), P(1, 0, 0), (0, -1, 0))
    _quad(out, P(0, 1, 0), P(1, 1, 0), P(1, 1, 1), P(0, 1, 1), (0, 1, 0))
    _quad(out, P(0, 0, 0), P(1, 0, 0), P(1, 1, 0), P(0, 1, 0), (0, 0, -1))
    _quad(out, P(0, 0, 1), P(0, 1, 1), P(1, 1, 1), P(1, 0, 1), (0, 0, 1))
    return out


def prism_x(x0, x1, quad):
    """a 4-sided prism along x: quad = [(y, z) x4] in order around its outline"""
    out = []
    Q0 = [np.array([x0, y, z]) for y, z in quad]
    Q1 = [np.array([x1, y, z]) for y, z in quad]
    c = (sum(Q0) + sum(Q1)) / 8.0

    def face(a, b, cc, d):
        n = np.cross(b - a, cc - a); n = n / np.linalg.norm(n)
        if n @ ((a + b + cc + d) / 4 - c) < 0:
            n = -n
        _quad(out, a, b, cc, d, n)
    face(*Q0); face(*Q1)
    for i in range(4):
        j = (i + 1) % 4
        face(Q0[i], Q0[j], Q1[j], Q1[i])
    return out


def annulus_x(xc, t, yc, zc, ro, ri, seg=48, bev=0.0):
    """a plate in the y-z plane (looked through along x): front / back faces, outer rim and the hole's rim; bev > 0 chamfers
    the hole on the -x (eye) side: radius ri + bev there, ri at the +x face"""
    out = []
    x0, x1 = xc - t / 2, xc + t / 2
    ri0, ri1 = ri + bev, ri
    P = lambda r, a, x: (x, yc + r * math.cos(a), zc + r * math.sin(a))
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        am = (a0 + a1) / 2
        rad = (0, math.cos(am), math.sin(am))
        _quad(out, P(ro, a0, x0), P(ro, a1, x0), P(ri0, a1, x0), P(ri0, a0, x0), (-1, 0, 0))
        _quad(out, P(ri1, a0, x1), P(ri1, a1, x1), P(ro, a1, x1), P(ro, a0, x1), (1, 0, 0))
        _quad(out, P(ro, a0, x0), P(ro, a0, x1), P(ro, a1, x1), P(ro, a1, x0), rad)
        # the hole's rim (a cone when chamfered): its normal points into the hole and back toward the eye
        nb = np.array([-(ri0 - ri1), -rad[1] * t, -rad[2] * t]); nb = nb / np.linalg.norm(nb)
        _quad(out, P(ri0, a0, x0), P(ri0, a1, x0), P(ri1, a1, x1), P(ri1, a0, x1), tuple(nb))
    return out


def parts():
    """{name: [(tri (3,3) gun frame, outward normal (3,))]}"""
    p = {}
    p['leaf'] = annulus_x(X_LEAF, LEAF_T, Y_L, Z_L, LEAF_R, HOLE, bev=HOLE_BEV)
    # the leaf's stem down to the arm (thinner than the plate: no coplanar faces)
    p['stem'] = box(X_LEAF - LEAF_T * 0.4, X_LEAF + LEAF_T * 0.4, Y_L - 0.16, Y_L + 0.16, Z_L + LEAF_R - 0.06, ARM_TOP + 0.02)
    p['arm'] = box(ARM_X0, ARM_X1, Y_L - ARM_W / 2, Y_L + ARM_W / 2, ARM_TOP, ARM_TOP + ARM_H)
    x0, x1, y0, y1, z0, z1 = DRUMBR
    p['drumbr'] = box(x0, x1, y0, y1, z0, z1)
    bx0 = X_BLADE - BLADE_L / 2
    p['blade'] = box(bx0, bx0 + BLADE_L, Y_L - BLADE_W / 2, Y_L + BLADE_W / 2, Z_L, Z_L + BLADE_H + 0.05)
    ex0 = X_BLADE - EAR_L / 2
    p['ears'] = (box(ex0, ex0 + EAR_L, Y_L - EAR_DY - EAR_T / 2, Y_L - EAR_DY + EAR_T / 2, Z_L - EAR_UP, Z_L + BLADE_H + 0.05)
                 + box(ex0, ex0 + EAR_L, Y_L + EAR_DY - EAR_T / 2, Y_L + EAR_DY + EAR_T / 2, Z_L - EAR_UP, Z_L + BLADE_H + 0.05))
    p['bracket'] = box(BR_X0, BR_X1, Y_L - EAR_DY - EAR_T / 2, Y_L + EAR_DY + EAR_T / 2, Z_L + BLADE_H, BR_BASE) +         prism_x(BR_X0 + 0.1, BR_X1 - 0.1, BR_STRUT)
    return p


# ---- the sights' own texture (newguns2 polish, coordinator QA): the leaf and arm read as a flat CG washer on one texel of
# the sheet. They get a surface of their own, `coop_bren_sight` - no tik line names it, so it draws with the shader of the
# same name in every tik (base, the seven finishes, the finishes2 variants: sights stay plain steel, as real ones do) - and a
# 512 x 512 sheet painted from the Bren sheet's own parkerized steel, with the edge wear laid where the UVs put the edges.
TEX = 512
DISC_C, DISC_R = (128.0, 128.0), 120.0            # the leaf faces: the disc maps onto this circle (r LEAF_R -> DISC_R px)
RIM_Y = (268.0, 308.0)                            # the rims (outer + the hole's chamfer): a worn strip, u = the angle
RECT = (264.0, 8.0, 504.0, 248.0)                 # every flat face of the boxes / prism, mapped edge to edge (worn border)
STEEL_XY, STEEL_W = (253, 808), 60                # the Bren sheet patch the steel is taken from (clean receiver steel, mean ~75)


def quad_uvs(name, tri_pair):
    """image-space UVs (pixels, y down) for one quad (two triangles from _quad: (a, b, c), (a, c, d))"""
    (t0, n), (t1, _) = tri_pair
    a, b, c, d = t0[0], t0[1], t0[2], t1[2]
    Q = np.array([a, b, c, d])
    if name == 'leaf' and abs(n[0]) > 0.9:              # front / back face: the disc
        u = DISC_C[0] + (Q[:, 1] - Y_L) / LEAF_R * DISC_R
        v = DISC_C[1] + (Q[:, 2] - Z_L) / LEAF_R * DISC_R
    elif name == 'leaf':                                # a rim: angle along u, x across the strip
        ang = np.arctan2(Q[:, 2] - Z_L, Q[:, 1] - Y_L) % (2 * math.pi)
        if ang.max() - ang.min() > math.pi:             # the quad that crosses 0
            ang = np.where(ang < math.pi, ang + 2 * math.pi, ang)
        u = 8.0 + ang / (2 * math.pi) * (TEX - 16.0) * 0.98
        v = RIM_Y[0] + (Q[:, 0] - (X_LEAF - LEAF_T / 2)) / LEAF_T * (RIM_Y[1] - RIM_Y[0])
    else:                                               # a flat face: its own in-plane axes, edge to edge
        e1 = b - a; e1 = e1 / max(np.linalg.norm(e1), 1e-9)
        e2 = np.cross(n, e1)
        s1, s2 = (Q - a) @ e1, (Q - a) @ e2
        s1 = (s1 - s1.min()) / max(np.ptp(s1), 1e-9); s2 = (s2 - s2.min()) / max(np.ptp(s2), 1e-9)
        u = RECT[0] + s1 * (RECT[2] - RECT[0]); v = RECT[1] + s2 * (RECT[3] - RECT[1])
    uv = np.stack([u, v], 1) / TEX
    return [uv[[0, 1, 2]], uv[[0, 2, 3]]]


def texture(sheet_png, out_jpg, seed=11):
    """paint the sights' sheet: parkerized steel from the Bren sheet + fine grain; edge wear (bright, polished, broken up by
    noise) along the disc's outer edge and hole, over the whole rim strip, and round every face rectangle's border"""
    from PIL import Image, ImageFilter
    src = np.asarray(Image.open(sheet_png).convert('RGB'), float)
    x, y = STEEL_XY; r = STEEL_W // 2
    col = src[y - r:y + r, x - r:x + r].reshape(-1, 3).mean(0)            # the Bren's own receiver steel colour
    base = np.ones((TEX, TEX, 3)) * col                                    # + parkerized mottle below (no tiled features)
    rng = np.random.RandomState(seed)
    grain = np.asarray(Image.fromarray((rng.rand(TEX, TEX) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), float) / 255.0 - 0.5
    lum = base.mean(2, keepdims=True)
    base = lum + (base - lum) * 0.5 + np.array([-2.0, 0.0, 3.0])        # parkerized: desaturated, a cold cast
    def octave(n, sig):
        o = rng.rand(TEX // n, TEX // n)
        o = np.asarray(Image.fromarray((o * 255).astype(np.uint8)).resize((TEX, TEX), Image.BICUBIC).filter(ImageFilter.GaussianBlur(sig)), float) / 255.0
        return o - o.mean()
    mott = 0.10 * grain + 0.07 * octave(4, 1.0) + 0.05 * octave(16, 2.0)
    base = base * (1.08 + mott[:, :, None])
    blot = np.asarray(Image.fromarray((rng.rand(TEX // 8, TEX // 8) * 255).astype(np.uint8)).resize((TEX, TEX), Image.BICUBIC), float) / 255.0
    yy, xx = np.mgrid[0:TEX, 0:TEX].astype(float)
    d = np.hypot(xx - DISC_C[0], yy - DISC_C[1])
    rh0, rh1 = DISC_R * (HOLE + HOLE_BEV) / LEAF_R, DISC_R * HOLE / LEAF_R
    wear = np.zeros((TEX, TEX))
    wear = np.maximum(wear, np.exp(-np.clip(DISC_R - d, 0, None) / 2.5) * (d <= DISC_R + 2))      # the outer edge
    wear = np.maximum(wear, np.exp(-np.clip(d - rh0, 0, None) / 2.5) * (d >= rh1 - 2))             # the hole's edge (+ its chamfer)
    wear[int(RIM_Y[0]) - 4:int(RIM_Y[1]) + 4, :] = np.maximum(wear[int(RIM_Y[0]) - 4:int(RIM_Y[1]) + 4, :], 0.75)
    x0, y0, x1, y1 = RECT
    db = np.minimum.reduce([xx - x0, x1 - xx, yy - y0, y1 - yy])
    inr = (xx >= x0 - 2) & (xx <= x1 + 2) & (yy >= y0 - 2) & (yy <= y1 + 2)
    wear = np.maximum(wear, np.exp(-np.clip(db, 0, None) / 4.0) * inr)
    wear = np.clip(wear * (0.35 + 0.9 * blot) * (1.0 + 0.6 * grain), 0, 1)
    worn = base.mean(2, keepdims=True) * 1.75 + 22.0                    # polished steel through the finish
    out = base * (1 - wear[:, :, None] * 0.8) + worn * (wear[:, :, None] * 0.8)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(out_jpg, quality=92)
    return out_jpg


def row():
    """the sight row, measured on the built parts: F = the blade's top face centre, R = the aperture hole's centre"""
    pr = parts()
    bl = np.array([t for t, n in pr['blade']]).reshape(-1, 3)
    top = bl[bl[:, 2] <= bl[:, 2].min() + 1e-6]
    F = np.array([X_BLADE, (top[:, 1].min() + top[:, 1].max()) / 2, top[:, 2].min()])
    lf = np.array([t for t, n in pr['leaf']]).reshape(-1, 3)
    rr = np.hypot(lf[:, 1] - Y_L, lf[:, 2] - Z_L)
    inner = lf[rr < HOLE + HOLE_BEV + 1e-6]          # both hole rims (eye side + front): centred on the leaf's mid-plane
    Rr = np.array([(inner[:, 0].min() + inner[:, 0].max()) / 2, inner[:, 1].mean(), inner[:, 2].mean()])
    return dict(F=F.tolist(), R=Rr.tolist(), up=[0.0, 0.0, -1.0], relief=RELIEF, delta_mrad=0.0,
                F_root=F.tolist(), R_root=Rr.tolist(), up_root=[0.0, 0.0, -1.0], frame_used='root')


if __name__ == '__main__':
    for k, v in parts().items():
        P = np.array([t for t, n in v]).reshape(-1, 3)
        print('%-8s %4d tris  x %6.2f..%6.2f y %5.2f..%5.2f z %5.2f..%5.2f' % (k, len(v), P[:, 0].min(), P[:, 0].max(),
              P[:, 1].min(), P[:, 1].max(), P[:, 2].min(), P[:, 2].max()))
    r = row()
    print('F', np.round(r['F'], 4), 'R', np.round(r['R'], 4), 'relief', r['relief'])
