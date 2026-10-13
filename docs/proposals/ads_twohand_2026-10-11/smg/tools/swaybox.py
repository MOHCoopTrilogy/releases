"""How much of the centre box does the AIM ITSELF cover beyond its own mask while nothing happens (aim sway / breath
on)? reloadbox.py's measure (reference shifted to each frame's background, as there) over the settled aim AFTER the
reload: the 52 frames before the mask's own 6. If the settled aim alone is over the 2 % bar, no reload can pass with
sway on - the aim framing has to change. Also prints how far the rear sight wandered on screen in those frames.
(Until 2026-10-13 this tool compared against the UNSHIFTED reference: after a long burst the view is still creeping
back, and the backdrop then counted as cover - the plain MP40 read 3-6 % that way. Those figures are void.)

    python swaybox.py <session> <tag substring> [...]
"""
import sys, re
import numpy as np
from PIL import Image
import reloadbox as RBX

for sub in sys.argv[2:]:
    run, tag, marks, rows, fs = RBX.load(sys.argv[1], sub)
    mk = {n: (f, si) for n, f, si in marks}
    low = mk['lower'][0] if 'lower' in mk else len(fs)
    Rf = np.asarray(Image.open(run + tag + '__ref.jpg').convert('RGB')).astype(np.int16)
    H, W = Rf.shape[:2]
    box = (int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6))
    Rb = Rf[box[2]:box[3], box[0]:box[1]]
    sh = RBX.make_shifter(Rf, box)
    base = [RBX.mask(fs[i], Rb, box) for i in range(low - 8, low - 2)]
    aimmask = RBX.grow(np.mean(base, axis=0) > 0.3)
    post = [float((RBX.mask(fs[i], sh(fs[i])[0], box) & ~aimmask).mean()) for i in range(low - 60, low - 8)]
    print('%-34s settled aim after the reload, box beyond its own mask: max %.1f %% (%d of %d frames over 2 %%)' % (
        tag.split('__', 2)[2][:34], 100 * max(post), sum(e > 0.02 for e in post), len(post)))
