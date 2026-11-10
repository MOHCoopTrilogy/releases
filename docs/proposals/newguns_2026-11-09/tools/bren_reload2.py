"""The Bren's reload hands, pass 2 (coordinator QA 2026-11-09: the VB's reload brings the right hand and forearm at the camera and
fills the right third of the screen). House rule (ADS reload = stay on target): keep the centre clear, the gun up, the work LOW,
never sweep across the view.

Model: per frame the VB clip's GUN (tag_weapon_left, the whole reload) gets a rigid world transform T(f) - a pitch about the
left hand's grip and a move, eased between keys - and BOTH hands ride with it: the left hand keeps its gun-relative pose, the
right hand keeps its gun-relative pose PLUS the magazine shift D (bren_hands.py: the Bren's well is ~5.7 u behind the VB's)
PLUS a gun-frame "keep low" offset L(f) for the trip to the pouch. Both arms are re-solved by two-bone IK; both tags keep their
local channels (gun on the left hand, magazine prop on the right). Frame count / time = the VB's (server timing unchanged).

Coverage (the pass condition): the frame rendered with the engine-calibrated rig (vmcam.scene2 + ctl_stand) at 21:9, hip
weapon fov (cg_fov 80 Hor+ = 112.6 deg); share of the screen covered by the right hand (triggerhand) and by sleeve pixels in
the right 45 % of the screen (the right forearm). Gate: hand + right sleeve <= 15 % on every frame.

    python bren_reload2.py report <clip> [...]        coverage per frame
    python bren_reload2.py bake <out dir>             write the 3 clips with the keys below + report
    python bren_reload2.py sheet <clip> <out.jpg> f,f,f
"""
import sys, os, math, json
T_ = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T_); _c = os.getcwd(); os.chdir(T_)
import vmcam as V  # noqa: E402
import key_bolt as KB  # noqa: E402
os.chdir(_c)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
R = V.R; S = R.S; B = KB.B
CTL = json.load(open(os.path.join(T_, '..', 'assets', 'ctl_stand.json')))
VM = 'models/human/animation/viewmodel/Vickers/'
TIK = 'models/weapons/coop_bren.tik'
PROP = 'models/weapons/coop_bren_clip.tik'
W, H = 344, 144
_gs = V.PR.gun_surfs


def _gun_surfs(Wb, tik, anim, t, vis, tag='tag_weapon_right'):
    # vmcam.scene2 draws the ammo prop at its clip time 0; the engine plays the prop's own idle clip with the reload
    if tik == PROP and 't' in V.PROP:
        t = V.PROP['t']
    return _gs(Wb, tik, anim, t, vis, tag)


V.PR.gun_surfs = _gun_surfs
FOV = 112.6
D = np.array([-5.65, 0.3, 1.2])          # gun frame (+x muzzle, +y right, +z down): the Bren magazine vs the VB's

# per clip: frames (ramp in / out of the magazine shift), and the gun keys: frame -> (pitch_down deg, yaw_right deg,
# fwd, left, up, roll about the bore deg) applied about the left hand grip in the model (= camera) frame; and the right hand's keep-low keys in the
# gun frame: frame -> (dx, dy, dz)
CLIPS = {
    'A_W_Vickers_reload_fps.skc': dict(out='coop_bren_reload_fps.skc', anim='reload', rin=(3, 12), rout=(54, 62)),
    'coop_A_W_Vickers_reload_fps_s.skc': dict(out='coop_bren_reload_fps_s.skc', anim='reload_s', rin=(3, 10), rout=(42, 49)),
    'coop_A_W_Vickers_reload_fps_m.skc': dict(out='coop_bren_reload_fps_m.skc', anim='reload_m', rin=(3, 10), rout=(54, 61)),
}
KEYS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bren_reload2_keys.json'))) \
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bren_reload2_keys.json')) else {}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(f, rin, rout):
    if f <= rin[0] or f >= rout[1]:
        return 0.0
    if f < rin[1]:
        return ease((f - rin[0]) / float(rin[1] - rin[0]))
    if f > rout[0]:
        return ease((rout[1] - f) / float(rout[1] - rout[0]))
    return 1.0


