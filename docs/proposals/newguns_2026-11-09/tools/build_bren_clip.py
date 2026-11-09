"""The Bren's reload prop: models/weapons/coop_bren/coop_bren_clip.skd on the VB clip prop's bones (origin, Vickers_Clip), so the VB's
A_W_vickers_reload_clip.skc and the torso's attach / remove commands drive it. The mesh is the Bren's OWN magazine (brenclip), placed
in the prop bone's frame where the gun's magazine is on the frame the prop appears (reload_s f15: the gun on the off hand, the prop on
tag_weapon_right) - so the hand-off is seamless; the rest follows the VB's hand path (the hand still lands on the VB's magazine well,
4.7 u ahead of the Bren's: a retargeted clip is the next step, see README).
    IRONSIGHT_EXTRA_PAKS=<ov.pk3> python build_bren_clip.py
"""
import sys, os, json
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa
os.chdir(_c)
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skx as X
import pk, skd as K

R = V.R
CLIP = 'models/human/animation/viewmodel/Vickers/coop_A_W_Vickers_reload_fps_s.skc'
F_ON = 15
OUT = r'H:\hzm_work\newguns\build\bren\ship\models\weapons\coop_bren\coop_bren_clip.skd'

c = R.load(CLIP)
t = F_ON * c.frameTime
Wb = R.evaluate(R.pose_dict(c, F_ON))
off = (0.0, c.numFrames * c.frameTime)
gun, _ = V.PR.gun_surfs(Wb, 'models/weapons/coop_bren.tik', 'reload_s', t, lambda f: False, 'tag_weapon_left')
mag = [s for s in gun if s['name'] == 'brenclip'][0]
prop, _ = V.PR.gun_surfs(Wb, 'models/weapons/Uk_W_Vickers_clip.tik', 'idle', t, lambda f: True, 'tag_weapon_right')
# the VB prop mesh: its skd-local verts vs their world positions -> affine local -> world
old = K.read(pk.read('models/weapons/Vickers/Uk_W_Vickers_clip.skd'))
Xl = np.array([np.asarray(v['pos'], float).reshape(-1, 3)[0] for v in old['surfaces'][0]['verts']])
Yw = np.asarray(prop[0]['P'])
assert len(Xl) == len(Yw)
Xa = np.hstack([Xl, np.ones((len(Xl), 1))])
M = np.linalg.lstsq(Xa, Yw, rcond=None)[0]
print('prop affine err', np.abs(Xa @ M - Yw).max().round(4))
Minv = np.linalg.inv(M[:3])
P = (np.asarray(mag['P']) - M[3]) @ Minv
tri = np.asarray(mag['tri'])
# normals: rebuild per face (the prop is small and flat-shaded enough at reload speed); UVs from the gun surface
UV = np.asarray(mag['UV'])
corners = []
for a, b, d in tri:
    p = P[[a, b, d]]
    n = np.cross(p[1] - p[0], p[2] - p[0]); n = n / max(np.linalg.norm(n), 1e-9)
    cc = [(1, p[k], -n, (float(UV[i, 0]), float(UV[i, 1]))) for k, i in enumerate((a, b, d))]
    corners.append(cc)
s = X.split_surfaces('brenclipprop', corners)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'wb').write(X.build_skd('coop_bren_clip', [('origin', 'worldbone'), ('Vickers_Clip', 'origin')], s))
print('wrote', OUT, len(tri), 'tris; local bounds', P.min(0).round(2), P.max(0).round(2), 'VB prop', Xl.min(0).round(2), Xl.max(0).round(2))
