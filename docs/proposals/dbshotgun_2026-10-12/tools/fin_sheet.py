"""Contact sheets of the finish set from a `--parts fin` run.

    python tools/fin_sheet.py <run id> <out prefix> [--refs]
        <prefix>_hip_aim.jpg     every finish: the hip crop and the aim crop side by side (labelled)
        <prefix>_third.jpg       every finish in third person (crop around the gun)
"""
import os, sys
from PIL import Image, ImageDraw
import dbslib as L

FINS = [('base', 'STANDARD'), ('gold', 'GOLD'), ('chrome', 'CHROME'), ('blued', 'BLUED'), ('bloody', 'BLOODY'),
        ('camo_woodland', 'WOODLAND'), ('camo_winter', 'WINTER'), ('camo_desert', 'DESERT')]
HIP = (0.26, 0.42, 0.78, 1.00)       # x0 y0 x1 y1 of the frame
AIM = (0.36, 0.42, 0.64, 1.00)
THIRD = (0.52, 0.00, 1.00, 0.52)


def crop(p, box, h):
    im = Image.open(p).convert('RGB')
    W, H = im.size
    c = im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))
    return c.resize((round(c.width * h / c.height), h), Image.LANCZOS)


def label(im, txt):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 10 + 7 * len(txt), 17], fill=(0, 0, 0))
    d.text((5, 3), txt, fill=(255, 230, 120))
    return im


def grid(cells, cols, out):
    w = max(c.width for c in cells); h = max(c.height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    sh = Image.new('RGB', (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (16, 16, 16))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    sh.save(out, quality=90)
    print('WROTE', out, sh.size)


def main():
    run, pre = sys.argv[1], sys.argv[2]
    d = os.path.join(L.RUNS, run)
    fins = list(FINS)
    if '--refs' in sys.argv:
        fins += [('ref_pump', 'PUMP GUN (STANDARD)'), ('ref_pump_gold', 'PUMP GUN (GOLD)'), ('ref_pump_camo_winter', 'PUMP GUN (WINTER)'), ('ref_pump_bloody', 'PUMP GUN (BLOODY)')]
    cells = []
    for k, nm in fins:
        a = crop(os.path.join(d, 'fin_%s_hip.jpg' % k), HIP, 300)
        b = crop(os.path.join(d, 'fin_%s_ads.jpg' % k), AIM, 300)
        c = Image.new('RGB', (a.width + b.width + 2, 300), (16, 16, 16))
        c.paste(a, (0, 0)); c.paste(b, (a.width + 2, 0))
        cells.append(label(c, nm + '   hip | aim'))
    grid(cells, 2, pre + '_hip_aim.jpg')
    cells = [label(crop(os.path.join(d, 'fin_%s_third.jpg' % k), THIRD, 330), nm) for k, nm in fins]
    grid(cells, 4, pre + '_third.jpg')


if __name__ == '__main__':
    main()
