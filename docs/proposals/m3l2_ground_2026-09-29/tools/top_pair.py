import sys, os, numpy as np
from PIL import Image, ImageDraw
import scene as SC, groundview as G, bsp_patch as BP, views as VW
gen, out = sys.argv[1], sys.argv[2]
region = tuple(float(v) for v in sys.argv[3].split(",")) if len(sys.argv) > 3 else (-4700, 1200, -2500, 3200)
ppu = 0.5
fy = np.asarray(Image.open(os.path.join(gen, "farmyard.png")).convert("RGB"))
rd = np.asarray(Image.open(os.path.join(gen, "road.png")).convert("RGB"))
orig = SC.bsp(); new, _ = BP.patch(orig)
a, _ = G.World(orig, region, res=2.0, zmax=60).topdown(SC.TexCache(), ppu)
b, _ = G.World(new, region, res=2.0, zmax=60, tcgen=VW.TCGEN).topdown(
    SC.TexCache({"textures/hzm_m3l2/farmyard": fy, "textures/hzm_m3l2/farmyard_b": fy, "textures/hzm_m3l2/road": rd}), ppu)
h, w = a.shape[:2]
im = Image.new("RGB", (w * 2 + 6, h)); im.paste(Image.fromarray(a), (0, 0)); im.paste(Image.fromarray(b), (w + 6, 0))
d = ImageDraw.Draw(im); d.text((6, 6), "BEFORE (live)", fill=(255, 255, 0)); d.text((w + 12, 6), "AFTER (proposal)", fill=(255, 255, 0))
im.save(out, quality=90)
