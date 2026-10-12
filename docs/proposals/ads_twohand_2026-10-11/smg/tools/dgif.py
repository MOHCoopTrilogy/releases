"""Small GIF of a run's captured frames with a STATIC background kept static: one shared palette, and every frame stores
only the pixels that changed against what is already on screen (the rest is the transparent index, disposal 1). The
harness view does not move during a reload, so the textured wall costs nothing after the first frame - three to five
times smaller than sheet.py's gif at the same size, which buys frame rate (pops are visible at 20 fps, not at 9).

    python dgif.py <session> <tag substring> <out.gif> --frames a:b:step [--w 400] [--ms 48] [--crop x0,y0,x1,y1]
                   [--colors 96] [--thr 26] [--box] [--labels f0=txt,f58=txt] [--hold 12]
--box draws the centre box (middle 20 % of the screen). Prints the size; the budget is 3 MB.
"""
import sys, os, glob, argparse
import numpy as np
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sess'); ap.add_argument('sub'); ap.add_argument('out'); ap.add_argument('--frames', required=True)
    ap.add_argument('--w', type=int, default=400); ap.add_argument('--ms', type=int, default=48); ap.add_argument('--crop')
    ap.add_argument('--colors', type=int, default=96); ap.add_argument('--thr', type=int, default=26); ap.add_argument('--box', action='store_true')
    ap.add_argument('--labels', default=''); ap.add_argument('--hold', type=int, default=12)
    a = ap.parse_args()
    fs = sorted(glob.glob('G:/mohaa-adsanim3/runs/%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (a.sess, a.sub)))
    assert fs, 'no frames'
    p = [int(x) for x in a.frames.split(':')]
    idx = list(range(p[0], min(p[1], len(fs)), p[2] if len(p) > 2 else 1))
    labels = dict((int(kv.split('=')[0][1:]), kv.split('=')[1]) for kv in a.labels.split(',') if kv)
    crop = [int(x) for x in a.crop.split(',')] if a.crop else None
    ims = []
    lab = ''
    for i in idx:
        im = Image.open(fs[i]).convert('RGB')
        W0, H0 = im.size
        if a.box:
            ImageDraw.Draw(im).rectangle((int(W0 * 0.4), int(H0 * 0.4), int(W0 * 0.6), int(H0 * 0.6)), outline=(255, 225, 0), width=2)
        if crop:
            im = im.crop(crop)
        im = im.resize((a.w, a.w * im.height // im.width), Image.LANCZOS)
        for k in sorted(labels):
            if k <= i:
                lab = labels[k]
        if lab:
            d = ImageDraw.Draw(im); d.rectangle((0, 0, 7 * len(lab) + 8, 14), fill=(0, 0, 0)); d.text((4, 1), lab.replace('_', ' '), fill=(255, 235, 120))
        ims.append(im)
    mont = Image.new('RGB', (a.w * 4, ims[0].height * 3))
    for k in range(12):
        mont.paste(ims[k * (len(ims) - 1) // 11], ((k % 4) * a.w, (k // 4) * ims[0].height))
    pal = mont.quantize(colors=a.colors, dither=0)
    T = a.colors                                    # transparent index
    out = []; durs = []
    screen = None
    for k, im in enumerate(ims):
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
    print(a.out, len(out), 'frames', os.path.getsize(a.out) // 1024, 'KB', '(over 3 MB!)' if os.path.getsize(a.out) > 3 * 1024 * 1024 else '')


if __name__ == '__main__':
    main()
