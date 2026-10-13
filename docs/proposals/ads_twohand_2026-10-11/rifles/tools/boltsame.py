"""Does a VARIANT tik play the capped aimed bolt row? The first-person model's silhouette (frame vs the same view
without the model, `__ref`) of the variant's capture is compared, frame by frame over the cycle, with the BASE rifle's
capped capture and with its uncapped (full retail stroke) capture: mean IoU of the model masks in the middle 40 % of
the picture. The finish changes colours, not the silhouette; sway moves it a few pixels in every run.

    python boltsame.py <variant run> <variant gun> <capped run> <uncapped run> <base gun> [--frames 30:80:2]
Runs are looked up in G:/mohaa-adsanim2/runs and H:/hzm_archive/rifles.
"""
import sys, os, glob
import numpy as np
from PIL import Image
ROOTS = ('G:/mohaa-adsanim2/runs/', 'H:/hzm_archive/rifles/')


def tagdir(run, gun):
    for r in ROOTS:
        for part in ('bolt', 'bolt2'):      # both start the same way: reference, 8 frames, the shot
            g = glob.glob('%s%s/ab__%s__%s__stand__%s__after__ref.jpg' % (r, run, run, gun, part))
            if g:
                return g[0][:-len('ref.jpg')]
    raise SystemExit('no capture: %s %s' % (run, gun))


def mask(pre, f):
    a = np.asarray(Image.open(pre + '%04d.jpg' % f).convert('RGB'), float)
    r = np.asarray(Image.open(pre + 'ref.jpg').convert('RGB'), float)
    h, w = a.shape[:2]
    y0, y1, x0, x1 = int(h * .3), int(h * .7), int(w * .3), int(w * .7)
    return (np.abs(a - r).sum(axis=2) > 60)[y0:y1, x0:x1]


def main():
    vrun, vgun, crun, urun, bgun = sys.argv[1:6]
    fr = '30:80:2'
    if '--frames' in sys.argv:
        fr = sys.argv[sys.argv.index('--frames') + 1]
    a, b, s = (int(x) for x in fr.split(':'))
    V, C, U = tagdir(vrun, vgun), tagdir(crun, bgun), tagdir(urun, bgun)
    iou = lambda p, q: (p & q).sum() / max(1, (p | q).sum())
    # only the frames in which the two BASE captures differ most (the bolt at the back of its stroke): the 8 lowest
    fs = sorted(range(a, b, s), key=lambda f: iou(mask(C, f), mask(U, f)))[:8]
    ic, iu = [], []
    for f in fs:
        mv, mc, mu = mask(V, f), mask(C, f), mask(U, f)
        ic.append(iou(mv, mc)); iu.append(iou(mv, mu))
    cu = np.mean([iou(mask(C, f), mask(U, f)) for f in fs])
    print('   frames', sorted(fs))
    print('%-28s vs %s capped (%s): IoU %.3f | vs uncapped (%s): IoU %.3f | base capped vs base uncapped: %.3f -> %s' % (
        vgun, bgun, crun, np.mean(ic), urun, np.mean(iu), cu, 'CAPPED row' if np.mean(ic) > np.mean(iu) + 0.03 else 'NOT DECIDED'))


if __name__ == '__main__':
    main()
