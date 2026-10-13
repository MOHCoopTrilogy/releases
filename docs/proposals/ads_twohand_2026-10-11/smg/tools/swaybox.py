"""How much of the centre box does the AIM ITSELF cover beyond its own mask while nothing happens (aim sway / breath
on)? reloadbox.py's measure over the settled aim BEFORE the first shot of an `sdemo` capture and after the reload.
If the settled aim alone is over the 2 % bar, no reload can pass with sway on - the aim framing has to change.

    python swaybox.py <session> <tag substring> [...]
"""
import sys
import numpy as np
from PIL import Image
import reloadbox as RBX

for sub in sys.argv[2:]:
    run, tag, marks, rows, fs = RBX.load(sys.argv[1], sub)
    mk = {n: (f, si) for n, f, si in marks}
    low = mk['lower'][0] if 'lower' in mk else len(fs)
    first = [n for n in marks if n[0] == 'fire'][0][1]
    Rf = np.asarray(Image.open(run + tag + '__ref.jpg').convert('RGB')).astype(np.int16)
    H, W = Rf.shape[:2]
    box = (int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6))
    Rb = Rf[box[2]:box[3], box[0]:box[1]]
    base = [RBX.mask(fs[i], Rb, box) for i in range(low - 8, low - 2)]
    aimmask = RBX.grow(np.mean(base, axis=0) > 0.3)
    pre = [float((RBX.mask(fs[i], Rb, box) & ~aimmask).mean()) for i in range(mk['raise'][0] + 45, first - 1)]
    post = [float((RBX.mask(fs[i], Rb, box) & ~aimmask).mean()) for i in range(low - 60, low - 8)]
    print('%-34s settled aim, box beyond its own mask: before the shots max %.1f %% (%d of %d frames over 2 %%), after the reload max %.1f %% (%d of %d)' % (
        tag.split('__', 2)[2][:34], 100 * max(pre or [0]), sum(e > 0.02 for e in pre), len(pre), 100 * max(post), sum(e > 0.02 for e in post), len(post)))
