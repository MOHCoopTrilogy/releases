"""Offline before / after of an aim pose from the eye (calibrated ADS camera), centre box drawn, light backdrop, plus
the centre-box cover of each and which SURFACES are inside the box.

    cd smg/assets; python ../tools/eyepair.py <sight gun> <old aim.skc> <new aim.skc> <out.jpg> [--w 960] [--crop 0.5]
"""
import sys, os, json, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
BG = (206, 212, 218)


def eye(gun, clip, W, corr_clip=None):
    from PIL import Image, ImageDraw
    a = R.load(clip)
    sight = V.SIGHTS[gun]
    pd = R.pose_dict(a, a.numFrames - 1)
    ca = R.load(corr_clip) if corr_clip else a
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(ca, ca.numFrames - 1), CTL), sight)
    H = W * 9 // 16
    surfs, E, Wb = V.scene2(pd, gun, sight['tik'], 'idle', 0.0, CTL, corr, None)
    rgb, ids, _ = V.shade_render(surfs, E, V.weapon_fov(), W, H, bg=BG, tex=True)
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)
    box = ids[y0:y1, x0:x1]
    names = {}
    sid = np.where(box >= 0, box // 1000000, -1)
    for i in np.unique(sid[sid >= 0]):
        nm = surfs[int(i)]['name']
        names[nm] = round(names.get(nm, 0.0) + 100.0 * float((sid == i).mean()), 1)
    # support hand / left sleeve pixels to the RIGHT of the screen centre, as a share of the frame (a left hand showing
    # on the right of the gun reads wrong from the eye)
    full = np.where(ids >= 0, ids // 1000000, -1)
    lh = [i for i, s in enumerate(surfs) if s['name'] in ('lefthand', 'leftsleeve', 'leftarm')]
    names['_left_hand_right_of_centre_px'] = int(np.isin(full[:, W // 2 + 2:], lh).sum())
    names['_surfs'] = sorted(set(s['name'] for s in surfs if not s['name'].lower().startswith(gun.split('_')[0][:4])))[:8]
    im = Image.fromarray(rgb.astype(np.uint8))
    ImageDraw.Draw(im).rectangle((x0, y0, x1, y1), outline=(255, 230, 0), width=2)
    return im, float((box >= 0).mean()), names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('out')
    ap.add_argument('--w', type=int, default=960); ap.add_argument('--crop', type=float, default=0.6)
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    ims = []
    for lab, clip in (('BEFORE', a.old), ('AFTER', a.new)):
        im, cov, names = eye(a.gun, clip, a.w, a.old)
        W, H = im.size
        cw, ch = int(W * a.crop), int(H * a.crop)
        im = im.crop(((W - cw) // 2, int((H - ch) * 0.62), (W - cw) // 2 + cw, int((H - ch) * 0.62) + ch))
        ImageDraw.Draw(im).text((6, 6), '%s %s  centre box covered %.1f %%' % (a.gun, lab, 100 * cov), fill=(0, 0, 0))
        print(lab, os.path.basename(clip), 'box %.1f %%' % (100 * cov), names)
        ims.append(im)
    S = Image.new('RGB', (ims[0].width * 2 + 6, ims[0].height), 'white')
    S.paste(ims[0], (0, 0)); S.paste(ims[1], (ims[0].width + 6, 0))
    S.save(a.out, quality=90)
    print(a.out)


if __name__ == '__main__':
    main()
