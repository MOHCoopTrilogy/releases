"""Where is the support (left) hand relative to the gun in the HIP idle and in the AIM pose of every view-model prefix?
(user 2026-10-12: in ADS "the left hand should stay on the mag ... for any weapon where the mag is braced")

Wrist place in the gun frame (weapon tag: x forward, y right, z down; u), hip idle frame 0 against the aim pose row
(`<prefix>_charge`, else the idle itself); `d` = how far apart, `match` = within 1.5 u. Staged aim poses given as
prefix=clip arguments (the mkov form) are used instead of the released row.

    cd stage; python ../handsurvey.py [prefix=clip ...]     -> handsurvey.json (read by coverage.py)
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
H = RB.H; R = RB.R


def rel(clip):
    a = R.load(R.ANIM + clip)
    W = R.evaluate(R.pose_dict(a, 0))
    return ((W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']))[3, :3] * R.S).round(1).tolist()


rows = H.fps_rows()
staged = dict(a.split('=') for a in sys.argv[1:] if '=' in a and not a.startswith('row:'))
out = {}
for k in sorted(rows):
    if not (k.endswith('_idle') or k.endswith('_idle1')):      # retail prefixes number their idles
        continue
    pfx = k[:k.rindex('_idle')]
    if pfx in out:
        continue
    aimrow = staged.get(pfx) or rows.get(pfx + '_charge') or rows[k]
    try:
        h, a = rel(rows[k]), rel(aimrow)
    except Exception as e:
        continue
    d = float(np.linalg.norm(np.array(h) - np.array(a)))
    out[pfx] = dict(hip=h, aim=a, d=round(d, 1), match=bool(d <= 1.5), aim_clip=aimrow, hip_clip=rows[k], staged=pfx in staged)
json.dump(out, open(os.path.join(HERE, 'handsurvey.json'), 'w'), indent=1, sort_keys=True)
for p, v in sorted(out.items(), key=lambda kv: -kv[1]['d']):
    print('%-14s hip %-20s aim %-20s d %4.1f %s %s' % (p, v['hip'], v['aim'], v['d'], 'match' if v['match'] else 'MISMATCH', '(staged)' if v['staged'] else ''))
