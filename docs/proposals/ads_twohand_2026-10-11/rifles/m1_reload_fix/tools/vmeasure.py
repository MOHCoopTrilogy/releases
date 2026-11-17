"""OFFLINE per-frame figures of an aimed reload clip (rview's scene, no engine sway / aim solve):
  front / rear = screen height (fraction, 0 top, 1 bottom) of the front / rear sight points
  top   = highest gun pixel (fraction of the picture height; the centre box is 0.40-0.60)
  gunpx = gun pixels on screen (% of the picture) - how much of the rifle is IN VIEW
  low   = lowest-third share of the gun pixels that touch the bottom edge row (1 = the rifle runs off the bottom)
  box   = % of the centre box covered by anything (gun, hands, prop)

    cd rifles/assets; python ../m1_reload_fix/tools/vmeasure.py garand <clip.skc> [--frames 0:60:2] [--json out.json]
"""
import sys, os, json, argparse
import numpy as np
RT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')
sys.path.insert(0, RT)
import rview as RV
V, R, A = RV.V, RV.R, RV.A


def measure(gun, clip, frames, w=480):
    g = RV.VIEW[gun.replace('_up', '')]
    aim = R.load(A + g['aim'])
    sight = V.SIGHTS[g['sight']]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), RV.CTL), sight)
    W, H = w, w * 9 // 16
    fov = V.weapon_fov()
    c = R.load(clip)
    oh = (g['oh'][0] * c.frameTime, g['oh'][1] * c.frameTime)
    out = {}
    for f in frames or range(c.numFrames):
        f = min(f, c.numFrames - 1); t = f * c.frameTime
        V.PROP.clear()
        p = g.get('prop')
        if p:
            V.PROP.update(tik=p['tik'], tag=p['tag'], t0=p['f0'] * c.frameTime, t1=p['f1'] * c.frameTime)
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), g['sight'], sight['tik'], g['anim'], t, RV.CTL, corr, oh, lambda fr: True)
        keep = [s for s in surfs if not (g.get('vis', {}).get(s['name']) is not None and not any(a <= f <= b for a, b in g['vis'][s['name']]))]
        _, ids, _ = V.shade_render(keep, E, fov, W, H, tex=False)
        gi = [i for i, s in enumerate(keep) if s.get('gun')]
        m = ids >= 0
        gm = m & np.isin(ids // 1000000, gi)
        rows = np.where(gm.any(1))[0]
        bx = m[int(H * .4):int(H * .6), int(W * .4):int(W * .6)]
        tg = Wb['tag_weapon_left' if oh[0] <= t + 1e-6 <= oh[1] else 'tag_weapon_right']
        Ag = tg[0:3, 0:3]; Gp = tg[3, 0:3] * R.S
        fpx = (W / 2.0) / np.tan(np.radians(fov / 2.0))
        def sy(P):
            d = P - E
            return round(0.5 - fpx * d[2] / d[0] / H, 3)
        out_f = dict(fy=sy(Gp + np.array(sight['F']) @ Ag), ry=sy(Gp + np.array(sight['R']) @ Ag))
        out[f] = dict(**out_f, top=round(float(rows[0]) / H, 3) if len(rows) else None, gunpx=round(100.0 * gm.mean(), 2),
                      edge=round(100.0 * gm[-1].mean(), 1), box=round(100.0 * bx.mean(), 2))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('clip'); ap.add_argument('--frames'); ap.add_argument('--json')
    a = ap.parse_args()
    fr = RV.parse_frames(a.frames) if a.frames else None
    r = measure(a.gun, a.clip, fr)
    for f, v in r.items():
        print('f%-3d front %.3f rear %.3f  top %-6s gun %5.2f %%  bottom-row %5.1f %%  box %5.2f %%' % (f, v['fy'], v['ry'], v['top'], v['gunpx'], v['edge'], v['box']))
    if a.json:
        json.dump(r, open(a.json, 'w'), indent=0)
