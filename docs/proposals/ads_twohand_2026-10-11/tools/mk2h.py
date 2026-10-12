"""Two-handed pistol aim pose builder (2026-10-11, user: "two hands holding handguns in ads").

From the gun's one-handed aim pose (`<gun>_charge`, 1 frame) build a pose where the support (left) hand wraps the
firing hand: the left hand = the right hand's grip MIRRORED through the gun's vertical centre plane (the rig's
left/right bones are mirror frames with local z flipped: F = diag(1,1,-1), measured from the hand meshes), then moved
out / down / forward and turned by the recipe, fingers opened to go around the firing hand's fingers, thumb keyed.
Left arm by two-bone IK from the (optionally re-posed) left shoulder. Everything else - trunk, eye, right arm, right
fingers, tag_weapon_right - is BIT-IDENTICAL to the source pose, so the rig solve / sight picture cannot change.

    python mk2h.py <recipe> <out.skc> [--view out.jpg] [--set k=v ...]
"""
import sys, os, json, math, argparse, copy
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_cwd = os.getcwd()
os.chdir(T)
import vmcam as V
import key_bolt as K
os.chdir(_cwd)
R = V.R; B = K.B; PR = V.PR
F = np.diag([1.0, 1.0, -1.0])
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))

FINGERS = ['Finger0', 'Finger01', 'Finger02', 'Finger1', 'Finger11', 'Finger12', 'Finger2', 'Finger21', 'Finger22',
           'Finger3', 'Finger31', 'Finger32', 'Finger4', 'Finger41', 'Finger42']

RECIPES = {
    # d = (fwd, right, down) u in the gun frame, added to the mirrored wrist; rot = (roll about bore, pitch, yaw) deg
    # about the mirrored wrist; curl = per-finger extra flexion (deg, + = more closed) at (knuckle, mid, tip)
    'colt45': dict(src='viewmodel/coltpose00.skc', sight='colt_45', yc=None, d=(0.0, -0.8, 0.3), rot=(0.0, 0.0, 0.0),
                   curl={}, thumb=None, clav=None, pole=(0.0, 0.0, 0.0)),
}


def rot_gun(deg3):
    """rows rotation in the gun frame: roll about x, pitch about y, yaw about z"""
    r, p, y = deg3
    return R.axis_angle_rows((1, 0, 0), r) @ R.axis_angle_rows((0, 1, 0), p) @ R.axis_angle_rows((0, 0, 1), y)


