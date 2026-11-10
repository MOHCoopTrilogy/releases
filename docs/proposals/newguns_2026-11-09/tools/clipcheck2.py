"""First-person clip check of the Bren's reload hands (viewclip_2026-11-09 clip_survey.measure + hand_survey.frame_cover, run on the
Bren mesh instead of the VB): the VB's clips as shipped vs the retargeted Bren clips. Hip rows: since v1.10.67 (r_weaponProjAlways 1,
r_weaponznear 0.6) the hip is drawn with the WEAPON near plane, so `fix` (vertices nearer than 1 u) is the number that matters.
    IRONSIGHT_EXTRA_PAKS=... python clipcheck.py
"""
import sys, os, json
VC = r'C:\mohaa-coop-dev\docs\proposals\viewclip_2026-11-09\tools'
sys.path.insert(0, VC)
_c = os.getcwd(); os.chdir(VC)
import clip_survey as CS  # noqa: E402
import hand_survey as HS  # noqa: E402
os.chdir(_c)
import numpy as np  # noqa: E402
V, R = CS.V, CS.R
_load = R.load


def load(p):
    i = p.find('H:\\')
    return _load(p[i:] if i >= 0 else p)


R.load = load
V.SIGHTS['bren'] = dict(V.SIGHTS['vickers_berthier'], tik='models/weapons/coop_bren.tik')
CS.SAMPLES = 100
ctl = json.load(open(os.path.join(CS.BOLT, '..', 'assets', 'ctl_stand.json')))
VM = 'human/animation/viewmodel/Vickers/'
OUT = r'H:\hzm_work\newguns\brenhands\out2' + '\\'
pairs = [('reload', VM + 'A_W_Vickers_reload_fps.skc', OUT + 'coop_bren_reload_fps.skc'),
         ('reload_s', VM + 'coop_A_W_Vickers_reload_fps_s.skc', OUT + 'coop_bren_reload_fps_s.skc'),
         ('reload_m', VM + 'coop_A_W_Vickers_reload_fps_m.skc', OUT + 'coop_bren_reload_fps_m.skc')]
for name, old, new in pairs:
    for tag, p in (('VB clip', old), ('Bren clip', new)):
        r, n, ads = CS.measure('vickers_' + name, p if p.startswith('H:') else p.replace('human/animation/', ''), 'bren', ctl, None)
        print('%-9s %-9s arm_min %5.2f gun_min %5.2f  cut(r_znear 4) %d/%d  cut(weapon plane 1) %d/%d  nearest %.2f f%d' % (
            name, tag, r['arm'], r['gun'], r['cut16'], r['cut21'], r['fix16'], r['fix21'],
            r['worst_d'] if r['worst_d'] < 1e8 else -1, r['worst_f']))
