"""Fit of Shorty_Digitan's FG42 (Sketchfab d699ac259bd74f70a51125a7e4320f4b, CC BY 4.0) into the game FG 42's bone space.

Source frame (Blender, metres): +y muzzle, +x right, +z up.  Bone-local game frame of `FG42` (raw skd units, the tik scales x0.52):
+x muzzle, +y right, +z DOWN  ->  g = (y, x, -z).
Uniform scale so the gun is as long as the shipped one (99.1 raw, butt plate to brake), a small pitch so the sight line has the
shipped irons' slope (the gun sits in the hands and the ADS picture at the angle players know), and a translation that puts the
pistol grip where the shipped grip is (the right hand of DaRKaNGeL's animations closes on it) and the bore on the shipped bore.
"""
import math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, '..', 'build')
SHIP = os.path.join(HERE, '..', 'ship')
SCALE_TIK = 0.52
OLD_LEN = 61.81 - (-37.27)                 # raw: brake tip .. butt (shipped fg42base + fg42barrel)
SRC_Y0, SRC_Y1 = -0.41821, 0.45170          # source butt .. brake (m)
S = OLD_LEN / (SRC_Y1 - SRC_Y0)
R_SRC = np.array([0.0, -0.1412, 0.0805])    # diopter aperture centre (m)
F_SRC = np.array([0.0, 0.3440, 0.0863])     # front post tip (m)
APER_Z0 = 0.0778                            # source z above which the Rear_sight verts are the aperture loop
GRIP_SRC_Y = -0.1505                        # pistol grip centre along the gun (m)
BORE_SRC_Z = 0.0342                         # bore height at the muzzle (m)
# shipped irons (raw, bone-local): aperture centre, post tip, grip centre, bore
R_OLD = np.array([-11.78, -0.07, -3.57])
F_OLD = np.array([51.62, -0.07, -2.92])
GRIP_OLD_X = float(os.environ.get('FG_GRIPX', '-5.2'))   # puts the magazine where the shipped one is (the reload hands)
BORE_OLD_Z = 0.97
CENTRE_Y = -0.07                            # the shipped gun's centre plane (raw)


def _g(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 1], p[..., 0], -p[..., 2]], -1)


def rot_y(deg):
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])      # row vectors: +deg lifts the front (x -> -z)


def _solve():
    old = (F_OLD[2] - R_OLD[2]) / (F_OLD[0] - R_OLD[0])
    best = None
    for a in np.linspace(-6, 6, 4801):
        Rm = rot_y(a)
        r = _g(R_SRC) * S @ Rm; f = _g(F_SRC) * S @ Rm
        d = abs((f[2] - r[2]) / (f[0] - r[0]) - old)
        if best is None or d < best[0]:
            best = (d, a)
    Rm = rot_y(best[1])
    grip = _g([0, GRIP_SRC_Y, BORE_SRC_Z]) * S @ Rm
    muz = _g([0, SRC_Y1, BORE_SRC_Z]) * S @ Rm
    tx = GRIP_OLD_X - grip[0]
    tz = BORE_OLD_Z - muz[2]
    return best[1], Rm, np.array([tx, CENTRE_Y, tz])


PITCH, ROT, TRANS = _solve()


def to_raw(p):
    return _g(p) * S @ ROT + TRANS


def nrm_raw(n):
    n = _g(n) @ ROT
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)


if __name__ == '__main__':
    print('S %.3f raw/m  pitch %.3f deg  trans %s' % (S, PITCH, np.round(TRANS, 3)))
    for nm, p in (('aperture', R_SRC), ('post tip', F_SRC), ('muzzle', [0, SRC_Y1, BORE_SRC_Z]), ('butt', [0, SRC_Y0, 0.0])):
        print('%-9s raw %s' % (nm, np.round(to_raw(np.array(p, float)), 2)))
    print('old aperture', R_OLD, 'old post', F_OLD)


# [QA 2026-11-08] the ghost ring that replaces the source's pin-hole aperture loop (metres, source frame; 1 scaled game unit = 1.69 cm)
U = 1.0 / (SCALE_TIK * S)                   # metres per scaled game unit
RING_RO, RING_RI, RING_T = 0.86 * U, 0.70 * U, 0.0030
DRUM_TOP = 0.0770
RING_C = np.array([0.0, R_SRC[1], DRUM_TOP + RING_RO + 0.0020])
RING_UV = (0.9336, 0.6836)


def ring_tris(seg=40):
    """thin ring in the x-z plane (looked through along y), plus a stem down to the drum: per-corner rows like tris.npz"""
    out = []
    c = RING_C
    y0, y1 = c[1] - RING_T / 2, c[1] + RING_T / 2

    def P(r, a, y):
        return np.array([c[0] + r * math.cos(a), y, c[2] + r * math.sin(a)])

    def quad(p0, p1, p2, p3, n):
        for tri in ((p0, p1, p2), (p0, p2, p3)):
            out.append([list(q) + list(n) + [0.0, 0.0] for q in tri])
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        am = (a0 + a1) / 2
        rad = np.array([math.cos(am), 0, math.sin(am)])
        quad(P(RING_RO, a0, y0), P(RING_RO, a1, y0), P(RING_RO, a1, y1), P(RING_RO, a0, y1), rad)            # outer wall
        quad(P(RING_RI, a0, y1), P(RING_RI, a1, y1), P(RING_RI, a1, y0), P(RING_RI, a0, y0), -rad)           # inner wall
        quad(P(RING_RI, a0, y0), P(RING_RI, a1, y0), P(RING_RO, a1, y0), P(RING_RO, a0, y0), (0, -1, 0))     # eye side
        quad(P(RING_RO, a0, y1), P(RING_RO, a1, y1), P(RING_RI, a1, y1), P(RING_RI, a0, y1), (0, 1, 0))      # muzzle side
    # stem: a small block from the drum top to the ring's bottom
    w, zb, zt = 0.0022, DRUM_TOP - 0.001, c[2] - RING_RO + 0.0005
    v = lambda x, y, z: np.array([x, y, z])
    for (a, b, n) in (((-w, y0), (w, y0), (0, -1, 0)), ((w, y1), (-w, y1), (0, 1, 0)), ((w, y0), (w, y1), (1, 0, 0)), ((-w, y1), (-w, y0), (-1, 0, 0))):
        quad(v(a[0], a[1], zb), v(b[0], b[1], zb), v(b[0], b[1], zt), v(a[0], a[1], zt), n)
    return np.array(out, np.float32)
