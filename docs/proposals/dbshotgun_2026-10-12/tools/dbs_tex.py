"""Compose the first-person diffuse sheet from the Blender bakes (build/bake_d.npy, bake_ao.npy; linear float RGBA).

    python tools/dbs_tex.py            -> build/dbs_diffuse.png (2048, sRGB), build/dbs_ao.png (for looking at)

colour = projected author diffuse (linear) x (1 - AO_K * (1 - ao)), then a small lift of the wood (the author's baked
sheet is very dark next to the mod's guns), texels the bake did not cover filled outward from their neighbours (no
magenta under mip-mapping).
"""
import os, sys
import numpy as np
from PIL import Image
import dbslib as L

AO_K = 0.8
GAIN = 1.0
STEEL_MED = 0.023   # linear median of the steel (sRGB 42)
STEEL_POW = 1.5
WOOD = (0.50, 0.50, 0.50)   # x the diffuse sheet: walnut about sRGB 66 36 25 (look2: 0.6 drew orange; look3:
                            # 0.62 0.80 0.80 drew mustard under the map light)
WOOD_SHEEN = 0.10   # + this much of the glossy sheet on the wood


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def dilate(rgb, mask, n):
    rgb = rgb.copy(); mask = mask.copy()
    for _ in range(n):
        if mask.all():
            break
        acc = np.zeros_like(rgb); cnt = np.zeros(mask.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            m = np.roll(mask, (dy, dx), (0, 1)); c = np.roll(rgb, (dy, dx), (0, 1))
            acc += c * m[..., None]; cnt += m
        new = (~mask) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        mask |= new
    if not mask.all():
        rgb[~mask] = rgb[mask].mean(0)
    return rgb


def main():
    d = np.load(os.path.join(L.BUILD, 'bake_d.npy'))
    ao = np.load(os.path.join(L.BUILD, 'bake_ao.npy'))
    mask = d[..., 3] > 0.5
    a = np.clip(ao[..., 0], 0, 1)
    g = np.load(os.path.join(L.BUILD, 'bake_g.npy'))[..., :3]
    lum = d[..., :3].sum(2)
    wood = np.clip((lum - 0.006) / 0.024, 0, 1); wood = (wood * wood * (3 - 2 * wood))[..., None]
    # steel: the glossy sheet's colour (blue-grey, scratches), brought to a blued-steel level; never fully black
    # run look1: at 0.5 x the glossy sheet the steel drew light blue-grey next to the retail guns (pump sheet median
    # sRGB 35, Thompson 24). Blued steel: median STEEL_MED linear, the sheet's scratches / wear kept as contrast
    # (power STEEL_POW about its median), half of its blue cast taken out
    gl = g.mean(2, keepdims=True)
    med = float(np.median(gl[mask & (wood[..., 0] < 0.5) & (gl[..., 0] > 0.02)]))
    tint = g / np.maximum(gl, 1e-4)
    tint = 0.5 * tint + 0.5
    steel = np.maximum(STEEL_MED * np.power(np.maximum(gl / med, 0.0), STEEL_POW) * tint, 0.004)
    walnut = d[..., :3] * np.array(WOOD) + g * WOOD_SHEEN
    base = walnut * wood + steel * (1 - wood)
    col = base * (1 - AO_K * (1 - a))[..., None] * GAIN
    col = dilate(col.astype(np.float32), mask, 24)
    out = (srgb(col) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(out).save(os.path.join(L.BUILD, 'dbs_diffuse.png'))
    aoi = dilate(np.repeat(a[..., None], 3, 2).astype(np.float32), ao[..., 3] > 0.5, 24)
    Image.fromarray((aoi * 255).astype(np.uint8)).save(os.path.join(L.BUILD, 'dbs_ao.png'))
    m = out[mask]
    print('diffuse mean rgb', m.mean(0).round(1), 'p5', np.percentile(m, 5, 0), 'p95', np.percentile(m, 95, 0), 'covered %.1f%%' % (100 * mask.mean()))


if __name__ == '__main__':
    main()
