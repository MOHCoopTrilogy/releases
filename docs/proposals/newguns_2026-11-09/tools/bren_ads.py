"""The Bren's OWN aim pose `coopr_bren_charge` (newguns2 2026-11-09, BREN_SIGHTS.md part B).

The Vickers-Berthier's aim row `vickers_charge` = bar_stand00.skc holds the gun so the Bren's rear aperture sits 3.4 u BEHIND
the eye; the rig's eye-relief move is clamped to +-4 u, so the eye ended ~0.6 u behind the aperture (a "pipe" view) and the
rig's residual swung the near ring by hundreds of pixels. Here the rig's whole correction for the rebuilt sight row
(bren_sights.py: F = blade tip, R = aperture centre, relief 3) is BAKED into the pose - rotation about the eye, the move onto
the line, the cant and the full relief move - so the sight line already runs through the eye, the aperture 3 u in front of it,
and the engine's rig target is ~zero (nothing to clamp, nothing to swing). The hands ride with the gun (both arms re-solved
by two-bone IK); the left hand is then moved along the gun to the butt (gun-frame offset LEFT_D, elbow down) as on the real
gun, out of the aim picture.

Picture (engine-calibrated: vmcam.scene2 + ctl_stand, ADS weapon fov 95.8 at 3440x1440): F / R pixels, the aperture ring's
outer height as a share of the screen height, hand / sleeve cover of the centre box.
    python bren_ads.py probe <clip> [...]              the rig target the engine would compute on the clip's last frame
    python bren_ads.py bake <src clip> <out.skc>       write the aim pose (src = viewmodel/bar_stand00.skc)
    python bren_ads.py sheet <clip> <out.jpg> [tik]    the ADS picture + numbers
Overlay paks: IRONSIGHT_EXTRA_PAKS=<mkov.py pk3> (the staged coop_bren mesh).
"""
import sys, os, math, json
T_ = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T_); _c = os.getcwd(); os.chdir(T_)
import vmcam as V  # noqa: E402
import key_bolt as KB  # noqa: E402
os.chdir(_c)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brenlib as L  # noqa: E402
import bren_sights as BS  # noqa: E402
R = V.R; S = R.S
CTL = json.load(open(os.path.join(T_, '..', 'assets', 'ctl_stand.json')))
TIK = 'models/weapons/coop_bren.tik'
ROW = BS.row()
V.SIGHTS['bren'] = dict(V.SIGHTS['vickers_berthier'], tik=TIK, name='Bren', **ROW)
W, H, FOV = 3440, 1440, 95.8
LEFT_D = np.array([float(v) for v in os.environ.get('BREN_LEFT_D', '0,0,0').split(',')])   # gun frame (+x muzzle, +y right, +z down)
LEFT_POLE = float(os.environ.get('BREN_LEFT_POLE', '0'))


def target(Wb, clamp=True):
    """CG_AdsRigSolve's target (vmcam.rig_target), with the relief move unclamped when clamp=False"""
    c = V.rig_target(Wb, dict(V.SIGHTS['bren'], relief=0.0))
    R2 = V.rotv(c['R'] - c['E'], c['ax'], c['ang']) + c['T']
    rel = ROW['relief'] - R2[0]
    c['relief'] = max(-4.0, min(4.0, rel)) if clamp else rel
    c['R2'] = R2[0]
    return c


def corr_raw(c):
    """the correction as a 4x4 row-vector transform on RAW (unscaled) world positions"""
    O = V.apply_corr(np.zeros((1, 3)), c)[0]
    M = np.eye(4)
    for i in range(3):
        e = np.zeros((1, 3)); e[0, i] = S
        M[i, 0:3] = (V.apply_corr(e, c)[0] - O) / S
    M[3, 0:3] = O / S
    return M


