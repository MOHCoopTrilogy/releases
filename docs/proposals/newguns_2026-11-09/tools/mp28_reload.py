"""MP 28 hip reloads of its own (coordinator QA 2026-11-09: on the Sten's hip reload the gun swings up steeply toward the eye and the
hand looks clamped on the receiver). The Sten's hip reload clips with the GUN re-posed by a rigid transform about the right (grip)
hand - pitched down / yawed / rolled, eased in and out - and BOTH hands riding with it (each keeps its gun-relative pose; the left
hand with the magazine stays on the magazine). Arms re-solved by two-bone IK; tags keep their local channels; frame count / time
are the Sten's (server timing unchanged). Rows: coopr_mp28_reload[_empty], cv_mp28_reload[_empty]_s / _m.
    python mp28_reload.py sheet <clip> <out.jpg> f,f,f [pitch yaw roll fw lf up]
    python mp28_reload.py bake <out dir> pitch yaw roll fw lf up
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bren_reload2 as B2  # noqa: E402  (IK, ease, render plumbing)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
R, V, S, KB = B2.R, B2.V, B2.S, B2.KB
TIK = 'models/weapons/coop_bergmann.tik'
VM = 'models/human/animation/viewmodel/sten/'
CLIPS = {'coop_sten_reload_hip.skc': 'coop_mp28_reload_hip.skc', 'coop_sten_reload_empty_hip.skc': 'coop_mp28_reload_empty_hip.skc',
         'coop_sten_reload_hip_s.skc': 'coop_mp28_reload_hip_s.skc', 'coop_sten_reload_hip_m.skc': 'coop_mp28_reload_hip_m.skc',
         'coop_sten_reload_empty_hip_s.skc': 'coop_mp28_reload_empty_hip_s.skc', 'coop_sten_reload_empty_hip_m.skc': 'coop_mp28_reload_empty_hip_m.skc'}
EASE_F = 12         # frames to ease the re-pose in at the start and out at the end


def world_T(Wc, g):
    pdn, yr, roll, fw, lf, up = g
    piv = Wc['Bip01 R Hand'][3, 0:3]
    bore = Wc['tag_weapon_right'][0, 0:3]; bore = bore / np.linalg.norm(bore)
    Rm = R.axis_angle_rows(bore, roll) @ R.axis_angle_rows([0, 1.0, 0], pdn) @ R.axis_angle_rows([0, 0, 1.0], -yr)
    T = np.eye(4); T[0:3, 0:3] = Rm
    T[3, 0:3] = piv - piv @ Rm + np.array([fw, lf, up]) / S
    return T


def steady_T(G, Gref, k):
    """row-vector T with G @ T = the gun moved fraction k of the way from G to Gref (rotation slerped, position lerped)"""
    from scipy.spatial.transform import Rotation as Ro, Slerp
    r = Slerp([0, 1], Ro.from_matrix(np.stack([G[0:3, 0:3].T, Gref[0:3, 0:3].T])))([k]).as_matrix()[0].T
    Gn = np.eye(4); Gn[0:3, 0:3] = r; Gn[3, 0:3] = G[3, 0:3] + k * (Gref[3, 0:3] - G[3, 0:3])
    return np.linalg.inv(G) @ Gn


def bake(src, g):
    hip = R.load(VM + src); out = R.load(VM + src); cm = R.chanmap(out)
    n = hip.numFrames; clamps = []
    steady = g[0] if len(g) in (2, 8) else None          # [k, ref fraction]: hold the gun near the reference frame's pose
    if steady is not None:
        Gref = R.evaluate(R.pose_dict(hip, int(round(g[1] * (n - 1)))))['tag_weapon_right']
    for f in range(n):
        w = B2.ease(min(f, n - 1 - f) / float(EASE_F))
        if w <= 0:
            continue
        pd = R.pose_dict(hip, f); Wc = R.evaluate(pd)
        if steady is not None:
            T = steady_T(Wc['tag_weapon_right'], Gref, steady * w)
            if len(g) == 8:
                Wm = {k: (v @ T if k in ('Bip01 R Hand', 'tag_weapon_right') else v) for k, v in Wc.items()}
                T = T @ world_T(Wm, np.asarray(g[2:], float) * w)
        else:
            T = world_T(Wc, np.asarray(g, float) * w)
        for side in ('R', 'L'):
            if B2.solve_arm(pd, Wc, side, Wc['Bip01 %s Hand' % side] @ T):
                clamps.append((side, f))
        KB.write_frame(out, hip, cm, f, pd)
    assert np.array_equal(out.V[0], hip.V[0]) and np.array_equal(out.V[-1], hip.V[-1])
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(out.numFrames)]
    return out, clamps


def render(clip, f, w, h, tex=True):
    surfs, E, Wb = V.scene2(R.pose_dict(clip, f), 'sten_mark_ii', TIK, 'reload', f * clip.frameTime, B2.CTL, None, None, None)
    surfs = [s for s in surfs if np.abs(s['P']).max() < 1e3]
    rgb, ids, dep = V.shade_render(surfs, E, B2.FOV, w, h, tex=tex)
    m = ids >= 0
    return rgb, m.mean(), m[int(h * .35):int(h * .65), int(w * .4):int(w * .6)].mean()


def sheet(clip, frames, out, w=688, h=288):
    S_ = Image.new('RGB', (w * 4, h * ((len(frames) + 3) // 4)))
    for i, f in enumerate(frames):
        rgb, a, c = render(clip, f, w, h)
        im = Image.fromarray(rgb); ImageDraw.Draw(im).text((6, 6), 'f%d all %.0f%% centre %.0f%%' % (f, 100 * a, 100 * c), fill=(255, 255, 0))
        S_.paste(im, ((i % 4) * w, (i // 4) * h))
    S_.save(out, quality=80)


def main():
    cmd = sys.argv[1]
    if cmd == 'sheet':
        c = R.load(sys.argv[2])
        if len(sys.argv) > 5:
            o, cl = bake(os.path.basename(sys.argv[2]), [float(x) for x in sys.argv[5:]])
            tmp = r'H:\hzm_work\newguns\brenhands\sw\mp28r.skc'
            open(tmp, 'wb').write(R.skc_io.write(o)); c = R.load(tmp)
            print('clamps', len(cl), sorted(set(f for _, f in cl))[:20])
        print('frames', c.numFrames)
        sheet(c, [int(x) for x in sys.argv[4].split(',')], sys.argv[3])
    elif cmd == 'bake':
        od = sys.argv[2]; g = [float(x) for x in sys.argv[3:]]
        os.makedirs(od, exist_ok=True)
        for src, dst in CLIPS.items():
            o, cl = bake(src, g)
            open(os.path.join(od, dst), 'wb').write(R.skc_io.write(o))
            print(dst, o.numFrames, 'frames, clamps', len(cl), sorted(set(f for _, f in cl))[:12])


if __name__ == '__main__':
    main()
