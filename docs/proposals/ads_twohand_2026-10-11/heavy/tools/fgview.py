"""Offline LOOK at an FG 42 reload clip from the eye - the calibrated ADS camera (iron sights) or the HIP camera (the
hip pose's eyes bone) - with the gun's own animation row, the server's magazine prop on the off-hand tag in its window
and the gun's own magazine hidden in the same frames (what FG42.tik's `reload` row does on the server).

    cd heavy/assets; python ../tools/fgview.py <clip.skc> <gun anim> <f,f,..|a:b:step> <out.jpg> [--hip] [--w 480]
          [--cols 6] [--zoom x0,y0,x1,y1] [--tik models/weapons/coop_fg42_irons.tik] [--right]  (--right: an outside
          view of the gun's right side beside each frame)
IRONSIGHT_EXTRA_PAKS=<overlay> so that the staged tik / mesh / gun clip are found.
"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
import fg42bake as FB
H, R, V, CTL = FB.H, FB.R, FB.V, FB.CTL
_c = os.getcwd(); os.chdir(hv.BOLT)
import raster
os.chdir(_c)
from PIL import Image, ImageDraw


def frames(s, n):
    if ':' in s:
        p = [int(x) for x in s.split(':')]
        return list(range(p[0], min(p[1], n), p[2] if len(p) > 2 else 1))
    return [int(x) for x in s.split(',')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip'); ap.add_argument('anim'); ap.add_argument('frames'); ap.add_argument('out')
    ap.add_argument('--hip', action='store_true'); ap.add_argument('--w', type=int, default=480); ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--zoom'); ap.add_argument('--tik', default='models/weapons/coop_fg42_irons.tik'); ap.add_argument('--right', action='store_true')
    a = ap.parse_args()
    pose = FB.HIPPOSE if a.hip else FB.AIMPOSE
    aim = R.load(R.ANIM + pose)
    sight = V.SIGHTS[FB.SIGHT]
    pc = R.pose_dict(aim, aim.numFrames - 1)
    Wcc = V.evaluate_ctl(pc, CTL)
    corr = V.rig_target(Wcc, sight)
    if a.hip:
        corr = dict(ax=np.array([0, 0, 1.0]), ang=0.0, T=np.zeros(3), cant=0.0, relief=0.0, E=Wcc['eyes bone'][3, 0:3] * R.S, F=corr['F'], R=corr['R'])
    c = R.load(a.clip if os.path.isfile(a.clip) else R.ANIM + a.clip)
    V.PROP.clear()
    V.PROP.update(tik='models/ammo/fg42clip.tik', t0=20.3 * c.frameTime, t1=40.5 * c.frameTime, tag='tag_weapon_left')
    W = a.w; Hh = W * 9 // 16
    fov = V.weapon_fov()
    z = [float(x) for x in a.zoom.split(',')] if a.zoom else None
    ims = []
    for f in frames(a.frames, c.numFrames):
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), FB.SIGHT, a.tik, a.anim, f * c.frameTime, CTL, corr, None)
        if 20 <= f < 40:
            surfs = [s for s in surfs if not (s.get('gun') and s['name'].lower() == 'fg42clip')]
        if z:
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
        if a.right:
            gp = np.vstack([s['P'] for s in surfs if s.get('gun')])
            cen = gp.mean(0)
            up = np.array([0, 0, 1.0]); fwd = np.array([1.0, 0, 0]); left = np.array([0, 1.0, 0])
            r2, _, _ = raster.render({'surfs': surfs}, cen - left * 30 + up * 6 - fwd * 6, cen, up, fov=40, W=im.size[0], H=im.size[1],
                                     bg=(150, 160, 170), znear=1.0, tex=True)
            i2 = Image.fromarray(r2.astype(np.uint8)); ImageDraw.Draw(i2).text((4, 4), 'f%d right side' % f, fill=(0, 0, 0))
            ims.append(i2)
    cols = min(a.cols, len(ims))
    w, h = ims[0].size
    S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * w, (i // cols) * h))
    S.save(a.out, quality=86)
    print(a.out, len(ims), 'cells')


if __name__ == '__main__':
    main()
