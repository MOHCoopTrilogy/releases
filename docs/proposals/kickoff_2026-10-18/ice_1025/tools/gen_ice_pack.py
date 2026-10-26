"""gen_ice_pack.py - builds textures/hzm/ice_pack.tga (and the gl1 colour tile) from ambientCG Ice001 (CC0).

  python gen_ice_pack.py [out_dir]     default H:/hzm_work/ice1025_assets

ice_pack.tga, 1024x1024 RGBA: R,G = GL normal x,y (as shipped by ambientCG, 0..255), B = roughness, A = colour luminance.
The water pass (glsl/hzmwater_fp.glsl, ICE and COLD presets) maps the luminance to clear-ice blue / bubble white itself,
so the colour is carried as ONE channel. Source: https://ambientcg.com/a/Ice001 (CC0 1.0). Input read as DATA only.
Also writes ice_gl1.tga: a blue-graded 512 colour tile for the gl1 fallback shader (same luminance mapping, baked).
"""
import os, sys
import numpy as np
from PIL import Image

SRC = r"H:\hzm_work\ice1025_textures\Ice001"
OUT = sys.argv[1] if len(sys.argv) > 1 else r"H:\hzm_work\ice1025_assets"
os.makedirs(OUT + r"\textures\hzm", exist_ok=True)
col = Image.open(SRC + r"\Ice001_2K-JPG_Color.jpg").convert("RGB").resize((1024, 1024), Image.LANCZOS)
nrm = Image.open(SRC + r"\Ice001_2K-JPG_NormalGL.jpg").convert("RGB").resize((1024, 1024), Image.LANCZOS)
rgh = Image.open(SRC + r"\Ice001_2K-JPG_Roughness.jpg").convert("L").resize((1024, 1024), Image.LANCZOS)
c = np.asarray(col, np.float32) / 255.0
lum = (c * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1)
n = np.asarray(nrm, np.uint8)
pack = np.zeros((1024, 1024, 4), np.uint8)
pack[..., 0] = n[..., 0]
pack[..., 1] = n[..., 1]
pack[..., 2] = np.asarray(rgh, np.uint8)
pack[..., 3] = np.clip(lum * 255 + 0.5, 0, 255).astype(np.uint8)
Image.fromarray(pack, "RGBA").save(OUT + r"\textures\hzm\ice_pack.tga")
# gl1: baked clear-ice colour, same mapping as the shader: k = clamp((lum-0.18)/0.55)^1.1 ; mix(deep, white, k)
k = np.clip((lum - 0.18) / 0.55, 0, 1) ** 1.1
deep = np.array([0.035, 0.11, 0.20], np.float32); white = np.array([0.80, 0.90, 0.98], np.float32)
g1 = deep[None, None] * (1 - k[..., None]) + white[None, None] * k[..., None]
g1 = np.clip(np.power(g1, 1 / 2.2) * 255 + 0.5, 0, 255).astype(np.uint8)
Image.fromarray(g1, "RGB").resize((512, 512), Image.LANCZOS).save(OUT + r"\textures\hzm\ice_gl1.tga")
print("wrote", OUT)
