"""MP 28 (BrendanStakenburg, Sketchfab a8838ccaf87243cfa71a321092065d6a, CC BY 4.0) -> the Sten Mk II's gun frame.

Source (bl_extract.py, metres): +x muzzle, +y LEFT (the magazine), +z up.  Gun frame (gungeo, the posed Sten, root applied):
+x muzzle, -y left, +z DOWN.  g = (x, -y, -z) * S + T.
S: the real MP 28 is 812 mm long; the Sten (760 mm) is 39.70 u in the gun frame, so 52.2 u/m; the source is 0.856 m long.
T: the magazine (housing centre) where the Sten's is (12.39 x: the left hand of the Sten clips holds it), the bore on the Sten's
bore (tag_barrel z -2.95), the centre plane on the Sten's (-0.7 y). The trigger then lands at -0.7 x, the Sten's is at ~-1.
"""
import numpy as np

BUILD = r"H:\hzm_work\newguns\build\mp28"
STEN_UPM = 39.70 / 0.760
SRC_X0, SRC_X1 = -0.462, 0.394
S = 0.812 * STEN_UPM / (SRC_X1 - SRC_X0)
MAG_SRC_X, BORE_SRC_Z, CTR_SRC_Y = 0.160, 0.0255, -0.010
STEN_MAG_X, STEN_BORE_Z, STEN_Y = 12.39, -2.95, -0.70
T = np.array([STEN_MAG_X - MAG_SRC_X * S, STEN_Y + CTR_SRC_Y * S, STEN_BORE_Z + BORE_SRC_Z * S])
MAG_PARTS = {49, 51}          # the magazine body and its floor plate (48 / 50 / 44 = the fixed housing and its catch)


def to_gun(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], -p[..., 1], -p[..., 2]], -1) * S + T


def nrm_gun(n):
    n = np.asarray(n, float)
    n = np.stack([n[..., 0], -n[..., 1], -n[..., 2]], -1)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