def interp(keys, f, n):
    """eased piecewise interpolation of key tuples {frame: tuple}; zero outside"""
    if not keys:
        return np.zeros(n)
    ks = sorted((int(k), np.asarray(v, float)) for k, v in keys.items())
    if f <= ks[0][0]:
        return ks[0][1] * 0
    if f >= ks[-1][0]:
        return ks[-1][1] * 0
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * ease((f - f0) / float(f1 - f0))
    return ks[0][1] * 0


def rot_rows(axis, deg):
    return R.axis_angle_rows(axis, deg)


def solve_arm(pd, Wc, side, HT):
    Wb = R.evaluate(pd)
    U, Fo, Hd, Cl = ('Bip01 %s UpperArm' % side, 'Bip01 %s Forearm' % side, 'Bip01 %s Hand' % side, 'Bip01 %s Clavicle' % side)
    Sp, Ep, Wp = Wc[U][3, 0:3], Wc[Fo][3, 0:3], Wc[Hd][3, 0:3]
    Wt = HT[3, 0:3]
    la, lb = np.linalg.norm(Ep - Sp), np.linalg.norm(Wp - Ep)
    dvec = Wt - Sp; dist = np.linalg.norm(dvec)
    clamp = dist > la + lb - 1e-3
    if clamp:
        Wt = Sp + dvec / dist * (la + lb - 1e-3); dist = la + lb - 1e-3
    dh = dvec / np.linalg.norm(dvec)
    pole = (Ep - Sp) - ((Ep - Sp) @ dh) * dh; pole /= np.linalg.norm(pole)
    x = (la * la - lb * lb + dist * dist) / (2 * dist); h = math.sqrt(max(0.0, la * la - x * x))
    En = Sp + dh * x + pole * h
    Uw = B.align(Wc[U][0:3, 0:3], Ep - Sp, En - Sp)
    Fw = B.align(Wc[Fo][0:3, 0:3], Wp - Ep, Wt - En)
    par = Wb[Cl][0:3, 0:3]
    pd[U + ' rot'] = R.rows_to_quat(Uw @ par.T)
    pd[Fo + ' rot'] = R.rows_to_quat(Fw @ Uw.T)
    pd[Hd + ' rot'] = R.rows_to_quat(HT[0:3, 0:3] @ Fw.T)
    return clamp


def world_T(Wc, g):
    """4x4 row-vector rigid transform: pitch_down / yaw_right about the left hand, then a move (scaled units -> raw)"""
    pdn, yr, fw, lf, up, roll = g
    piv = Wc['Bip01 L Hand'][3, 0:3]
    bore = Wc['tag_weapon_left'][0, 0:3]; bore = bore / np.linalg.norm(bore)
    Rm = rot_rows(bore, roll) @ rot_rows([0, 1.0, 0], pdn) @ rot_rows([0, 0, 1.0], -yr)
    T = np.eye(4)
    T[0:3, 0:3] = Rm
    T[3, 0:3] = piv - piv @ Rm + np.array([fw, lf, up]) / S
    return T


def bake(src, cfg, keys):
    hip = R.load(VM + src)
    out = R.load(VM + src)
    cm = R.chanmap(out)
    clamps = []
    gk = keys.get('gun', {}); lk = keys.get('low', {}); wk = keys.get('loww', {})
    for f in range(hip.numFrames):
        w = ramp(f, cfg['rin'], cfg['rout'])
        g = interp(gk, f, 6); lo = interp(lk, f, 3)
        lw = interp(wk, f, 3)
        if w <= 0 and not np.any(g) and not np.any(lo) and not np.any(lw):
            continue
        pd = R.pose_dict(hip, f)
        Wc = R.evaluate(pd)
        G = Wc['tag_weapon_left']
        T = world_T(Wc, g)
        HR = Wc['Bip01 R Hand'].copy()
        HR[3, 0:3] = HR[3, 0:3] + ((w * D) + lo) @ G[0:3, 0:3] / S
        HL = Wc['Bip01 L Hand']
        HRT = HR @ T
        HRT[3, 0:3] = HRT[3, 0:3] + lw / S          # [QA 2] world (camera) frame: fwd, left, up - the reach starts LOW
        if np.any(g):
            if solve_arm(pd, Wc, 'L', HL @ T):
                clamps.append(('L', f))
        if solve_arm(pd, Wc, 'R', HRT):
            clamps.append(('R', f))
        KB.write_frame(out, hip, cm, f, pd)
    assert np.array_equal(out.V[0], hip.V[0]) and np.array_equal(out.V[-1], hip.V[-1])
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(out.numFrames)]
    return out, clamps


