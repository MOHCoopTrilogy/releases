"""Shared constants and the fit of the no12u C96 into the game's C96 gun frame (raw skd units; the tik scales x0.52).

Source frame (BU, Blender): +y muzzle, +z up, +x right.  Game frame: +x muzzle, +y right, +z DOWN  (g = (y, x, -z)).
The fit is UNIFORM scale + a small pitch about the lateral axis + a translation, chosen so that
  * the muzzle end and the bore height are where the mod's current C96's are (tag_barrel 30.9, -1.6, -6.3 raw),
  * the sight line of the new model (rear leaf top -> front post top) lies on the line of the mod's sight row
    (cg_adssights.h: F = (15.4048, -0.8000, -3.8262), R = (4.5035, -0.8461, -4.3355), scaled units) - so the
    engine's ADS solve keeps working with NO engine change,
  * the overall length equals the current model's (17.3 scaled units).
"""
import os, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
BUILD = os.path.join(ROOT, 'build')
STAGE = os.path.join(ROOT, 'ship')
SCALE = 0.52
F_OLD = np.array([15.4048, -0.8000, -3.8262])      # scaled units
R_OLD = np.array([4.5035, -0.8461, -4.3355])
# source landmarks (BU)
R_NEW = np.array([0.0, 0.5417, 0.3083])           # rear leaf top
F_NEW = np.array([0.0, 2.2676, 0.2770])           # front post top
MUZ_Y, TAIL_Y = 2.3752, 0.2027
BORE_Z = 0.158                                    # bore centre height at the muzzle (BU)
S_SCALED = 17.3 / (MUZ_Y - TAIL_Y)                # scaled units per BU
S = S_SCALED / SCALE                              # raw units per BU
CENTRE_Y_RAW = -1.58                              # lateral centre of the gun, raw
MUZZLE_X_RAW = 30.80


def rot_rows(axis, deg):
    """3x3 for row vectors; +deg about gun +y (right) lifts the FRONT (+x goes to -z)"""
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    Rc = np.eye(3) + s * K + (1 - c) * (K @ K)
    return Rc.T


def mat_quat(m):
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2; q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    return [float(x) for x in q]


def _g(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 1], p[..., 0], -p[..., 2]], -1)


def _solve():
    """pitch (deg about +y) and translation (raw) of the fit"""
    # slopes of the sight line (z down per x forward)
    old = (F_OLD[2] - R_OLD[2]) / (F_OLD[0] - R_OLD[0])
    best = None
    for a in np.linspace(-6, 6, 2401):
        Rm = rot_rows((0, 1, 0), a)
        r = _g(R_NEW) * S @ Rm; f = _g(F_NEW) * S @ Rm
        sl = (f[2] - r[2]) / (f[0] - r[0])
        if best is None or abs(sl - old) < best[0]:
            best = (abs(sl - old), a)
    a = best[1]
    Rm = rot_rows((0, 1, 0), a)
    # translation: muzzle tip (y=MUZ_Y, bore) at x = MUZZLE_X_RAW; lateral centre; rear leaf top ON the old sight line
    m = _g(np.array([0, MUZ_Y, BORE_Z])) * S @ Rm
    r = _g(R_NEW) * S @ Rm
    tx = MUZZLE_X_RAW - m[0]
    rx_scaled = (r[0] + tx) * SCALE
    z_line = R_OLD[2] + (rx_scaled - R_OLD[0]) * (F_OLD[2] - R_OLD[2]) / (F_OLD[0] - R_OLD[0])      # scaled
    tz = z_line / SCALE - r[2]
    return a, Rm, np.array([tx, CENTRE_Y_RAW, tz])


PITCH_DEG, ROT, TRANS = _solve()


def to_raw(p):
    """BU source point(s) -> raw game-frame point(s)"""
    return _g(p) * S @ ROT + TRANS


def nrm_raw(n):
    n = _g(n) @ ROT
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)


if __name__ == '__main__':
    print('pitch %.3f deg, S raw/BU %.4f, trans %s' % (PITCH_DEG, S, np.round(TRANS, 3)))
    for nm, p in (('rear leaf', R_NEW), ('front post', F_NEW), ('muzzle', [0, MUZ_Y, BORE_Z]), ('tail', [0, TAIL_Y, 0.0])):
        r = to_raw(np.array(p, float))
        print('%-10s raw %s  scaled %s' % (nm, np.round(r, 3), np.round(r * SCALE, 3)))
    print('old R', R_OLD, 'old F', F_OLD)
