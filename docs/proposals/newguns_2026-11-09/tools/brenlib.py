"""Bren Mk I (maximiliaanmaene, Sketchfab df74f7e3720d469e8bf425407e7ddc34, CC BY 4.0) -> the Vickers-Berthier's gun frame.

Source (bl_extract.py with NG_ROTX=90: the FBX object is pitched 77.9 deg instead of 90, set level): x = BUTT (+) .. muzzle (-),
y = right, z = up; units 1 = 1/19.74 of the gun.  Gun frame (gungeo, the posed VB): +x muzzle, +y right, +z DOWN, game units.
g = (-x, y, -z) * S + T.  S: the Bren Mk I and the Vickers-Berthier are both 1156 mm long, so the gun is as long as the VB.
T: the pistol grip where the VB's grip is (the right hand of the VB animations closes on it), the bore on the VB's bore.
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = r"H:\hzm_work\newguns\build\bren"
VB_LEN = 44.01 - (-20.51)          # posed VB: butt .. muzzle (gungeo, game units)
SRC_X0, SRC_X1 = -9.78, 9.96       # source muzzle .. butt
S = VB_LEN / (SRC_X1 - SRC_X0)
BORE_SRC_Z = 1.94                  # barrel centre at x -8 (source)
GRIP_SRC_X = 4.30                  # pistol grip (part 23) centre along the gun (source)
VB_BORE_Z = -3.96                  # tag_barrel z (posed VB)
VB_GRIP_X = float(os.environ.get('BREN_GRIPX', '-5.0'))
T = np.array([VB_GRIP_X + GRIP_SRC_X * S, 0.0, VB_BORE_Z + BORE_SRC_Z * S])


def to_gun(p):
    p = np.asarray(p, float)
    return np.stack([-p[..., 0], p[..., 1], -p[..., 2]], -1) * S + T


def nrm_gun(n):
    n = np.asarray(n, float)
    n = np.stack([-n[..., 0], n[..., 1], -n[..., 2]], -1)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)


# ---- sights (source frame). The rear aperture (part 49) is real size: a 0.035 hole = 0.11 u, a pin-hole at game scale, and
# the receiver's left lip (x 2.9) reaches 0.045 above the line through it. It is replaced by a thin GHOST RING (the fg42hd
# recipe: 0.86 / 0.70 u) centred RING_DZ higher, so the line clears the receiver and the sight arm sits low in the ring.
APER = np.array([5.705, -0.379, 2.416])          # the source aperture disc centre
POST = np.array([-7.886, -0.380, 2.527])         # the front blade tip (part 55), between the protector ears (part 16)
RING_DZ = 0.14
RING_C = APER + np.array([0.0, 0.0, RING_DZ])
RING_RO, RING_RI, RING_T = 0.80 / S, 0.70 / S, 0.012   # thinner than the FG 42's 0.86: the first look read as a heavy dark hoop


def ring_tris(uv, seg=40):
    """ring in the y-z plane around RING_C (looked through along x); rows like tris.npz: (T, 3, 8)"""
    import math
    out = []
    c = RING_C
    x0, x1 = c[0] - RING_T / 2, c[0] + RING_T / 2

    def P(r, a, x):
        return np.array([x, c[1] + r * math.cos(a), c[2] + r * math.sin(a)])

    def quad(p0, p1, p2, p3, n):
        for tri in ((p0, p1, p2), (p0, p2, p3)):
            out.append([list(q) + list(n) + list(uv) for q in tri])
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        am = (a0 + a1) / 2
        rad = np.array([0, math.cos(am), math.sin(am)])
        quad(P(RING_RO, a0, x0), P(RING_RO, a1, x0), P(RING_RO, a1, x1), P(RING_RO, a0, x1), rad)
        quad(P(RING_RI, a0, x1), P(RING_RI, a1, x1), P(RING_RI, a1, x0), P(RING_RI, a0, x0), -rad)
        quad(P(RING_RI, a0, x0), P(RING_RI, a1, x0), P(RING_RO, a1, x0), P(RING_RO, a0, x0), (-1, 0, 0))
        quad(P(RING_RO, a0, x1), P(RING_RO, a1, x1), P(RING_RI, a1, x1), P(RING_RI, a0, x1), (1, 0, 0))
    return np.array(out, np.float32)


def sight_row():
    """cg_adssights.h F / R (gun frame = the root-applied model space the VB row uses), U = gun up"""
    return to_gun(POST), to_gun(RING_C)
