"""One 2048 game sheet from the FG42's per-material PBR maps (H:/hzm_work/fg42_src/x/textures, untrusted PNG data, read only).

The weapon shaders have ONE texture stage + rgbGen lightingSpherical (no normal / spec stage), so the PBR look is BAKED into the
diffuse, the C96 recipe (c96_model_2026-10-18/tools/paint_sheet.py): normal-map relief lit from the gun's left, edge / cavity
darkening, the BaseColor's own wear kept as luminance on metal (phosphate-grey steel), wood keeps its colour and grain.
    python atlas.py      -> build/fg42hd.png (+ build/fg42hd_metal.png, build/atlas.json = the tile of every material)
"""
import os, json
import numpy as np
from PIL import Image
from scipy_free_filters import box_blur

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, '..', 'build')
SRC = os.environ.get('FG_TEX', r'H:/hzm_work/fg42_src/x/textures')
N = 2048
PAD = 6
TILES = {'Body': (0, 0, 1024), 'Wood': (1024, 0, 1024), 'Barrel': (0, 1024, 512), 'Bipod': (512, 1024, 512),
         'Magazine': (1024, 1024, 512), 'Rear_sight': (1536, 1024, 512), 'Grip': (0, 1536, 512), 'Bolt': (512, 1536, 256),
         'EjectionPort': (768, 1536, 256), 'Trigger': (512, 1792, 256)}
EXTRA = {'Scope': (1024, 1536, 512), 'Rubber': (1536, 1536, 256)}
SCOPE_MEAN, SCOPE_TINT = 0.105, np.array([0.92, 0.96, 1.06], np.float32)     # blued: darker than the receiver (Body ~0.14)
RUBBER_MEAN = 0.065
WOOD = {'Wood', 'Grip'}
EMB, EDGE_DARK, POLISH = 0.85, 0.45, 0.20
STEEL = np.array([0.84, 0.88, 0.95], np.float32)
WOOD_GAIN, WOOD_TINT = 0.72, np.array([0.95, 0.86, 0.80], np.float32)
WOOD_SAT, WOOD_GRAIN = 0.45, 1.6   # the menu light lifted it to orange; tuned on the viewer stills


def load(mat, kind, size, ch3):
    p = os.path.join(SRC, 'FG42_%s_%s.png' % (mat, kind))
    if not os.path.isfile(p):
        return None
    im = Image.open(p)
    im = im.convert('RGB' if ch3 else 'L').resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def paint(mat, size):
    base = load(mat, 'BaseColor', size, True)
    nrm = load(mat, 'Normal', size, True)
    rough = load(mat, 'Roughness', size, False)
    metal = load(mat, 'Metallic', size, False)
    nrm = (nrm * 2 - 1) if nrm is not None else np.zeros((size, size, 3), np.float32)
    rough = rough if rough is not None else np.full((size, size), 0.6, np.float32)
    if metal is None:
        metal = np.zeros((size, size), np.float32) if mat in WOOD else np.ones((size, size), np.float32)
    lum = base @ np.array([0.299, 0.587, 0.114], np.float32)
    m = np.clip((metal - 0.3) / 0.4, 0, 1)
    emb = np.clip(-0.9 * nrm[:, :, 0] + 0.25 * nrm[:, :, 1], -1.2, 1.2)
    gx = np.abs(np.gradient(nrm[:, :, 0], axis=1)) + np.abs(np.gradient(nrm[:, :, 1], axis=0))
    edge = box_blur(gx, 1) + 0.5 * box_blur(gx, 3)
    edge = np.clip(edge / (np.percentile(edge, 99) + 1e-6), 0, 1)
    l0 = np.clip((lum - 0.10) / 0.55, 0, 1) ** 1.2
    polish = np.clip((0.55 - rough) / 0.45, 0, 1) * POLISH
    shade = (1.0 + EMB * emb) * (1.0 - EDGE_DARK * edge)
    # the shipped FG42 sheet averages 33/255; the menus' lightingSpherical lifts a brighter sheet to near-chrome
    steel = ((0.045 + 0.25 * l0 + 0.4 * polish) * shade)[..., None] * STEEL[None, None, :]
    # oiled walnut (QA 2026-11-08: the first pass read saturated orange, near plastic): saturation pulled to ~45 %, a dark
    # red-brown base, and the source's grain kept as luminance variation (a high-pass of the BaseColor, boosted) so it reads as wood
    wl = base @ np.array([0.299, 0.587, 0.114], np.float32)
    grain = wl - box_blur(wl, 6)
    sat = wl[..., None] + (base - wl[..., None]) * WOOD_SAT
    wood = np.clip(sat * WOOD_GAIN, 0, 1) * WOOD_TINT[None, None, :]
    wood = wood * (1.0 + WOOD_GRAIN * grain[..., None] / (wl[..., None] + 0.05))
    wood = wood * (1.0 + 0.6 * EMB * emb[..., None]) * (1.0 - 0.3 * EDGE_DARK * edge[..., None])
    mm = m[..., None]
    return np.clip(steel * mm + wood * (1 - mm), 0, 1), m


