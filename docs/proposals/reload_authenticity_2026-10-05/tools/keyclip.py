"""keyclip.py - HAND-KEYED first-person reload clips (reload authenticity phase B polish).

Replaces the donor re-timing of retarget.py for the guns whose borrowed clips could not be made to look right. The
clip is authored from scratch on the gun's own idle pose:
  * the GUN sits at its idle hold plus keyed small moves/tilts (gun frame), so it never sinks out of view;
  * each HAND is driven by keys that put an EFFECTOR (palm / index tip / thumb tip / finger wrap) on a point of the
    gun, in the gun frame (x fwd, y right, z down, game units), with a hand rotation relative to its idle grip;
    positions use a monotone cubic through the keys (no linear moves, no overshoot); FOLLOW segments add a key every
    frame that rides a moving part (cover edge, charging handle, bolt) so the hand is on it exactly while it moves;
  * FINGERS blend between named poses (idle / open / grip / pinch) on eased curves - they curl when they take hold;
  * arms by two-bone IK (ads_bolt key_bolt.solve_arms), body = the idle pose (the camera never moves);
  * tag_weapon_left freezes (gun transform at a grip frame, expressed in the hand) carry gun-space props;
  * frame count / frame time = the template clip (the torso reload it runs under), first/last frame = the idle.
QA (report json + printout): IK error, effector-to-target at every contact frame, hand-to-part distance while each part
moves (the ads_bolt handle_qa.py measure: nearest hand/finger bone, grip <= 2.5 u), peak effector speed and peak
acceleration (snaps).

    python keyclip.py <recipe> <out.skc> [--report r.json]
"""
import sys, os, json, math, argparse
import numpy as np
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T)
_cwd = os.getcwd(); os.chdir(T)
import vmcam as V        # noqa: E402
import key_bolt as K     # noqa: E402
os.chdir(_cwd)
R = V.R
B = K.B
A = R.ANIM
MOD_ANIM = r'C:/mohaa-coop-dev/hzm-mohaa-coop-mod/models/human/animation/'


def ap(p):
    """clip path: 'mod:viewmodel/...' = the mod working tree, else the game's animation tree"""
    if os.path.isabs(p):
        return p
    return MOD_ANIM + p[4:] if p.startswith('mod:') else A + p
GRIP_QA = 2.5

FINGERS = ['Finger%d%s' % (i, k) for i in range(5) for k in ('', '1', '2')]
# named finger poses: (clip, frame, side) - measured (curl.py, mean fingertip-to-wrist): open 8.5 u, grip 4.7 u
POSES = {'open': ('viewmodel/pistol/reload_p38.skc', 57, 'L'), 'grip': ('viewmodel/coop_dp28/dp28_reload.skc', 57, 'L'),
         'wrap': ('viewmodel/coop_dp28/dp28_reload.skc', 27, 'L'), 'pinch': ('viewmodel/pistol/reload_p38.skc', 18, 'L')}
EFF = {'palm': ['Finger1', 'Finger2', 'Finger3', 'Finger4'], 'index': ['Finger12'], 'thumb': ['Finger02'],
       'wrap': ['Finger11', 'Finger21', 'Finger31'], 'pinch': ['Finger02', 'Finger12']}


def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def euler_rows(e):
    """gun-frame rotation (deg about x, then y, then z), row-vector convention"""
    M = np.eye(3)
    for ax, a in zip(np.eye(3), e):
        if a:
            M = M @ R.axis_angle_rows(ax, a)
    return M


def pchip_curve(xs, ys, x):
    return K.pchip(list(map(float, xs)), list(map(float, ys)), float(x))


