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
}


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
    TAGL = [None]
    rep = {'recipe': name, 'frames': []}
    for f in range(n):
        pd = R.pose_dict(hip, f)
        W = R.evaluate(pd)
        lo, hi = rc['offhand'] if rc['offhand'] else (-1, -1)
        G = W['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right'].copy()
        relR = W['Bip01 R Hand'] @ R.inv(G)
        relL = W['Bip01 L Hand'] @ R.inv(G)
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
        K.solve_arms(pd, W, HR, HL, G)
        if rc.get('tagL'):
            gf, ta, tb = rc['tagL']
            if f == gf:
                TAGL[0] = G @ R.inv(HL)
            if ta <= f <= tb and TAGL[0] is not None:
                pd['tag_weapon_left rot'] = R.rows_to_quat(TAGL[0][0:3, 0:3])
                pd['tag_weapon_left pos'] = np.array([TAGL[0][3, 0], TAGL[0][3, 1], TAGL[0][3, 2], 0.0])
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
