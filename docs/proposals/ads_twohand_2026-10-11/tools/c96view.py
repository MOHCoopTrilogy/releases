"""c96view.py - offline tiles of a C96 hands clip WITH the server's stripper-clip props (pistol lane, 2026-10-13).

The server's torso row `coop_reload_c96` (anims_shared.txt) hangs the mod's own prop on the hands' tags:
    28 full clip on tag_weapon_left | 41 full clip on tag_weapon_right (the gun) | 44 the EMPTY clip there
    47 the empty clip on tag_weapon_left | 56 gone
vmcam.scene2 draws one prop only; this draws the whole schedule (torso frames -> seconds by the torso clip's frame time).

    python c96view.py <hands.skc> <gun anim> <out.jpg> [--frames 24-60:2] [--crop 0.2,0.3,0.85,1.0] [--w 640] [--cols 5]
                      [--aim <aim.skc>] [--gun mauser_c96] [--noprops] [--box]
Run from the staging dir (IRONSIGHT_EXTRA_PAKS = the wip overlay).
"""
import sys, os, json, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R
PR = V.PR
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
FULL = 'models/ammo/coop_c96_stripper_full.tik'
EMPTY = 'models/ammo/coop_c96_stripper_empty.tik'
SCHED = [(FULL, 28, 41, 'tag_weapon_left'), (FULL, 41, 44, 'tag_weapon_right'), (EMPTY, 44, 47, 'tag_weapon_right'), (EMPTY, 47, 56, 'tag_weapon_left')]
TORSO_FT = 1 / 30.0


def scene(pd, gun, tik, anim, t, corr, props=True):
    Wb = V.evaluate_ctl(pd, CTL)
    surfs = V.arm_surfs(Wb, gun)
    gs, _ = PR.gun_surfs(Wb, tik, anim, t, lambda f: False, 'tag_weapon_right')
    for s in gs:
        s['gun'] = True
    if props:
        for ptik, f0, f1, tag in SCHED:
            if f0 * TORSO_FT - 1e-6 <= t < f1 * TORSO_FT - 1e-6:
                ps, _ = PR.gun_surfs(Wb, ptik, 'idle', 0.0, lambda f: True, tag)
                for s in ps:
                    s['gun'] = True; s['name'] = 'prop_' + s['name']
                gs = gs + ps
    surfs = surfs + gs
    E = Wb['eyes bone'][3, 0:3] * R.S
    if corr is not None:
        shift = E - corr['E']
        surfs = [dict(s, P=V.apply_corr(s['P'] - shift, corr)) for s in surfs]
        E = corr['E']
    return surfs, E


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip'); ap.add_argument('anim'); ap.add_argument('out')
    ap.add_argument('--frames', default='24-60:2'); ap.add_argument('--crop', default='0,0,1,1')
    ap.add_argument('--w', type=int, default=640); ap.add_argument('--cols', type=int, default=5)
    ap.add_argument('--aim', default='models/human/animation/viewmodel/pistol/p38_ads2h.skc'); ap.add_argument('--gun', default='mauser_c96')
    ap.add_argument('--noprops', action='store_true'); ap.add_argument('--box', action='store_true'); ap.add_argument('--tik')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    aim = R.load(a.aim)
    sight = V.SIGHTS[a.gun]
    tik = a.tik or sight['tik']
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    c = R.load(a.clip)
    W, H = a.w, a.w * 9 // 16
    fov = V.weapon_fov()
    rng, st = (a.frames.split(':') + ['1'])[:2]
    f0, f1 = [int(x) for x in rng.split('-')]
    cr = [float(x) for x in a.crop.split(',')]
    box = (int(W * cr[0]), int(H * cr[1]), int(W * cr[2]), int(H * cr[3]))
    ims = []
    for f in range(f0, min(f1, c.numFrames - 1) + 1, int(st)):
        surfs, E = scene(R.pose_dict(c, f), a.gun, tik, a.anim, f * c.frameTime, corr, not a.noprops)
        rgb, ids, _ = V.shade_render(surfs, E, fov, W, H, tex=True)
        im = Image.fromarray(rgb)
        d = ImageDraw.Draw(im)
        if a.box:
            d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0))
        im = im.crop(box)
        ImageDraw.Draw(im).text((3, 2), 'f%d' % f, fill=(255, 255, 0))
        ims.append(im)
    cols = min(a.cols, len(ims))
    tw, th = ims[0].size
    S = Image.new('RGB', (tw * cols, th * ((len(ims) + cols - 1) // cols)), 'black')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * tw, (i // cols) * th))
    S.save(a.out, quality=88)
    print(a.out, S.size, 'clip frames', c.numFrames, 'ft %.4f' % c.frameTime)


if __name__ == '__main__':
    main()