class Clip:
    def __init__(self, rc):
        self.rc = rc
        self.tpl = R.load(ap(rc['template']))
        self.out = R.load(ap(rc['template']))
        self.cm = R.chanmap(self.out)
        self.n = self.tpl.numFrames
        idl = R.load(ap(rc['idle']))
        self.pi = R.pose_dict(idl, 0)
        self.Wi = R.evaluate(self.pi)
        self.Gi = self.Wi['tag_weapon_right']
        self.rel_idle = {s: self.Wi['Bip01 %s Hand' % s] @ R.inv(self.Gi) for s in 'LR'}
        self.poses = {'idle_L': {f: self.pi['Bip01 L %s rot' % f] for f in FINGERS},
                      'idle_R': {f: self.pi['Bip01 R %s rot' % f] for f in FINGERS}}
        for name, (clip, fr, side) in POSES.items():
            pd = R.pose_dict(R.load(ap(clip)), fr)
            for s in 'LR':   # left-hand poses mirror to the right hand by channel name only (same skeleton rig)
                self.poses['%s_%s' % (name, s)] = {f: pd['Bip01 %s %s rot' % (side, f)] for f in FINGERS}
        self._rcache = {}
        self.eff_local = {}
        for s in 'LR':
            for e, bones in EFF.items():
                pd = dict(self.pi)
                fp = {'palm': 'open', 'wrap': 'wrap', 'pinch': 'pinch', 'index': 'pinch', 'thumb': 'pinch'}[e]
                for f in FINGERS:
                    pd['Bip01 %s %s rot' % (s, f)] = self.poses['%s_%s' % (fp, s)][f]
                W = R.evaluate(pd)
                Hm = W['Bip01 %s Hand' % s]
                p = np.mean([W['Bip01 %s %s' % (s, b)][3, 0:3] for b in bones], axis=0)
                self.eff_local[(s, e)] = (p - Hm[3, 0:3]) @ Hm[0:3, 0:3].T
        self.gun = self._gun_track()
        self.hands = {s: self._hand_track(s) for s in 'LR'}
        self.fing = {s: self._finger_track(s) for s in 'LR'}

    # ---------------------------------------------------------------- gun
    def _gun_track(self):
        keys = self.rc.get('gun', [])
        n = self.n
        if not keys:
            return [self.Gi.copy() for _ in range(n)]
        ks = [(0, (0, 0, 0), (0, 0, 0))] + list(keys) + [(n - 1, (0, 0, 0), (0, 0, 0))]
        fs = [k[0] for k in ks]
        out = []
        for f in range(n):
            pos = np.array([pchip_curve(fs, [k[1][i] for k in ks], f) for i in range(3)])
            for (fa, _, ra), (fb, _, rb) in zip(ks, ks[1:]):
                if fa <= f <= fb:
                    w = ease((f - fa) / float(max(1, fb - fa)))
                    e = np.array(ra) * (1 - w) + np.array(rb) * w
                    break
            # LIFE (polish, user: 'not robotic'): a slow breathing drift of the held gun (zero at the first / last frame,
            # so the clip starts and ends on the idle) and damped kicks where the hands strike or a part slams home
            w = math.sin(math.pi * f / float(n - 1))
            pos = pos + w * np.array([0.12 * math.sin(2 * math.pi * f / 36.0), 0.10 * math.sin(2 * math.pi * f / 47.0 + 1.0),
                                      0.15 * math.sin(2 * math.pi * f / 41.0 + 2.0)])
            e = np.array(e, float) + w * np.array([0.5 * math.sin(2 * math.pi * f / 53.0), 0.4 * math.sin(2 * math.pi * f / 39.0 + 0.5),
                                                   0.3 * math.sin(2 * math.pi * f / 44.0 + 1.5)])
            for fk, dp, dr in self.rc.get('gun_fx', []):
                t = f - fk
                if t >= 0:
                    k = math.exp(-t / 3.5) * math.sin(t * math.pi / 4.0)   # up over 2 frames, one small overshoot, settled by ~10
                    pos = pos + k * np.asarray(dp, float); e = e + k * np.asarray(dr, float)
            D = B.H(euler_rows(e), pos / R.S)
            out.append(D @ self.Gi)
        return out

    # ---------------------------------------------------------------- hands
    def part_point(self, f, spec):
        """a gun-frame point (game units) that may ride a moving part: spec = (x, y, z) or ('part', name, (x, y, z))"""
        if spec and spec[0] == 'part':
            return np.asarray(self.rc['parts'][spec[1]](f, np.array(spec[2], float)))
        return np.asarray(spec, float)

    def rot_of(self, s, rot):
        if rot and rot[0] == 'from':                 # ('from', clip, frame, side, gun tag[, euler tweak])
            key = tuple(rot[:5])
            if key not in self._rcache:
                W = R.evaluate(R.pose_dict(R.load(ap(rot[1])), rot[2]))
                self._rcache[key] = (W['Bip01 %s Hand' % rot[3]] @ R.inv(W[rot[4]]))[0:3, 0:3]
            Rr = self._rcache[key]
            return Rr @ euler_rows(rot[5]) if len(rot) > 5 else Rr
        return self.rel_idle[s][0:3, 0:3] @ euler_rows(rot)

    def _key_rel(self, s, f, eff, target, rot):
        Rr = self.rot_of(s, rot)
        tgt = self.part_point(f, target) / R.S
        pos = tgt - self.eff_local[(s, eff)] @ Rr
        return B.H(Rr, pos)

    def _hand_track(self, s):
        raw = [k for k in self.rc.get('hands', []) if k[0] == s]
        keys = []
        for k in raw:
            if k[1] == 'follow':           # ('L', 'follow', f0, f1, eff, target, rot)
                _, _, f0, f1, eff, target, rot = k
                for f in range(f0, f1 + 1):
                    keys.append((f, self._key_rel(s, f, eff, target, rot)))
            elif k[1] == 'idle':           # ('L', 'idle', f) - on its idle grip
                keys.append((k[2], self.rel_idle[s].copy()))
            elif k[1] == 'turn':           # ('R', 'turn', f, eff, rot) - still at the idle grip, hand turned to rot
                _, _, f, eff, rot = k      # (the wrist sets itself up off screen before the hand rises into view)
                Ri = self.rel_idle[s]
                p_eff = (self.eff_local[(s, eff)] @ Ri[0:3, 0:3] + Ri[3, 0:3]) * R.S
                keys.append((f, self._key_rel(s, f, eff, tuple(p_eff), rot)))
            else:                          # ('L', f, eff, target, rot)
                _, f, eff, target, rot = k
                keys.append((f, self._key_rel(s, f, eff, target, rot)))
        keys.sort(key=lambda x: x[0])
        ded = {}
        for f, m in keys:                 # one key per frame: the later definition wins
            ded[f] = m
        keys = sorted(ded.items())
        n = self.n
        if not keys:
            return [self.rel_idle[s].copy() for _ in range(n)]
        if keys[0][0] > 0:
            keys.insert(0, (0, self.rel_idle[s].copy()))
        if keys[-1][0] < n - 1:
            keys.append((n - 1, self.rel_idle[s].copy()))
        fs = [k[0] for k in keys]
        out = []
        for f in range(n):
            pos = np.array([pchip_curve(fs, [k[1][3, i] for k in keys], f) for i in range(3)])
            for (fa, A_), (fb, B_) in zip(keys, keys[1:]):
                if fa <= f <= fb:
                    w = ease((f - fa) / float(max(1, fb - fa))) if fb - fa > 1 else (f - fa) / float(max(1, fb - fa))
                    Rr = R.quat_to_rows(R.qslerp(R.rows_to_quat(A_[0:3, 0:3]), R.rows_to_quat(B_[0:3, 0:3]), w))
                    break
            out.append(B.H(Rr, pos))
        return out

    def _finger_track(self, s):
        keys = sorted([k for k in self.rc.get('fingers', []) if k[0] == s], key=lambda k: k[1])
        n = self.n
        keys = ([(s, 0, 'idle')] if not keys or keys[0][1] > 0 else []) + keys
        if keys[-1][1] < n - 1:
            keys = keys + [(s, n - 1, 'idle')]
        out = []
        for f in range(n):
            for (_, fa, pa), (_, fb, pb) in zip(keys, keys[1:]):
                if fa <= f <= fb:
                    w = ease((f - fa) / float(max(1, fb - fa)))
                    P, Q = self.poses['%s_%s' % (pa, s)], self.poses['%s_%s' % (pb, s)]
                    out.append({c: R.qslerp(np.asarray(P[c]), np.asarray(Q[c]), w) for c in FINGERS})
                    break
        # fingers curl and release PROGRESSIVELY (polish): a 5-frame smoothing of every finger channel turns a 1-2 frame
        # shape change into a ~4-frame curl; the outer joints lag the knuckle by a frame (finger tips follow)
        kn = np.array([1, 4, 6, 4, 1], float); kn /= kn.sum()
        sm = [dict(o) for o in out]
        for c in FINGERS:
            Q = np.array([np.asarray(o[c], float) for o in out])
            for i in range(1, n):
                if Q[i] @ Q[i - 1] < 0:
                    Q[i] = -Q[i]
            lag = 1 if c.endswith('2') else 0
            Qp = np.pad(Q, ((2 + lag, 2), (0, 0)), mode='edge')[: n + 4]
            S_ = np.array([kn @ Qp[i:i + 5] for i in range(n)])
            S_ /= np.linalg.norm(S_, axis=1)[:, None]
            for i in range(n):
                sm[i][c] = S_[i]
        for i in (0, n - 1):           # exact idle at the ends
            sm[i] = out[i]
        return sm

    # ---------------------------------------------------------------- bake
    def bake(self):
        n = self.n
        frz = []
        for gf, ta, tb in self.rc.get('tagL', []):
            frz.append((ta, tb, self.gun[gf] @ R.inv(self.hands['L'][gf] @ self.gun[gf])))
        rep = {'frames': []}
        self.world = []
        natural = self.rc.get('ik', 'natural') == 'natural'
        if natural:   # anatomical IK: hinge elbows, swivel chosen over the whole clip (natik.py)
            import natik
            arms = {s: natik.Arm(R, self.Wi, s) for s in 'LR'}
            swivel = {}
            for s in 'LR':
                tg = []
                for f in range(n):
                    HT = self.hands[s][f] @ self.gun[f]
                    ai = (float(np.abs(self.hands[s][f] - self.rel_idle[s]).max()) < 1e-3 and
                          float(np.abs(self.gun[f] - self.Gi).max()) < 1e-4)     # hand AND gun on the idle
                    tg.append((HT[3, 0:3].copy(), HT, ai))
                swivel[s] = arms[s].solve_track(tg)
            Wb0 = R.evaluate(dict(self.pi))
        for f in range(n):
            pd = dict(self.pi)
            for s in 'LR':
                for c in FINGERS:
                    pd['Bip01 %s %s rot' % (s, c)] = self.fing[s][f][c]
            G = self.gun[f]
            HR = self.hands['R'][f] @ G
            HL = self.hands['L'][f] @ G
            if natural:
                for s_, HT in (('R', HR), ('L', HL)):
                    arms[s_].apply(pd, Wb0, HT[3, 0:3].copy(), HT, float(swivel[s_][f]))
                    tl = G @ R.inv(HT)
                    tg_ = 'tag_weapon_%s' % ('right' if s_ == 'R' else 'left')
                    pd[tg_ + ' rot'] = R.rows_to_quat(tl[0:3, 0:3])
                    pd[tg_ + ' pos'] = np.array([tl[3, 0], tl[3, 1], tl[3, 2], 0.0])
            else:
                K.solve_arms(pd, self.Wi, HR, HL, G)
            for ta, tb, Tl in frz:
                if ta <= f <= tb:
                    pd['tag_weapon_left rot'] = R.rows_to_quat(Tl[0:3, 0:3])
                    pd['tag_weapon_left pos'] = np.array([Tl[3, 0], Tl[3, 1], Tl[3, 2], 0.0])
            for ch in self.tpl.names:
                v = pd.get(ch, self.pi.get(ch))
                if v is None:
                    v = self.tpl.V[f, self.cm[ch]]
                v = np.asarray(v, dtype=np.float64)
                if ch.endswith(' pos'):
                    v = np.array([v[0], v[1], v[2], self.tpl.V[min(f, n - 1), self.cm[ch], 3]])
                self.out.V[f, self.cm[ch]] = v
            W = R.evaluate(pd)
            self.world.append(W)
            err = max(float(np.linalg.norm((W['Bip01 R Hand'][3, 0:3] - HR[3, 0:3]) * R.S)),
                      float(np.linalg.norm((W['Bip01 L Hand'][3, 0:3] - HL[3, 0:3]) * R.S)))
            rep['frames'].append({'f': f, 'ik_err_u': round(err, 3)})
        # quaternion hemisphere continuity
        for c in range(self.out.numChannels):
            if self.tpl.names[c].endswith(' rot'):
                for f in range(1, n):
                    if self.out.V[f, c] @ self.out.V[f - 1, c] < 0:
                        self.out.V[f, c] = -self.out.V[f, c]
        self.out.values = [[[float(np.float32(x)) for x in self.out.V[f, c]] for c in range(self.out.numChannels)]
                           for f in range(n)]
        rep.update(self.qa())
        return self.out, rep

    def qa(self):
        n = self.n
        res = {'contacts': [], 'parts': [], 'speed': {}}
        for k in self.rc.get('contacts', []):          # (side, f0, f1, eff, target, label)
            s, f0, f1, eff, target, label = k
            worst = 0.0
            for f in range(f0, f1 + 1):
                W = self.world[f]; G = self.gun[f]
                p = np.mean([W['Bip01 %s %s' % (s, b)][3, 0:3] for b in EFF[eff]], axis=0)
                tg = self.part_point(f, target) / R.S @ G[0:3, 0:3] + G[3, 0:3]
                worst = max(worst, float(np.linalg.norm(p - tg) * R.S))
            res['contacts'].append({'label': label, 'frames': [f0, f1], 'worst_u': round(worst, 2), 'ok': worst <= 1.0})
        for name, (fn, frames, pt) in self.rc.get('moving', {}).items():   # handle_qa measure while a part moves
            worst = 0.0
            for f in frames:
                W = self.world[f]; G = self.gun[f]
                tg = fn(f, np.array(pt, float)) / R.S @ G[0:3, 0:3] + G[3, 0:3]
                d = min(float(np.linalg.norm(W[b][3, 0:3] - tg) * R.S) for b in
                        ['Bip01 %s Hand' % s for s in 'LR'] + ['Bip01 %s %s' % (s, c) for s in 'LR' for c in FINGERS])
                worst = max(worst, d)
            res['parts'].append({'part': name, 'frames': [frames[0], frames[-1]], 'worst_u': round(worst, 2),
                                 'ok': worst <= GRIP_QA})
        # view blocking: a forearm/hand sample inside the central 25 deg cone of the view (model +x = view axis) and
        # closer than 18 u blocks the picture; reported per side as the frames it happens on
        blk = {'L': [], 'R': []}
        for f in range(n):
            W = self.world[f]; E = W['eyes bone'][3, 0:3]
            for s in 'LR':
                a_, b_ = W['Bip01 %s Forearm' % s][3, 0:3], W['Bip01 %s Hand' % s][3, 0:3]
                for t in np.linspace(0, 1, 9):
                    v = (a_ + (b_ - a_) * t - E) * R.S
                    if v[0] > 0 and math.degrees(math.atan2(math.hypot(v[1], v[2]), v[0])) < 25 and np.linalg.norm(v) < 18:
                        blk[s].append(f); break
        res['view_block'] = blk
        for s in 'LR':
            P = np.array([self.world[f]['Bip01 %s Hand' % s][3, 0:3] * R.S for f in range(n)])
            v = np.linalg.norm(np.diff(P, axis=0), axis=1) / self.tpl.frameTime
            a = np.abs(np.diff(v)) / self.tpl.frameTime
            res['speed'][s] = {'peak_u_s': round(float(v.max()), 1), 'peak_acc_u_s2': round(float(a.max()), 0),
                               'peak_acc_frame': int(a.argmax()) + 1}
        return res