def render(clip, anim, f, w=W, h=H, tex=False):
    t = f * clip.frameTime
    V.PROP.update(tik=PROP, anim='idle', tag='tag_weapon_right', t0=19 * clip.frameTime, t1=51 * clip.frameTime, hide='brenclip', t=t)
    surfs, E, Wb = V.scene2(R.pose_dict(clip, f), 'vickers_berthier', TIK, anim, t, CTL, None, (0.0, clip.numFrames * clip.frameTime), None)
    surfs = [s for s in surfs if np.abs(s['P']).max() < 1e3]
    rgb, ids, dep = V.shade_render(surfs, E, FOV, w, h, tex=tex)
    return rgb, ids, surfs


COV_CENTRE = [0.0]


def coverage(clip, anim, f):
    rgb, ids, surfs = render(clip, anim, f)
    names = [s['name'] for s in surfs]
    sid = ids // 1000000
    m = ids >= 0
    hand = np.zeros(ids.shape, bool); slv = np.zeros(ids.shape, bool)
    for i, n in enumerate(names):
        if n == 'triggerhand':
            hand |= m & (sid == i)
        if n == 'viewsleeves':
            slv |= m & (sid == i)
    slv[:, :int(W * 0.55)] = False
    cen = m[int(H * 0.35):int(H * 0.65), int(W * 0.4):int(W * 0.6)].mean()
    COV_CENTRE[0] = max(COV_CENTRE[0], cen)
    return hand.mean(), slv.mean()


def report(clip, anim, step=2):
    rows = []
    for f in range(0, clip.numFrames, step):
        a, b = coverage(clip, anim, f)
        rows.append((f, a, b))
    worst = max(rows, key=lambda r: r[1] + r[2])
    return rows, worst


def sheet(clip, anim, frames, out, w=860, h=360):
    ims = []
    for f in frames:
        rgb, ids, _ = render(clip, anim, f, w, h, tex=True)
        im = Image.fromarray(rgb); a, b = coverage(clip, anim, f)
        ImageDraw.Draw(im).text((6, 6), 'f%d hand %.1f%% rsleeve %.1f%%' % (f, 100 * a, 100 * b), fill=(255, 255, 0))
        ims.append(im)
    cols = 4
    Sx = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims):
        Sx.paste(im, ((i % cols) * w, (i // cols) * h))
    Sx.save(out, quality=82)


def main():
    cmd = sys.argv[1]
    if cmd == 'report':
        for p in sys.argv[2:]:
            c = R.load(p)
            anim = 'reload_s' if p.endswith('_s.skc') else 'reload_m' if p.endswith('_m.skc') else 'reload'
            rows, worst = report(c, anim)
            print(os.path.basename(p), 'worst f%d hand %.1f%% rsleeve %.1f%%' % (worst[0], 100 * worst[1], 100 * worst[2]))
            print('  ' + ' '.join('%d:%.0f/%.0f' % (f, 100 * a, 100 * b) for f, a, b in rows))
    elif cmd == 'bake':
        od = sys.argv[2]
        os.makedirs(od, exist_ok=True)
        for src, cfg in CLIPS.items():
            out, clamps = bake(src, cfg, KEYS.get(cfg['out'], KEYS.get('*', {})))
            data = R.skc_io.write(out)
            p = os.path.join(od, cfg['out'])
            open(p, 'wb').write(data)
            c = R.load(p)
            rows, worst = report(c, cfg['anim'])
            print(cfg['out'], 'clamps', clamps[:6], len(clamps), '| worst f%d hand %.1f%% rsleeve %.1f%%' % (worst[0], 100 * worst[1], 100 * worst[2]))
            print('  ' + ' '.join('%d:%.0f/%.0f' % (f, 100 * a, 100 * b) for f, a, b in rows))
    elif cmd == 'sheet':
        p = sys.argv[2]
        c = R.load(p)
        anim = 'reload_s' if p.endswith('_s.skc') else 'reload_m' if p.endswith('_m.skc') else 'reload'
        sheet(c, anim, [int(x) for x in sys.argv[4].split(',')], sys.argv[3])


if __name__ == '__main__':
    main()
