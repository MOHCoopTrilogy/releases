"""PROVE the rack grasp (user 2026-10-12: "Make sure the hand is actually over the slide on the hi standard"): per frame of
a baked hands clip, the left hand measured against the slide in GUN space (weapon tag: x fwd, y right, z down; u).

    cd stage; python ../rackcheck.py <hands clip> <gun name in pistolgun.GUNS> <pull0> <pull1> <fwd0> <fwd1> [frames a:b]
prints per frame: slide travel (from the shared rack_slide), hand travel along the bore (wrist x minus its x at the grasp),
palm height above the slide top, palm / thumb / finger sides against the slide's two flanks.
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
import pistolgun
H = RB.H; R = RB.R
clip, name = sys.argv[1], sys.argv[2]
pull = (int(sys.argv[3]), int(sys.argv[4])); fwd = (int(sys.argv[5]), int(sys.argv[6]))
a0, a1 = [int(x) for x in sys.argv[7].split(':')] if len(sys.argv) > 7 else (pull[0] - 3, fwd[1] + 4)
sp = json.load(open(os.path.join(HERE, 'slide_%s.json' % name)))
SL = dict(x0=-1.04, x1=5.4, yl=-1.03, yr=0.15, top=-2.93)            # the slide island of the Hi-Standard mesh (meshparts.py), rest pose
a = R.load(clip)
x_ref = None
print('frame | slide back u | hand back u | palm above slide top u | palm y (slide spans %.2f..%.2f) | thumb tip y,z | middle finger tip y,z | index tip y,z' % (SL['yl'], SL['yr']))
for f in range(a0, a1 + 1):
    W = R.evaluate(R.pose_dict(a, f))
    Gi = R.inv(W['tag_weapon_right'])
    P = lambda b: (W[b] @ Gi)[3, :3] * R.S
    wr = P('Bip01 L Hand')
    kn = P('Bip01 L Finger2')                    # middle finger's knuckle: palm = between it and the wrist
    palm = 0.5 * (wr + kn)
    th, mi, ix = P('Bip01 L Finger02'), P('Bip01 L Finger22'), P('Bip01 L Finger12')
    sb = pistolgun.rack_slide(f, pull, fwd) * sp['travel']
    if f == pull[0]:
        x_ref = wr[0]
    hb = (x_ref - wr[0]) if x_ref is not None else 0.0
    print('f%-3d | %5.2f | %5.2f | %5.2f | %5.2f | %5.2f %5.2f | %5.2f %5.2f | %5.2f %5.2f   palm x %.1f (slide rear at %.1f)' % (
        f, sb, hb, SL['top'] - palm[2], palm[1], th[1], th[2], mi[1], mi[2], ix[1], ix[2], palm[0], SL['x0'] - sb))
