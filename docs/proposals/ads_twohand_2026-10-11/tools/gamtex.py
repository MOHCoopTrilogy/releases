"""Beretta (TT It_W_Beretta.jpg) and silenced Beretta (`Beretta.jpg`): readable from behind (list item E - "reads
near-black", seen in runs tl3 and pa6).

Both sheets are finished art whose steel sits at 10-30 of 255: under the game's lighting the slide and frame are one
black shape in the aim. The art is kept; its SHADOWS are opened with a gamma curve (out = in ^ G, highlights and hue
unchanged, nothing repainted). Alpha is passed through.

    python gamtex.py <stage root> [--view sheet.jpg]
"""
import sys, os, io
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
vfs = gunskc.R.vfs
SHEETS = {'textures/models/weapons/beretta/it_w_beretta.jpg': 0.62, 'textures/models/weapons/beretta/beretta.jpg': 0.62}


def find(p):
    for cand in (p, p.lower()):
        w = vfs.winner(cand)
        if w:
            return w
    base = os.path.basename(p).lower()
    hits = [k for k in vfs.index() if k.endswith('/' + base)]
    assert len(hits) == 1, (p, hits)
    return vfs.winner(hits[0])


def run(root, view=None):
    tiles = []
    for p, g in SHEETS.items():
        w = find(p)
        with __import__('zipfile').ZipFile(w[0]) as z:
            raw = z.read(w[1])
        im = Image.open(io.BytesIO(raw))
        has_a = im.mode == 'RGBA'
        a = np.asarray(im.convert('RGBA')).astype(np.float64)
        b = a.copy()
        b[..., :3] = 255.0 * (a[..., :3] / 255.0) ** g
        dst = os.path.join(root, w[1].replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        out = Image.fromarray(b.astype(np.uint8), 'RGBA')
        if w[1].lower().endswith('.jpg'):
            out.convert('RGB').save(dst, quality=92)
        else:
            (out if has_a else out.convert('RGB')).save(dst, format='TGA', compression='tga_rle')
        print('%s (%s) %s gamma %.2f: median %.0f -> %.0f, mean %.0f -> %.0f, %d bytes' % (
            w[1], vfs.pakname(w[0]), im.size, g, np.median(a[..., :3]), np.median(b[..., :3]), a[..., :3].mean(), b[..., :3].mean(), os.path.getsize(dst)))
        tiles += [im.convert('RGB').resize((384, 384)), out.convert('RGB').resize((384, 384))]
    if view:
        sh = Image.new('RGB', (384 * len(tiles), 384))
        for i, t in enumerate(tiles):
            sh.paste(t, (384 * i, 0))
        sh.save(view, quality=85)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[sys.argv.index('--view') + 1] if '--view' in sys.argv else None)
