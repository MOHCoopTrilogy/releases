"""Standalone decal set for the Armory Customize bench: every insignia / plate / stamp from assets/decals, trimmed to its alpha
box (+4 % margin), premultiplied-safe edges (colour bled under alpha 0 so mip/bilinear sampling never shows a dark fringe),
written at 512 / 256 / 128 on the long side, plus decals/manifest.json (name, category, recommended size on the gun in cm and
model units, aspect, files, the finish that uses it by default).
    python export_decals.py
"""
import json, os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'assets', 'decals')
OUT = os.path.join(HERE, '..', 'decals')
U_PER_CM = 16.0 / 30.48

# name: (category, label, recommended long side in cm, default finish)
SET = {
    'ab82':     ('insignia', '82nd Airborne "AA" patch', 4.0, 'airborne'),
    'ab101':    ('insignia', '101st Airborne "Screaming Eagle" patch with AIRBORNE tab', 4.5, 'airborne101'),
    'lorraine': ('insignia', 'Cross of Lorraine (FFI)', 4.0, 'ffi'),
    'dak_palm': ('insignia', 'Afrika Korps palm', 4.5, 'dak'),
    'crest':    ('plate', 'Trench-art crest plate', 4.5, 'trenchart'),
    'plaque':   ('plate', 'Presentation plaque', 5.0, 'parade'),
    'waa':      ('stamp', 'Captured: WaA acceptance stamp', 3.0, 'captured'),
    'souvenir': ('stamp', 'Captured: souvenir carving', 4.0, 'captured'),
    # US awards and badges (public domain US government insignia, drawn by medals.py) - bench only, no finish uses them
    'moh_army':     ('award', 'Medal of Honor (Army, 1944)', 4.5, None),
    'purple_heart': ('award', 'Purple Heart', 4.0, None),
    'silver_star':  ('award', 'Silver Star', 4.0, None),
    'bronze_star':  ('award', 'Bronze Star', 4.0, None),
    'cib':          ('badge', 'Combat Infantryman Badge', 5.0, None),
    'jump_wings':   ('badge', 'Parachutist Badge (jump wings)', 5.0, None),
}
SIZES = (512, 256, 128)


def bleed(im):
    """fill RGB under transparent pixels with the nearest opaque colour (repeated dilation) - clean edges when filtered"""
    a = np.asarray(im)[..., 3]
    rgb = im.convert('RGB')
    known = a > 8
    arr = np.asarray(rgb, float)
    for _ in range(24):
        if known.all():
            break
        blur = np.asarray(rgb.filter(ImageFilter.BoxBlur(1)), float)
        k = Image.fromarray((known * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1))
        kw = np.asarray(k, float)[..., None] / 255.0
        fill = np.where(kw > 0, blur / np.maximum(kw, 1e-3), arr)
        arr = np.where(known[..., None], arr, np.clip(fill, 0, 255))
        known = known | (kw[..., 0] > 0)
        rgb = Image.fromarray(arr.astype(np.uint8))
    return Image.fromarray(np.dstack([arr.astype(np.uint8), a]), 'RGBA')


def main():
    os.makedirs(OUT, exist_ok=True)
    man = []
    for name, (cat, label, cm, fin) in SET.items():
        im = Image.open(os.path.join(SRC, name + '.png')).convert('RGBA')
        a = np.asarray(im)[..., 3]
        ys, xs = np.nonzero(a > 4)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        m = int(0.04 * max(x1 - x0, y1 - y0))
        im = im.crop((max(x0 - m, 0), max(y0 - m, 0), min(x1 + m, im.width), min(y1 + m, im.height)))
        im = bleed(im)
        w, h = im.size
        files = []
        for S in SIZES:
            k = S / max(w, h)
            sz = (max(1, round(w * k)), max(1, round(h * k)))
            f = '%s_%d.png' % (name, S)
            im.resize(sz, Image.LANCZOS).save(os.path.join(OUT, f), optimize=True)
            files.append(dict(file=f, w=sz[0], h=sz[1]))
        man.append(dict(name=name, category=cat, label=label, aspect=round(w / h, 3),
                        recommended_long_side_cm=cm, recommended_long_side_units=round(cm * U_PER_CM, 2),
                        default_finish=fin, upright='decal +s = towards the muzzle, +t = down (as drawn)',
                        files=files))
    json.dump(dict(source='docs/proposals/finishes2_2026-11-09/tools/export_decals.py', decals=man),
              open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
    print('wrote', len(man), 'decals to', OUT)


if __name__ == '__main__':
    main()
