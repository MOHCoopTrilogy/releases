"""Game diffuse sheets from the 4K PBR maps (build/maps2048.npz from bl_tex.py).

The engine's weapon shaders have ONE texture stage + rgbGen lightingSpherical (vanilla colt45 / p38 / luger alike): no spec,
no normal map. So the PBR look is BAKED into the diffuse:
  * lighting from the normal map: a fixed light from the gun's left, shade = -0.9 nx + 0.25 ny (X is the same in GL and
    DX normal maps, so ridges read right whichever convention the baker used), applied as a multiplier = machining,
    engraving, the ribs of the grip stand out;
  * cavity / edge darkening from the normal map's edge strength (crevices, panel lines);
  * metal: the BaseColor's own wear and scratches kept as luminance, contrast-stretched, re-toned (blued steel);
    wood (non-metal) keeps its walnut colour and grain, only lifted;
  * polish: smooth (low roughness) wear is lifted a little, the highlight a spec stage would have given.
Finishes that tint metal (gold, chrome, blued) are baked here too, from the same shading, so wood is KEPT (the mod's stage
finishes multiply a flat tint over everything).
    python paint_sheet.py          -> build/c96_diffuse_final.png, fin_gold|chrome|blued.png, c96_metalmask.png
Env knobs C96_*; see top.
"""
import os
import numpy as np
from PIL import Image
from scipy_free_filters import box_blur

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, '..', 'build')
E = lambda k, d: float(os.environ.get(k, d))
EMB = E('C96_EMB', '1.00')            # machining / relief strength (multiplier swing)
EDGE_DARK = E('C96_EDGE_DARK', '0.50')
POLISH = E('C96_POLISH', '0.20')
WOOD_GAIN = E('C96_WOOD_GAIN', '1.15')
WOOD_TINT = np.array([1.00, 0.96, 1.12])      # walnut: the source's yellow-brown pulled toward brown


def load():
    d = np.load(os.path.join(B, 'maps2048.npz'))
    base = d['base'].astype(np.float32) / 255.0
    nrm = d['normal'].astype(np.float32) / 255.0 * 2 - 1
    rough = d['rough'][:, :, 0].astype(np.float32) / 255.0
    metal = d['metal'][:, :, 0].astype(np.float32) / 255.0
    return base, nrm, rough, metal


def build():
    base, nrm, rough, metal = load()
    lum = base @ np.array([0.299, 0.587, 0.114], np.float32)
    m = np.clip((metal - 0.3) / 0.4, 0, 1)
    emb = -0.9 * nrm[:, :, 0] + 0.25 * nrm[:, :, 1]
    emb = np.clip(emb, -1.2, 1.2)
    gx = np.abs(np.gradient(nrm[:, :, 0], axis=1)) + np.abs(np.gradient(nrm[:, :, 1], axis=0))
    edge = box_blur(gx, 1) + 0.5 * box_blur(gx, 3)
    edge = np.clip(edge / (np.percentile(edge, 99) + 1e-6), 0, 1)
    l0 = np.clip((lum - 0.18) / 0.6, 0, 1) ** 1.3                   # the source's wear / scratch luminance, stretched
    polish = np.clip((0.55 - rough) / 0.45, 0, 1) * POLISH
    shade = (1.0 + EMB * emb) * (1.0 - EDGE_DARK * edge)

    def metal_tone(tint, floor, span):
        v = (floor + span * l0 + polish) * shade
        return v[..., None] * np.asarray(tint, np.float32)[None, None, :]
    wood = np.clip(base * WOOD_GAIN, 0, 1) * WOOD_TINT[None, None, :]
    wood = wood * (1.0 + 0.7 * EMB * emb[..., None]) * (1.0 - 0.35 * EDGE_DARK * edge[..., None])
    mm = m[..., None]
    outs = {
        'c96_diffuse_final': metal_tone((0.62, 0.70, 0.84), 0.22, 0.68),          # blued steel
        'fin_gold': metal_tone((1.00, 0.78, 0.30), 0.30, 0.65),
        'fin_chrome': metal_tone((0.88, 0.92, 0.98), 0.40, 0.55),
        'fin_blued': metal_tone((0.42, 0.50, 0.85), 0.12, 0.40),
    }
    for k, steel in outs.items():
        out = np.clip(steel * mm + wood * (1 - mm), 0, 1)
        Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(B, k + '.png'))
        mk = m > 0.5
        print('%-18s metal mean %s  wood mean %s' % (k, (out[mk].mean(0) * 255).round(0), (out[~mk].mean(0) * 255).round(0)))
    Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(B, 'c96_metalmask.png'))


if __name__ == '__main__':
    build()
