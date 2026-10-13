"""The mod's first-person rig tools as a library (read-only reuse, the way heavy/tools/hv.py does it):
    R  ads_anims adsrig      (load / pose_dict / evaluate, quaternion helpers, R.S = 0.52, R.ANIM)
    V  ads_bolt vmcam        (offline scene + shade_render of arms and gun)
    K  ads_bolt key_bolt     (solve_arms: two-bone arm IK onto given hand matrices, write_frame)
    B  ads_anims bake_ads    (H, blend_H)
Matrices are 4x4 ROW form (p' = p @ M[:3,:3] + M[3,:3]) in rig units; x S = game units.
"""
import os, sys
import numpy as np
import dbslib as L

BOLT = os.path.join(L.DOCS, 'proposals', 'ads_bolt_2026-10-04', 'tools')
SHARED = os.path.join(L.DOCS, 'proposals', 'ads_twohand_2026-10-11', 'tools')
for p in (SHARED, BOLT):
    if p not in sys.path:
        sys.path.insert(0, p)
_c = os.getcwd(); os.chdir(BOLT)
try:
    import vmcam as V
    import key_bolt as K
finally:
    os.chdir(_c)
R = V.R
B = K.B
VM = 'viewmodel/shotgun/'
CLIPS = dict(idle=VM + 'idle_shotgun.skc', fire=VM + 'fire_shotgun_stand.skc', reload=VM + 'reload_start.skc',
             reload_single=VM + 'reload_fill.skc', reload_end=VM + 'reload_end.skc',
             pullout=VM + 'raise_shotgun_standplayer.skc', putaway=VM + 'lower_shotgun_stand.skc',
             charge='viewmodel/idle_shotgun00.skc')


def load(name):
    return R.load(R.ANIM + CLIPS.get(name, name))


def gun_pt(G, p):
    """a gun point (scaled game units, weapon-tag frame) -> rig world"""
    return (np.asarray(p, float) / R.S) @ G[0:3, 0:3] + G[3, 0:3]


def in_gun(G, w):
    """rig world point -> gun frame, scaled game units"""
    return ((np.asarray(w, float) - G[3, 0:3]) @ G[0:3, 0:3].T) * R.S
