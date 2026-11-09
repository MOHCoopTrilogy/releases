"""One 2048 game sheet from the MP 28's per-material PBR maps (H:/hzm_work/newguns/src/mp28/textures, untrusted PNG data, read only):
one 1024 tile per material (Wood, Steel, Dark Steel), the fg42hd atlas.py bake (normal relief, edge darkening, wear as luminance on
metal, oiled walnut), tone matched to the Sten's sheet range. -> H:/hzm_work/newguns/build/mp28/mp28.png/.jpg + atlas.json
    python mp28_sheet.py
"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools")
from scipy_free_filters import box_blur

Image.MAX_IMAGE_PIXELS = None
SRC = r"H:/hzm_work/newguns/src/mp28/textures"
OUT = r"H:/hzm_work/newguns/build/mp28"
N, PAD = 2048, 6
TILES = {'Wood': (0, 0, 1024), 'Steel': (1024, 0, 1024), 'Dark Steel': (0, 1024, 1024)}
EMB, EDGE_DARK, POLISH = 0.85, 0.45, 0.15
STEEL = np.array([0.84, 0.88, 0.95], np.float32)
DARK = {'Steel': 1.0, 'Dark Steel': 0.70}
WOOD_GAIN, WOOD_TINT = 0.78, np.array([0.95, 0.86, 0.80], np.float32)
WOOD_SAT, WOOD_GRAIN = 0.55, 1.5


def load(mat, kind, size, ch3):
    p = os.path.join(SRC, '%s_%s.png' % (mat.replace(' ', '_'), kind))
    if not os.path.isfile(p):
        return None
    return np.asarray(Image.open(p).convert('RGB' if ch3 else 'L').resize((size, size), Image.LANCZOS)).astype(np.float32) / 255.0


def paint(mat, size):
    base = load(mat, 'Base_color', size, True)
    nrm = load(mat, 'Normal', size, True)
    rough = load(mat, 'Roughness', size, False)
    nrm = (nrm * 2 - 1) if nrm is not None else np.zeros((size, size, 3), np.float32)
    rough = rough if rough is not None else np.full((size, size), 0.6, np.float32)
    lum = base @ np.array([0.299, 0.587, 0.114], np.float32)
    emb = np.clip(-0.9 * nrm[:, :, 0] + 0.25 * nrm[:, :, 1], -1.2, 1.2)
    gx = np.abs(np.gradient(nrm[:, :, 0], axis=1)) + np.abs(np.gradient(nrm[:, :, 1], axis=0))
    edge = box_blur(gx, 1) + 0.5 * box_blur(gx, 3)
    edge = np.clip(edge / (np.percentile(edge, 99) + 1e-6), 0, 1)
    if mat == 'Wood':
        grain = lum - box_blur(lum, 6)
        sat = lum[..., None] + (base - lum[..., None]) * WOOD_SAT
        wood = np.clip(sat * WOOD_GAIN, 0, 1) * WOOD_TINT[None, None, :]
        wood = wood * (1.0 + WOOD_GRAIN * grain[..., None] / (lum[..., None] + 0.05))
        return np.clip(wood * (1.0 + 0.6 * EMB * emb[..., None]) * (1.0 - 0.3 * EDGE_DARK * edge[..., None]), 0, 1), 0.0
    l0 = np.minimum(np.clip((lum - 0.10) / 0.55, 0, 1) ** 1.2, 0.6)
    polish = np.clip((0.55 - rough) / 0.45, 0, 1) * POLISH
    shade = (1.0 + EMB * emb) * (1.0 - EDGE_DARK * edge)
    # [QA 2026-11-09 ng3] read near-black in daylight: x1.45 (still darker than the Bren: blued steel)
    steel = ((0.05 + 0.25 * l0 + 0.4 * polish) * shade * DARK[mat] * 1.45)[..., None] * STEEL[None, None, :]
    return np.clip(steel, 0, 1), 1.0


def main():
    sheet = np.zeros((N, N, 3), np.float32)
    meta = {}
    for mat, (x, y, s) in TILES.items():
        inner = s - 2 * PAD
        img, _m = paint(mat, inner)
        sheet[y:y + s, x:x + s] = np.pad(img, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
        meta[mat] = dict(x=x, y=y, size=s, inner=inner, pad=PAD)
        print('%-11s mean %s' % (mat, (img.mean((0, 1)) * 255).round(0)))
    # the free corner: a flat mid steel texel block (the tiled-UV spring and any part without a usable UV)
    sheet[1024 + 64:1024 + 192, 1024 + 64:1024 + 192] = sheet[1024 + 400:1024 + 528, 400:528].mean((0, 1))
    meta['Flat'] = dict(u=(1024 + 128) / N, v=(1024 + 128) / N)
    os.makedirs(OUT, exist_ok=True)
    im = Image.fromarray((sheet * 255 + 0.5).astype(np.uint8))
    im.save(os.path.join(OUT, 'mp28.png')); im.save(os.path.join(OUT, 'mp28.jpg'), quality=92)
    json.dump(dict(size=N, tiles=meta), open(os.path.join(OUT, 'atlas.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
