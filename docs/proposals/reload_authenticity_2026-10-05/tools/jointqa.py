"""jointqa.py - joint-limit QA for first-person clips (reload authenticity polish, user feedback 'hands bending all weird').

Per frame and side, from the LOCAL bone rotations of the biped rig (Bip01: x along the bone, z the bend axis):
  wrist  = Hand relative to Forearm: swing-twist about x -> twist (forearm 'candy-wrap'), swing split into flex/ext
           (about z) and radial/ulnar deviation (about y)
  elbow  = Forearm relative to UpperArm: bend about z and the off-hinge part
  finger = every finger bone: bend about z (sign = curl direction) and off-hinge part
Angles are reported RELATIVE TO THE GUN'S IDLE POSE (its wrist is the neutral the artist set), so a clip is judged by how
far it goes from a natural hold.  python jointqa.py <clip> [--idle <clip>] [--json out]
"""
import sys, os, math, json, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyclip as KC
R = KC.R

FING = ['Finger%d%s' % (i, k) for i in range(5) for k in ('', '1', '2')]


def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])


def qinv(q):
    return np.array([-q[0], -q[1], -q[2], q[3]]) / float(np.dot(q, q))


def swing_twist(q):
    """q = swing * twist, twist about x. -> twist deg, swing about y deg, swing about z deg"""
    q = q / np.linalg.norm(q)
    if q[3] < 0:
        q = -q
    tw = np.array([q[0], 0, 0, q[3]]); n = np.linalg.norm(tw)
    tw = tw / n if n > 1e-9 else np.array([0, 0, 0, 1.0])
    sw = qmul(q, qinv(tw))
    twist = math.degrees(2 * math.atan2(tw[0], tw[3]))
    # swing has no x component: rotation vector (0, ry, rz)
    ang = 2 * math.acos(max(-1.0, min(1.0, sw[3])))
    s = math.sin(ang / 2)
    axis = sw[0:3] / s if s > 1e-9 else np.zeros(3)
    return twist, math.degrees(ang * axis[1]), math.degrees(ang * axis[2])


def rel(pd, ch, neutral):
    if neutral is None:          # anatomical: the bone's local rotation itself (identity = in line with its parent)
        return np.asarray(pd[ch], float)
    return qmul(qinv(np.asarray(neutral[ch], float)), np.asarray(pd[ch], float))


def unit(v):
    return v / np.linalg.norm(v)


def arm_angles(W, s):
    """geometric, convention-light wrist / elbow / finger angles of one arm (world matrices W, rows = axes)"""
    U, F, H = W['Bip01 %s UpperArm' % s], W['Bip01 %s Forearm' % s], W['Bip01 %s Hand' % s]
    up = unit(F[3, 0:3] - U[3, 0:3]); fd = unit(H[3, 0:3] - F[3, 0:3])
    # hand frame from the skin points, not the bone axes (the rig's hand bone x is not along the metacarpals):
    # hx = wrist -> middle of the index/middle/ring knuckles, hy = palm normal (the side the fingers curl to: bone +y,
    # measured), hz = hx x hy
    kn = np.mean([W['Bip01 %s Finger%d' % (s, k)][3, 0:3] for k in (1, 2, 3)], axis=0)
    hx = unit(kn - H[3, 0:3]); hy = unit(H[1, 0:3]); hy = unit(hy - (hy @ hx) * hx); hz = np.cross(hx, hy)
    flex = math.degrees(math.atan2(-(fd @ hy), fd @ hx))                 # + = toward the palm (flexion)
    dev = math.degrees(math.atan2(-(fd @ hz), fd @ hx))
    # pronation: the hand's z projected across the forearm vs the elbow hinge axis (forearm z), signed about the forearm
    fz = unit(F[2, 0:3]); pz = hz - (hz @ fd) * fd
    pron = math.degrees(math.atan2(np.cross(fz, unit(pz)) @ fd, fz @ unit(pz))) if np.linalg.norm(pz) > 1e-6 else 0.0
    elbow = math.degrees(math.acos(max(-1.0, min(1.0, up @ fd))))
    hinge_off = math.degrees(math.acos(max(-1.0, min(1.0, abs(unit(U[2, 0:3]) @ fz)))))
    back, side = 0.0, 0.0
    for k in range(1, 5):
        a, b, c = W['Bip01 %s Finger%d' % (s, k)][3, 0:3], W['Bip01 %s Finger%d1' % (s, k)][3, 0:3], W['Bip01 %s Finger%d2' % (s, k)][3, 0:3]
        for p_, q_ in ((hx, b - a), (b - a, c - b)):
            p_, q_ = unit(p_), unit(q_)
            ax = np.cross(p_, q_); ang = math.degrees(math.asin(max(-1.0, min(1.0, np.linalg.norm(ax)))))
            if np.linalg.norm(ax) > 1e-6:
                ax = unit(ax)
                inward = ax @ hz                     # curl toward the palm = rotation about +hand z
                back = max(back, -ang * inward)      # bending backwards
                side = max(side, ang * math.sqrt(max(0.0, 1 - inward * inward)))   # sideways (off the curl plane)
    # on screen? (weapon view ~90 x 60 deg; a little margin): hand, wrist end of the forearm or the knuckles in the frustum
    Eye = W['eyes bone'][3, 0:3]; vis = False
    for P in (H[3, 0:3], kn, F[3, 0:3] * 0.3 + H[3, 0:3] * 0.7):
        v = P - Eye
        if v[0] > 0 and abs(math.degrees(math.atan2(v[1], v[0]))) < 50 and abs(math.degrees(math.atan2(v[2], v[0]))) < 36:
            vis = True
    return dict(vis=vis, flex=round(flex, 1), dev=round(dev, 1), pron=round(pron, 1), elbow=round(elbow, 1),
                hinge_off=round(hinge_off, 1), finger_back=round(back, 1), finger_side=round(side, 1))


