"""One 2048 game sheet from the Bren's PBR maps (H:/hzm_work/newguns/src/bren/textures, untrusted PNG data, read only).

The weapon shaders have one texture stage + rgbGen lightingSpherical, so the PBR look is BAKED into the diffuse: the fg42hd
atlas.py recipe (normal-map relief lit from the gun's left, edge darkening, the BaseColor's wear kept as luminance on metal,
oiled walnut for the wood), on the source's own single UV layout (no tiling needed: one material, one 0..1 UV set).
[QA 2026-11-09] the source's barrel and flash hider are bright bare steel (it read as chrome in the preview): the steel tone is
compressed (L_CAP), so every steel part sits in the receiver's dark range.
    python bren_sheet.py   -> H:/hzm_work/newguns/build/bren/bren.png / .jpg / bren_metal.png
"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools")
from scipy_free_filters import box_blur

Image.MAX_IMAGE_PIXELS = None
SRC = r"H:/hzm_work/newguns/src/bren/textures"
OUT = r"H:/hzm_work/newguns/build/bren"
N = int(os.environ.get('BREN_N', '2048'))
EMB, EDGE_DARK, POLISH = 0.85, 0.45, 0.12
STEEL = np.array([0.84, 0.88, 0.95], np.float32)
L_CAP = 0.55                        # steel luminance ceiling (the bare barrel)
STEEL_GAIN = float(os.environ.get('NG_STEEL_GAIN', '1.75'))
WOOD_GAIN, WOOD_TINT = 0.80, np.array([0.95, 0.86, 0.80], np.float32)
WOOD_SAT, WOOD_GRAIN = 0.55, 1.4


# [newguns] the same bake serves every single-material source: GUN=pzf reads the Panzerfaust's maps (its BaseColor with the
# labels re-lettered by pzf_decal.py; it has no AO map)
GUN = os.environ.get('NG_GUN', 'bren')
FILES = {'bren': (SRC, OUT, 'bren', {k: 'BrenLMG_%s.tga.png' % k for k in ('Basecolor', 'Normal', 'Roughness', 'Metalness', 'AO')}),
         'pzf': (r"H:/hzm_work/newguns/src/panzerfaust/source/panzerfaust60/textures", r"H:/hzm_work/newguns/build/pzf", 'pzf',
                 {'Basecolor': r'H:/hzm_work/newguns/build/pzf/base_fixed.png', 'Normal': 'Material.001_Normal.png',
                  'Roughness': 'Material.001_Roughness.png', 'Metalness': 'Material.001_Metallic.png'})}
SRC, OUT, NAME, MAPS = FILES[GUN]
if GUN == 'pzf':   # its non-metal is PAINTED STEEL (dunkelgelb), not walnut: keep the colour, no grain boost
    WOOD_GAIN, WOOD_TINT, WOOD_SAT, WOOD_GRAIN = 0.80, np.array([1.0, 0.97, 0.92], np.float32), 0.90, 0.35
    STEEL_GAIN = 1.0


def load(kind, ch3):
    if kind not in MAPS:
        return None
    im = Image.open(os.path.join(SRC, MAPS[kind])).convert('RGB' if ch3 else 'L').resize((N, N), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def main():
    base = load('Basecolor', True); nrm = load('Normal', True) * 2 - 1
    rough = load('Roughness', False); metal = load('Metalness', False); ao = load('AO', False)
    ao = ao if ao is not None else np.ones((N, N), np.float32)
    lum = base @ np.array([0.299, 0.587, 0.114], np.float32)
    m = np.clip((metal - 0.3) / 0.4, 0, 1)
    emb = np.clip(-0.9 * nrm[:, :, 0] + 0.25 * nrm[:, :, 1], -1.2, 1.2)
    gx = np.abs(np.gradient(nrm[:, :, 0], axis=1)) + np.abs(np.gradient(nrm[:, :, 1], axis=0))
    edge = box_blur(gx, 1) + 0.5 * box_blur(gx, 3)
    edge = np.clip(edge / (np.percentile(edge, 99) + 1e-6), 0, 1)
    l0 = np.minimum(np.clip((lum - 0.10) / 0.55, 0, 1) ** 1.2, L_CAP)
    polish = np.clip((0.55 - rough) / 0.45, 0, 1) * POLISH
    aof = (0.35 + 0.65 * ao)
    shade = (1.0 + EMB * emb) * (1.0 - EDGE_DARK * edge) * aof
    # [QA 2026-11-09 ng3] the fg42hd tone (mean 33/255) drew the Bren near-black in daylight; the VB's own sheet averages ~58
    steel = ((0.05 + 0.25 * l0 + 0.4 * polish) * shade * STEEL_GAIN)[..., None] * STEEL[None, None, :]
    grain = lum - box_blur(lum, 6)
    sat = lum[..., None] + (base - lum[..., None]) * WOOD_SAT
    wood = np.clip(sat * WOOD_GAIN, 0, 1) * WOOD_TINT[None, None, :]
    wood = wood * (1.0 + WOOD_GRAIN * grain[..., None] / (lum[..., None] + 0.05))
    wood = wood * (1.0 + 0.6 * EMB * emb[..., None]) * (1.0 - 0.3 * EDGE_DARK * edge[..., None]) * aof[..., None]
    mm = m[..., None]
    sheet = np.clip(steel * mm + wood * (1 - mm), 0, 1)
    os.makedirs(OUT, exist_ok=True)
    im = Image.fromarray((sheet * 255 + 0.5).astype(np.uint8))
    im.save(os.path.join(OUT, NAME + '.png')); im.save(os.path.join(OUT, NAME + '.jpg'), quality=92)
    Image.fromarray((m * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, NAME + '_metal.png'))
    print('sheet mean', (sheet.mean((0, 1)) * 255).round(1), 'metal share %.2f' % m.mean())


if __name__ == '__main__':
    main()
