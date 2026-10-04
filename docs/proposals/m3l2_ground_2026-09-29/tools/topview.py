import sys, time, numpy as np
from PIL import Image, ImageDraw
import scene as SC, groundview as G
region = tuple(float(v) for v in sys.argv[1].split(","))
out = sys.argv[2]; ppu = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
zmax = float(sys.argv[4]) if len(sys.argv) > 4 else 60
t = time.time()
w = G.World(SC.bsp(), region, res=2.0, zmax=zmax)
tc = SC.TexCache()
img, sid = w.topdown(tc, ppu)
# legend: outline surfaces by shader
names = w.surf_shader
im = Image.fromarray(img); d = ImageDraw.Draw(im)
H, W = sid.shape
lab = {}
for s in np.unique(sid):
    if s < 0: continue
    ys, xs = np.nonzero(sid == s)
    lab.setdefault(names[s], []).append((xs.mean(), ys.mean(), len(xs)))
for nm, L in lab.items():
    for x, y, n in L:
        if n > 1500:
            d.text((x - 20, y), nm.split("/")[-1][:18], fill=(255, 255, 0))
# grid every 256u
x0, y0, x1, y1 = region
for gxw in np.arange(np.ceil(x0 / 256) * 256, x1, 256):
    X = (gxw - x0) * ppu; d.line([(X, 0), (X, H)], fill=(80, 80, 255)); d.text((X + 2, 2), "%d" % gxw, fill=(120, 120, 255))
for gyw in np.arange(np.ceil(y0 / 256) * 256, y1, 256):
    Y = (y1 - gyw) * ppu; d.line([(0, Y), (W, Y)], fill=(80, 80, 255)); d.text((2, Y + 2), "%d" % gyw, fill=(120, 120, 255))
im.save(out, quality=90)
print("done %.1fs" % (time.time() - t), {k: v for k, v in tc.src.items()})
