"""Hip idle with the support hand's fingers ALREADY curled as in the two-handed aim (P38 sheet: "two open fingers show for
a frame or two as the left hand arrives" - the raise is an engine crossblend from the hip idle, whose left hand hangs
open out of view; its fingers were still half open when the hand reached the gun). Only the left FINGER channels
change; the hand is out of view at the hip.

    python idle2h.py <stage root>     -> coop_<prefix>_idle2h.skc per pistol prefix + idle_rows.txt (row repoints for mkov)
"""
import sys, os, hashlib
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import hold_bake as H
os.chdir(_c)
R = H.R
HERE = os.path.dirname(os.path.abspath(__file__))
root = sys.argv[1]
AIM = {'colt45': 'viewmodel/pistol/colt45_ads2h.skc', 'p38': 'viewmodel/pistol/p38_ads2h.skc',
       'histandard': 'viewmodel/pistol/histandard_ads2h.skc', 'beretta': 'viewmodel/beretta/beretta_ads2h.skc',
       'webley': 'viewmodel/webley/webley_ads2h.skc', 'nagantrev': 'viewmodel/nagantrev/nagantrev_ads2h.skc',
       'm10': 'viewmodel/coop_m10/m10_ads2h.skc'}
rows = H.fps_rows()
args = []
for pfx, aimc in AIM.items():
    idle = rows[pfx + '_idle']
    a = R.load(R.ANIM + idle)
    aim = R.load(os.path.join(root, 'models', 'human', 'animation', aimc.replace('/', os.sep)))
    pa = R.pose_dict(aim, aim.numFrames - 1)
    cm = R.chanmap(a)
    n = 0
    for ch in a.names:
        if ch.startswith('Bip01 L Finger') and ch.endswith(' rot') and ch in pa:
            for f in range(a.numFrames):
                v = np.asarray(pa[ch], float)
                if v @ a.V[f, cm[ch]] < 0:
                    v = -v
                a.V[f, cm[ch]] = v
            n += 1
    a.values = [[[float(np.float32(x)) for x in a.V[f, c]] for c in range(a.numChannels)] for f in range(a.numFrames)]
    out = '%s/coop_%s_idle2h.skc' % (os.path.dirname(aimc), pfx)
    dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
    b = R.skc_io.write(a)
    open(dst, 'wb').write(b)
    args.append('row:%s_idle=%s' % (pfx, out))
    print(pfx, idle, '->', out, a.numFrames, 'frames,', n, 'finger channels', hashlib.md5(b).hexdigest()[:8])
open(os.path.join(HERE, 'ovargs_idle.txt'), 'w').write(' '.join(args) + '\n')