def analyse(clip, idle=None):
    c = R.load(KC.ap(clip))
    out = []
    for f in range(c.numFrames):
        W = R.evaluate(R.pose_dict(c, f))
        out.append(dict(f=f, L=arm_angles(W, 'L'), R=arm_angles(W, 'R')))
    return out


# wrist window = natik.py's (centre of the retail reload range, half-widths = the user's anatomical limits 70 flexion /
# 60 extension / deviation 30 widened to 40); retail elbows are pure hinges (off-hinge 0); pronation is judged by its
# frame-to-frame change (a forearm 'candy-wrap' shows as a jump), retail fingers bend sideways up to ~35 deg
import natik as _N   # noqa: E402
LIMITS = dict(flex=_N.FLEX_RANGE, dev=_N.DEV_RANGE, dev_R=(-_N.DEV_RANGE[1] - 4.0, -_N.DEV_RANGE[0]), pron_step=25.0, elbow=(0.0, 160.0), hinge_off=5.0, finger_back=15.0,
              finger_side=35.0)


def violations(rows, sides='LR', lim=None, visible_only=True):
    """frames over the limits WHILE THE HAND IS ON SCREEN (an off-screen wrist - e.g. the MG idles' right hand, 7 u
    under the camera - is not judged)"""
    L = dict(LIMITS, **(lim or {}))
    bad = []
    prev = {}
    for r in rows:
        for s in sides:
            j = r[s]; why = []
            # a wrist judged against the window, but not for being as far out as the gun's own idle (frame 0) already is
            dr = L['dev'] if s == 'L' else L['dev_R']
            if not L['flex'][0] <= j['flex'] <= L['flex'][1]:
                why.append('flex %.0f' % j['flex'])
            if not dr[0] <= j['dev'] <= dr[1]:
                why.append('dev %.0f' % j['dev'])
            if s in prev:
                d = (j['pron'] - prev[s] + 180) % 360 - 180
                if abs(d) > L['pron_step']:
                    why.append('pronation jump %.0f' % d)
            prev[s] = j['pron']
            if not L['elbow'][0] <= j['elbow'] <= L['elbow'][1]:
                why.append('elbow %.0f' % j['elbow'])
            if j['hinge_off'] > L['hinge_off']:
                why.append('elbow off-hinge %.0f' % j['hinge_off'])
            if j['finger_back'] > L['finger_back']:
                why.append('finger back %.0f' % j['finger_back'])
            if j['finger_side'] > L['finger_side']:
                why.append('finger side %.0f' % j['finger_side'])
            if why and (j.get('vis', True) or not visible_only):
                bad.append((r['f'], s, why))
    return bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('clips', nargs='+'); ap.add_argument('--idle'); ap.add_argument('--rows', action='store_true')
    a = ap.parse_args()
    for cl in a.clips:
        rows = analyse(cl, a.idle or 'abs')
        mx = {s: {k: (min(r[s][k] for r in rows), max(r[s][k] for r in rows)) for k in rows[0][s] if k != 'vis'} for s in 'LR'}
        bad = violations(rows)
        alln = len(set(b[0] for b in violations(rows, visible_only=False)))
        print('%s: %d frames, %d over limits on screen (%d incl. off-screen)' % (cl[-50:], len(rows), len(set(b[0] for b in bad)), alln))
        for s in 'LR':
            print('   %s ' % s + '  '.join('%s %.0f..%.0f' % (k, v[0], v[1]) for k, v in mx[s].items()))
        if a.rows:
            for b in bad[:40]:
                print('     f%d %s %s' % b)
