"""Stay-in-ADS reload baker (user 2026-10-04: "the weapon stays in ads when it gets cocked or reloaded").

The gun stays at the aim pose - sights on the target, no dip, no cant. The only gun motion allowed is a SLIDE along the
line of sight (`slide` keys, u; the sights stay lined up), used where the action works right under the eye (bolt
guns: the open bolt and the loading hand would otherwise sit 1-2 u from the camera). Both hands keep the retail hip
clip's hand-to-gun relation frame by frame (its own contact with clip, magazine, bolt), blended from/to the aim grip
at the ends of the reload SEQUENCE (enter / exit: multi-clip reloads only blend at the first clip's start and the last
clip's end), fingers likewise; arms by two-bone IK from the aim pose's shoulders; trunk and eye held; both weapon tags
on the gun. Same channel layout, frame count and frame time as the hip clip.

    python hold_bake.py <recipe> <out.skc> [--ctl ctl.json]
"""
import os
import sys, json, math, argparse
import numpy as np
import vmcam as V
import key_bolt as K
B = K.B
R = V.R

# class settings (coordinator 2026-10-04): hand clearance and damping only - the gun pose itself is locked
RECIPES = {
    'garand_reload': dict(gun='garand', hip='viewmodel/rifle/vm_riflereload.skc', charge='viewmodel/grnd_stand00.skc',
                          offhand=(1, 57), enter=8, exit=8, weight=dict(max_rot=1.0, max_move=0.6),
                          # review ab14: right hand fills the view while thumbing the clip (clip f22-48, ~8 u from the
                          # eye) -> the rifle is pushed out along the sight line for the clip work, sights stay aligned
                          # ab17: a 3.5 u push alone brought the forearm across the view -> small dip (user option
                          # (c), as the bolt clips): butt lowered 4 deg about the front sight (post stays on target, the
                          # receiver drops into view, the hand works below the sight line) + 2 u push
                          slide={0: 0, 18: 0, 26: 2.0, 48: 2.0, 55: 0, 60: 0}, dip_pivot=30.0,
                          dip={0: (0, 0, 0), 16: (0, 0, 0), 26: (0, 0, -4.0), 48: (0, 0, -4.0), 56: (0, 0, 0), 60: (0, 0, 0)},
                          prop_pin=dict(tag='tag_weapon_right', tik='models/ammo/garand_clip_reload.tik', pin=33, seat=40,
                                        until=42, gun_tik='models/weapons/m1_garand.tik', gun_anim='reload',
                                        seat_frame=40, surface='material8'),
                          clear=dict(slope=None, min_dist=6.0)),
    # magazine rifles (no server hand-off: the gun stays on the right hand tag)
    'g43_reload': dict(gun='g43', hip='viewmodel/g43/g43_reload.skc', charge='viewmodel/grnd_stand00.skc',
                       offhand=(-1, -1), enter=8, exit=8, slide={}, weight=dict(max_rot=1.5)),
    'johnson_reload': dict(gun='johnson_m1941', hip='viewmodel/coop_johnson/johnson_reload.skc',
                           charge='viewmodel/grnd_stand00.skc', offhand=(-1, -1), enter=10, exit=10, slide={}, weight=dict(max_rot=1.5)),
    'kar98_reload': dict(gun='kar98', hip='viewmodel/rifle/kar98_reload.skc', charge='viewmodel/kar_stand00.skc',
                         offhand=(1, 100), enter=8, exit=10,
                         slide={0: 0, 6: 2.0, 12: 4.0, 88: 4.0, 101: 0}),
}


def fps_rows():
    import zipfile
    rows = {}
    for f in ('rifle', 'smg', 'mg', 'pistol', 'shotgun'):
        d = R.vfs.read('models/player/base/fps_anims_%s.txt' % f)
        for l in (d.decode('latin-1').splitlines() if d else []):
            t = l.split('//')[0].split()
            if len(t) >= 2 and t[0] not in rows:
                rows[t[0]] = t[1]
    return rows


