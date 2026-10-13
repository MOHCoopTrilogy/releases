"""Does the GUN stay put BETWEEN the keys of a hands clip? The engine blends every channel on its own between two
frames (rotations slerp, positions lerp); the weapon tag is a child of the firing hand, so while that hand moves off
its grip the tag is counter-keyed - exact on the keys, not between them. This prints, per clip frame, how far the
weapon tag is at the half-way point from the mean of its two keyed places (u, and deg of its axis).

Found 2026-10-13 (MP18, run se5): the gun jumped on every other 16 ms capture frame while the firing hand left the grip.

    cd smg/assets; python ../tools/midframe.py <clip.skc> [a:b] [--tag tag_weapon_right]
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smgbake as SB
R = SB.R


def mid_pose(pa, pb, u=0.5):
    pd = {}
    for ch in pa:
        a, b = np.asarray(pa[ch], float), np.asarray(pb[ch], float)
        pd[ch] = R.qslerp(a, b, u) if ch.endswith(' rot') else (1 - u) * a + u * b
    return pd


def scan(path, a=0, b=None, tag='tag_weapon_right'):
    c = R.load(path)
    b = c.numFrames - 1 if b is None else min(b, c.numFrames - 1)
    out = []
    for f in range(a, b):
        pa, pb = R.pose_dict(c, f), R.pose_dict(c, f + 1)
        Wa, Wb, Wm = R.evaluate(pa)[tag], R.evaluate(pb)[tag], R.evaluate(mid_pose(pa, pb))[tag]
        want = (Wa[3, 0:3] + Wb[3, 0:3]) / 2
        dpos = float(np.linalg.norm(Wm[3, 0:3] - want) * R.S)
        xa = (Wa[0, 0:3] + Wb[0, 0:3]); xa /= np.linalg.norm(xa)
        xm = Wm[0, 0:3] / np.linalg.norm(Wm[0, 0:3])
        dang = float(np.degrees(np.arccos(max(-1.0, min(1.0, xa @ xm)))))
        out.append((f, dpos, dang))
    return out


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    a, b = ([int(x) for x in args[1].split(':')] if len(args) > 1 else (0, None))
    tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'tag_weapon_right'
    r = scan(args[0], a, b, tag)
    worst = sorted(r, key=lambda x: -(x[1] + x[2]))[:10]
    print('%s: gun off its keyed path at the half-way point: max %.3f u, %.3f deg' % (os.path.basename(args[0]), max(x[1] for x in r), max(x[2] for x in r)))
    print('   worst frames (f: u / deg):', '  '.join('%d: %.2f / %.2f' % x for x in sorted(worst)))