def bake(src, out_p):
    hip = R.load(src); out = R.load(src); cm = R.chanmap(out)
    for f in range(hip.numFrames):
        pd = R.pose_dict(hip, f)
        Wn = R.evaluate(pd)
        Wc = V.evaluate_ctl(pd, CTL)
        K = R.inv(Wn['Bip01 Spine1']) @ Wc['Bip01 Spine1']
        assert np.abs(Wn['eyes bone'] @ K - Wc['eyes bone']).max() < 1e-3
        c = target(Wc, clamp=False)
        Mn = K @ corr_raw(c) @ R.inv(K)
        G = Wn['tag_weapon_right'] @ Mn
        HR = Wn['Bip01 R Hand'] @ Mn
        HL = Wn['Bip01 L Hand'] @ Mn
        A = G[0:3, 0:3]
        HL[3, 0:3] = HL[3, 0:3] + (LEFT_D @ A) / S      # A maps gun-frame game units to scaled world (as vmcam.rig_target)
        KB.solve_arms(pd, Wn, HR, HL, G, pole_bias={'L': [0, 0, -LEFT_POLE]} if LEFT_POLE else None)
        KB.write_frame(out, hip, cm, f, pd)
        print('f%d baked: rot %.2f deg, move %s, cant %.3f rad, relief %.2f u (R was %.2f u ahead of the eye)' % (
            f, c['ang'], np.round(c['T'], 2), c['cant'], c['relief'], c['R2']))
    out.values = [[[float(np.float32(x)) for x in out.V[f, cc]] for cc in range(out.numChannels)] for f in range(out.numFrames)]
    open(out_p, 'wb').write(R.skc_io.write(out))


# ---- the AIMED reload (`coopr_bren_reload_ads`, `cv_bren_reload_s_ads`, `cv_bren_reload_m_ads`): the hip reload clips
# (bren_reload2.py: gun re-posed low, magazine work low and right) with the GUN LOCKED in the aim pose instead - the rig's
# held target is ~zero now, so a hip clip would drop the gun to the hip. Per frame: the gun = the aim pose's gun (moved with
# THIS frame's eye) plus a small keyed reaction (roll about the view axis, a drop, a pitch about the eye); both hands keep
# their gun-relative pose from the hip clip (the magazine prop rides the right hand: tag locals untouched), arms re-solved
# by IK. Keys per clip: frame -> (roll deg, drop u, pitch deg); eased, 0 outside.
def _rkeys(n, pin, ins, cock, pout, roll=70.0, kroll=73.0, pitch=6.0):
    """roll in by `pin`, a pitch about the eye (muzzle dips) around the insert frame `ins`, hold the roll through the cocking
    stroke to `cock`, back to the aim pose by `pout`"""
    return {0: (0, 0, 0), pin: (roll, 0, 0), ins - 11: (roll, 0, 0), ins - 5: (roll, 0, pitch * 0.7), ins: (kroll, 0, pitch),
            ins + 7: (roll, 0, pitch * 0.6), ins + 13: (roll, 0, 0), cock: (roll, 0, 0), pout: (0, 0, 0), n - 1: (0, 0, 0)}


# roll about the VIEW AXIS keeps the aperture (a circle) and the post on the target; 70 deg turns the top magazine and the hand
# working it out to the right, the short pitch around the insert keeps the seating hand under the centre (sweep: arms in the
# centre box <= 3.1 %, no IK clamp on the main clip; 35 deg = the hip reload's roll left the seating fist over the centre, 13.9 %)
RELOAD_ADS = {
    'coop_bren_reload_fps.skc': dict(out='coop_bren_reload_fps_ads.skc', keys=_rkeys(94, 7, 51, 84, 93)),
    'coop_bren_reload_fps_s.skc': dict(out='coop_bren_reload_fps_s_ads.skc', keys=_rkeys(76, 6, 41, 68, 75)),
    'coop_bren_reload_fps_m.skc': dict(out='coop_bren_reload_fps_m_ads.skc', keys=_rkeys(88, 7, 51, 79, 87)),
}


def _ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _key(keys, f):
    ks = sorted(keys.items())
    if f <= ks[0][0]:
        return np.array(ks[0][1], float)
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1:
            return np.array(v0, float) + (np.array(v1, float) - np.array(v0, float)) * _ease((f - f0) / float(f1 - f0))
    return np.array(ks[-1][1], float)


def _rigid(axis, deg, pivot):
    """4x4 row-vector rotation about an axis through pivot (raw units)"""
    M = np.eye(4)
    M[0:3, 0:3] = R.axis_angle_rows(axis, deg)
    M[3, 0:3] = pivot - pivot @ M[0:3, 0:3]
    return M


