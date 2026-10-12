"""Offline sheet of a view clip's frames through the calibrated ADS camera (the aim pose's held rig correction) and an
optional close-up from the left-front. Reports per frame the left hand's nearest vertex to the eye and how deep
left-hand vertices sit inside the right hand / gun (crude: distance to the right hand's bone segments).

    python clipview.py <clip.skc> <aim pose.skc> <sight gun> <out.jpg> --frames 0,2,4.. [--gunanim reload] [--cu]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip'); ap.add_argument('aim'); ap.add_argument('gun'); ap.add_argument('out')
    ap.add_argument('--frames', required=True); ap.add_argument('--gunanim', default='idle'); ap.add_argument('--cu', action='store_true')
    ap.add_argument('--prop'); ap.add_argument('--w', type=int, default=480); ap.add_argument('--cols', type=int, default=4)
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    c = R.load(a.clip); aim = R.load(a.aim)
    sight = V.SIGHTS[a.gun]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    W, H = a.w, a.w * 9 // 16
    fov = V.weapon_fov()
    th = math.tan(math.radians(fov / 2)); tv = th * H / W
    if a.prop:
        sp = a.prop.split(':')
        V.PROP.update(tik=sp[0], t0=float(sp[1]) * c.frameTime, t1=float(sp[2]) * c.frameTime, tag='tag_weapon_left')
    fr = [int(x) for x in a.frames.split(',')] if ',' in a.frames or a.frames.isdigit() else \
        list(range(*[int(x) for x in a.frames.split(':')]))
    ims = []
    print(a.clip, 'frames', c.numFrames, 'ft', c.frameTime)
    for f in fr:
        if f >= c.numFrames:
            continue
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), a.gun, sight['tik'], a.gunanim, f * c.frameTime, CTL, corr)
        lh = [s for s in surfs if s['name'] == 'lefthand'][0]['P'] - E
        inv = (lh[:, 0] > 0.05) & (np.abs(lh[:, 1]) < lh[:, 0] * th) & (np.abs(lh[:, 2]) < lh[:, 0] * tv)
        near = float(np.linalg.norm(lh[inv], axis=1).min()) if inv.any() else -1
        if a.cu:
            cen = np.vstack([s['P'] for s in surfs if s['name'] == 'triggerhand']).mean(0)
            rgb, ids, dep = raster.render({'surfs': surfs}, cen + np.array([14.0, 18.0, 2.0]), cen, np.array([0, 0, 1.0]),
                                          fov=42, W=W, H=H, bg=(150, 160, 170), znear=1.0, tex=True)
            rgb = rgb.astype(np.uint8)
        else:
            rgb, _, _ = V.shade_render(surfs, E, fov, W, H)
        im = Image.fromarray(rgb)
        txt = 'f%d  Lhand in view %d%%  near %.1fu' % (f, 100 * inv.mean(), near)
        ImageDraw.Draw(im).text((4, 4), txt, fill=(0, 0, 0))
        print(txt)
        ims.append(im)
    cols = min(a.cols, len(ims))
    S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * W, (i // cols) * H))
    S.save(a.out, quality=88)
    print(a.out)


if __name__ == '__main__':
    main()
