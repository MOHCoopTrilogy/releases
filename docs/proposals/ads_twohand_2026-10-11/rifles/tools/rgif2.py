"""Side-by-side delta GIF of several captures (variants of one clip next to each other), on the rifle lane's runs.

    python rgif2.py <out.gif> --panel "<session>|<tag substring>|<label>" [--panel ...] --frames a:b:step
                    [--w 320] [--ms 48] [--crop x0,y0,x1,y1] [--box] [--hold 12] [--colors 96]
Every panel shows the same capture frame numbers (the harness captures one frame per 16 ms of game time, so equal
frame numbers are equal times after the same key press). The label is drawn top left of its panel.
"""
import sys, os, glob, argparse
import numpy as np
from PIL import Image, ImageDraw
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim2/runs').rstrip('/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--panel', action='append', required=True); ap.add_argument('--frames', required=True)
    ap.add_argument('--w', type=int, default=320); ap.add_argument('--ms', type=int, default=48); ap.add_argument('--crop')
    ap.add_argument('--colors', type=int, default=96); ap.add_argument('--thr', type=int, default=26); ap.add_argument('--box', action='store_true')
    ap.add_argument('--hold', type=int, default=12)
    a = ap.parse_args()
    p = [int(x) for x in a.frames.split(':')]
    crop = [int(x) for x in a.crop.split(',')] if a.crop else None
    pans = []
    for spec in a.panel:
        sess, sub, lab = spec.split('|')
        fs = sorted(glob.glob(RUNS + '/%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (sess, sub)))
        assert fs, 'no frames for ' + spec
        pans.append((fs, lab))
    n = min(p[1], min(len(fs) for fs, _ in pans))
    idx = list(range(p[0], n, p[2] if len(p) > 2 else 1))
    ims = []
    for i in idx:
        row = []
        for fs, lab in pans:
            im = Image.open(fs[i]).convert('RGB')
            W0, H0 = im.size
            if a.box:
                ImageDraw.Draw(im).rectangle((int(W0 * 0.4), int(H0 * 0.4), int(W0 * 0.6), int(H0 * 0.6)), outline=(255, 225, 0), width=2)
            if crop:
                im = im.crop(crop)
            im = im.resize((a.w, a.w * im.height // im.width), Image.LANCZOS)
            d = ImageDraw.Draw(im); d.rectangle((0, 0, 6 * len(lab) + 8, 14), fill=(0, 0, 0)); d.text((4, 1), lab, fill=(255, 235, 120))
            row.append(im)
        S = Image.new('RGB', (a.w * len(row) + 2 * (len(row) - 1), row[0].height), (0, 0, 0))
        for k, im in enumerate(row):
            S.paste(im, (k * (a.w + 2), 0))
        ims.append(S)
    mont = Image.new('RGB', (ims[0].width * 2, ims[0].height * 6))
    for k in range(12):
        mont.paste(ims[k * (len(ims) - 1) // 11], ((k % 2) * ims[0].width, (k // 2) * ims[0].height))
    pal = mont.quantize(colors=a.colors, dither=0)
    T = a.colors
    out, durs, screen = [], [], None
    for im in ims:
        A = np.asarray(im).astype(np.int16)
        q = np.asarray(im.quantize(palette=pal, dither=0)).copy()
        if screen is None:
            screen = A.copy(); fr = q
        else:
            ch = np.abs(A - screen).sum(axis=2) > a.thr
            fr = np.where(ch, q, T).astype(np.uint8)
            screen[ch] = A[ch]
        f = Image.fromarray(fr.astype(np.uint8), 'P'); f.putpalette(pal.getpalette()[:3 * a.colors] + [0, 0, 0])
        out.append(f); durs.append(a.ms)
    durs[-1] = a.ms * a.hold
    out[0].save(a.out, save_all=True, append_images=out[1:], duration=durs, loop=0, optimize=False, transparency=T, disposal=1)
    sz = os.path.getsize(a.out)
    print(a.out, len(out), 'frames', sz // 1024, 'KB', '(over 3 MB!)' if sz > 3 * 1024 * 1024 else '')


if __name__ == '__main__':
    main()
