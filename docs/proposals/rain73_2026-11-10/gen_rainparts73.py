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

# the drops (rain73 v2, coordinator QA: "spherical bubble sprites that look pasted on" - wanted refractive, varied, streaky):
# a drop on glass is mostly CLEAR - the world shows through it, bent: a thin dark meniscus at its edge, a bright refracted band
# low inside it (the sky above, flipped), a pin glint high on one side; alpha is high only at the rim and the bright band.
#   hzm_wx_glassdrop   round      hzm_wx_glassdrop2  irregular (a lobed outline)      hzm_wx_glassdrop3  a running trickle: a
#   heavier head at the BOTTOM of the sprite (v down the pane is image bottom) and a tapering, thinning tail up the pane
N = 64
g = (np.arange(N) + 0.5) / N * 2 - 1
X, Y = np.meshgrid(g, g)                  # Y -1 = top (up the pane)


def drop_sprite(r, X, Y, tail=None):
    edge = np.clip(1 - np.abs(r - 0.86) / 0.13, 0, 1)
    inside = np.clip((1.0 - r) / 0.07, 0, 1)
    band = np.exp(-((Y - 0.42) / 0.22) ** 2) * np.clip(1 - np.abs(X) / 0.85, 0, 1)           # the refracted sky, low inside
    glint = np.exp(-(((X + 0.30) ** 2 + (Y + 0.45) ** 2) / 0.010))
    col = np.clip(0.30 + 0.62 * band + 0.9 * glint - 0.20 * edge, 0, 1)
    al = inside * np.clip(0.10 + 0.55 * edge + 0.45 * band + 0.6 * glint, 0, 1)
    if tail is not None:
        al = np.maximum(al, tail)
    return col, al


def save(nm, col, al):
    rgb = np.dstack([col * 0.97, col * 0.99, col * 1.03]).clip(0, 1)
    Image.fromarray((np.dstack([rgb, al.clip(0, 1)]) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, nm + ".tga"))


r = np.sqrt(X * X + Y * Y)
save("hzm_wx_glassdrop", *drop_sprite(r, X, Y))
ang = np.arctan2(Y, X)
r2 = np.sqrt((X / 0.86) ** 2 + (Y / 1.0) ** 2) / (1.0 + 0.10 * np.sin(3 * ang + 0.7) + 0.06 * np.sin(5 * ang + 2.1))
save("hzm_wx_glassdrop2", *drop_sprite(r2, X, Y))
# the skylight's bead (seen small, up through the pane against the cloud: a rim alone vanishes at 6-18 px - a lens with BODY:
# brighter refracted lower half, darker upper, a clear rim line)
# (v3b, QA: the first body read as opaque grey bubbles) - mostly see-through: a dark rim line, the dark upper and bright lower
# lens kept, the middle only lightly tinted, a pin glint
lens = np.clip(0.5 + 0.6 * Y, 0, 1)
inside_s = np.clip((1.0 - r) / 0.10, 0, 1)
rim_s = np.clip(1 - np.abs(r - 0.84) / 0.12, 0, 1)
low = np.clip((Y - 0.15) / 0.6, 0, 1) * np.clip(1 - np.abs(X) / 0.8, 0, 1)
gl = np.exp(-(((X + 0.32) ** 2 + (Y + 0.40) ** 2) / 0.010))
col_s = np.clip(0.18 + 0.75 * lens - 0.18 * rim_s + 0.8 * gl, 0, 1)
save("hzm_wx_skydrop", col_s, inside_s * np.clip(0.16 + 0.55 * rim_s + 0.40 * low + 0.6 * gl, 0, 1))
# the trickle: head (round, lower 45 %), tail (upper part) a narrowing wet streak
hy = (Y - 0.45) / 0.55
rh = np.sqrt((X / 0.75) ** 2 + hy ** 2)
tw = 0.10 + 0.32 * np.clip((Y + 1.0) / 1.45, 0, 1)                   # the tail widens down towards the head
tail = np.clip(1 - np.abs(X) / tw, 0, 1) ** 1.5 * np.clip((Y + 0.95) / 0.5, 0, 1) * (Y < 0.2) * 0.42
c3, a3 = drop_sprite(rh, X, hy)
c3 = np.where(tail > a3, 0.36, c3)
save("hzm_wx_glassdrop3", c3, np.maximum(a3, tail))
# the trail bead: 32 x 32, soft, faint, a touch darker than the glass
M = 32
h = (np.arange(M) + 0.5) / M * 2 - 1
X2, Y2 = np.meshgrid(h, h)
r2 = np.sqrt((X2 / 0.45) ** 2 + (Y2 / 1.0) ** 2)
a2 = np.clip(1 - r2, 0, 1) ** 1.4 * 0.45
c2 = 0.45 + 0.25 * np.clip(Y2, 0, 1)
Image.fromarray((np.dstack([c2, c2, c2 * 1.04, a2]).clip(0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, "hzm_wx_glasstrail.tga"))

SH = ["// rain73 (gen_rainparts73.py): the dynamic rain's sprites - drawn by the engine (cl_uiscene.cpp WxRainDraw), vertex colour + alpha"]
for nm, sort in (("hzm_wx_streak", 8.40), ("hzm_wx_glassdrop", 8.50), ("hzm_wx_glassdrop2", 8.50), ("hzm_wx_glassdrop3", 8.50), ("hzm_wx_skydrop", 8.50), ("hzm_wx_glasstrail", 8.49)):
    SH.append("%s\n{\n\tnopicmip\n\tnomipmaps\n\tcull none\n\tsort %.2f\n\t{\n\t\tclampmap textures/menu/%s.tga\n\t\tblendFunc blend\n"
              "\t\trgbGen vertex\n\t\talphaGen vertex\n\t}\n}" % (nm, sort, nm))
open(os.path.join(sdir, "hzm_wxrain73.shader"), "w", newline="\n").write("\n\n".join(SH) + "\n")
print("rain parts -> %s" % add)
