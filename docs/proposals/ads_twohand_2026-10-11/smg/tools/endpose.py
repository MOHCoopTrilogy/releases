"""Is a staged aimed clip's first / last frame really the aim pose? Per frame: the angle between the clip's gun (weapon
tag, world) and the aim pose's, the tag's offset, and the largest channel difference. A clip that ends 0.06 deg off
shows it for as long as the engine holds its rig solve.

    cd smg/assets; python ../tools/endpose.py <gun> [ads_loaded|ads_empty] [--frames 0,1,70,73,74,75]
"""
import sys, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smgbake as SB
R = SB.R
name = sys.argv[1]
which = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'ads_loaded'
g = SB.GUNS[name]
path, _ = SB.clip_of(name, '.', which)
c = R.load(path)
aimp = os.path.join('models', 'human', 'animation', g['aim'].replace('/', os.sep))
ac = R.load(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'])
pa = R.pose_dict(ac, ac.numFrames - 1)
Wa = R.evaluate(pa)
fr = [int(x) for x in sys.argv[sys.argv.index('--frames') + 1].split(',')] if '--frames' in sys.argv else [0, 1, 2, c.numFrames - 4, c.numFrames - 3, c.numFrames - 2, c.numFrames - 1]
print('%s %s (%d frames) against %s' % (name, which, c.numFrames, g['aim']))
for f in fr:
    pc = R.pose_dict(c, f)
    Wc = R.evaluate(pc)
    Ga, Gc = Wa['tag_weapon_right'], Wc['tag_weapon_right']
    ang = math.degrees(math.acos(max(-1.0, min(1.0, float(Ga[0, 0:3] @ Gc[0, 0:3]) / (np.linalg.norm(Ga[0, 0:3]) * np.linalg.norm(Gc[0, 0:3]))))))
    off = float(np.linalg.norm(Ga[3, 0:3] - Gc[3, 0:3]) * R.S)
    def diff(ch):
        a, b = np.asarray(pc[ch], float), np.asarray(pa[ch], float)
        if ch.endswith(' rot') and float(a @ b) < 0:        # q and -q are the same rotation
            b = -b
        return float(np.abs(a - b).max())
    worst = max(((diff(ch), ch) for ch in pc if ch in pa), default=(0.0, '-'))
    print('   f%-3d gun axis %.3f deg off the aim pose, tag %.3f u off; largest channel difference %.5f (%s)' % (f, ang, off, worst[0], worst[1]))
