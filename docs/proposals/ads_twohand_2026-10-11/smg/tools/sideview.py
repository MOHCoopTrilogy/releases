"""Offline look at a view clip's hands ON THE GUN: per frame three panels - the eye (calibrated ADS camera, centre box
drawn), the gun's LEFT side, and from below-left-front. Where is the support hand, what is it holding?

    cd smg/assets; python ../tools/sideview.py <clip.skc> <aim pose.skc> <sight gun> <out.jpg> --frames 0,10 [--gunanim idle]
                                                [--hip]  (a hip clip: eye panel from the pose's own eye, no rig solve)
Also prints the support wrist in the gun frame (weapon tag: x fwd, y right, z down; u).
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
BG = (206, 212, 218)


def panels(c, f, gun, corr, gunanim='idle', W=480, eye_tex=True, offhand=None, only_eye=False):
    from PIL import Image, ImageDraw
    H = W * 9 // 16
    sight = V.SIGHTS[gun]
    fov = V.weapon_fov()
    surfs, E, Wb = V.scene2(R.pose_dict(c, f), gun, sight['tik'], gunanim, f * c.frameTime, CTL, corr, offhand)
    rgb, ids, _ = V.shade_render(surfs, E, fov, W, H, bg=BG, tex=eye_tex)
    eye = Image.fromarray(rgb.astype(np.uint8))
    d = ImageDraw.Draw(eye)
    d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0))
    lh = np.vstack([s['P'] for s in surfs if s['name'] == 'lefthand']).mean(0)
    rh = np.vstack([s['P'] for s in surfs if s['name'] == 'triggerhand']).mean(0)
    cen = (lh + rh) / 2.0
    fw = rh - E; fw[2] = 0; fw /= np.linalg.norm(fw)          # roughly the gun's forward in the scene (level)
    left = np.array([-fw[1], fw[0], 0.0])
    up = np.array([0, 0, 1.0])
    out = [eye]
    if only_eye:
        return out
    # SV_RIGHT=1: the gun's RIGHT side and from above-right-rear instead (a handle on the right, worked by the firing hand)
    cams = ((left * -44 + up * 1.0, 40), (left * -16 - fw * 20 + up * 26, 44)) if os.environ.get('SV_RIGHT') else \
        ((left * 44 + up * 1.0, 40), (left * 20 + fw * 16 - up * 22, 44))
    for off, fv in cams:
        r2, _, _ = raster.render({'surfs': surfs}, cen + off, cen, up, fov=fv, W=W, H=H, bg=BG, znear=1.0, tex=True)
        out.append(Image.fromarray(r2.astype(np.uint8)))
    return out


def corr_of(aimclip, gun):
    aim = R.load(aimclip)
    return V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), V.SIGHTS[gun])


def rel_hand(c, f):
    Wd = R.evaluate(R.pose_dict(c, f))
    return (Wd['Bip01 L Hand'] @ R.inv(Wd['tag_weapon_right']))[3, :3] * R.S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip'); ap.add_argument('aim'); ap.add_argument('gun'); ap.add_argument('out')
    ap.add_argument('--frames', default='0'); ap.add_argument('--gunanim', default='idle'); ap.add_argument('--w', type=int, default=480)
    ap.add_argument('--label', default=''); ap.add_argument('--prop', help='tik:f0:f1[:tag] an attached ammo prop (clip frames)')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    c = R.load(a.clip)
    corr = corr_of(a.aim, a.gun)
    if a.prop:
        sp = a.prop.split(':')
        V.PROP.update(tik=sp[0], t0=float(sp[1]) * c.frameTime, t1=float(sp[2]) * c.frameTime, tag=(sp[3] if len(sp) > 3 else 'tag_weapon_left'))
    fr = [int(x) for x in a.frames.split(',')] if ':' not in a.frames else list(range(*[int(x) for x in a.frames.split(':')]))
    rows = []
    np.set_printoptions(precision=1, suppress=True)
    for f in fr:
        ps = panels(c, f, a.gun, corr, a.gunanim, a.w)
        ImageDraw.Draw(ps[0]).text((4, 4), '%s f%d  L wrist (gun frame) %s' % (a.label or os.path.basename(a.clip), f, rel_hand(c, f)), fill=(0, 0, 0))
        rows.append(ps)
        print(os.path.basename(a.clip), 'f%d' % f, 'L wrist in the gun frame', rel_hand(c, f))
    W, H = rows[0][0].size
    S = Image.new('RGB', (W * 3, H * len(rows)), 'white')
    for i, ps in enumerate(rows):
        for j, im in enumerate(ps):
            S.paste(im, (j * W, i * H))
    S.save(a.out, quality=88)
    print(a.out)


if __name__ == '__main__':
    main()
