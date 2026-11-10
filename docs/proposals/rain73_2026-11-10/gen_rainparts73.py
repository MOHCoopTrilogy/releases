"""gen_rainparts73.py <add dir> - rain73 stages 2 + 3 content: the sprites the engine's dynamic rain draws (cl_uiscene.cpp WxRainDraw).

  hzm_wx_streak     a falling streak: a thin soft line, brightest mid-way, fading at both ends (motion blur of a drop)
  hzm_wx_glassdrop  a drop on glass: a lens - the world above it seen upside down, so DARK in its upper half and LIGHT in its lower,
                    a thin dark rim and a small glint high on the light side (texture v up = up the pane, the engine orients it)
  hzm_wx_glasstrail the wet trail a running drop leaves: a faint, slightly elongated smear
All rgbGen / alphaGen vertex (the engine sets brightness from the daylight and a strike, alpha from the intensity / the trail's life),
blendFunc blend, cull none; sorts after the fog banks (8.2x) and the town: streaks 8.40, glass 8.50.
"""
import math, os, sys
import numpy as np
from PIL import Image

add = sys.argv[1]
tdir, sdir = os.path.join(add, "textures", "menu"), os.path.join(add, "scripts")
os.makedirs(tdir, exist_ok=True)
os.makedirs(sdir, exist_ok=True)

# the streak: 16 x 128, a gaussian line across, a smooth bump along
W, H = 16, 128
x = (np.arange(W) + 0.5) / W * 2 - 1
y = (np.arange(H) + 0.5) / H
a = np.exp(-(x[None, :] / 0.28) ** 2) * (np.sin(np.pi * y)[:, None] ** 0.8)
Image.fromarray((np.dstack([np.ones((H, W, 3)), a[..., None]])[..., :4] * 255).astype(np.uint8).reshape(H, W, 4), "RGBA") \
    .save(os.path.join(tdir, "hzm_wx_streak.tga"))

# the drop: 64 x 64 lens (image row 0 = up the pane)
N = 64
g = (np.arange(N) + 0.5) / N * 2 - 1
X, Y = np.meshgrid(g, g)                  # Y -1 = top (up the pane)
r = np.sqrt(X * X + Y * Y)
inside = np.clip((1.0 - r) / 0.08, 0, 1)
lens = np.clip(0.5 + 0.55 * Y, 0, 1)      # dark top, light bottom
rim = np.clip(1 - np.abs(r - 0.86) / 0.14, 0, 1)
glint = np.exp(-(((X + 0.32) ** 2 + (Y + 0.42) ** 2) / 0.012))
col = np.clip(0.22 + 0.62 * lens - 0.25 * rim + 0.8 * glint, 0, 1)
al = inside * np.clip(0.50 + 0.30 * rim + 0.25 * glint, 0, 1)
rgb = np.dstack([col * 0.97, col * 0.99, col * 1.03]).clip(0, 1)
Image.fromarray((np.dstack([rgb, al]) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, "hzm_wx_glassdrop.tga"))
# the trail bead: 32 x 32, soft, faint, a touch darker than the glass
M = 32
h = (np.arange(M) + 0.5) / M * 2 - 1
X2, Y2 = np.meshgrid(h, h)
r2 = np.sqrt((X2 / 0.8) ** 2 + (Y2 / 1.0) ** 2)
a2 = np.clip(1 - r2, 0, 1) ** 1.4 * 0.7
c2 = 0.45 + 0.25 * np.clip(Y2, 0, 1)
Image.fromarray((np.dstack([c2, c2, c2 * 1.04, a2]).clip(0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, "hzm_wx_glasstrail.tga"))

SH = ["// rain73 (gen_rainparts73.py): the dynamic rain's sprites - drawn by the engine (cl_uiscene.cpp WxRainDraw), vertex colour + alpha"]
for nm, sort in (("hzm_wx_streak", 8.40), ("hzm_wx_glassdrop", 8.50), ("hzm_wx_glasstrail", 8.49)):
    SH.append("%s\n{\n\tnopicmip\n\tnomipmaps\n\tcull none\n\tsort %.2f\n\t{\n\t\tclampmap textures/menu/%s.tga\n\t\tblendFunc blend\n"
              "\t\trgbGen vertex\n\t\talphaGen vertex\n\t}\n}" % (nm, sort, nm))
open(os.path.join(sdir, "hzm_wxrain73.shader"), "w", newline="\n").write("\n\n".join(SH) + "\n")
print("rain parts -> %s" % add)
