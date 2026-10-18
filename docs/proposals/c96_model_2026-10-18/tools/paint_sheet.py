"""Game diffuse sheet from the 4K PBR maps (via build/maps2048.npz, bl_tex.py): the engine has no spec / normal stage for
these weapon shaders (one `map` + rgbGen lightingSpherical, like every gun sheet), so the PBR look is BAKED into the diffuse:
  * metal (metallic map) is re-toned from the source's light grey to blued gun steel, keeping the wear / scratch detail
    (luminance), polished edges stay lighter;
  * wood (non-metal) keeps its colour, slightly lifted;
  * the normal map's edge strength darkens crevices and engraving (no sign convention needed);
  * roughness lifts smooth polished wear a little (the highlight a spec stage would have given).
    python paint_sheet.py [size]       -> build/c96_diffuse.png (+ build/c96_metalmask.png)
Params at the top; `--view` crops for a look.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy_free_filters import box_blur

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, '..', 'build')
STEEL = np.array([0.50, 0.56, 0.68])        # blue-grey tint of the steel (relative)
STEEL_GAIN = float(os.environ.get('C96_STEEL_GAIN', '0.85'))
STEEL_GAMMA = float(os.environ.get('C96_STEEL_GAMMA', '1.25'))
WOOD_GAIN = float(os.environ.get('C96_WOOD_GAIN', '1.45'))
EDGE_DARK = float(os.environ.get('C96_EDGE_DARK', '0.45'))
POLISH = float(os.environ.get('C96_POLISH', '0.30'))


def srgb_to_lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def main():
    d = np.load(os.path.join(B, 'maps2048.npz'))
    base = d['base'].astype(np.float32) / 255.0
    nrm = d['normal'].astype(np.float32) / 255.0 * 2 - 1
    rough = d['rough'][:, :, 0].astype(np.float32) / 255.0
    metal = d['metal'][:, :, 0].astype(np.float32) / 255.0
    lum = base @ np.array([0.299, 0.587, 0.114], np.float32)
    # edge strength of the normal map: gradient of nx, ny, at two scales
    gx = np.abs(np.gradient(nrm[:, :, 0], axis=1)) + np.abs(np.gradient(nrm[:, :, 1], axis=0))
    edge = box_blur(gx, 1) + 0.5 * box_blur(gx, 3)
    edge = np.clip(edge / (np.percentile(edge, 99) + 1e-6), 0, 1)
    # metal re-tone
    l2 = np.clip(lum, 0, 1) ** STEEL_GAMMA
    polish = np.clip((0.55 - rough) / 0.45, 0, 1) * POLISH               # smooth = lifted
    steel = (STEEL_GAIN * (l2[..., None] + polish[..., None])) * (STEEL / STEEL.mean())[None, None, :]
    wood = np.clip(base * WOOD_GAIN, 0, 1)
    m = np.clip((metal - 0.3) / 0.4, 0, 1)[..., None]
    out = steel * m + wood * (1 - m)
    out = out * (1.0 - EDGE_DARK * edge[..., None] * (0.35 + 0.65 * m))
    out = np.clip(out, 0, 1)
    img = Image.fromarray((out * 255 + 0.5).astype(np.uint8))
    img.save(os.path.join(B, 'c96_diffuse_final.png'))
    Image.fromarray((m[..., 0] * 255).astype(np.uint8)).save(os.path.join(B, 'c96_metalmask.png'))
    print('mean metal', float(steel[m[..., 0] > 0.5].mean()), 'mean wood', float(wood[m[..., 0] < 0.5].mean()))


if __name__ == '__main__':
    main()
