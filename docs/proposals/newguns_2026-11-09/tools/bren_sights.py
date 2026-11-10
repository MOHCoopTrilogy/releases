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


def annulus_x(xc, t, yc, zc, ro, ri, seg=36):
    """a plate in the y-z plane (looked through along x): front / back faces, outer and inner rims"""
    out = []
    x0, x1 = xc - t / 2, xc + t / 2
    P = lambda r, a, x: (x, yc + r * math.cos(a), zc + r * math.sin(a))
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        am = (a0 + a1) / 2
        rad = (0, math.cos(am), math.sin(am))
        _quad(out, P(ro, a0, x0), P(ro, a1, x0), P(ri, a1, x0), P(ri, a0, x0), (-1, 0, 0))
        _quad(out, P(ri, a0, x1), P(ri, a1, x1), P(ro, a1, x1), P(ro, a0, x1), (1, 0, 0))
        _quad(out, P(ro, a0, x0), P(ro, a0, x1), P(ro, a1, x1), P(ro, a1, x0), rad)
        _quad(out, P(ri, a0, x0), P(ri, a1, x0), P(ri, a1, x1), P(ri, a0, x1), tuple(-v for v in rad))
    return out


def parts():
    """{name: [(tri (3,3) gun frame, outward normal (3,))]}"""
    p = {}
    p['leaf'] = annulus_x(X_LEAF, LEAF_T, Y_L, Z_L, LEAF_R, HOLE)
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


def row():
    """the sight row, measured on the built parts: F = the blade's top face centre, R = the aperture hole's centre"""
    pr = parts()
    bl = np.array([t for t, n in pr['blade']]).reshape(-1, 3)
    top = bl[bl[:, 2] <= bl[:, 2].min() + 1e-6]
    F = np.array([X_BLADE, (top[:, 1].min() + top[:, 1].max()) / 2, top[:, 2].min()])
    lf = np.array([t for t, n in pr['leaf']]).reshape(-1, 3)
    rr = np.hypot(lf[:, 1] - Y_L, lf[:, 2] - Z_L)
    inner = lf[np.abs(rr - HOLE) < 1e-6]
    Rr = np.array([inner[:, 0].mean(), inner[:, 1].mean(), inner[:, 2].mean()])
    return dict(F=F.tolist(), R=Rr.tolist(), up=[0.0, 0.0, -1.0], relief=RELIEF, delta_mrad=0.0,
                F_root=F.tolist(), R_root=Rr.tolist(), up_root=[0.0, 0.0, -1.0], frame_used='root')


if __name__ == '__main__':
    for k, v in parts().items():
        P = np.array([t for t, n in v]).reshape(-1, 3)
        print('%-8s %4d tris  x %6.2f..%6.2f y %5.2f..%5.2f z %5.2f..%5.2f' % (k, len(v), P[:, 0].min(), P[:, 0].max(),
              P[:, 1].min(), P[:, 1].max(), P[:, 2].min(), P[:, 2].max()))
    r = row()
    print('F', np.round(r['F'], 4), 'R', np.round(r['R'], 4), 'relief', r['relief'])
