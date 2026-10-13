"""Where a gun's surfaces are, per frame of one of its own animations (gun frame u: x forward, +y right, +z DOWN as the
other tools print it): bounding box and centre of every surface whose name matches, or all of them.

    cd rifles/assets; python ../tools/surfinfo.py models/weapons/kar98.tik reload 43,52,53,61 [material]
"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_c = os.getcwd(); os.chdir(T)
import staged  # noqa
import vmcam as V
os.chdir(_c)
G = V.PR.gungeo


def main():
    tik, anim, frames = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
    pat = sys.argv[4].lower() if len(sys.argv) > 4 else ''
    for f in frames:
        g = G.load_gun(tik, anim=anim, frame=f)
        for s in g['surfs']:
            if pat and pat not in s['name'].lower():
                continue
            P = np.asarray(s['P'], float)
            print('f%-3d %-14s %4d v  x %6.2f..%6.2f  y %6.2f..%6.2f  z %6.2f..%6.2f   centre %6.2f %6.2f %6.2f' % (
                f, s['name'], len(P), P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max(), P[:, 2].min(), P[:, 2].max(),
                *P.mean(0)))


if __name__ == '__main__':
    main()