def build(rc):
    src = R.load(R.ANIM + rc['src'])
    pd = R.pose_dict(src, src.numFrames - 1)
    W0 = R.evaluate(pd)
    G0 = W0['tag_weapon_right']
    sight = V.SIGHTS[rc['sight']]
    # AIM FRAME: x = the sight line (rear -> front sight), z = down (the sight row's up, squared to x), y = right,
    # origin at the weapon tag. Every gun's own tag frame differs (the Breakthrough pistols are root-frame meshes with
    # other axes); the sight line and its up are what the eye sees, so the grip is described in that frame.
    sfx = '_root' if (PR.gungeo.ROOT_APPLY and sight.get('frame_used') == 'root' and 'F_root' in sight) else ''
    Fg, Rg, Ug = (np.array(sight[k + sfx], float) for k in ('F', 'R', 'up'))
    ax = (Fg - Rg) / np.linalg.norm(Fg - Rg)
    up = Ug - (Ug @ ax) * ax; up /= np.linalg.norm(up)
    az = -up; ay = np.cross(az, ax)
    A = np.eye(4); A[0:3, 0:3] = np.array([ax, ay, az])
    G = A @ G0
    ysight = float(Rg @ ay)
    yc = rc['yc'] if rc.get('yc') is not None else ysight + rc.get('yc_off', 0.29)             # grip centre plane (aim y, u)
    relR = W0['Bip01 R Hand'] @ R.inv(G)                                                      # hand in the gun frame
    My = np.diag([1.0, -1.0, 1.0])
    rot = F @ relR[0:3, 0:3] @ My
    pos = relR[3, 0:3] * R.S
    pos = np.array([pos[0], 2 * yc - pos[1], pos[2]])
    Rt = rot_gun(rc['rot'])
    rot = rot @ Rt
    pv = np.array(rc.get('pivot', (0.0, 0.0, 0.0)))                # pivot offset from the mirrored wrist (gun frame, u)
    pos = pos + pv - pv @ Rt + np.array(rc['d'], float)
    relL = np.eye(4); relL[0:3, 0:3] = rot; relL[3, 0:3] = pos / R.S
    HL = relL @ G
    out = dict(pd)
    # left fingers = mirrored right fingers (local), then opened / closed per recipe about the flexion axis (local z)
    cp = rc.get('copy', {})
    for fn in FINGERS:
        srcf = fn
        for a_, b_ in cp.items():                                # e.g. {'Finger1': 'Finger2'}: index curls like the middle
            if fn.startswith(a_) and (len(fn) == len(a_) or fn[len(a_):] in ('1', '2')) and fn[:7] == a_:
                srcf = b_ + fn[len(a_):]
        qr = pd['Bip01 R %s rot' % srcf]
        Ml = F @ R.quat_to_rows(qr) @ F
        add = rc.get('curl', {}).get(fn)
        if add:                                                  # extra flexion about the bone's own z (+ = closed)
            Ml = R.axis_angle_rows((0, 0, 1), add) @ Ml
        tw = rc.get('spread', {}).get(fn)
        if tw:                                                   # (axis xyz, deg) in the bone's own frame
            Ml = R.axis_angle_rows(tw[0:3], tw[3]) @ Ml
        out['Bip01 L %s rot' % fn] = R.rows_to_quat(Ml)
    if rc.get('clav'):                                           # re-pose the left shoulder: extra world rotation rows
        ax, deg = rc['clav'][0:3], rc['clav'][3]
        Wb = R.evaluate(out)
        cur = Wb['Bip01 L Clavicle'][0:3, 0:3]
        par = Wb[R.skeleton().bones['Bip01 L Clavicle']['parent']][0:3, 0:3]
        want = cur @ R.axis_angle_rows(ax, deg)
        out['Bip01 L Clavicle rot'] = R.rows_to_quat(want @ par.T)
    if rc.get('shoulder'):                                       # left shoulder joint toward this camera-frame point (u)
        Wb = R.evaluate(out)
        Wcc = V.evaluate_ctl(pd, CTL)
        corr = V.rig_target(Wcc, sight)
        C = R.inv(W0['Bip01 Spine1']) @ Wcc['Bip01 Spine1']; C[3, 0:3] *= R.S
        Mcam = C @ V.model_to_cam(corr)
        tgt = (np.r_[np.asarray(rc['shoulder'], float), 1.0] @ R.inv(Mcam))[0:3] / R.S      # pre-scale model
        Cp = Wb['Bip01 L Clavicle'][3, 0:3]; Sp0 = Wb['Bip01 L UpperArm'][3, 0:3]
        a0 = (Sp0 - Cp) / np.linalg.norm(Sp0 - Cp); a1 = (tgt - Cp) / np.linalg.norm(tgt - Cp)
        ax = np.cross(a0, a1); sn = np.linalg.norm(ax)
        ang = math.degrees(math.atan2(sn, a0 @ a1))
        cur = Wb['Bip01 L Clavicle'][0:3, 0:3]
        par = Wb[R.skeleton().bones['Bip01 L Clavicle']['parent']][0:3, 0:3]
        out['Bip01 L Clavicle rot'] = R.rows_to_quat(cur @ R.axis_angle_rows(ax / sn, ang) @ par.T)
        print('clavicle turned %.1f deg' % ang)
    # left arm IK (the right arm is not touched)
    Wb = R.evaluate(out)
    U, Fo, Hd, Cl = 'Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand', 'Bip01 L Clavicle'
    Sp, Ep, Wp = Wb[U][3, 0:3], Wb[Fo][3, 0:3], Wb[Hd][3, 0:3]
    Wt = HL[3, 0:3]
    la, lb = np.linalg.norm(Ep - Sp), np.linalg.norm(Wp - Ep)
    dvec = Wt - Sp; dist = np.linalg.norm(dvec)
    clamp = False
    if dist > la + lb - 1e-3:
        clamp = True
        dist = la + lb - 1e-3
    dh = dvec / np.linalg.norm(dvec)
    # pole: default = straight down in the model frame (elbow under the line shoulder->wrist), plus the recipe's bias
    pole = np.array([0.0, 0.0, -1.0]) + np.array(rc.get('pole', (0, 0, 0)), float)
    pole = pole - (pole @ dh) * dh; pole /= np.linalg.norm(pole)
    x = (la * la - lb * lb + dist * dist) / (2 * dist); h = math.sqrt(max(0.0, la * la - x * x))
    En = Sp + dh * x + pole * h
    Wtt = Sp + dh * dist
    Uw = B.align(Wb[U][0:3, 0:3], Ep - Sp, En - Sp)
    Fw = B.align(Wb[Fo][0:3, 0:3], Wp - Ep, Wtt - En)
    par = Wb[Cl][0:3, 0:3]
    out[U + ' rot'] = R.rows_to_quat(Uw @ par.T)
    out[Fo + ' rot'] = R.rows_to_quat(Fw @ Uw.T)
    out[Hd + ' rot'] = R.rows_to_quat(HL[0:3, 0:3] @ Fw.T)
    tl = G0 @ R.inv(HL)
    out['tag_weapon_left rot'] = R.rows_to_quat(tl[0:3, 0:3])
    out['tag_weapon_left pos'] = np.array([tl[3, 0], tl[3, 1], tl[3, 2], 0.0])
    _aims = dict(rc.get('aim') or {})
    for k_ in (rc.get('aimpt') or {}):
        _aims.setdefault(k_, [1, 0, 0])
    for fn in [f_ for f_ in FINGERS if f_ in _aims]:
        dg = _aims[fn]                # bone x-axis -> gun-frame direction (minimal turn)
        Wb = R.evaluate(out)
        bn = 'Bip01 L %s' % fn
        cur = Wb[bn][0:3, 0:3]
        par = Wb[R.skeleton().bones[bn]['parent']][0:3, 0:3]
        if fn in (rc.get('aimpt') or {}):                        # aim at a POINT of the aim frame (u) instead
            ptw = (np.r_[np.asarray(rc['aimpt'][fn], float) / R.S, 1.0] @ G)[0:3]
            tgt = ptw - Wb[bn][3, 0:3]
        else:
            tgt = np.asarray(dg[0:3], float) @ G[0:3, 0:3]
        tgt = tgt / np.linalg.norm(tgt)
        x = cur[0] / np.linalg.norm(cur[0])
        ax = np.cross(x, tgt); sn = np.linalg.norm(ax)
        if sn > 1e-6:
            ang = math.degrees(math.atan2(sn, x @ tgt))
            new = cur @ R.axis_angle_rows(ax / sn, ang)
            if len(dg) > 3:                                      # extra roll about the bone's own axis
                new = new @ R.axis_angle_rows(tgt, dg[3])
            out[bn + ' rot'] = R.rows_to_quat(new @ par.T)
    # report
    W1 = R.evaluate(out)
    wrist = math.degrees(math.acos(max(-1, min(1, (np.trace(HL[0:3, 0:3] @ Fw.T) - 1) / 2))))
    elb = math.degrees(math.acos(max(-1, min(1, ((Sp - En) @ (Wtt - En)) / (la * lb)))))
    def _bend(side, Wx):
        e, w = Wx['Bip01 %s Forearm' % side][3, 0:3], Wx['Bip01 %s Hand' % side][3, 0:3]
        fd = (w - e) / np.linalg.norm(w - e)
        return round(math.degrees(math.acos(max(-1, min(1, fd @ Wx['Bip01 %s Hand' % side][0, 0:3])))), 1)
    print('wrist bend (forearm vs hand axis): R %.1f  L %.1f deg; L elbow cam-model pos %s' % (
        _bend('R', W1), _bend('L', W1), np.round((W1['Bip01 L Forearm'][3, 0:3] - W1['eyes bone'][3, 0:3]) * R.S, 1)))
    rep = dict(clamp=clamp, wrist_bend=round(wrist, 1), elbow=round(elb, 1), reach=round(dist * R.S, 2),
               max_reach=round((la + lb) * R.S, 2),
               tag_left_err=float(np.abs(W1['tag_weapon_left'] - G0).max()),
               right_same=float(max(np.abs(W1[b] - W0[b]).max() for b in W0 if ' R ' in b or b in ('tag_weapon_right', 'eyes bone'))))
    # write: same layout as the source, 1 frame
    cm = R.chanmap(src)
    sk = R.load(R.ANIM + rc['src'])
    f = src.numFrames - 1
    for ch in src.names:
        v = np.asarray(out[ch], dtype=np.float64)
        if ch.endswith(' pos'):
            v = np.array([v[0], v[1], v[2], src.V[f, cm[ch], 3]])
        elif v @ src.V[f, cm[ch]] < 0:
            v = -v
        if ch.startswith('Bip01 L ') or ch.startswith('tag_weapon_left'):
            sk.V[:, cm[ch]] = v
    rep['joints'] = {b[6:]: [round(float(x), 2) for x in ((W1[b] @ R.inv(G))[3, 0:3] * R.S)] for b in W1 if b.startswith('Bip01 L') and ('Finger' in b or 'Hand' in b)}
    sk.values = [[[float(np.float32(x)) for x in sk.V[fr, c]] for c in range(sk.numChannels)] for fr in range(sk.numFrames)]
    return sk, out, rep


