"""OFFLINE grip explorer: bake an aimed bolt clip with recipe overrides per variant and draw the same clip frames of
every variant side by side (textured, centre box drawn, hands' box cover printed) - to choose a knob grip by eye.

    cd rifles/assets; python ../tools/gripx.py <gun> <out.jpg> --frames 12,18 --w 560 \
        --v "A: knob_off=(0,1.2,0.6)" --v "B: grip_rot=(-60,0,0); knob_off=(0,0.4,0.2); finger_s={'1':(0.6,0.8,0.8)}"
Variant clips are written beside the staged one as *_x<n>.skc and deleted afterwards (the staged clip is not touched).
"""
import sys, os, ast, json, argparse, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boltphys as BP
from PIL import Image, ImageDraw
V, R = BP.K.V, BP.R
CTL = BP.CTL


def render(g, clip, frames, w, crop=None):
    sight = V.SIGHTS[g['sight']]
    aim = R.load(R.ANIM + g['aim'])
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    W, H = w, w * 9 // 16
    fov = V.weapon_fov()
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)
    c = R.load(clip)
    s0, E0, _ = V.scene2(R.pose_dict(aim, aim.numFrames - 1), g['sight'], sight['tik'], 'idle', 0.0, CTL, corr, None)
    _, ids0, _ = V.shade_render(s0, E0, fov, W, H, tex=False)
    out = []
    for f in frames:
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), g['sight'], sight['tik'], g.get('anim', 'rechamber'), f * c.frameTime, CTL, corr, None)
        rgb, ids, _ = V.shade_render(surfs, E, fov, W, H, tex=True)
        box = ids[y0:y1, x0:x1]
        hand = np.zeros(box.shape, bool)
        for si, s in enumerate(surfs):
            if 'hand' in s['name'].lower():
                hand |= (box // 1000000 == si) & (box >= 0)
        hp = 100.0 * float((hand & ~(ids0[y0:y1, x0:x1] >= 0)).mean())
        im = Image.fromarray(rgb)
        ImageDraw.Draw(im).rectangle((x0, y0, x1, y1), outline=(255, 230, 0) if hp <= 2.0 else (255, 0, 0))
        if crop:
            im = im.crop((int(W * crop[0]), int(H * crop[1]), int(W * crop[2]), int(H * crop[3]))).resize((W, int(W * (crop[3] - crop[1]) * H / ((crop[2] - crop[0]) * W))), Image.LANCZOS)
        out.append((im, hp))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('out'); ap.add_argument('--frames', default='12,18'); ap.add_argument('--w', type=int, default=560)
    ap.add_argument('--v', action='append', default=[]); ap.add_argument('--crop', help='x0,y0,x1,y1 fractions of the picture')
    a = ap.parse_args()
    frames = [int(x) for x in a.frames.split(',')]
    crop = [float(x) for x in a.crop.split(',')] if a.crop else None
    base = copy.deepcopy(BP.GUNS[a.gun])
    rows = []
    for n, spec in enumerate(a.v or ['staged:']):
        label, _, body = spec.partition(':')
        g = copy.deepcopy(base)
        for kv in [x for x in body.split(';') if x.strip()]:
            k, v = kv.split('=', 1)
            g.setdefault('rc', {})[k.strip()] = ast.literal_eval(v.strip())
        BP.GUNS[a.gun] = g
        sfx = '_x%d' % n
        dst = BP.bake(a.gun, '.', dict(BP.HOLD), 2.5, False, sfx)
        tiles = render(g, dst, frames, a.w, crop)
        print('%s: hands in the box %s' % (label, ' '.join('f%d %.1f %%' % (f, hp) for f, (_, hp) in zip(frames, tiles))))
        rows.append((label + '  ' + body.strip(), tiles))
        os.remove(dst)
        if os.path.isfile(dst[:-4] + '_phys.json'):
            os.remove(dst[:-4] + '_phys.json')
    BP.GUNS[a.gun] = base
    tw, th = rows[0][1][0][0].size
    S = Image.new('RGB', (tw * len(frames), (th + 14) * len(rows)), 'white')
    d = ImageDraw.Draw(S)
    for r, (label, tiles) in enumerate(rows):
        d.text((3, r * (th + 14) + 1), label[:int(tw * len(frames) / 6)], fill=(0, 0, 0))
        for c, (im, hp) in enumerate(tiles):
            S.paste(im, (c * tw, r * (th + 14) + 14))
            d.text((c * tw + 4, r * (th + 14) + 16), 'f%d hands %.1f%%' % (frames[c], hp), fill=(0, 0, 0))
    S.save(a.out, quality=88)
    print(a.out)


if __name__ == '__main__':
    main()
