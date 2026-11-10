"""First-person clip check of the MP 28's own hip reloads vs the Sten's (viewclip clip_survey.measure, hip rows, MP 28 mesh)."""
import sys, os, json
VC = r'C:\mohaa-coop-dev\docs\proposals\viewclip_2026-11-09\tools'
sys.path.insert(0, VC)
_c = os.getcwd(); os.chdir(VC)
import clip_survey as CS  # noqa: E402
os.chdir(_c)
V, R = CS.V, CS.R
_load = R.load


def load(p):
    i = p.find('H:\\')
    return _load(p[i:] if i >= 0 else p)


R.load = load
CS.SAMPLES = 100
ctl = json.load(open(os.path.join(CS.BOLT, '..', 'assets', 'ctl_stand.json')))
V.SIGHTS['mp28'] = dict(V.SIGHTS['sten_mark_ii'], tik='models/weapons/coop_bergmann.tik')
O = 'H:\\hzm_work\\newguns\\brenhands\\out_mp28\\'
SRC = {'coop_mp28_reload_hip': 'coop_sten_reload_hip', 'coop_mp28_reload_empty_hip': 'coop_sten_reload_empty_hip',
       'coop_mp28_reload_hip_s': 'coop_sten_reload_hip_s', 'coop_mp28_reload_hip_m': 'coop_sten_reload_hip_m',
       'coop_mp28_reload_empty_hip_s': 'coop_sten_reload_empty_hip_s', 'coop_mp28_reload_empty_hip_m': 'coop_sten_reload_empty_hip_m'}
for name, src in SRC.items():
    for tag, p in (('Sten', 'viewmodel/sten/' + src + '.skc'), ('MP28', O + name + '.skc')):
        r, n, ads = CS.measure('sten_reload', p, 'mp28', ctl, None)
        print('%-30s %-5s arm_min %5.2f gun_min %5.2f cut(weapon plane 1) %d/%d' % (name, tag, r['arm'], r['gun'], r['fix16'], r['fix21']))
