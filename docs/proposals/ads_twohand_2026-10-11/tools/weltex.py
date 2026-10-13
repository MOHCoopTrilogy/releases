"""Welrod: readable shading (list item D - "its rear reads as a near-black disc").

The gun's five diffuse sheets (zzzzz_xw_weapons.pk3, textures/models/weapons/welrod/*.tga) carry real art - the knurled
knob with its ring and stamps, brushed bolt, screws - at levels of 0-60 of 255 (mean 5): in the game the whole pistol
is a black silhouette and the knob a black disc. The art is kept, its LEVELS are lifted: per sheet the 99.5th
percentile goes to TOP (dark blued steel, not grey), with a gamma that opens the shadows. Nothing is repainted.

    python weltex.py <stage root>          -> <root>/textures/models/weapons/welrod/{bolt,rec,barrel,misc,clip}.tga
"""
import sys, os, io
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
vfs = gunskc.R.vfs
TOP = dict(bolt=178, rec=150, barrel=140, misc=150, clip=150)     # the bolt / knob a little brighter: bare polished steel
GAMMA = 0.80


def run(root):
    for n, top in TOP.items():
        p = 'textures/models/weapons/welrod/%s.tga' % n
        im = Image.open(io.BytesIO(vfs.read(p))).convert('RGBA')
        a = np.asarray(im).astype(np.float64)
        rgb = a[..., :3]
        lum = rgb.max(axis=2)
        hi = max(1.0, float(np.percentile(lum, 99.5)))
        x = np.clip(rgb / hi, 0.0, 1.6)
        out = np.clip((x ** GAMMA) * top, 0, 255)
        a[..., :3] = out
        dst = os.path.join(root, p.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        Image.fromarray(a.astype(np.uint8), 'RGBA').save(dst, format='TGA', compression='tga_rle')
        print('%-7s p99.5 %3.0f -> %d | mean %.1f -> %.1f | %s' % (n, hi, top, rgb.mean(), out.mean(), p))


if __name__ == '__main__':
    run(sys.argv[1])
