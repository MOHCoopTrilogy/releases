"""A sheet of chosen STILLS of lane runs: one cell per item, the full frame (or a crop), labelled.

    python picksheet.py <out.jpg> <cols> <cell width> [--crop x0,y0,x1,y1] [--box] <run>:<tag substring>[:<index, default last>[:<label>]] ...
"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw
args = sys.argv[1:]
crop = None; box = False
if '--crop' in args:
    i = args.index('--crop'); crop = tuple(int(v) for v in args[i + 1].split(',')); del args[i:i + 2]
if '--box' in args:
    args.remove('--box'); box = True
out, cols, W = args[0], int(args[1]), int(args[2])
cells = []
for it in args[3:]:
    p = it.split(':')
    fs = sorted(f for f in glob.glob(os.path.join(os.environ.get('ADS_RUNS', hv.RUNS), p[0], '*%s*.jpg' % p[1])) if not f.endswith('__ref.jpg'))
    assert fs, it
    f = fs[int(p[2])] if len(p) > 2 and p[2] else fs[-1]
    im = Image.open(f).convert('RGB')
    if box:
        w, h = im.size
        ImageDraw.Draw(im).rectangle([int(w * 0.4), int(h * 0.4), int(w * 0.6), int(h * 0.6)], outline=(235, 220, 60), width=2)
    if crop:
        im = im.crop(crop)
    im = im.resize((W, W * im.size[1] // im.size[0]), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    lab = p[3] if len(p) > 3 else p[1]
    d.rectangle([0, 0, 8 + 7 * len(lab), 16], fill=(0, 0, 0)); d.text((4, 2), lab, fill=(255, 255, 255))
    cells.append(im)
rows = (len(cells) + cols - 1) // cols
H = max(c.size[1] for c in cells)
S = Image.new('RGB', (cols * W, rows * H), (255, 255, 255))
for k, c in enumerate(cells):
    S.paste(c, ((k % cols) * W, (k // cols) * H))
S.save(out, quality=88)
print(out, len(cells), 'cells', S.size)