def auto_recipe(name, **kw):
    """<prefix>_<reload|reload_single|reload_end> -> recipe from fps_anims (hip clip, charge or idle as the aim pose);
    no server hand-off (SMGs/MGs/pistols keep the gun on the right hand)"""
    rows = fps_rows()
    prefix = name.split('_reload')[0]
    rc = dict(gun=kw.pop('gun', prefix), hip=rows[name], charge=rows.get(prefix + '_charge', rows.get(prefix + '_idle')),
              offhand=(-1, -1), enter=8, exit=8, slide={}, weight=dict(max_rot=1.5))
    # START / LOAD / END split (revolvers, shotgun: <p>_reload -> <p>_reload_single looped -> <p>_reload_end): the
    # gun is held across the seams, so only the outer ends blend from/to the aim pose; the weight fades to zero at
    # every inner seam (each clip runs its own spring from rest, so a seam with weight left on would pop)
    if prefix + '_reload_single' in rows:
        part = name[len(prefix):]
        if part == '_reload':
            rc.update(exit=0, wfade=(0, 6))
        elif part == '_reload_single':
            rc.update(enter=0, exit=0, wfade=(6, 6))
        elif part == '_reload_end':
            rc.update(enter=0, wfade=(6, 0))
    rc.update(kw)
    return rc


def ease(x):
    return R.smoothstep(x)


def slide_at(rc, f):
    ks = sorted(rc['slide'])
    if not ks:
        return 0.0
    return K.pchip(ks, [rc['slide'][k] for k in ks], f)


WEIGHT = dict(k_fast=0.25, k_slow=0.04, slow_sigma=10.0, hz=5.0, zeta=0.55, max_rot=2.0, max_move=0.8)