def build(name):
    import recipes_keyed as RK
    rc = RK.RECIPES[name]
    c = Clip(rc)
    return c.bake()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recipe'); ap.add_argument('out'); ap.add_argument('--report')
    a = ap.parse_args()
    sk, rep = build(a.recipe)
    data = R.skc_io.write(sk)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, 'wb').write(data)
    if a.report:
        json.dump(rep, open(a.report, 'w'), indent=1)
    print('wrote', a.out, len(data), 'max ik err %.3f u' % max(x['ik_err_u'] for x in rep['frames']))
    for c in rep['contacts']:
        print('  contact %-28s f%d-%d worst %.2f u %s' % (c['label'], c['frames'][0], c['frames'][1], c['worst_u'], 'OK' if c['ok'] else 'FAIL'))
    for p in rep['parts']:
        print('  part    %-28s f%d-%d hand-to-part %.2f u %s' % (p['part'], p['frames'][0], p['frames'][1], p['worst_u'], 'OK' if p['ok'] else 'FAIL'))
    print('  view blocked (forearm/hand in the central 25 deg, < 18 u): L %s  R %s' % (rep['view_block']['L'], rep['view_block']['R']))
    for s, v in rep['speed'].items():
        print('  %s hand peak speed %s u/s, peak accel %s u/s2 at f%d' % (s, v['peak_u_s'], v['peak_acc_u_s2'], v['peak_acc_frame']))


if __name__ == '__main__':
    main()
