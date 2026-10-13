"""The armory's round-count picture for a 2-round gun: textures/hud/clip/clip_2.tga (the mod ships clip_1, _5, _6 ... -
a bar of N segments, 456 x 48; none for 2). Built from the mod's own clip_5.tga: its first and last segment's end
caps and its gap width, each segment stretched to the new width - same colours, same bevel, same gap.

    python tools/dbs_clip.py
"""
import os
import numpy as np
from PIL import Image
import dbslib as L

SRC = os.path.join(L.DOCS, '..', 'hzm-mohaa-coop-mod', 'textures', 'hud', 'clip', 'clip_5.tga')
OUT = os.path.join(L.ASSETS, 'textures', 'hud', 'clip', 'clip_2.tga')
N = 2

im = Image.open(SRC).convert('RGBA')
a = np.asarray(im)
W, H = im.size
col = a[..., 3].max(0) > 8                      # columns that carry a segment
edges = np.flatnonzero(np.diff(col.astype(int)))
starts = [0] if col[0] else []
starts += [e + 1 for e in edges if not col[e]]
ends = [e + 1 for e in edges if col[e]] + ([W] if col[-1] else [])
assert len(starts) == len(ends) == 5, (starts, ends)
gap = starts[1] - ends[0]
x0, x1 = starts[0], ends[-1]
segw = (x1 - x0 - gap * (N - 1)) / N
seg = im.crop((starts[0], 0, ends[0], H))
out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
cap = 6                                         # the bevel at a segment's ends is not stretched
for k in range(N):
    sx = round(x0 + k * (segw + gap)); ex = round(x0 + k * (segw + gap) + segw)
    w = ex - sx
    mid = seg.crop((cap, 0, seg.width - cap, H)).resize((w - 2 * cap, H), Image.BILINEAR)
    out.paste(seg.crop((0, 0, cap, H)), (sx, 0)); out.paste(mid, (sx + cap, 0)); out.paste(seg.crop((seg.width - cap, 0, seg.width, H)), (ex - cap, 0))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.save(OUT)
print('wrote', OUT, out.size, 'gap', gap, 'segment', round(segw, 1))
