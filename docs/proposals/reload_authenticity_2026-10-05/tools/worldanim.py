"""worldanim.py - world (gun) reload anims for the magazine-swap guns, driven by swapsched.py so the bolt / cocking
handle moves on exactly the frames the hand is on it. Output is 1/30 s, frame count = the hand clip.

  tommy50: models/weapons/Thompson/coop_tommy50_reload.skc  (retail ThompsonSMG_reload.skc re-keyed: every bone at
           its frame-0 pose, Bolt between its rest pose (f0) and its forward pose (f8) by swapsched weight)
  mp18:    models/weapons/coop_mp18/coop_mp18_reload.skc     (mp18_reload.skc frame 0 for every bone - the drum stays
           on the gun, the prop does the moving - Bone2 between rest (f0) and pulled (f72) by swapsched weight)

    python worldanim.py [tommy50] [mp18]
"""
import os, sys, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swapsched as SS
from skc_slice import slice_skc
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T)
_cwd = os.getcwd(); os.chdir(T)
import vmcam as V   # noqa: E402
os.chdir(_cwd)
R = V.R
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'

JOBS = {
    'tommy50': dict(src=('vfs', 'models/weapons/Thompson/ThompsonSMG_reload.skc'), base=0, a=0, b=8, bone='Bolt',
                    out='models/weapons/Thompson/coop_tommy50_reload.skc'),
    'mp18': dict(src=('git', 'models/weapons/coop_mp18/coop_mp18_reload.skc'), base=0, a=0, b=72, bone='Bone2',
                 out='models/weapons/coop_mp18/coop_mp18_reload.skc'),
}


def src_bytes(kind, path):
    if kind == 'vfs':
        return R.vfs.read(path)
    return subprocess.run(['git', '-C', MOD, 'show', 'HEAD:' + path],
                          capture_output=True, check=True).stdout


def build(gun):
    j = JOBS[gun]
    n = SS.GUNS[gun]['nframes']
    raw = src_bytes(*j['src'])
    src = R.skc_io.read(raw)
    va = [list(v) for v in src.values[j['a']]]; vb = src.values[j['b']]
    out = R.skc_io.read(slice_skc(raw, [j['base']] * n, 1.0 / 30))
    ci = {nm: i for i, nm in enumerate(out.names)}
    cp, cr = ci['%s pos' % j['bone']], ci['%s rot' % j['bone']]
    for f in range(n):
        w = SS.bolt_w(gun, f)
        out.values[f][cp] = [va[cp][k] * (1 - w) + vb[cp][k] * w for k in range(3)] + [va[cp][3]]
        q = R.qslerp(np.array(va[cr]), np.array(vb[cr]), w)
        out.values[f][cr] = [float(x) for x in q]
    data = R.skc_io.write(out)
    p = os.path.join(MOD, j['out'])
    open(p, 'wb').write(data)
    print('wrote', p, n, 'frames')


if __name__ == '__main__':
    for g in sys.argv[1:] or list(JOBS):
        build(g)
