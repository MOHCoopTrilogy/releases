"""retarget.py - build a per-gun first-person reload from a DONOR hip clip (reload authenticity phase B).

Per frame of the donor clip (same frame count / frame time, so a donor torso's notetracks keep their timing):
  * the gun = the donor's gun tag (right, or left inside the server hand-off window `offhand`), optionally moved by a
    GUN delta (gun-local, game units) - e.g. to sit the receiver where the donor's hand expects it;
  * each hand keeps the donor's hand-to-gun relation, plus keyed HAND OFFSETS in the gun frame (game units) with
    eased in/out - this is what moves a magazine hand onto THIS gun's magazine well;
  * SEAMS: the first `seam_in` / last `seam_out` frames blend gun and hands from / to the IDLE pose of the gun's own
    hand set (the prefix it idles in), so the cut from idle into the clip (and back) does not pop;
  * arms by the two-bone IK of ads_bolt key_bolt.solve_arms (shoulders from the donor frame); both weapon tags on
    the gun; fingers and everything else are the donor's.
    python retarget.py <recipe> <out.skc> [--report r.json]
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

RECIPES = {
    # M1 Carbine: the G43's bottom-box reload. The carbine's magazine (surface Skin7) sits ~2.5 u further back and
    # ~0.75 u lower (gun frame; gun up = -z) than the G43's well (g43_clip surface centre) - the left hand carries that
    # offset from the moment it grips the old magazine until it lets go of the new one. Seams to the Garand idle the
    # carbine wears (rifle/idle_rifle.skc; donor f0 differs by 1.7 u gun / 4.7 u left hand).
    'carbine': dict(donor='viewmodel/g43/g43_reload.skc', idle='viewmodel/rifle/idle_rifle.skc', offhand=None,
                    # hand-to-magazine (finger) distance on the G43 clip: grips the old magazine 0.3-0.5 s, away
                    # 0.6-1.6 s, seats the new one 1.7-1.8 s; 2.0-2.1 s the left hand goes to the G43's LEFT-side
                    # cocking handle - the carbine's operating slide is on the RIGHT, so that excursion is HELD out
                    # (left hand interpolated f55 -> f67 in the gun frame): magazine swap only, no wrong-side cock.
                    hand=[('L', 3, 9, 54, 60, (-2.5, 0.0, 0.75))], hold=[('L', 55, 67)], gun=None,
                    seam_in=10, seam_out=12),
    # Lewis Gun (top 47-round pan): Lt. Pato's DP-28 pan reload (hand grips the pan 0.79-0.89 s, carries it off
    # 0.99-1.39 s, seats a pan 1.48-1.58 s) on the Lewis: left hand moved onto the Lewis pan centre (+1.3 x, -0.7 y,
    # +0.4 z gun frame vs the DP-28's) through the pan handling, seams to the BAR idle the Lewis wears (donor f0 is
    # 4 u gun / 7.7 u right hand away from it). tag_weapon_left CARRIES THE PAN: from the grip frame on it is frozen in
    # the hand at the gun transform of that frame, so the pan prop (BAR.skd, drum only) leaves exactly from the gun's
    # pan and lands back on it (torso coop_reload_lewis attaches it f29-f45).
    'lewis': dict(donor='viewmodel/coop_dp28/dp28_reload.skc', idle='viewmodel/mg/barpose.skc', offhand=None,
                  hand=[('L', 18, 24, 48, 54, (1.3, -0.7, 0.4))], gun=None, seam_in=10, seam_out=12,
                  tagL=(27, 26, 47)),
    # Thompson DRUM (Thompson 50rd = 50-round L drum, 1928 Tommy): the drum slides out SIDEWAYS - it hangs in
    # receiver guides across the bore and is inserted / removed laterally with the bolt back (FM 23-40 era practice;
    # side chosen: the shooter's LEFT, which the left hand reaches - the sources found do not state the side, see
    # AUDIT). Donor: the Thompson stick reload (its hand grips the magazine 0.1-0.3 s). From the grip frame the left
    # hand follows a keyed path in the gun frame (x fwd, y right, z down): slide 10 u left, away down-left out of view,
    # back, slide in, seated at f48 (1.6 s); tag_weapon_left carries the drum prop from f10. Seams to the Thompson idle.
    'tommydrum': dict(donor='viewmodel/smg/reload_tommy_stand.skc', idle='viewmodel/smg/idle_tommy_stand.skc',
                      offhand=None, hand=[], gun=None, seam_in=6, seam_out=10, tagL=(10, 10, 48),
                      path=dict(side='L', grip=10, pre=None,
                                # hold on the drum f10-13 and again f46-52: the gun hides its drum 2 frames AFTER the
                                # prop appears and shows it 2 frames BEFORE the prop goes, both at the same spot - no
                                # empty frame (rb2 found a one-frame drum flicker with the prop and hide on one frame)
                                keys=[(10, (0, 0, 0)), (13, (0, 0, 0)), (20, (0, -10, 0)), (27, (-1, -12, 14)),
                                      (33, (-1, -12, 14)), (40, (0, -10, 0)), (46, (0, 0, 0)), (52, (0, 0, 0))], out=6)),
    # MP18 snail drum (TM08): hangs on the LEFT of the receiver on its sleeve and comes off sideways. Donor: the MP40
    # bottom-box reload (hand on the magazine 0.1-0.3 s); the grip relation is moved from the MP40 magazine centre to
    # the snail drum centre (-3.2, -10.6, -8.5 gun frame) as the hand reaches (f0-f10), then the same lateral path.
    # The drum sits HIGH on the left of the receiver, so a hand on it is close to the eye: while the drum is handled
    # the gun is carried 3 u forward and 3 u lower (rb2: 5 u dropped it out of view) (gun frame) - review: forearm filled the view at 1.8 s otherwise -
    # and the hand takes the drum by its lower half (grip z -6 not -8.5).
    'mp18': dict(donor='viewmodel/MP40/reload_mp40_stand.skc', idle='viewmodel/mp40/mp40_stand_idle.skc',
                 offhand=None, hand=[], gun=(2, 12, 46, 66, (3.0, 0.0, 3.0)), seam_in=6, seam_out=10, tagL=(10, 10, 46),
                 path=dict(side='L', grip=10, pre=(0, 10, (-3.2, -10.6, -6.0)),
                           keys=[(10, (0, 0, 0)), (13, (0, 0, 0)), (20, (0, -8, 0)), (27, (-2, -12, 10)),
                                 (33, (-2, -12, 10)), (40, (0, -8, 0)), (44, (0, 0, 0)), (50, (0, 0, 0))], out=22, out_to=75)),
    # (out_to: the MP40 donor's left hand goes to the MP40's LEFT-side cocking handle 1.8-2.4 s; the MP18 cocks on the
    # RIGHT, so the left hand returns straight to its grip pose of f75 instead.)
    # Mauser C96 (+Trench): fixed 10-round box AHEAD of the trigger, loaded from the TOP through the open action with a
    # stripper clip - was the P38's grip-magazine swap. Donor: the P38 reload (pistol in the right hand; its left hand
    # racks the slide at the rear top at f57 - that grip is the base: the C96's bolt ears). Keyed left hand, gun frame
    # (x fwd, y right, z down): pull the bolt back 1.5 u and let go (it stays open on the follower - the mesh has no
    # separate bolt, so the bolt itself does not move), fetch the clip from below, set it in the guides above the
    # magazine (+3.6 u forward of the bolt), thumb the rounds down, strip the empty clip up and toss it; out to the
    # donor's hand-away f72. Two tag_weapon_left freezes: the full clip rides in landing exactly in the guides (f41),
    # the empty clip leaves from there (f47); between them the clip sits on the gun (torso coop_reload_c96).
    'c96': dict(donor='viewmodel/pistol/reload_p38.skc', idle='viewmodel/pistol/coltpose.skc', offhand=None, hand=[],
                gun=None, seam_in=4, seam_out=8, tagL=[(41, 28, 41), (47, 47, 56)],
                path=dict(side='L', grip=57, pre=(0, 12, (0, 0, 0)),
                          keys=[(12, (0, 0, 0)), (17, (-1.5, 0, 0)), (21, (-1.5, 0, 0)), (28, (1, -3, 6)),
                                (34, (1, -3, 6)), (41, (3.6, 0, -1.0)), (44, (3.6, 0, 0.6)), (47, (3.6, 0, 0.6)),
                                (51, (3.6, 0, -1.8)), (56, (2, -4, 5))], out=12, out_to=72)),
}


def path_offset(keys, f):
    for (fa, a), (fb, b) in zip(keys, keys[1:]):
        if fa <= f <= fb:
            w = ease((f - fa) / float(fb - fa))
            return np.array(a) * (1 - w) + np.array(b) * w
    return None


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def window_w(f, a, b, c, d):
    """0 before a, ramps a->b, 1 b..c, ramps c->d, 0 after d"""
    if f <= a or f >= d:
        return 0.0
    if f < b:
        return ease((f - a) / float(b - a))
    if f <= c:
        return 1.0
    return 1.0 - ease((f - c) / float(d - c))


# ---- group 8: belt-fed guns (M1919 .30 cal, MG42) - the cover opens on its own bone (beltgun.py) -------------------
# Donor: Lt. Pato's DP-28 reload (its left hand grips the pan ON TOP of the receiver at f27, palm down - the base
# orientation for working a top cover). Keys are left-hand positions in the gun frame relative to that grip (game units,
# x fwd, y right, z down), computed from each gun's cover latch, cover rear edge at 35 deg (the hand lifts it that far
# and lets it swing to 70 deg; closing, it catches it at 35 and presses it shut), belt end, and charging handle.
def _belt(latch, edge35, belt, away, charge, pulls):
    k = [(10, (latch[0], latch[1], latch[2] - 1.0)), (12, latch), (17, edge35), (20, (edge35[0], -2.0, edge35[2] - 0.7)),
         (28, belt), (30, belt), (36, away), (42, belt), (44, belt), (49, (edge35[0], -2.0, edge35[2] - 0.7)),
         (51, edge35), (56, latch), (58, latch)]
    f = 63
    back = (charge[0] - 4.0, charge[1], charge[2])
    k.append((f, charge))
    for _ in range(pulls):
        k += [(f + 3, back), (f + 6, charge)]
        f += 6
    k.append((f + 3, (charge[0] - 0.5, charge[1] - 1.0, charge[2] - 2.5)))
    pre = k[0][1]
    return dict(side='L', grip=27, pre=(2, 10, pre), keys=[(fr, tuple(np.array(v) - np.array(pre))) for fr, v in k],
                out=14, out_to=96)


RECIPES.update({
    # MG42: cock (the bolt must be back; here after closing, the common drill for a belt change on a hot gun is
    # cock - cover - belt - close; the handle is pulled once), belt from the LEFT, cover latch at the REAR.
    'mg42': dict(donor='viewmodel/coop_dp28/dp28_reload.skc', idle='viewmodel/mg/barpose.skc', offhand=None, hand=[],
                 gun=None, seam_in=8, seam_out=12, tagL=(30, 30, 44),
                 path=_belt((-3.9, 0.2, -0.9), (-1.76, 0.2, -5.27), (1.1, -4.5, 2.9), (1.1, -9.8, 6.8),
                            (-0.5, 2.8, 1.8), 1)),
    # M1919: belt laid in from the LEFT across the feed tray, cover closed, charging handle on the RIGHT pulled TWICE
    # (the first pull only grips the first round; the second chambers it).
    'm1919': dict(donor='viewmodel/coop_dp28/dp28_reload.skc', idle='viewmodel/mg/barpose.skc', offhand=None, hand=[],
                  gun=None, seam_in=8, seam_out=12, tagL=None,
                  path=_belt((-1.0, 0.2, -1.3), (1.57, 0.2, -7.87), (7.5, -5.8, 2.3), (6.5, -10.8, 6.8),
                             (3.5, 4.0, 1.3), 2)),
})

def build(name):
    rc = RECIPES[name]
    hip = R.load(A + rc['donor'])
    out = R.load(A + rc['donor'])
    cm = R.chanmap(out)
    idl = R.load(A + rc['idle'])
    pi = R.pose_dict(idl, 0)
    Wi = R.evaluate(pi)
    Gi = Wi['tag_weapon_right']
    relRi = Wi['Bip01 R Hand'] @ R.inv(Gi)
    relLi = Wi['Bip01 L Hand'] @ R.inv(Gi)
    n = hip.numFrames
    PATHREL = [None]
    rep = {'recipe': name, 'frames': []}

    def targets(f):
        pd = R.pose_dict(hip, f)
        W = R.evaluate(pd)
        lo, hi = rc['offhand'] if rc['offhand'] else (-1, -1)
        G = W['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right'].copy()
        relR = W['Bip01 R Hand'] @ R.inv(G)
        relL = W['Bip01 L Hand'] @ R.inv(G)
        pth = rc.get('path')
        if pth:
            keys = pth['keys']; g0 = pth['grip']; k0, k1 = keys[0][0], keys[-1][0]
            if PATHREL[0] is None:
                Wg = R.evaluate(R.pose_dict(hip, g0))
                PATHREL[0] = Wg['Bip01 %s Hand' % pth['side']] @ R.inv(Wg['tag_weapon_right'])
            pre = pth.get('pre')
            base = PATHREL[0]
            if pre:
                base = base @ B.H(np.eye(3), np.array(pre[2]) / R.S)
            cur = relL if pth['side'] == 'L' else relR
            if pre and f < k0:
                w = ease((f - pre[0]) / float(pre[1] - pre[0]))
                cur = B.blend_H(cur, base, w)
            elif k0 <= f <= k1:
                cur = base @ B.H(np.eye(3), path_offset(keys, f) / R.S)
            elif k1 < f <= k1 + pth['out']:
                tgt = cur
                if pth.get('out_to') is not None:      # blend to a FIXED donor frame (skips a donor excursion)
                    Wt = R.evaluate(R.pose_dict(hip, pth['out_to']))
                    tgt = Wt['Bip01 %s Hand' % pth['side']] @ R.inv(Wt['tag_weapon_right'])
                cur = B.blend_H(base @ B.H(np.eye(3), np.array(keys[-1][1]) / R.S), tgt, ease((f - k1) / float(pth['out'])))
            elif pth.get('out_to') is not None and k1 + pth['out'] < f < pth['out_to']:
                Wt = R.evaluate(R.pose_dict(hip, pth['out_to']))
                cur = Wt['Bip01 %s Hand' % pth['side']] @ R.inv(Wt['tag_weapon_right'])
            if pth['side'] == 'L':
                relL = cur
            else:
                relR = cur
        for side, ha, hb in rc.get('hold', []):
            if ha < f < hb:
                def rel_at(k):
                    Wk = R.evaluate(R.pose_dict(hip, k))
                    Gk = Wk['tag_weapon_left' if lo <= k <= hi else 'tag_weapon_right']
                    return Wk['Bip01 %s Hand' % side] @ R.inv(Gk)
                v = B.blend_H(rel_at(ha), rel_at(hb), ease((f - ha) / float(hb - ha)))
                if side == 'L':
                    relL = v
                else:
                    relR = v
        for side, a, b, c, d, off in rc['hand']:
            w = window_w(f, a, b, c, d)
            if w > 0:
                D = B.H(np.eye(3), np.array(off) / R.S * w)
                if side == 'L':
                    relL = relL @ D
                else:
                    relR = relR @ D
        if rc.get('gun'):
            a, b, c, d, off = rc['gun']
            w = window_w(f, a, b, c, d)
            G = B.H(np.eye(3), np.array(off) / R.S * w) @ G
        # seams: blend gun and hand relations toward the idle pose at the clip ends
        ws = 1.0
        if f < rc['seam_in']:
            ws = ease(f / float(rc['seam_in']))
        if f > n - 1 - rc['seam_out']:
            ws = min(ws, ease((n - 1 - f) / float(rc['seam_out'])))
        if ws < 1.0:
            G = B.blend_H(Gi, G, ws)
            relR = B.blend_H(relRi, relR, ws)
            relL = B.blend_H(relLi, relL, ws)
        HR = relR @ G
        HL = relL @ G
        return pd, W, G, HR, HL, ws

    # tag_weapon_left FREEZES: (grip frame, start, end) - over [start, end] the left-hand tag holds the gun transform of
    # the grip frame expressed in the hand, so a prop modelled in GUN space rides the hand and sits exactly where the
    # gun's part is at the grip frame (start may precede the grip frame: a prop carried IN that lands there).
    tl = rc.get('tagL')
    wins = [tl] if (tl and not isinstance(tl[0], (tuple, list))) else (tl or [])
    freezes = []
    for gf, ta, tb in wins:
        _, _, Gg, _, HLg, _ = targets(gf)
        freezes.append((ta, tb, Gg @ R.inv(HLg)))
    for f in range(n):
        pd, W, G, HR, HL, ws = targets(f)
        K.solve_arms(pd, W, HR, HL, G)
        for ta, tb, T in freezes:
            if ta <= f <= tb:
                pd['tag_weapon_left rot'] = R.rows_to_quat(T[0:3, 0:3])
                pd['tag_weapon_left pos'] = np.array([T[3, 0], T[3, 1], T[3, 2], 0.0])
        K.write_frame(out, hip, cm, f, pd)
        Wn = R.evaluate(pd)
        err = max(float(np.linalg.norm((Wn['Bip01 R Hand'][3, 0:3] - HR[3, 0:3]) * R.S)),
                  float(np.linalg.norm((Wn['Bip01 L Hand'][3, 0:3] - HL[3, 0:3]) * R.S)))
        rep['frames'].append({'f': f, 'seam_w': round(ws, 3), 'ik_err_u': round(err, 3)})
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(n)]
    return out, rep


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


if __name__ == '__main__':
    main()
