"""gen_cold_gl1.py - the two tileable gl1/fallback textures of the cold-harbour water look (no source art: generated).

  textures/hzm/coldwater.tga      256x256 RGB: dark green-grey-black body with slow soft ripple luminance (+-22 %)
  textures/hzm/coldwater_add.tga  256x256 RGB: very dim cold streaks for the additive second layer (0..~38 / 255)

Tileable by construction (FFT-filtered noise on the torus). Deterministic (fixed seeds).
  python gen_cold_gl1.py [out_dir]     default H:/hzm_work/ice1025_assets
"""
import os, sys
import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else r"H:\hzm_work\ice1025_assets"
os.makedirs(OUT + r"\textures\hzm", exist_ok=True)
N = 256


def field(seed, kmin, kmax, aniso=1.0):
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(N) * N
    kx, ky = np.meshgrid(f, f)
    k = np.sqrt((kx / aniso) ** 2 + ky ** 2)
    amp = np.where((k >= kmin) & (k <= kmax), k ** -1.4, 0.0)
    ph = rng.uniform(0, 2 * np.pi, (N, N))
    a = np.real(np.fft.ifft2(amp * np.exp(1j * ph)))
    a = (a - a.mean()) / a.std()
    return a


body_n = field(11, 2, 14)
base = np.array([32, 54, 56], np.float32)                      # sRGB ~ the COLD deep colour once lit
img = base[None, None] * (1 + 0.22 * np.tanh(body_n[..., None] * 0.9))
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(OUT + r"\textures\hzm\coldwater.tga")

st = field(23, 3, 22, aniso=2.5)
v = np.clip(0.5 + 0.5 * np.tanh(st * 1.2), 0, 1) ** 2.2
add = (v[..., None] * np.array([26, 38, 40], np.float32)[None, None])
Image.fromarray(np.clip(add, 0, 255).astype(np.uint8), "RGB").save(OUT + r"\textures\hzm\coldwater_add.tga")
print("wrote", OUT)