def views(pd, sight_gun, path, W=640, src_pd=None, extra=True):
    """shooter's eye (calibrated engine camera) [+ source pose] + left side + front-below close-ups"""
    from PIL import Image, ImageDraw
    import raster
    sight = V.SIGHTS[sight_gun]
    H = W * 9 // 16
    fov = V.weapon_fov()
    ims = []

    def eye_view(p, label):
        Wcc = V.evaluate_ctl(p, CTL)
        corr = V.rig_target(Wcc, sight)
        surfs, E, Wb = V.scene2(p, sight_gun, sight['tik'], 'idle', 0.0, CTL, corr)
        rgb, ids, dep = V.shade_render(surfs, E, fov, W, H)
        im = Image.fromarray(rgb); ImageDraw.Draw(im).text((4, 4), label, fill=(0, 0, 0))
        return im, surfs, E
    if src_pd is not None:
        ims.append(eye_view(src_pd, 'source (one hand)')[0])
    im, surfs, E = eye_view(pd, 'two hands - eye')
    ims.append(im)
    if extra:
        # close-ups around the grip: centre = right hand mesh centroid
        c = np.vstack([s['P'] for s in surfs if s['name'] == 'triggerhand']).mean(0)
        for label, off, up in (('left side', (0, 22, 2), (0, 0, 1)), ('front', (24, 3, -4), (0, 0, 1)),
                               ('top', (0, 0.01, 24), (1, 0, 0)), ('below', (2, 4, -24), (1, 0, 0)),
                               ('right side', (0, -22, 2), (0, 0, 1)), ('front-left', (16, 16, 4), (0, 0, 1))):
            g = {'surfs': surfs}
            rgb, ids, dep = raster.render(g, c + np.array(off, float), c, np.array(up, float), fov=40, W=W, H=H,
                                          bg=(150, 160, 170), znear=1.0, tex=True)
            L = np.array([0.4, 0.5, 0.75]); L /= np.linalg.norm(L)
            shade = np.ones(ids.shape); m = ids >= 0
            for si, s in enumerate(surfs):
                P = s['P']; tr = s['tri']
                n = np.cross(P[tr[:, 1]] - P[tr[:, 0]], P[tr[:, 2]] - P[tr[:, 0]])
                n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
                k = 0.45 + 0.55 * np.abs(n @ L)
                sel = m & (ids // 1000000 == si)
                shade[sel] = k[ids[sel] % 1000000]
            im = Image.fromarray(np.clip(rgb * shade[:, :, None], 0, 255).astype(np.uint8))
            ImageDraw.Draw(im).text((4, 4), label, fill=(0, 0, 0))
            ims.append(im)
    sel = os.environ.get('V2H', 'eye,left,front,top,below,right,fl').split(',')
    names = (['src'] if src_pd is not None else []) + ['eye', 'left', 'front', 'top', 'below', 'right', 'fl']
    ims = [im for n_, im in zip(names, ims) if n_ in sel]
    cols = 2
    Sx = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        Sx.paste(im, ((i % cols) * W, (i // cols) * H))
    Sx.save(path, quality=90)
    return surfs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recipe'); ap.add_argument('out'); ap.add_argument('--view'); ap.add_argument('--json')
    ap.add_argument('--w', type=int, default=640)
    a = ap.parse_args()
    rc = copy.deepcopy(RECIPES[a.recipe])
    if a.json:
        rc.update(json.load(open(a.json)))
    sk, pd, rep = build(rc)
    open(a.out, 'wb').write(R.skc_io.write(sk))
    print(json.dumps({k: v for k, v in rep.items() if k != 'joints'}))
    for k, v in rep['joints'].items():
        print('   ', k, v)
    if a.view:
        src = R.load(R.ANIM + rc['src'])
        views(pd, rc['sight'], a.view, a.w, R.pose_dict(src, src.numFrames - 1))
        print('view', a.view)


if __name__ == '__main__':
    main()