def weight_track(hip, lo, hi, wt, env):
    """WEIGHT (user 2026-10-04: "there should be weight to it"): the gun's own motion in the retail hip clip, in its own
    frame relative to frame 0, split into a slow part (the lowering to the hip - mostly discarded) and the fast events
    (clip pulled/seated, slapped home, bolt released), scaled down hard, run through an under-damped spring (overshoot
    and settle, never linear), soft-clamped to the budget and faded by the enter/exit envelope.
    -> list of gun-local 4x4 (pre-scale) deltas, applied before the aim gun placement"""
    n = hip.numFrames
    G = []
    for f in range(n):
        W = R.evaluate(R.pose_dict(hip, f))
        G.append(W['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right'])
    x = np.zeros((n, 6))
    for f in range(n):
        L = G[f] @ R.inv(G[0])
        ax, ang = B.rot_to_aa(L[0:3, 0:3])
        x[f, 0:3] = ax * math.radians(ang)
        x[f, 3:6] = L[3, 0:3] * R.S
    s = wt['slow_sigma']
    k = np.exp(-0.5 * (np.arange(-3 * int(s), 3 * int(s) + 1) / s) ** 2); k /= k.sum()
    pad = np.vstack([np.repeat(x[:1], len(k) // 2, 0), x, np.repeat(x[-1:], len(k) // 2, 0)])
    slow = np.array([np.convolve(pad[:, c], k, mode='valid') for c in range(6)]).T
    tgt = wt['k_fast'] * (x - slow) + wt['k_slow'] * slow
    w0 = 2 * math.pi * wt['hz']; dt = hip.frameTime
    y = np.zeros(6); v = np.zeros(6); out = []
    for f in range(n):
        for _ in range(8):                                  # substeps
            a = w0 * w0 * (tgt[f] - y) - 2 * wt['zeta'] * w0 * v
            v += a * dt / 8; y += v * dt / 8
        r = y[0:3]; ra = np.linalg.norm(r); t = y[3:6]; ta = np.linalg.norm(t)
        rc = math.radians(wt['max_rot']) * math.tanh(ra / math.radians(wt['max_rot'])) if ra > 1e-9 else 0.0
        tc = wt['max_move'] * math.tanh(ta / wt['max_move']) if ta > 1e-9 else 0.0
        e = env[f]
        Rm = R.axis_angle_rows(r / ra, math.degrees(rc) * e) if ra > 1e-9 else np.eye(3)
        M = B.H(Rm, (t / ta * tc * e / R.S) if ta > 1e-9 else np.zeros(3))
        out.append((M, math.degrees(rc) * e, tc * e))
    return out


def clear_hand(Hm, Mcam, cl):
    """HAND CLEARANCE (class setting): the retail hip art reaches OVER the gun (it was made with the gun at the hip);
    with the gun held at the eye that arm crosses the sight picture at the lens. Keep the wrist under a cone below the
    line of sight - camera frame z <= -(slope * x + drop) - with a smooth (softplus) floor, so the hand dips under the
    sight line instead of across it. The hand keeps its orientation; only its position moves."""
    p = np.r_[Hm[3, 0:3] * R.S, 1.0] @ Mcam
    q = p[0:3].copy()
    if cl.get('slope') is not None:
        x, z = q[0], q[2]
        lim = -(cl.get('slope', 0.45) * max(x, 0.0) + cl.get('drop', 1.0))
        k = cl.get('soft', 0.6)
        zc = lim - k * math.log1p(math.exp((lim - z) / k)) if z > lim - 6 * k else z
        q[2] = z + cl.get('cone_w', 1.0) * (zc - z)
    if cl.get('min_dist'):                                 # keep the wrist at least min_dist from the eye (soft)
        dmin, r = cl['min_dist'], np.linalg.norm(q)
        k = cl.get('dsoft', 0.4)                           # softplus floor: ~r beyond dmin + 2k, -> dmin well inside
        if r < dmin + 8 * k:
            r2 = max(r, dmin + k * math.log1p(math.exp((r - dmin) / k)))
            q = q / max(r, 1e-6) * r2
    q = p[0:3] + cl.get('fade', 1.0) * (q - p[0:3])
    if np.linalg.norm(q - p[0:3]) < 1e-6:
        return Hm
    d = np.r_[q - p[0:3], 0.0] @ R.inv(Mcam)              # camera-space move -> model (scaled) -> pre-scale
    out = Hm.copy(); out[3, 0:3] += d[0:3] / R.S
    return out


_PIN = {}


def pin_world(rc, pin, f, Gads):
    """prop tag world (pre-scale) for a pinned prop: its hip-art relation to the gun at frame `pin`, translated in gun
    space so its centroid lands on the gun's own clip surface (`seat` frame of the gun's anim) by `seat`"""
    key = (rc['hip'], pin['pin'], pin['seat'])
    if key not in _PIN:
        import sys as _s
        _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ads_anims_2026-10-04', 'tools'))
        import render as PR
        hip = R.load(R.ANIM + rc['hip'])
        lo, hi = rc['offhand']
        W = R.evaluate(R.pose_dict(hip, pin['pin']))
        G = W['tag_weapon_left' if lo <= pin['pin'] <= hi else 'tag_weapon_right']
        rel = W[pin['tag']] @ R.inv(G)                     # prop tag in gun-tag frame (pre-scale)
        P = np.vstack([s['P'] for s in PR.gungeo.load_gun(pin['tik'])['surfs']])
        pc_ = (P.mean(axis=0) @ rel[0:3, 0:3]) + rel[3, 0:3] * R.S     # prop centroid, gun space (scaled)
        m = [s['P'] for s in PR.gungeo.load_gun(pin['gun_tik'], anim=pin['gun_anim'], frame=pin['seat_frame'])['surfs']
             if s['name'] == pin['surface']][0]
        _PIN[key] = (rel, m.mean(axis=0) - pc_)
    rel, d = _PIN[key]
    a = ease((f - pin['pin']) / float(max(1, pin['seat'] - pin['pin'])))
    Rl = rel.copy(); Rl[3, 0:3] = rel[3, 0:3] + a * d / R.S
    return Rl @ Gads


def bake(name, ctl):
    rc = RECIPES[name] if name in RECIPES else auto_recipe(name)
    hip = R.load(R.ANIM + rc['hip'])
    chg = R.load(R.ANIM + rc['charge'])
    pc = R.pose_dict(chg, chg.numFrames - 1)
    Wc = R.evaluate(pc)
    Gc = Wc['tag_weapon_right']
    relRc = Wc['Bip01 R Hand'] @ R.inv(Gc)
    relLc = Wc['Bip01 L Hand'] @ R.inv(Gc)
    if rc['gun'] in V.SIGHTS:
        Wcc = V.evaluate_ctl(pc, ctl)
        corr = V.rig_target(Wcc, V.SIGHTS[rc['gun']])
        C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']
        C[3, 0:3] *= R.S
        Mcam = C @ V.model_to_cam(corr)
    else:                                                 # no sight row (legacy ADS table gun): only a slide needs it
        assert not rc['slide'], 'a sight-line slide needs the sight row of the gun'
        Mcam = np.eye(4)
    lo, hi = rc['offhand']
    out = R.load(R.ANIM + rc['hip'])
    # attached ammo props (server attachmodel windows, in this clip's frames) - for the hand-over rule below
    try:
        import prop_qa as _Q
        wins = [w for w in _Q.attach_windows(name, hip.numFrames, hip.frameTime)] if rc.get('handover', True) else []
    except Exception:
        wins = []
    cm = R.chanmap(out)
    n = hip.numFrames
    rep = {'recipe': name, 'frames': []}
    env = []
    for f in range(n):
        w = 1.0
        if rc.get('enter'):
            w = min(w, ease(f / float(rc['enter'])))
        if rc.get('exit'):
            w = min(w, ease((n - 1 - f) / float(rc['exit'])))
        env.append(w)
    wt = dict(WEIGHT, **rc.get('weight', {}))
    fi, fo = rc.get('wfade', (0, 0))
    wenv = [min(env[f], ease(f / float(fi)) if fi else 1.0, ease((n - 1 - f) / float(fo)) if fo else 1.0) for f in range(n)]
    track = weight_track(hip, lo, hi, wt, wenv) if wt.get('on', True) else [(np.eye(4), 0, 0)] * n
    for f in range(n):
        ph = R.pose_dict(hip, f)
        Wh = R.evaluate(ph)
        Gh = Wh['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right']
        w = 1.0
        if rc.get('enter'):
            w = min(w, ease(f / float(rc['enter'])))
        if rc.get('exit'):
            w = min(w, ease((n - 1 - f) / float(rc['exit'])))
        s = slide_at(rc, f)
        D = np.eye(4); D[3, 0] = s                       # camera +x = along the line of sight
        if rc.get('dip'):                                # small-dip (user option (c), as the bolt clips): camera-frame
            ks = sorted(rc['dip'])                       # drop (u, -z), roll (deg about +x), pitch (deg about +y),
            dp = [K.pchip(ks, [rc['dip'][k][j] for k in ks], f) for j in range(3)]   # pivot 12 u down the sight line
            Rr = R.axis_angle_rows((1, 0, 0), dp[1]) @ R.axis_angle_rows((0, 1, 0), dp[2])
            pv = rc.get('dip_pivot', 12.0); P = np.eye(4); P[3, 0:3] = (-pv, 0, 0)
            Q = np.eye(4); Q[0:3, 0:3] = Rr
            Pi = np.eye(4); Pi[3, 0:3] = (pv, 0, -dp[0])
            D = P @ Q @ Pi @ D
        Dm = Mcam @ D @ R.inv(Mcam); Dm[3, 0:3] /= R.S
        Gads = track[f][0] @ Gc @ Dm                     # weight (gun-local) on the aim gun, then the sight-line slide
        relRh = Wh['Bip01 R Hand'] @ R.inv(Gh)
        relLh = Wh['Bip01 L Hand'] @ R.inv(Gh)
        if rc.get('support_aim'):                        # cock.py clips: after the magazine the hip art's left hand is on
            a_, b_ = rc['support_aim']                   # the HIP support grip; aimed, it takes the AIM support grip
            ws_ = ease((f - a_) / float(max(1, b_ - a_))) if f > a_ else 0.0   # (eased in a..b, held to the end)
            if ws_ > 0:
                relLh = B.blend_H(relLh, relLc, ws_)
        HR = B.blend_H(relRc, relRh, w) @ Gads
        HL = B.blend_H(relLc, relLh, w) @ Gads
        if rc.get('fixed_right'):                        # pistols (user 2026-10-06): the firing hand keeps its AIM grip on
            HR = relRc @ Gads                            # the gun all reload - the retail clip tips the gun in the hand, baked
                                                         # upright that reads as the gun sliding up the hand
        wl = None
        if rc.get('left_grip'):                          # two-handed aim pose (user 2026-10-11): the support hand
            # starts and ends ON the gun. The retail left hand starts and ends hanging at the hip, so blending toward
            # it throws the hand out of view within two frames. Instead the hand travels from the aim grip straight to
            # where the retail art has it at frame `fa` (0..fa) and from frame `fb` back onto the grip (fb..n-1), on a
            # smootherstep with a sideways bulge (`way`, gun-frame u, sin-shaped) so the fingers come off the firing
            # hand before the hand drops. Between fa and fb: the retail relation, untouched.
            lg = rc['left_grip']
            fa, fb = lg['fa'], lg['fb']
            way = np.asarray(lg.get('way', (0.0, 0.0, 0.0)), float) / R.S

            def _relL(k):
                Wk = R.evaluate(R.pose_dict(hip, k))
                return Wk['Bip01 L Hand'] @ R.inv(Wk['tag_weapon_left' if lo <= k <= hi else 'tag_weapon_right'])

            def _ss(x):
                x = max(0.0, min(1.0, x))
                return x * x * x * (x * (x * 6 - 15) + 10)
            if f <= fa:
                wl = _ss(f / float(fa)); other_ = _relL(fa)
            elif f >= fb:
                wl = _ss((n - 1 - lg.get('hold', 0) - f) / float(n - 1 - lg.get('hold', 0) - fb)); other_ = _relL(fb)
            else:
                wl = 1.0; other_ = relLh
            rl = B.blend_H(relLc, other_, wl)
            rl[3, 0:3] += way * math.sin(math.pi * wl)
            HL = rl @ Gads
        HR0 = HR
        if rc.get('clear'):
            # never push a hand further out than where it rests in the aim pose itself (the charge pose's trigger hand
            # sits ~5.6 u from the eye on the Garand: a flat min_dist pushed it 3 u at every frame but the two
            # endpoints written from the pose, a pop at enter and exit)
            for side in ('R', 'L'):
                Hs = HR if side == 'R' else HL
                rest = float(np.linalg.norm((np.r_[((relRc if side == 'R' else relLc) @ Gads)[3, 0:3] * R.S, 1.0] @ Mcam)[0:3]))
                cl = dict(rc['clear'])
                if cl.get('drop_keys'):                    # cone drop varying over the clip [(frame, drop), ...]
                    ks = cl['drop_keys']
                    cl['drop'] = K.pchip([k for k, _ in ks], [v for _, v in ks], f)
                if cl.get('slope_keys'):                   # cone slope varying over the clip [(frame, slope), ...]
                    ks = cl['slope_keys']
                    cl['slope'] = K.pchip([k for k, _ in ks], [v for _, v in ks], f)
                # clearance fades with the enter/exit envelope: at w=0 the hand is the aim pose's own hand, and the
                # endpoints are written from that pose - a hand pushed at w<1 snapped back on the last frame (ab23
                # MP44 f179-180 hand snap)
                cl['fade'] = w
                if cl.get('cone_frames'):                  # cone only inside these clip frames, 4-frame eased ramps
                    a, b = cl['cone_frames']
                    cl['cone_w'] = min(ease((f - a + 4) / 4.0), ease((b + 4 - f) / 4.0))
                if cl.get('min_dist'):
                    cl['min_dist'] = min(cl['min_dist'], rest - 1.0)
                Hs = clear_hand(Hs, Mcam, cl)
                if side == 'R':
                    HR = Hs
                else:
                    HL = Hs
        eyeR = float(np.linalg.norm((np.r_[HR0[3, 0:3] * R.S, 1.0] @ Mcam)[0:3]))
        pushR = float(np.linalg.norm(HR[3, 0:3] - HR0[3, 0:3]) * R.S)
        pd = dict(pc)
        for ch in hip.names:
            if ch not in pd:
                pd[ch] = ph[ch].copy()
            if ' Finger' in ch:
                pd[ch] = R.qslerp(pc.get(ch, ph[ch]), ph[ch], w)
                if wl is not None and ch.startswith('Bip01 L '):   # left_grip: the support hand's fingers open on its
                    kf = lg['fa'] if f <= lg['fa'] else (lg['fb'] if f >= lg['fb'] else f)   # own track (faster: off
                    pd[ch] = R.qslerp(pc.get(ch, ph[ch]), R.pose_dict(hip, kf)[ch], min(1.0, wl * lg.get('finger_lead', 2.0)))
        pb = None
        if rc.get('elbow_down'):                         # {side: [(frame, weight), ...]} - elbow swung down (camera -z)
            dm = (np.array([0.0, 0.0, -1.0]) @ R.inv(Mcam)[0:3, 0:3])
            pb = {}
            for side, keys in rc['elbow_down'].items():
                ks = [k for k, _ in keys]
                pb[side] = dm / np.linalg.norm(dm) * K.pchip(ks, [v for _, v in keys], f)
        K.solve_arms(pd, Wc, HR, HL, Gads, pb)
        # the tag the server does NOT carry the gun on keeps the hip art's value: it holds the ammo prop
        # (rifle_reload: garand_clip_reload.tik on tag_weapon_right 4-42 while the gun is on the left hand)
        other = 'tag_weapon_right' if lo <= f <= hi else 'tag_weapon_left'
        # every inner frame, also inside the enter/exit blend (review ab14: MP44 magazine floated upright beside the gun
        # at the start - the prop was already attached while the tag still held the aim pose's gun value)
        if rc.get('free_tag', True) and (0 < f < n - 1 or lo < 0):   # no hand-off: the endpoints too (ab17 MP44)
            for ch in (other + ' rot', other + ' pos'):
                if ch in ph:
                    pd[ch] = ph[ch].copy()
        # HAND-OVER (user 2026-10-05: "the random clip that pops up near the gun for a frame or so"): the retail art
        # attaches/removes a prop where it coincides with the gun's own mesh, relative to a hand that is in the retail
        # hand-to-gun relation. Our hand is not (enter/exit blend from the aim grip, clearance), so a hand-relative
        # prop appears/vanishes beside the gun (ab19 MP44 upright magazine, MP40 sliver). Near its attach and remove
        # frames and inside the blends the prop keeps its RETAIL relation to the GUN, easing to the hand over 6 frames.
        for tik, tg, a0, a1 in wins:
            if not (a0 <= f <= a1) or tg not in ('tag_weapon_left', 'tag_weapon_right'):
                continue
            g = max(1.0 - w, ease(1.0 - (f - a0) / 6.0), ease(1.0 - (a1 - f) / 6.0))
            if g <= 1e-3:
                continue
            Hh = HR if tg == 'tag_weapon_right' else HL
            rel = Wh[tg] @ R.inv(Gh)                          # retail prop-to-gun
            hold = rc.get('prop_hold', {}).get(tg)             # retail art attaches the prop before the hand is there
            if hold is not None and f < hold:                  # (MP44: upright above the gun f0-4) -> park it at its
                Wq = R.evaluate(R.pose_dict(hip, hold))        # retail spot of frame `hold` (in the gun's own mag)
                rel = Wq[tg] @ R.inv(Wq['tag_weapon_left' if lo <= hold <= hi else 'tag_weapon_right'])
                g = 1.0
            elif hold is not None and f < hold + 6:
                g = max(g, ease(1.0 - (f - hold) / 6.0))
            Tg = rel @ Gads                                    # world, gun-relative
            lh = Wh[tg] @ R.inv(Wh['Bip01 %s Hand' % ('R' if tg.endswith('right') else 'L')])   # retail prop-to-hand
            lg = Tg @ R.inv(Hh)                                                                      # gun-relative, as hand-local
            q = R.qslerp(R.rows_to_quat(lh[0:3, 0:3]), R.rows_to_quat(lg[0:3, 0:3]), g)
            pp = (1 - g) * lh[3, 0:3] + g * lg[3, 0:3]
            pd[tg + ' rot'] = q
            pd[tg + ' pos'] = np.array([pp[0], pp[1], pp[2], 0.0])
        pin = rc.get('prop_pin')
        if pin and pin['pin'] <= f <= pin['until']:
            # user 2026-10-05 "the random clip that pops up near the gun for a frame or so": the retail hand lifts the
            # en-bloc clip back OUT of the receiver (still attached, f36-42) before the server removes it - hidden at
            # the hip, a clip flying up and vanishing in ADS. Pin it in the gun from `pin` and ease it onto the gun's
            # own clip surface by `seat`, so the removal is a hand-over to the gun's mesh.
            Tw = pin_world(rc, pin, f, Gads)
            Hh = HR if pin['tag'] == 'tag_weapon_right' else HL
            tl = Tw @ R.inv(Hh)
            pd[pin['tag'] + ' rot'] = R.rows_to_quat(tl[0:3, 0:3])
            pd[pin['tag'] + ' pos'] = np.array([tl[3, 0], tl[3, 1], tl[3, 2], 0.0])
        K.write_frame(out, hip, cm, f, pd)
        rep['frames'].append({'f': f, 'w': round(w, 3), 'slide': round(s, 2), 'rot': round(track[f][1], 2), 'move': round(track[f][2], 2),
                              'eyeR': round(eyeR, 2), 'pushR': round(pushR, 2)})
    if rc.get('enter'):
        for ch in hip.names:
            if ch in pc and not ch.startswith('tag_weapon_left'):
                out.V[0, cm[ch]] = pc[ch]
    if rc.get('exit'):
        for ch in hip.names:
            if ch in pc and not ch.startswith('tag_weapon_left'):
                out.V[n - 1, cm[ch]] = pc[ch]
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(n)]
    return out, rep


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('recipe'); ap.add_argument('out')
    ap.add_argument('--ctl', default='../assets/ctl_stand.json')
    a = ap.parse_args()
    sk, rep = bake(a.recipe, json.load(open(a.ctl)))
    open(a.out, 'wb').write(R.skc_io.write(sk))
    json.dump(rep, open(a.out[:-4] + '_rep.json', 'w'), indent=0)
    fr = rep['frames']
    print('weight: max rot %.2f deg, max move %.2f u' % (max(x['rot'] for x in fr), max(x['move'] for x in fr)))
    print(' '.join('%d:%.1f/%.2f' % (x['f'], x['rot'], x['move']) for x in fr[::3]))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
