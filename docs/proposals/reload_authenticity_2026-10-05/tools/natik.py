"""natik.py - anatomical two-bone arm IK for keyclip.py (user feedback 2026-10-05: 'hands bending all weird').

The ads_bolt solve_arms aligned each arm bone with a minimal rotation from the idle pose, which leaves the forearm with
an off-hinge rotation (retail clips: 0 deg, ours up to 90 deg - the elbow bends sideways) and dumps whatever is left into
the wrist. Here:
  * the ELBOW IS A HINGE: upper arm and forearm share their z axis (the rig's bend axis, measured on retail clips), the
    forearm's local rotation is about z only; the upper arm's twist follows from the arm plane;
  * the elbow's SWIVEL around the shoulder-wrist line is chosen for the whole clip at once (Viterbi over a 72-step grid)
    to keep the wrist inside its range (flexion / extension / deviation, jointqa.py's measure), the elbow near its idle
    direction (down and out), and the swivel smooth frame to frame;
  * hand rotation = the keyed hand-to-gun rotation (unchanged), so contacts are exact.
"""
import math
import numpy as np


def unit(v):
    return v / np.linalg.norm(v)


# wrist window (deg) in jointqa.arm_angles' measure. Centre = the middle of the range retail reload clips use (BAR, Thompson,
# MP40, Kar98 hands: flex -67..44, dev -44..80 -> centre -12 / 18); half-widths = the user's anatomical limits (70 flexion,
# 60 extension; deviation 30, widened to 40 because this measure mixes some pronation into it)
FLEX_C, DEV_C = -12.0, 18.0
LAG_ALPHA = 0.55
PRON_W = 6.0      # Viterbi: cost per deg^2 of forearm twist beyond 12 deg / frame
FLEX_RANGE = (FLEX_C - 60.0, FLEX_C + 70.0)
DEV_RANGE = (DEV_C - 40.0, DEV_C + 40.0)


def wrist_angles(fd, HT, kn_local):
    """fd = forearm direction (world), HT = hand world matrix (rows = axes, row 3 = origin), kn_local = knuckle centroid
    in hand-local coordinates -> (flex, dev) as jointqa.arm_angles"""
    kn = kn_local @ HT[0:3, 0:3] + HT[3, 0:3]
    hx = unit(kn - HT[3, 0:3]); hy = unit(HT[1, 0:3]); hy = unit(hy - (hy @ hx) * hx); hz = np.cross(hx, hy)
    return math.degrees(math.atan2(-(fd @ hy), fd @ hx)), math.degrees(math.atan2(-(fd @ hz), fd @ hx))


def over(v, lo, hi):
    return max(0.0, lo - v, v - hi)


