"""Offline before / after sheet of an aim pose: the calibrated ADS camera (centre box drawn) and a view from the left
side and from below-left that shows what the support hand actually holds.

    cd heavy/assets; python ../tools/posecmp.py <prefix> <out.jpg> [clip ...]     default clips: hip idle, old aim, staged aim
"""
import sys, os, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
_c = os.getcwd(); os.chdir(hv.BOLT)
import raster
os.chdir(_c)
from PIL import Image, ImageDraw
import handpose


def views(clip, gun, tik, label, W=480, aimref=None, hipcam=False):
    a = R.load(clip if os.path.isfile(clip) else R.ANIM + clip)
    f = 0
    pd = R.pose_dict(a, f)
    sight = V.SIGHTS[gun]
    ref = R.load(aimref if os.path.isfile(aimref) else R.ANIM + aimref)
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(ref, ref.numFrames - 1), CTL), sight)
    Hh = W * 9 // 16
    fov = V.weapon_fov()
    surfs, E, Wb = V.scene2(pd, gun, tik, 'idle', 0.0, CTL, corr, None)
    ims = []
    if not hipcam:
        rgb, ids, _ = V.shade_render(surfs, E, fov, W, Hh)
        im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
        x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(Hh * 0.4), int(Hh * 0.6)
        cov = 100.0 * (ids >= 0)[y0:y1, x0:x1].mean()
        d.rectangle((x0, y0, x1, y1), outline=(255, 230, 0))
        d.text((4, 4), '%s - eye view, box covered %.1f %%' % (label, cov), fill=(0, 0, 0))
        ims.append(im)
    else:
        im = Image.new('RGB', (W, Hh), (150, 160, 170)); ImageDraw.Draw(im).text((4, 4), label + ' (hip: no eye view)', fill=(0, 0, 0))
        ims.append(im)
    lh = [s for s in surfs if s['name'] == 'lefthand'][0]['P']
    cen = lh.mean(0)
    fwd = corr['F'] / np.linalg.norm(corr['F']) if 'F' in corr else np.array([1.0, 0, 0])
    up = np.array([0, 0, 1.0])
    left = np.cross(up, fwd); left /= np.linalg.norm(left)
    for nm, off in (('left side', left * 30 + up * 2), ('below-left', left * 16 - up * 22 + fwd * 4)):
        rgb, _, _ = raster.render({'surfs': surfs}, cen + off, cen, up, fov=40, W=W, H=Hh, bg=(150, 160, 170), znear=1.0, tex=True)
        im = Image.fromarray(rgb.astype(np.uint8)); ImageDraw.Draw(im).text((4, 4), '%s - %s' % (label, nm), fill=(0, 0, 0))
        ims.append(im)
    return ims


def main():
    p, out = sys.argv[1], sys.argv[2]
    g = hv.GUNS[p]
    rows = H.fps_rows()
    old = 'viewmodel/bar_stand00.skc'
    new = hv.staged('models/human/animation/' + handpose.out_clip(p))
    sets = [(rows[g['idle']], 'HIP idle', True), (old, 'aim TODAY', False), (new, 'aim NEW', False)]
    W = 480; Hh = W * 9 // 16
    S = Image.new('RGB', (W * 3, Hh * len(sets)), 'white')
    for r, (clip, lab, hipcam) in enumerate(sets):
        for c, im in enumerate(views(clip, g['sight'], g['tik'], '%s %s' % (p, lab), W, aimref=old, hipcam=hipcam)):
            S.paste(im, (c * W, r * Hh))
    S.save(out, quality=88)
    print(out)


if __name__ == '__main__':
    main()
