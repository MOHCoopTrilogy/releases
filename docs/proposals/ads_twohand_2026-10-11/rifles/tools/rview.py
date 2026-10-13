"""OFFLINE close look at an aimed clip: chosen clip frames, textured, cropped to a part of the picture, with the gun's
own frame-keyed surfaces (the charger / rounds on the action) and the server's ammo prop on the hand tag drawn as the
tik rows time them. For judging hand contacts before an engine run - not a measurement.

    cd rifles/assets; python ../tools/rview.py kar98 out.jpg [--clip <view clip>] [--frames 40:66:2 | 8,12,43] [--crop x0,y0,x1,y1] [--w 960] [--cols 6]

crop is in fractions of the picture (default 0.25,0.35,0.85,1.0 = the lowered rifle and the working hand).
"""
import sys, os, json, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_c = os.getcwd(); os.chdir(T)
import staged  # noqa
import vmcam as V
os.chdir(_c)
R = V.R
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
A = 'models/human/animation/'
# per gun: sight key, aim pose, default view clip, gun anim, off-hand window (clip frames), frame-keyed gun surfaces
# {surface: [(first, last)]} (clip frames it is DRAWN; any other listed surface frame = hidden), server prop
VIEW = {
    'kar98': dict(sight='kar98', aim='viewmodel/kar_stand00.skc', clip='viewmodel/rifle/kar98_reload_ads.skc', anim='reload',
                  oh=(1, 100), vis={'material7': [(43, 52)], 'material8': [(43, 61)]},
                  prop=dict(tik='models/ammo/kar98_clip_reload.tik', tag='tag_weapon_right', f0=27, f1=45)),
    'mosin': dict(sight='mosin_nagant_rifle', aim='viewmodel/kar_stand00.skc', clip='viewmodel/mosin_nagant/mosin_reload_ads.skc', anim='reload',
                  oh=(1, 91), prop=dict(tik='models/ammo/enfield_clip1.tik', tag='tag_weapon_right', f0=30, f1=55)),
    'enfield': dict(sight='lee_enfield', aim='viewmodel/kar_stand00.skc', clip='viewmodel/enfield/enfield_reload_ads.skc', anim='reload',
                    oh=(1, 115), prop=dict(tik='models/ammo/enfield_clip1.tik', tag='tag_weapon_right', f0=30, f1=82)),
    'enfield2': dict(sight='lee_enfield', aim='viewmodel/kar_stand00.skc', clip='viewmodel/enfield/enfield_reload_ads.skc', anim='reload',
                     oh=(1, 115), prop=dict(tik='models/ammo/enfield_clip2.tik', tag='Bip01 R Hand', f0=30, f1=55)),
    'springfield': dict(sight='springfield_unscoped', aim='viewmodel/sprng_stand00.skc', clip='viewmodel/rifle/springfield_reload_ads.skc', anim='reload', oh=(1, 48)),
    'springfield_single': dict(sight='springfield_unscoped', aim='viewmodel/sprng_stand00.skc', clip='viewmodel/rifle/springfield_reload_single_ads.skc',
                               anim='reload_single', oh=(0, 28), prop=dict(tik='models/ammo/springfield_clip_reload.tik', tag='tag_weapon_right', f0=0, f1=6)),
    'springfield_end': dict(sight='springfield_unscoped', aim='viewmodel/sprng_stand00.skc', clip='viewmodel/rifle/springfield_reload_end_ads.skc', anim='reload_end', oh=(0, 32)),
    'garand': dict(sight='garand', aim='viewmodel/grnd_stand00.skc', clip='viewmodel/rifle/coop_garand_reload_ads.skc', anim='reload',
                   oh=(1, 57), vis={'material8': [(28, 47)]},
                   prop=dict(tik='models/ammo/garand_clip_reload.tik', tag='tag_weapon_right', f0=4, f1=42)),
}


def render(gun, out, clip=None, frames=None, crop=(0.25, 0.35, 0.85, 1.0), w=960, cols=6, anim=None, noprop=False):
    from PIL import Image, ImageDraw
    g = VIEW[gun]
    aim = R.load(A + g['aim'])
    sight = V.SIGHTS[g['sight']]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    W, H = w, w * 9 // 16
    fov = V.weapon_fov()
    c = R.load(clip or (A + g['clip']))
    an = anim or g['anim']
    oh = (g['oh'][0] * c.frameTime, g['oh'][1] * c.frameTime) if g.get('oh') else None
    frames = frames or list(range(0, c.numFrames, 4))
    ims = []
    for f in frames:
        f = min(f, c.numFrames - 1)
        t = f * c.frameTime
        V.PROP.clear()
        p = g.get('prop')
        if p and not noprop:
            V.PROP.update(tik=p['tik'], tag=p['tag'], t0=p['f0'] * c.frameTime, t1=p['f1'] * c.frameTime)
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), g['sight'], sight['tik'], an, t, CTL, corr, oh, lambda fr: True)
        keep = []
        for s in surfs:
            v = g.get('vis', {}).get(s['name'])
            if v is not None and not any(a <= f <= b for a, b in v):
                continue
            keep.append(s)
        rgb, ids, _ = V.shade_render(keep, E, fov, W, H, tex=True)
        im = Image.fromarray(rgb)
        d = ImageDraw.Draw(im)
        d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0))
        im = im.crop((int(W * crop[0]), int(H * crop[1]), int(W * crop[2]), int(H * crop[3])))
        ImageDraw.Draw(im).text((4, 3), 'f%d' % f, fill=(0, 0, 0))
        ims.append(im)
    cw, ch = ims[0].size
    cols = min(cols, len(ims))
    S = Image.new('RGB', (cw * cols, ch * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * cw, (i // cols) * ch))
    S.save(out, quality=88)
    print(out, S.size)


def parse_frames(s):
    if ':' in s:
        p = [int(x) for x in s.split(':')]
        return list(range(p[0], p[1] + 1, p[2] if len(p) > 2 else 1))
    return [int(x) for x in s.split(',')]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('out'); ap.add_argument('--clip'); ap.add_argument('--frames')
    ap.add_argument('--crop', default='0.25,0.35,0.85,1.0'); ap.add_argument('--w', type=int, default=960)
    ap.add_argument('--cols', type=int, default=6); ap.add_argument('--anim'); ap.add_argument('--noprop', action='store_true')
    a = ap.parse_args()
    render(a.gun, a.out, a.clip, parse_frames(a.frames) if a.frames else None, tuple(float(x) for x in a.crop.split(',')),
           a.w, a.cols, a.anim, a.noprop)