class Arm:
    def __init__(self, R, Wi, side):
        self.R = R; self.s = side
        self.eye = Wi['eyes bone'][3, 0:3].copy()     # the camera (model +x = view axis): elbows stay out of the picture
        self.up0 = (Wi['Bip01 %s Forearm' % side][3, 2] - Wi['Bip01 %s UpperArm' % side][3, 2]) * R.S   # idle elbow height
        U, Fo, Hd = ('Bip01 %s UpperArm' % side, 'Bip01 %s Forearm' % side, 'Bip01 %s Hand' % side)
        self.names = (U, Fo, Hd, 'Bip01 %s Clavicle' % side)
        self.S = Wi[U][3, 0:3].copy()
        E, Wp = Wi[Fo][3, 0:3], Wi[Hd][3, 0:3]
        self.la, self.lb = np.linalg.norm(E - self.S), np.linalg.norm(Wp - E)
        # hinge sign: the idle arm's plane normal vs its upper-arm z
        n0 = np.cross(E - self.S, Wp - E)
        self.sgn = 1.0 if n0 @ Wi[U][2, 0:3] >= 0 else -1.0
        self.pole0 = unit((E - self.S) - ((E - self.S) @ unit(Wp - self.S)) * unit(Wp - self.S))
        kn = np.mean([Wi['Bip01 %s Finger%d' % (side, k)][3, 0:3] for k in (1, 2, 3)], axis=0)
        H = Wi[Hd]
        self.kn_local = (kn - H[3, 0:3]) @ np.linalg.inv(H[0:3, 0:3])
        # the right hand's rig axes are mirrored: its deviation window is the left one mirrored (retail: L dev -44..80,
        # R dev -53..0 on the SMG grips)
        self.dev_range = DEV_RANGE if side == 'L' else (-DEV_RANGE[1] - 4.0, -DEV_RANGE[0])   # R: retail grips reach -59
        # the idle wrist: an artist's idle that is itself outside the window is not 'fixed' by moving the elbow (the
        # clip must start and end on the idle exactly) - the cost only counts going FURTHER out than the idle
        fl0, dv0 = wrist_angles(unit(Wp - E), H, self.kn_local)
        self.idle_over = (over(fl0, *FLEX_RANGE), over(dv0, *self.dev_range))
        # constant bone-axis corrections so that swivel 0 at the idle wrist reproduces the idle arm EXACTLY (the rig's
        # bone x is not exactly along the joint line, nor its z exactly on the arm-plane normal): actual = c @ ik
        self.cu = self.cf = np.eye(3)
        xu, xf, z = self.frames(Wp, E)
        Uk = np.stack([xu, np.cross(z, xu), z]); Fk = np.stack([xf, np.cross(z, xf), z])
        nrm = lambda M: M / np.linalg.norm(M, axis=1)[:, None]
        self.cu = nrm(Wi[U][0:3, 0:3]) @ Uk.T
        self.cf = nrm(Wi[Fo][0:3, 0:3]) @ Fk.T
        # bone-axis lengths (row norms carry the rig scale)
        self.su = np.linalg.norm(Wi[U][0:3, 0:3], axis=1); self.sf = np.linalg.norm(Wi[Fo][0:3, 0:3], axis=1)

    def circle(self, Wt):
        d = Wt - self.S; dist = np.linalg.norm(d)
        reach = self.la + self.lb - 1e-3
        if dist > reach:
            Wt = self.S + d / dist * reach; dist = reach
        dh = d / np.linalg.norm(d)
        x = (self.la ** 2 - self.lb ** 2 + dist ** 2) / (2 * dist); h = math.sqrt(max(0.0, self.la ** 2 - x ** 2))
        u = unit(self.pole0 - (self.pole0 @ dh) * dh)
        v = np.cross(dh, u)
        return Wt, self.S + dh * x, h, u, v

    def elbow(self, Wt, phi):
        Wt, C, h, u, v = self.circle(Wt)
        return Wt, C + h * (math.cos(phi) * u + math.sin(phi) * v)

    def frames(self, Wt, E):
        xu = unit(E - self.S); xf = unit(Wt - E)
        z = np.cross(E - self.S, Wt - E)
        z = unit(z) * self.sgn if np.linalg.norm(z) > 1e-6 else None
        return xu, xf, z

    def on_screen(self, P):
        v = P - self.eye
        return v[0] > 0 and abs(math.degrees(math.atan2(v[1], v[0]))) < 50 and abs(math.degrees(math.atan2(v[2], v[0]))) < 36

    def pron(self, Wt, HT, phi):
        """forearm pronation (deg) as jointqa measures it: hand z across the forearm vs the hinge axis"""
        Wt, E = self.elbow(Wt, phi)
        fd = unit(Wt - E); _, _, z = self.frames(Wt, E)
        if z is None:
            return 0.0
        fz = unit((self.cf @ np.stack([fd, np.cross(z, fd), z]))[2])     # the forearm's world z (as applied)
        kn = self.kn_local @ HT[0:3, 0:3] + HT[3, 0:3]
        hx = unit(kn - HT[3, 0:3]); hy = unit(HT[1, 0:3]); hy = unit(hy - (hy @ hx) * hx); hz = np.cross(hx, hy)
        pz = hz - (hz @ fd) * fd
        if np.linalg.norm(pz) < 1e-6:
            return 0.0
        pz = unit(pz)
        return math.degrees(math.atan2(np.cross(fz, pz) @ fd, fz @ pz))

    def cost(self, Wt, HT, phi, at_idle=False):
        Wt, E = self.elbow(Wt, phi)
        fl, dv = wrist_angles(unit(Wt - E), HT, self.kn_local)
        if self.on_screen(Wt):     # a wrist the player can see is held to the window absolutely
            c = over(fl, *FLEX_RANGE) ** 2 + over(dv, *self.dev_range) ** 2
        else:                      # off screen (e.g. the MG idles' right hand under the camera): no worse than its idle
            c = max(0.0, over(fl, *FLEX_RANGE) - self.idle_over[0]) ** 2 + max(0.0, over(dv, *self.dev_range) - self.idle_over[1]) ** 2
        # preference for the idle elbow direction (down / out) - strong while the hand is on its idle grip, so the clip
        # starts and ends on the idle arm - and a mild one for a mid-range wrist
        dc = sum(self.dev_range) / 2.0
        # keep the elbow and the upper arm OUT OF THE VIEW (rb6: the right upper arm swung up into the picture as a
        # sleeve slab): penalise any of them inside a 55 deg cone around the view axis, in front of the eye
        # rb6 in engine: the swivel chose an elbow-UP arm (elbow above and behind the head, forearm sleeve sweeping past
        # the camera) - so also: the elbow stays below the shoulder, and no arm point comes within 8 u of the eye (rb6: 3 u)
        for P in (E, (E + self.S) * 0.5, E * 0.7 + Wt * 0.3, E * 0.4 + Wt * 0.6):
            v = P - self.eye
            dist = np.linalg.norm(v) * self.R.S
            if dist < 8.0:
                c += 400.0 * (8.0 - dist) ** 2
            if v[0] > 0 and self.s == 'R':     # the gun hand's arm stays out of the picture (the left one works in it)
                ang = math.degrees(math.atan2(math.hypot(v[1], v[2]), v[0]))
                if ang < 55.0:
                    c += 50.0 * (55.0 - ang) ** 2
        up = (E[2] - self.S[2]) * self.R.S - max(-1.0, self.up0) - 3.0   # not raised above the idle elbow / shoulder
        if up > 0 and self.s == 'R':
            c += 2000.0 * up ** 2
        c += (1e6 if at_idle else 40.0) * (1 - math.cos(phi)) + 0.02 * ((fl - FLEX_C) ** 2 + (dv - dc) ** 2)
        return c

    def solve_track(self, targets, n_phi=72, smooth=1500.0):
        """targets = [(Wt, HT, at_idle)] per frame -> swivel per frame (Viterbi: per-frame cost + smooth * dphi^2)"""
        phis = np.linspace(-math.pi, math.pi, n_phi, endpoint=False)
        n = len(targets)
        C = np.array([[self.cost(Wt, HT, p, ai) for p in phis] for Wt, HT, ai in targets])
        Pr = np.array([[self.pron(Wt, HT, p) for p in phis] for Wt, HT, ai in targets])   # forearm twist per swivel
        D = phis[:, None] - phis[None, :]
        D = (D + math.pi) % (2 * math.pi) - math.pi
        T = smooth * D ** 2
        acc = C[0].copy(); back = np.zeros((n, n_phi), int)
        for f in range(1, n):
            dP = (Pr[f][:, None] - Pr[f - 1][None, :] + 180.0) % 360.0 - 180.0
            tot = acc[None, :] + T + PRON_W * np.maximum(0.0, np.abs(dP) - 12.0) ** 2   # [to, from]: no forearm flips
            back[f] = tot.argmin(axis=1)
            acc = tot.min(axis=1) + C[f]
        path = [int(acc.argmin())]
        for f in range(n - 1, 0, -1):
            path.append(back[f][path[-1]])
        path = path[::-1]
        ph = np.unwrap(phis[path])
        # light smoothing of the grid quantisation (5 deg steps)
        k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
        pp = np.pad(ph, 2, mode='edge')
        sm = np.convolve(pp, k, mode='valid')
        idle = np.array([t[2] for t in targets])
        # OVERLAP (polish): the elbow follows the hand a frame or so behind - an exponential follower on the swivel
        # (LAG_ALPHA per frame), handed back to the exact path over the last 8 frames before the trailing idle
        x, al = sm[0], LAG_ALPHA
        fol = np.zeros(n)
        for f in range(n):
            x += al * (sm[f] - x); fol[f] = x
        last = n - 1
        while last > 0 and idle[last]:
            last -= 1
        wend = np.clip((np.arange(n) - (last - 8)) / 8.0, 0, 1)
        fol = fol * (1 - wend) + sm * wend
        return np.where(idle, ph, fol)      # on the idle grip: exactly the grid value (0 = the idle elbow)

    def apply(self, pd, Wb, Wt, HT, phi):
        """write upper arm / forearm / hand local rotations (the clavicle stays as it is in pd)"""
        R = self.R
        U, Fo, Hd, Cl = self.names
        Wt, E = self.elbow(Wt, phi)
        xu, xf, z = self.frames(Wt, E)
        if z is None:
            z = unit(Wb[U][2, 0:3])
        Uw = self.cu @ np.stack([xu, np.cross(z, xu), z]); Fw = self.cf @ np.stack([xf, np.cross(z, xf), z])
        par = Wb[Cl][0:3, 0:3]
        parn = par / np.linalg.norm(par, axis=1)[:, None]
        pd[U + ' rot'] = R.rows_to_quat(Uw @ parn.T)
        pd[Fo + ' rot'] = R.rows_to_quat(Fw @ Uw.T)
        Hn = HT[0:3, 0:3] / np.linalg.norm(HT[0:3, 0:3], axis=1)[:, None]
        pd[Hd + ' rot'] = R.rows_to_quat(Hn @ Fw.T)
        return E
