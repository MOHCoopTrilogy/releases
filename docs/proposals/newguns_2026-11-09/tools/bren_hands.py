"""The Bren's own reload HANDS: the Vickers-Berthier's three view reload clips (calm / stressed / fumbled) with the right hand
retargeted onto the Bren's magazine. The Bren is rigged on the VB's bones, but its magazine well sits ~5.7 u further back
(and lower) than the VB's, so on the VB's clips the hand closed on air ahead of the Bren magazine it was carrying.

Per frame, in the GUN frame (the gun is on tag_weapon_left for the whole reload - anims_vickers.txt `attachtohand offhand`
entry .. last): the right hand's world matrix is moved by D * w(f), where D = the Bren magazine's centroid minus the VB
magazine prop's centroid at the swap frames (19 / 51, measured by probe3.py), and w eases 0 -> 1 while the hand rises off
the pistol grip to the old magazine and 1 -> 0 while it leaves the new one for the cocking handle. The right arm is re-solved
by the same analytic two-bone IK the ADS lanes use (key_bolt.solve_arms, right side only). tag_weapon_right keeps its LOCAL
channel, so the magazine prop rides the moved hand; build_bren_clip.py then re-places the prop mesh against the new clip.
The left arm, the body, the eyes and both tags' local channels are untouched; frame count / frame time are the VB's
(the server's reload timing is the shared Vickers state).

    python bren_hands.py <out dir>            -> coop_bren_reload_fps.skc, coop_bren_reload_fps_s.skc, coop_bren_reload_fps_m.skc
"""
import sys, os, math
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa: E402
import key_bolt as KB  # noqa: E402
os.chdir(_c)
import numpy as np  # noqa: E402
R = V.R; S = R.S; B = KB.B

VM = 'models/human/animation/viewmodel/Vickers/'
D = np.array([-5.65, 0.3, 1.2])          # gun frame (+x muzzle, +y right, +z down), game units; z halved from the 2.35
                                         # centroid delta: the hand holds a magazine by its top half, and the Bren's is shorter
# clip -> (ramp in f0, f1), (ramp out f0, f1): the hand leaves the grip ~f3 and is on the old magazine by the pull;
# it leaves the seated magazine for the cocking handle after the insert (probe.py hand paths)
CLIPS = {'A_W_Vickers_reload_fps.skc': ('coop_bren_reload_fps.skc', (3, 12), (54, 62)),
         'coop_A_W_Vickers_reload_fps_s.skc': ('coop_bren_reload_fps_s.skc', (3, 10), (42, 49)),
         'coop_A_W_Vickers_reload_fps_m.skc': ('coop_bren_reload_fps_m.skc', (3, 10), (54, 61))}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def weight(f, rin, rout):
    if f <= rin[0] or f >= rout[1]:
        return 0.0
    if f < rin[1]:
        return ease((f - rin[0]) / float(rin[1] - rin[0]))
    if f > rout[0]:
        return ease((rout[1] - f) / float(rout[1] - rout[0]))
    return 1.0


def solve_right(pd, Wc, HT):
    """key_bolt.solve_arms, right arm only, tags untouched (the prop on tag_weapon_right follows the hand)"""
    Wb = R.evaluate(pd)
    U, Fo, Hd, Cl = 'Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand', 'Bip01 R Clavicle'
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


def bake(src, rin, rout):
    hip = R.load(VM + src)
    out = R.load(VM + src)
    cm = R.chanmap(out)
    worst = 0.0
    for f in range(hip.numFrames):
        w = weight(f, rin, rout)
        if w <= 0.0:
            continue
        pd = R.pose_dict(hip, f)
        Wc = R.evaluate(pd)
        G = Wc['tag_weapon_left']
        HT = Wc['Bip01 R Hand'].copy()
        HT[3, 0:3] = HT[3, 0:3] + (w * D) @ G[0:3, 0:3] / S
        if solve_right(pd, Wc, HT):
            print('  IK clamp f%d' % f)
        # verify: the solved hand lands where asked
        W2 = R.evaluate(pd)
        err = np.abs(W2['Bip01 R Hand'][3, 0:3] - HT[3, 0:3]).max() * S
        worst = max(worst, err)
        KB.write_frame(out, hip, cm, f, pd)
    # first and last frames must be bit-identical to the VB's (the hand is on the grip at both ends)
    assert np.array_equal(out.V[0], hip.V[0]) and np.array_equal(out.V[-1], hip.V[-1])
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(out.numFrames)]
    return out, worst


def main():
    od = sys.argv[1]
    os.makedirs(od, exist_ok=True)
    for src, (dst, rin, rout) in CLIPS.items():
        out, worst = bake(src, rin, rout)
        data = R.skc_io.write(out)
        open(os.path.join(od, dst), 'wb').write(data)
        print('wrote', dst, out.numFrames, 'frames, hand error max %.4f u' % worst)


if __name__ == '__main__':
    main()
