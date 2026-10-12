"""OFFLINE centre-box check of a staged aimed clip set, before an engine run (the engine figure is centrebox.py's).

The calibrated ADS camera of clipview.py renders every frame of each part small; the centre box is the middle 20 % of
the picture; a frame's EXTRA cover is the share of box pixels covered by the first-person model that the settled aim
(the aim clip's last frame, mask grown by the same few pixels as centrebox.py) does not cover. Bar: under 2 %.

    python offbox.py <sight gun> <aim.skc> <clip.skc>|<gun anim>[|o0,o1] [...] [--w 320] [--sheet out.jpg] [--every 2] [--prop tik:f0:f1[:tag]]
Run from the staging dir. o0,o1 = frames during which the gun is in the off hand (Nagant).
"""
import sys, os, json, math, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
import raster
os.chdir(_c)
R = V.R
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))


def grow(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('aim'); ap.add_argument('parts', nargs='+')
    ap.add_argument('--w', type=int, default=320); ap.add_argument('--sheet'); ap.add_argument('--every', type=int, default=2)
    ap.add_argument('--cols', type=int, default=8); ap.add_argument('--prop')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    aim = R.load(a.aim)
    sight = V.SIGHTS[a.gun]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    W, H = a.w, a.w * 9 // 16
    fov = V.weapon_fov()
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)

    def frame(c, f, anim, oh, tex=False):
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), a.gun, sight['tik'], anim, f * c.frameTime, CTL, corr, oh)
        return V.shade_render(surfs, E, fov, W, H, tex=tex)
    _, ids, _ = frame(aim, aim.numFrames - 1, 'idle', None)
    aimmask = grow((ids >= 0)[y0:y1, x0:x1], max(1, int(round(6 * W / 1280.0))))
    print('aim covers %.1f %% of the box' % (100 * (ids >= 0)[y0:y1, x0:x1].mean()))
    ims = []
    worst = 0.0
    for spec in a.parts:
        sp = spec.split('|')
        c = R.load(sp[0]); anim = sp[1] if len(sp) > 1 else 'idle'
        oh = None
        if len(sp) > 2 and sp[2]:
            o0, o1 = [float(x) for x in sp[2].split(',')]
            oh = (o0 * c.frameTime, o1 * c.frameTime)
        V.PROP.clear()
        if a.prop and '_single' in sp[0]:
            pp = a.prop.split(':')
            V.PROP.update(tik=pp[0], t0=float(pp[1]) * c.frameTime, t1=float(pp[2]) * c.frameTime, tag=(pp[3] if len(pp) > 3 else 'tag_weapon_left'))
        ex = []
        for f in range(c.numFrames):
            want = a.sheet and f % a.every == 0
            rgb, ids, _ = frame(c, f, anim, oh, tex=bool(want))
            m = (ids >= 0)[y0:y1, x0:x1]
            e = float((m & ~aimmask).mean())
            ex.append(e)
            if want:
                im = Image.fromarray(rgb)
                d = ImageDraw.Draw(im)
                d.rectangle((x0, y0, x1, y1), outline=(255, 230, 0) if e <= 0.02 else (255, 0, 0))
                d.text((3, 2), '%s f%d  %.1f%%' % (os.path.basename(sp[0])[:-4][-18:], f, 100 * e), fill=(0, 0, 0))
                ims.append(im)
        worst = max(worst, max(ex))
        print('%-44s %2d frames  max extra %5.1f %%  over 2 %%: %s' % (os.path.basename(sp[0]), c.numFrames, 100 * max(ex),
              ' '.join('%d:%.0f' % (k, 100 * e) for k, e in enumerate(ex) if e > 0.02) or '-'))
    print('WORST %.1f %%  %s' % (100 * worst, 'PASS' if worst <= 0.02 else 'over the bar'))
    if a.sheet and ims:
        cols = min(a.cols, len(ims))
        S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
        for i, im in enumerate(ims):
            S.paste(im, ((i % cols) * W, (i // cols) * H))
        S.save(a.sheet, quality=86)
        print(a.sheet)


if __name__ == '__main__':
    main()