def bake_reload(aim_p, src_p, out_p, keys):
    import bren_reload2 as BR
    aim = R.load(aim_p)
    pa = R.pose_dict(aim, aim.numFrames - 1)
    Wa = V.evaluate_ctl(pa, CTL)
    Ga, Ea = Wa['tag_weapon_right'], Wa['eyes bone'][3, 0:3]
    hip = R.load(src_p); out = R.load(src_p); cm = R.chanmap(out)
    for f in range(hip.numFrames):
        pd = R.pose_dict(hip, f)
        Wn = R.evaluate(pd); Wc = V.evaluate_ctl(pd, CTL)
        K = R.inv(Wn['Bip01 Spine1']) @ Wc['Bip01 Spine1']
        Ef = Wc['eyes bone'][3, 0:3]
        roll, drop, pitch = _key(keys, f)
        G2 = Ga.copy(); G2[3, 0:3] = Ga[3, 0:3] + (Ef - Ea)
        D = _rigid([1.0, 0, 0], roll, Ef) @ _rigid([0, 1.0, 0], pitch, Ef)
        G2 = G2 @ D
        G2[3, 2] -= drop / S
        Gf = Wc['tag_weapon_left']
        Mg = R.inv(Gf) @ G2                      # the gun's move this frame (ctl frame)
        HR = Wc['Bip01 R Hand'] @ Mg
        HL = Wc['Bip01 L Hand'] @ Mg
        Ki = R.inv(K)
        cl = []
        for side, HT in (('L', HL @ Ki), ('R', HR @ Ki)):
            if BR.solve_arm(pd, Wn, side, HT):
                cl.append(side)
        if cl:
            print('  f%d IK clamp %s' % (f, cl))
        KB.write_frame(out, hip, cm, f, pd)
    out.values = [[[float(np.float32(x)) for x in out.V[f, cc]] for cc in range(out.numChannels)] for f in range(out.numFrames)]
    open(out_p, 'wb').write(R.skc_io.write(out))
    print('wrote', out_p, hip.numFrames, 'frames')


def gun_world(Wb, P):
    T = Wb['tag_weapon_right']
    return T[3, 0:3] * S + np.asarray(P, float) @ T[0:3, 0:3]


def measure(clip, f=None, corr=None):
    f = clip.numFrames - 1 if f is None else f
    Wb = V.evaluate_ctl(R.pose_dict(clip, f), CTL)
    c = corr or target(Wb)
    pts = {'F': ROW['F'], 'R': ROW['R']}
    out = {}
    for k, p in pts.items():
        Pw = V.apply_corr(gun_world(Wb, [p]) - (Wb['eyes bone'][3, 0:3] * S - c['E']), c)
        x, y, z = V.project(Pw, c['E'], FOV, W, H)
        out[k] = (float(x[0] - W / 2), float(y[0] - H / 2), float(z[0]))
    th = np.linspace(0, 2 * math.pi, 73)
    ring = np.stack([np.full_like(th, BS.X_LEAF), BS.Y_L + BS.LEAF_R * np.cos(th), BS.Z_L + BS.LEAF_R * np.sin(th)], 1)
    Pw = V.apply_corr(gun_world(Wb, ring) - (Wb['eyes bone'][3, 0:3] * S - c['E']), c)
    x, y, z = V.project(Pw, c['E'], FOV, W, H)
    out['ring_h'] = float((y.max() - y.min()) / H)
    out['ring_c'] = (float(x.mean() - W / 2), float(y.mean() - H / 2))
    out['corr'] = c
    return out


def render(clip, f, w, h, tex=True, corr=None):
    Wb = V.evaluate_ctl(R.pose_dict(clip, f), CTL)
    c = corr or target(Wb)
    surfs, E, _ = V.scene2(R.pose_dict(clip, f), 'bren', TIK, 'idle', 0.0, CTL, c, None, None)
    surfs = [s for s in surfs if np.abs(s['P']).max() < 1e3]
    rgb, ids, dep = V.shade_render(surfs, E, FOV, w, h, tex=tex, znear=0.6)
    return rgb, ids, surfs


PROP_T = {94: (19, 51), 76: (16, 41), 88: (19, 51)}   # bren_reload2 / anims_vickers: the prop is out between these frames (main clip measured)


