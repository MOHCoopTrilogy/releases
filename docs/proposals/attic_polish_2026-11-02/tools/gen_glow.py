"""gen_glow.py <out dir> - D-A5: a softer hover glow (textures/menu/hzm_hot_glow.jpg, additive, drawn by the engine's Scene3D at 1.9x the
hotspot radius).  The shipped one was a linear cone peaking at 251: a hot white-orange disc with a visible rim that read as a 2D sticker
over the prop.  This is a low gaussian (peak 150, sigma 0.30 of the half-size) with a smooth fade to 0 well inside the square, so a
hovered prop looks as if its lamp were turned up rather than spot-lit.  Shipped in the menus3d pak (it sorts after the asset pak)."""
import os, sys
import numpy as np
from PIL import Image
out = os.path.join(sys.argv[1], "textures", "menu")
os.makedirs(out, exist_ok=True)
n = 256
y, x = (np.mgrid[0:n, 0:n] + 0.5) / n * 2 - 1
r = np.sqrt(x * x + y * y)
g = np.exp(-(r / 0.42) ** 2 * 1.0)
win = np.clip((1.0 - r) / 0.25, 0, 1) ** 2 * (3 - 2 * np.clip((1.0 - r) / 0.25, 0, 1))
v = 150 * g * win
Image.fromarray(np.clip(v + 0.5, 0, 255).astype(np.uint8)).convert("RGB").save(os.path.join(out, "hzm_hot_glow.jpg"), quality=95)
print("glow ->", out, "peak", v.max())