def main():
    sheet = np.zeros((N, N, 3), np.float32)
    mask = np.zeros((N, N), np.float32)
    meta = {}
    for mat, (x, y, s) in TILES.items():
        inner = s - 2 * PAD
        img, m = paint(mat, inner)
        # bleed: edge-extend the tile into its padding so mips never mix two parts
        img = np.pad(img, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
        m = np.pad(m, PAD, mode='edge')
        sheet[y:y + s, x:x + s] = img
        mask[y:y + s, x:x + s] = m
        # UV mapping (GL convention, v up): u' = (x + PAD + u*inner)/N ; v' = 1 - (y + PAD + (1-v)*inner)/N
        meta[mat] = dict(x=x, y=y, size=s, inner=inner, pad=PAD)
        print('%-13s tile %4d,%4d %4d  metal %.2f  mean %s' % (mat, x, y, s, m.mean(), (img.mean((0, 1)) * 255).round(0)))
    # [scope] two tiles in the sheet's free corner for the in-house ZFG 42 (scope_mesh.py): blued scope steel from the barrel's own
    # paint (its machining streaks, combed along the tube and darkened to a blued finish under the receiver's tone) and the eyecup's
    # matte rubber. Placed where no source part lives, so every other tile - and the Irons' mesh UVs - are unchanged.
    for mat, (x, y, s) in EXTRA.items():
        inner = s - 2 * PAD
        if mat == 'Scope':
            img, _m = paint('Barrel', inner)
            lum = img @ np.array([0.299, 0.587, 0.114], np.float32)
            comb = np.stack([np.convolve(lum[:, j], np.ones(15) / 15.0, mode='same') for j in range(inner)], 1)
            comb = 0.5 * comb + 0.5 * lum
            img = np.clip((comb / max(comb.mean(), 1e-4) * SCOPE_MEAN)[..., None] * SCOPE_TINT[None, None, :], 0, 1)
            m = np.ones((inner, inner), np.float32)
        else:
            rng = np.random.default_rng(7)
            n = box_blur(rng.standard_normal((inner, inner)).astype(np.float32), 2)
            img = np.clip((RUBBER_MEAN * (1.0 + 0.25 * n / (np.abs(n).max() + 1e-6)))[..., None] * np.ones(3, np.float32), 0, 1)
            m = np.zeros((inner, inner), np.float32)
        img = np.pad(img, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
        sheet[y:y + s, x:x + s] = img
        mask[y:y + s, x:x + s] = np.pad(m, PAD, mode='edge')
        meta[mat] = dict(x=x, y=y, size=s, inner=inner, pad=PAD)
        print('%-13s tile %4d,%4d %4d  (scope)  mean %s' % (mat, x, y, s, (img.mean((0, 1)) * 255).round(0)))
    Image.fromarray((sheet * 255 + 0.5).astype(np.uint8)).save(os.path.join(B, 'fg42hd.png'))
    Image.fromarray((sheet * 255 + 0.5).astype(np.uint8)).save(os.path.join(B, 'fg42hd.jpg'), quality=92)   # what ships
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8)).save(os.path.join(B, 'fg42hd_metal.png'))
    json.dump(dict(size=N, tiles=meta), open(os.path.join(B, 'atlas.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