def render_reload(clip, f, aim, w, h, tex=True):
    import bren_reload2  # noqa: F401  (installs its prop-time hook on vmcam.PR.gun_surfs)
    Wa = V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL)
    c = target(Wa)
    t = f * clip.frameTime
    p0, p1 = PROP_T.get(clip.numFrames, (19, 51))
    V.PROP.update(tik='models/weapons/coop_bren_clip.tik', anim='idle', tag='tag_weapon_right', t0=p0 * clip.frameTime,
                  t1=p1 * clip.frameTime, hide='brenclip', t=t)
    pd = R.pose_dict(clip, f)
    Wb = V.evaluate_ctl(pd, CTL)
    c = dict(c, E=Wb['eyes bone'][3, 0:3] * S)     # the engine pins THIS pose's eye to the camera
    surfs, E, _ = V.scene2(pd, 'bren', TIK, 'idle', t, CTL, c, (0.0, clip.numFrames * clip.frameTime), None)
    V.PROP.clear()
    surfs = [s for s in surfs if np.abs(s['P']).max() < 1e3]
    rgb, ids, dep = V.shade_render(surfs, E, FOV, w, h, tex=tex, znear=0.6)
    return rgb, ids, surfs


def reload_sheet(clip, aim, frames, out_p, w=688, h=288):
    ims = []
    worst = 0.0
    for f in frames:
        rgb, ids, surfs = render_reload(clip, f, aim, w, h)
        a, b, g = cover(ids, surfs)
        worst = max(worst, a)
        im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
        d.line([(w // 2 - 5, h // 2), (w // 2 + 5, h // 2)], fill=(255, 0, 0)); d.line([(w // 2, h // 2 - 5), (w // 2, h // 2 + 5)], fill=(255, 0, 0))
        d.text((5, 5), 'f%d arms in centre box %.1f%%, screen %.1f%%' % (f, 100 * a, 100 * b), fill=(255, 255, 0))
        ims.append(im)
    cols = 4
    Sx = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims):
        Sx.paste(im, ((i % cols) * w, (i // cols) * h))
    Sx.save(out_p, quality=85)
    print(out_p, 'worst centre-box arm cover %.1f%%' % (100 * worst))


def cover(ids, surfs):
    """share of the centre box (40-60 % x, 35-65 % y) covered by hands / sleeves; share of the whole screen by the gun"""
    h, w = ids.shape
    sid = ids // 1000000; m = ids >= 0
    arm = np.zeros(ids.shape, bool); gun = np.zeros(ids.shape, bool)
    for i, s in enumerate(surfs):
        (gun if s.get('gun') else arm)[m & (sid == i)] = True
    box = (slice(int(h * 0.35), int(h * 0.65)), slice(int(w * 0.4), int(w * 0.6)))
    return arm[box].mean(), arm.mean(), gun.mean()


def sheet(clip, out_p, frames=None, w=1032, h=432):
    frames = frames or [clip.numFrames - 1]
    ims = []
    for f in frames:
        rgb, ids, surfs = render(clip, f, w, h)
        m = measure(clip, f)
        a, b, g = cover(ids, surfs)
        im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
        d.line([(w // 2 - 6, h // 2), (w // 2 + 6, h // 2)], fill=(255, 0, 0)); d.line([(w // 2, h // 2 - 6), (w // 2, h // 2 + 6)], fill=(255, 0, 0))
        d.text((6, 6), 'f%d F(%.0f,%.0f) R(%.0f,%.0f)px@3440  ring %.0f%% H  arms centre %.1f%% all %.1f%%  gun %.1f%%  relief move %.2f' % (
            f, m['F'][0], m['F'][1], m['R'][0], m['R'][1], 100 * m['ring_h'], 100 * a, 100 * b, 100 * g, m['corr']['relief']), fill=(255, 255, 0))
        ims.append(im)
    Sx = Image.new('RGB', (w, h * len(ims)))
    for i, im in enumerate(ims):
        Sx.paste(im, (0, i * h))
    Sx.save(out_p, quality=88)
    print(out_p)


def main():
    cmd = sys.argv[1]
    if cmd == 'probe':
        for p in sys.argv[2:]:
            c = R.load(p)
            m = measure(c)
            k = m['corr']
            print('%s: rot %.2f deg move %s cant %.3f relief move %.2f (R %.2f u ahead before it) | F %s R %s px ring %.0f%% H' % (
                os.path.basename(p), k['ang'], np.round(k['T'], 2), k['cant'], k['relief'], k['R2'],
                np.round(m['F'][:2], 1), np.round(m['R'][:2], 1), 100 * m['ring_h']))
    elif cmd == 'bake':
        bake(sys.argv[2], sys.argv[3])
    elif cmd == 'sheet':
        sheet(R.load(sys.argv[2]), sys.argv[3])
    elif cmd == 'row':        # row <engine tree>: rewrite every coop_bren* row of cg_adssights.h from the model (bren_sights.row())
        import re
        hp = os.path.join(sys.argv[2], 'code', 'cgame', 'cg_adssights.h')
        b = open(hp, 'rb').read().decode('latin-1')
        F, Rr = ROW['F'], ROW['R']
        f3 = lambda v: '{%.4ff, %.4ff, %.4ff}' % tuple(v)
        note = ('// coop_bren [newguns2 2026-11-09] generated by bren_ads.py row from bren_sights.py: F = the rebuilt blade tip, R = the '
                'rebuilt aperture centre, both on the left offset line; relief %g (the coopr_bren_charge pose already puts R %g u ahead of the eye)'
                % (ROW['relief'], ROW['relief']))
        pat = re.compile(r'(\{"models/weapons/coop_bren(?:_[a-z_]+)?\.tik", "Bren[^"]*", )\{[^}]*\}, \{[^}]*\}, ([0-9.]+f), (\{[^}]*\}), [0-9.]+f\}, //[^\r\n]*')
        b2, n = pat.subn(lambda m: m.group(1) + f3(F) + ', ' + f3(Rr) + ', ' + m.group(2) + ', ' + m.group(3) + ', %.3ff}, ' % ROW['relief'] + note, b)
        assert n == 8, n
        open(hp, 'wb').write(b2.encode('latin-1'))
        print('rewrote %d rows' % n)
    elif cmd == 'clip':       # clip <aim clip> <aimed reload clip> [...]: vertices in the view frustum nearer than the weapon near plane
        aim = R.load(sys.argv[2])
        th_y = math.tan(math.radians(FOV / 2)); th_z = th_y * H / W
        for p in sys.argv[2:]:
            c = R.load(p)
            worst, cut06, cut1 = 1e9, 0, 0
            for f in range(c.numFrames):
                if p == sys.argv[2]:
                    Wb = V.evaluate_ctl(R.pose_dict(c, f), CTL)
                    surfs, E, _ = V.scene2(R.pose_dict(c, f), 'bren', TIK, 'idle', 0.0, CTL, target(Wb), None, None)
                else:
                    import bren_reload2  # noqa: F401
                    t = f * c.frameTime
                    p0, p1 = PROP_T.get(c.numFrames, (19, 51))
                    V.PROP.update(tik='models/weapons/coop_bren_clip.tik', anim='idle', tag='tag_weapon_right', t0=p0 * c.frameTime,
                                  t1=p1 * c.frameTime, hide='brenclip', t=t)
                    Wa = V.evaluate_ctl(R.pose_dict(aim, 0), CTL); pd = R.pose_dict(c, f); Wb = V.evaluate_ctl(pd, CTL)
                    cc = dict(target(Wa), E=Wb['eyes bone'][3, 0:3] * S)
                    surfs, E, _ = V.scene2(pd, 'bren', TIK, 'idle', t, CTL, cc, (0.0, c.numFrames * c.frameTime), None)
                    V.PROP.clear()
                for sf in surfs:
                    q = sf['P'] - E
                    q = q[np.abs(q).max(1) < 5000]
                    fw = q[:, 0]
                    inf = (fw > 0.01) & (np.abs(q[:, 1]) < fw * th_y) & (np.abs(q[:, 2]) < fw * th_z)
                    if inf.any():
                        worst = min(worst, float(fw[inf].min()))
                    cut06 += int((inf & (fw < 0.6)).sum()); cut1 += int((inf & (fw < 1.0)).sum())
            print('%-34s frames %3d  in view nearer than 0.6 u (r_weaponznear): %d, than 1 u: %d, nearest %.2f u' % (
                os.path.basename(p), c.numFrames, cut06, cut1, worst))
    elif cmd == 'rsheet':     # rsheet <reload clip> <aim clip> <out.jpg> f,f,f
        reload_sheet(R.load(sys.argv[2]), R.load(sys.argv[3]), [int(x) for x in sys.argv[5].split(',')], sys.argv[4])
    elif cmd == 'reload':     # reload <aim clip> <dir of the hip reload clips> <out dir>
        for src, cfg in RELOAD_ADS.items():
            bake_reload(sys.argv[2], os.path.join(sys.argv[3], src), os.path.join(sys.argv[4], cfg['out']), cfg['keys'])


if __name__ == '__main__':
    main()
