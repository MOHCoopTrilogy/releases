"""Contact sheet / crop sheet / GIF from a run's captured frames.

    python sheet.py sheet <session> <tag substring> <out.jpg> [--frames a:b:step | a,b,c] [--w 320] [--cols 8] [--crop x0,y0,x1,y1]
    python sheet.py gif   <session> <tag substring> <out.gif> [--frames a:b:step] [--w 640] [--ms 48] [--crop ...] [--labels f0=txt,f58=txt]
"""
import sys, os, glob, argparse
RUNS_DIR = __import__('os').environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')   # another lane's harness: set ADS_RUNS
from PIL import Image, ImageDraw


def frames_of(sess, sub):
    fs = sorted(glob.glob(RUNS_DIR + '/%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (sess, sub)))
    assert fs, 'no frames for %s %s' % (sess, sub)
    tags = {os.path.basename(f).rsplit('__', 1)[0] for f in fs}
    assert len(tags) == 1, tags
    return fs


def pick(fs, spec):
    if not spec:
        return list(range(len(fs)))
    if ':' in spec:
        p = [int(x) for x in spec.split(':')]
        return [i for i in range(*p) if i < len(fs)]
    return [int(x) for x in spec.split(',') if int(x) < len(fs)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode'); ap.add_argument('sess'); ap.add_argument('sub'); ap.add_argument('out')
    ap.add_argument('--frames'); ap.add_argument('--w', type=int, default=320); ap.add_argument('--cols', type=int, default=8)
    ap.add_argument('--crop'); ap.add_argument('--ms', type=int, default=48); ap.add_argument('--labels', default='')
    ap.add_argument('--colors', type=int, default=128)
    a = ap.parse_args()
    fs = frames_of(a.sess, a.sub)
    idx = pick(fs, a.frames)
    crop = [int(x) for x in a.crop.split(',')] if a.crop else None
    lab = dict((int(k[1:]), v) for k, v in (x.split('=') for x in a.labels.split(',') if x))

    def load(i):
        im = Image.open(fs[i]).convert('RGB')
        if crop:
            im = im.crop(crop)
        h = a.w * im.height // im.width
        return im.resize((a.w, h), Image.LANCZOS)
    if a.mode == 'sheet':
        ims = [load(i) for i in idx]
        w, h = ims[0].size
        cols = min(a.cols, len(ims))
        S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), (30, 30, 30))
        for k, (i, im) in enumerate(zip(idx, ims)):
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 34, 12), fill=(0, 0, 0)); d.text((2, 0), 'f%d' % i, fill=(255, 255, 0))
            S.paste(im, ((k % cols) * w, (k // cols) * h))
        S.save(a.out, quality=88)
        print(a.out, len(ims), 'frames of', len(fs))
    else:
        out = []
        cur = ''
        for i in idx:
            im = load(i)
            for k in sorted(lab):
                if i >= k:
                    cur = lab[k]
            if cur:
                d = ImageDraw.Draw(im)
                d.rectangle((0, im.height - 16, 8 + 7 * len(cur), im.height), fill=(0, 0, 0))
                d.text((4, im.height - 14), cur, fill=(255, 255, 255))
            out.append(im.quantize(colors=a.colors, dither=0))
        out[0].save(a.out, save_all=True, append_images=out[1:], duration=a.ms, loop=0, optimize=False)
        print(a.out, len(out), 'frames', os.path.getsize(a.out) // 1024, 'KB')


if __name__ == '__main__':
    main()
