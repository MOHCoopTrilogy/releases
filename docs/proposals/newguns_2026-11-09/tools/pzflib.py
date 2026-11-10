"""Panzerfaust 60 (marcusww, Sketchfab bb5ac613b7b84c5384900bc64ee83ead, CC BY 4.0) -> the Panzerschreck's gun frame.

Source (bl_extract.py, one of the model's two copies: circle, d1-d4, patrone, pin, spring, tube1, the screw): +x warhead, +y LEFT,
+z up; the tube's axis is y 1.245, z 0; 1 unit = 0.121 m (1.04 m overall).  Gun frame (gungeo, the posed Panzerschreck, no root
channel): +x muzzle, -y left, +z DOWN.  g = (x, -(y - 1.245), -z) * S + T.
S: 52.5 u/m (16 u per foot) - the shipped Panzerschreck mesh is undersized (67 u for 1.64 m), the Panzerfaust is built true size.
T: the trigger lever's rear end (x -0.40) under the right hand's index finger (gun x 3.6, pose_panzershrek f0), the tube resting on
the fingers of both hands (tube centre z -3.8: its underside at -2.43, the fingertips at -2.0 .. -2.8), centred on y 0.
"""
import numpy as np

BUILD = r"H:\hzm_work\newguns\build\pzf"
UPM = 16.0 / 0.3048
S = UPM * 1.04 / (4.237 - (-4.353))
AXIS_Y = 1.245
LEVER_SRC_X, HAND_X, TUBE_Z = -0.40, 3.6, -3.8
T = np.array([HAND_X - LEVER_SRC_X * S, 0.0, TUBE_Z])
HEAD_PARTS = {19, 20, 21, 22, 23, 24, 25}   # the projectile (patrone): warhead, its tail boom in the tube, pins - hidden once fired
PIN_TIP = np.array([3.530, AXIS_Y, 0.667])   # the warhead's sight pin (front sight)
LEAF_TOP = np.array([1.170, AXIS_Y, 0.585])  # the leaf's raised rear edge (rear sight: aim over it at the pin)


def to_gun(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], -(p[..., 1] - AXIS_Y), -p[..., 2]], -1) * S + T


def nrm_gun(n):
    n = np.asarray(n, float)
    n = np.stack([n[..., 0], -n[..., 1], -n[..., 2]], -1)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
