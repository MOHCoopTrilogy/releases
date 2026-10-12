"""Contact sheet of a run_rifle capture (G:/mohaa-adsanim2/runs) or of a GIF's decoded frames, centre box drawn.

    python rsheet.py <session> <tag substring> <out.jpg> a:b:step [--w 320] [--cols 8] [--crop x0,y0,x1,y1]
    python rsheet.py --gif <file.gif> <out.jpg> a:b:step [--w 320] [--cols 8]
"""
import sys, os, glob, argparse
from PIL import Image, ImageDraw, ImageSequence
RUNS = 'G:/mohaa-adsanim2/runs/'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('c'); ap.add_argument('d', nargs='?')
    ap.add_argument('--gif', action='store_true'); ap.add_argument('--w', type=int, default=320); ap.add_argument('--cols', type=int, default=8)
    ap.add_argument('--crop')
    a = ap.parse_args()
    if a.gif:
        g = Image.open(a.a)
        ims = []
        canvas = None
        for fr in ImageSequence.Iterator(g):
            f = fr.convert('RGBA')
            canvas = f if canvas is None else Image.alpha_composite(canvas, f)
            ims.append(canvas.convert('RGB'))
        out, spec, names = a.b, a.c, None
        print(len(ims), 'gif frames', g.size)
    else:
        fs = sorted(glob.glob(RUNS + '%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (a.a, a.b)))
        assert fs, 'no frames'
        out, spec = a.c, a.d
        ims = None
    p = [int(x) for x in spec.split(':')]
    n = len(ims) if ims is not None else len(fs)
    idx = list(range(p[0], min(p[1], n), p[2] if len(p) > 2 else 1))
    crop = [int(x) for x in a.crop.split(',')] if a.crop else None
    tiles = []
    for i in idx:
        im = ims[i] if ims is not None else Image.open(fs[i]).convert('RGB')
        W0, H0 = im.size
        if ims is None:
            ImageDraw.Draw(im).rectangle((int(W0 * 0.4), int(H0 * 0.4), int(W0 * 0.6), int(H0 * 0.6)), outline=(255, 225, 0), width=2)
        if crop:
            im = im.crop(crop)
        im = im.resize((a.w, a.w * im.height // im.width), Image.LANCZOS)
        d = ImageDraw.Draw(im); d.rectangle((0, 0, 30, 12), fill=(0, 0, 0)); d.text((2, 0), str(i), fill=(255, 235, 120))
        tiles.append(im)
    cols = min(a.cols, len(tiles))
    S = Image.new('RGB', (a.w * cols, tiles[0].height * ((len(tiles) + cols - 1) // cols)), 'white')
    for k, im in enumerate(tiles):
        S.paste(im, ((k % cols) * a.w, (k // cols) * tiles[0].height))
    S.save(out, quality=85)
    print(out, len(tiles), 'tiles')


if __name__ == '__main__':
    main()
