"""Offline LOOK at frames of a staged aimed clip, large: the calibrated ADS camera (textured, centre box drawn), an
optional zoom on a part of the picture, and optional outside views (left side / above-left) centred on the left hand.

    cd heavy/assets; python ../tools/eyeview.py <prefix> "<clip.skc>|<gun anim>" <f,f,...|a:b:step> <out.jpg>
          [--w 640] [--zoom x0,y0,x1,y1 (fractions of the picture)] [--side] [--cols 4] [--prop tik:f0:f1[:tag]]
          [--aim clip]   (default: the staged aim pose of the prefix)
IRONSIGHT_EXTRA_PAKS=<overlay> for staged gun rows / textures.
"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
_c = os.getcwd(); os.chdir(hv.BOLT)
import raster
os.chdir(_c)
from PIL import Image, ImageDraw
import handpose


def frames(s, n):
    if ':' in s:
        p = [int(x) for x in s.split(':')]
        return list(range(p[0], min(p[1], n), p[2] if len(p) > 2 else 1))
    return [int(x) for x in s.split(',')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('prefix'); ap.add_argument('part'); ap.add_argument('frames'); ap.add_argument('out')
    ap.add_argument('--w', type=int, default=640); ap.add_argument('--zoom'); ap.add_argument('--side', action='store_true')
    ap.add_argument('--cols', type=int, default=4); ap.add_argument('--prop'); ap.add_argument('--aim')
    ap.add_argument('--sight')
    a = ap.parse_args()
    g = hv.GUNS[a.prefix]
    gun = a.sight or g['sight']
    aimc = a.aim or hv.staged('models/human/animation/' + handpose.out_clip(a.prefix))
    aim = R.load(aimc if os.path.isfile(aimc) else R.ANIM + aimc)
    sight = V.SIGHTS[gun]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    sp = a.part.split('|')
    c = R.load(sp[0] if os.path.isfile(sp[0]) else R.ANIM + sp[0]); anim = sp[1] if len(sp) > 1 else 'idle'
    V.PROP.clear()
    if a.prop:
        pp = a.prop.split(':')
        V.PROP.update(tik=pp[0], t0=float(pp[1]) * c.frameTime, t1=float(pp[2]) * c.frameTime, tag=(pp[3] if len(pp) > 3 else 'tag_weapon_left'))
    W = a.w; Hh = W * 9 // 16
    fov = V.weapon_fov()
    z = [float(x) for x in a.zoom.split(',')] if a.zoom else None
    ims = []
    for f in frames(a.frames, c.numFrames):
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), gun, sight['tik'], anim, f * c.frameTime, CTL, corr, None)
        if z:
            # render at the resolution that makes the zoomed part W wide
            k = 1.0 / (z[2] - z[0])
            BW = int(W * k); BH = BW * 9 // 16
            rgb, ids, _ = V.shade_render(surfs, E, fov, BW, BH)
            im = Image.fromarray(rgb).crop((int(z[0] * BW), int(z[1] * BH), int(z[2] * BW), int(z[3] * BH)))
            im = im.resize((W, W * im.size[1] // im.size[0]), Image.LANCZOS)
        else:
            rgb, ids, _ = V.shade_render(surfs, E, fov, W, Hh)
            im = Image.fromarray(rgb)
            ImageDraw.Draw(im).rectangle((int(W * 0.4), int(Hh * 0.4), int(W * 0.6), int(Hh * 0.6)), outline=(255, 230, 0))
        ImageDraw.Draw(im).text((4, 4), 'f%d' % f, fill=(0, 0, 0))
        ims.append(im)
        if a.side:
            lh = [s for s in surfs if s['name'] == 'lefthand'][0]['P']
            cen = lh.mean(0)
            up = np.array([0, 0, 1.0]); fwd = np.array([1.0, 0, 0]); left = np.array([0, 1.0, 0])
            for nm, off in (('left side', left * 26 + up * 2), ('above-left', left * 10 + up * 24 - fwd * 4)):
                r2, _, _ = raster.render({'surfs': surfs}, cen + off, cen, up, fov=40, W=im.size[0], H=im.size[1],
                                         bg=(150, 160, 170), znear=1.0, tex=True)
                i2 = Image.fromarray(r2.astype(np.uint8)); ImageDraw.Draw(i2).text((4, 4), 'f%d %s' % (f, nm), fill=(0, 0, 0))
                ims.append(i2)
    cols = min(a.cols, len(ims))
    w, h = ims[0].size
    S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * w, (i // cols) * h))
    S.save(a.out, quality=88)
    print(a.out, len(ims), 'cells')


if __name__ == '__main__':
    main()
