"""hand bone positions in the GUN frame (gungeo frame of the gun on tag_weapon_right) for a view clip frame.
    python handpos.py <view clip> [frame]"""
import sys, os
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa
os.chdir(_c)
import numpy as np
R = V.R
c = R.load(sys.argv[1]); f = int(sys.argv[2]) if len(sys.argv) > 2 else 0
Wb = R.evaluate(R.pose_dict(c, f))
Tg = Wb['tag_weapon_right']; A = Tg[0:3, 0:3]; G = Tg[3, 0:3] * R.S
for b in sorted(Wb):
    if any(k in b.lower() for k in ('hand', 'finger0', 'finger2')) and ('l ' in b.lower() or 'r ' in b.lower() or 'left' in b.lower() or 'right' in b.lower()):
        p = Wb[b][3, 0:3] * R.S
        print('%-24s %s' % (b, np.round((p - G) @ np.linalg.inv(A), 2)))
