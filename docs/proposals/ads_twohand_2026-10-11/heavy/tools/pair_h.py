"""Before / after still pair of an aim pose: the ENGINE stills of two sessions (light backdrop, centre box drawn) over
the offline left-side view of the same two poses (what the support hand holds - mostly hidden from the eye).

    cd heavy/assets; python ../tools/pair_h.py <prefix> <before session> <after session> <out.jpg> [--yaw 165] [--stance stand]
"""
import sys, os, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw


def still(sess, gun, key):
    fs = sorted(glob.glob('%s/%s/ab__%s__%s__%s__aim__after__[0-9][0-9][0-9][0-9].jpg' % (hv.RUNS, sess, sess, gun, key)))
    assert fs, (sess, gun, key)
    return Image.open(fs[-1]).convert('RGB')


def boxed(im, label, w=640):
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0), width=2)
    im = im.resize((w, w * H // W), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 16), fill=(0, 0, 0)); d.text((4, 2), label, fill=(255, 255, 255))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('before'); ap.add_argument('after'); ap.add_argument('out')
    ap.add_argument('--yaw', type=int, default=165); ap.add_argument('--key')
    a = ap.parse_args()
    key = a.key or 'yaw%d' % a.yaw
    A = boxed(still(a.before, a.gun, key), '%s  aim TODAY (engine %s)' % (a.gun, a.before))
    B = boxed(still(a.after, a.gun, key), '%s  aim NEW: support hand as at the hip (engine %s)' % (a.gun, a.after))
    import posecmp as PC
    H, R, V, CTL = hv.lib()
    g = hv.GUNS[a.gun]
    old = 'viewmodel/bar_stand00.skc'
    new = hv.staged('models/human/animation/' + PC.handpose.out_clip(a.gun))
    rows = H.fps_rows()
    side = []
    for clip, lab, hipcam in ((rows[g['idle']], 'HIP idle (the reference)', True), (old, 'aim TODAY', False), (new, 'aim NEW', False)):
        v = PC.views(clip, g['sight'], g['tik'], '%s %s' % (a.gun, lab), 426, aimref=old, hipcam=hipcam)
        side.append(v[1])
    w, h = A.size
    sh = side[0].size[1]
    S = Image.new('RGB', (2 * w, h + sh), 'white')
    S.paste(A, (0, 0)); S.paste(B, (w, 0))
    for i, im in enumerate(side):
        S.paste(im, (i * 426, h))
    S.save(a.out, quality=88)
    print(a.out, S.size)


if __name__ == '__main__':
    main()
