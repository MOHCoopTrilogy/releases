"""Side-by-side GIF: old C96 (left) vs new C96 (right), same animation, same scene.
    python mkcmp.py <dirA> <prefixA> <dirB> <prefixB> <out.gif> [--a N --b N --step K --crop x0,y0,x1,y1 --w 360 --ms 60]"""
import os, re, sys, argparse
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('dirA'); ap.add_argument('pfxA'); ap.add_argument('dirB'); ap.add_argument('pfxB'); ap.add_argument('out')
ap.add_argument('--a', type=int, default=0); ap.add_argument('--b', type=int, default=10 ** 6); ap.add_argument('--step', type=int, default=1)
ap.add_argument('--crop', default='0,0,1,1'); ap.add_argument('--w', type=int, default=360); ap.add_argument('--ms', type=int, default=60)
ap.add_argument('--la', default='OLD C96 (mod)'); ap.add_argument('--lb', default='NEW C96 (no12u)')
a = ap.parse_args()


def frames(d, p):
    out = {}
    for f in os.listdir(d):
        m = re.match(re.escape(p) + r'_+(\d{4})\.jpg$', f)
        if m:
            out[int(m.group(1))] = os.path.join(d, f)
    return out


A, B = frames(a.dirA, a.pfxA), frames(a.dirB, a.pfxB)
idx = [i for i in sorted(set(A) & set(B)) if a.a <= i <= a.b][::a.step]
cr = [float(x) for x in a.crop.split(',')]
ims = []
for i in idx:
    pair = []
    for src, lab in ((A, a.la), (B, a.lb)):
        im = Image.open(src[i]).convert('RGB')
        W, H = im.size
        im = im.crop((int(W * cr[0]), int(H * cr[1]), int(W * cr[2]), int(H * cr[3])))
        im = im.resize((a.w, int(im.size[1] * a.w / im.size[0])), Image.LANCZOS)
        ImageDraw.Draw(im).text((5, 4), '%s  f%d' % (lab, i), fill=(255, 255, 0))
        pair.append(im)
    S = Image.new('RGB', (pair[0].size[0] * 2 + 4, pair[0].size[1]), (0, 0, 0))
    S.paste(pair[0], (0, 0)); S.paste(pair[1], (pair[0].size[0] + 4, 0))
    ims.append(S)
qs = [im.quantize(colors=112, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for im in ims]
qs[0].save(a.out, save_all=True, append_images=qs[1:], duration=a.ms, loop=0, optimize=True)
print(a.out, len(ims), 'frames', os.path.getsize(a.out) // 1024, 'KB')
