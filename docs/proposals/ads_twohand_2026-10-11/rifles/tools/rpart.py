"""OFFLINE: WHICH PART is in the centre box, per frame (offbox.py's camera and box; cover beyond the settled aim split
by surface name), plus the on-screen sight movement of the gun (deg from the settled aim: the angle between the eye ->
front sight line now and at the aim, and the rear sight the same way).

    cd rifles/assets; python ../tools/rpart.py <sight gun> <aim.skc> "<clip.skc>|<gun anim>[|o0,o1]" [--min 0.5] [--sheet out.jpg --every 2 --w 320 --zoom]
--zoom: the sheet shows the middle 40 % of the picture enlarged (the box and its surround).
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


def grow(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return o


def measure(gun, aimp, spec, w=320, sheet=None, every=2, zoom=False, minp=0.5, quiet=False):
    from PIL import Image, ImageDraw
    aim = R.load(aimp)
    sight = V.SIGHTS[gun]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    W, H = w, w * 9 // 16
    fov = V.weapon_fov()
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)
    sp = spec.split('|')
    c = R.load(sp[0]); anim = sp[1] if len(sp) > 1 else 'idle'
    oh = None
    if len(sp) > 2 and sp[2]:
        o0, o1 = [float(x) for x in sp[2].split(',')]
        oh = (o0 * c.frameTime, o1 * c.frameTime)

    def frame(cl, f, an, o, tex=False):
        t = f * cl.frameTime
        surfs, E, Wb = V.scene2(R.pose_dict(cl, f), gun, sight['tik'], an, t, CTL, corr, o)
        rgb, ids, _ = V.shade_render(surfs, E, fov, W, H, tex=tex)
        # the gun's two sight points as drawn (same shift + rig correction as the surfaces), eye at the origin
        T_ = Wb['tag_weapon_left' if o and o[0] <= t + 1e-6 <= o[1] else 'tag_weapon_right']
        A = T_[0:3, 0:3]; G = T_[3, 0:3] * R.S
        E_raw = Wb['eyes bone'][3, 0:3] * R.S
        pts = np.array([G + np.array(sight['F']) @ A, G + np.array(sight['R']) @ A])
        pts = V.apply_corr(pts - (E_raw - corr['E']), corr) - corr['E']
        return rgb, ids, surfs, pts
    _, ids, s0, S0 = frame(aim, aim.numFrames - 1, 'idle', None)
    aimmask = grow((ids >= 0)[y0:y1, x0:x1], max(1, int(round(6 * W / 1280.0))))
    ang = lambda a, b: float(np.degrees(np.arccos(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))
    out, ims = [], []
    for f in range(c.numFrames):
        want = sheet and f % every == 0
        rgb, ids, surfs, Sp = frame(c, f, anim, oh, tex=bool(want))
        box = ids[y0:y1, x0:x1]
        ext = (box >= 0) & ~aimmask
        parts = {}
        for si in np.unique(box[ext] // 1000000):
            parts[surfs[int(si)]['name']] = round(100.0 * float(((box // 1000000 == si) & ext).mean()), 1)
        d = dict(f=f, extra=round(100.0 * float(ext.mean()), 1), parts=parts,
                 muzzle_deg=round(ang(Sp[0], S0[0]), 2), rear_deg=round(ang(Sp[1], S0[1]), 2),
                 line_deg=round(ang(Sp[0] - Sp[1], S0[0] - S0[1]), 2),
                 # signed: the front sight's elevation against the settled aim (deg, + = ABOVE the target)
                 f_up=round(float(np.degrees(np.arctan2(Sp[0][2], Sp[0][0]) - np.arctan2(S0[0][2], S0[0][0]))), 3))
        out.append(d)
        if want:
            im = Image.fromarray(rgb)
            dr = ImageDraw.Draw(im)
            dr.rectangle((x0, y0, x1, y1), outline=(255, 230, 0) if d['extra'] <= 2.0 else (255, 0, 0))
            if zoom:
                im = im.crop((int(W * 0.25), int(H * 0.25), int(W * 0.75), int(H * 0.75))).resize((W, H), Image.LANCZOS)
                dr = ImageDraw.Draw(im)
            dr.text((3, 2), 'f%d  %.1f%%' % (f, d['extra']), fill=(0, 0, 0))
            ims.append(im)
    if not quiet:
        for d in out:
            if d['extra'] >= minp:
                print('  f%-3d %5.1f %%  %s' % (d['f'], d['extra'], '  '.join('%s %.1f' % kv for kv in sorted(d['parts'].items(), key=lambda kv: -kv[1]))))
    mx = max(out, key=lambda d: d['extra'])
    # bolt cycles (user 2026-10-12): the rifle's OWN bolt handle / bolt body are exempt from the 2 % bar - hands count
    hands = max(sum(v for k, v in d['parts'].items() if 'hand' in k.lower()) for d in out)
    gunp = max(sum(v for k, v in d['parts'].items() if 'hand' not in k.lower()) for d in out)
    print('  in the box beyond the aim: HANDS max %.1f %% (the bar), the gun\'s own surfaces max %.1f %% (exempt on a bolt cycle)' % (hands, gunp))
    print('%s: %d frames, max extra %.1f %% at f%d, %d over 2 %%; front sight off the target max %.2f deg, rear sight max %.2f deg, sight LINE turned max %.2f deg (last frame %.2f)' % (
        os.path.basename(sp[0]), c.numFrames, mx['extra'], mx['f'], sum(1 for d in out if d['extra'] > 2.0),
        max(d.get('muzzle_deg', 0) for d in out), max(d.get('rear_deg', 0) for d in out), max(d['line_deg'] for d in out), out[-1].get('muzzle_deg', 0)))
    if sheet and ims:
        cols = min(8, len(ims))
        S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
        for i, im in enumerate(ims):
            S.paste(im, ((i % cols) * W, (i // cols) * H))
        S.save(sheet, quality=86)
        print(sheet)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('aim'); ap.add_argument('part')
    ap.add_argument('--w', type=int, default=320); ap.add_argument('--sheet'); ap.add_argument('--every', type=int, default=2)
    ap.add_argument('--zoom', action='store_true'); ap.add_argument('--min', type=float, default=0.5)
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--track', action='store_true', help='print the signed front-sight elevation per clip frame (deg, + = above the target)')
    a = ap.parse_args()
    o = measure(a.gun, a.aim, a.part, a.w, a.sheet, a.every, a.zoom, a.min, a.quiet)
    if a.track:
        print('front sight up (deg) per frame:', ' '.join('%d:%.2f' % (d['f'], d['f_up']) for d in o))
