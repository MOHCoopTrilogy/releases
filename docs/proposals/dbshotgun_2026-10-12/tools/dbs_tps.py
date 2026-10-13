"""THIRD-PERSON torso clips for the double barrel: the pump gun's own clips with the PUMP STROKE taken out.

    python tools/dbs_tps.py        -> assets/models/human/animation/viewmodel/coop_dbshotgun/coop_dbs_tps_*.skc

Other players see the shared shotgun torso rows (models/player/base/anims_shotgun.txt): `shotgun_stand_fire`
(tps_fire_shotgun_idle.skc, 36 frames) and `shotgun_crouch_fire` (tps_fire_shotgun_stand.skc, 35) work the pump after
every shot - the left hand slides 6.5 u back and forward - and `shotgun_reload_end` (tps_reload_end.skc, 36) pumps a
round in after the last shell. This gun has no pump. Smallest correct change: three clips that are those clips frame
for frame (every channel, same frame count and frame time - so the server's timing, which runs on the torso
animation, does not change) with the LEFT ARM re-solved so the hand stays on the forend where the clip's rest pose
has it, riding the gun through the recoil:
    coop_dbs_tps_fire.skc           from tps_fire_shotgun_idle.skc    hand held on the forend for the whole clip
    coop_dbs_tps_fire_crouch.skc    from tps_fire_shotgun_stand.skc   the same
    coop_dbs_tps_reload_end.skc     from tps_reload_end.skc           the hand comes back to the forend as in the retail
                                                                      clip (frames 0-9) and STAYS (retail: pump 12-24)
The running fire rows already use rifle clips without a pump (fire_rifle_trot.skc, rifle_fire_crouch.skc); the start
and the per-shell rows are kept (a hand feeding shells in at the breech reads right from outside, and the gun's own
model shows the barrels dropped: the weapon tik's reload rows play for everyone).
Aliases: rows/tps_rows_coop_dbshotgun.txt; state rows: wiring/patch_torso_dbs.py.
"""
import os, sys, io, contextlib
import numpy as np
import dbslib as L
import dbs_skx as X
import dbs_rig as D

R, K, B = D.R, D.K, D.B
ODIR = os.path.join(L.ASSETS, 'models', 'human', 'animation', 'viewmodel', 'coop_dbshotgun')
JOBS = [  # out, source, reference frame of the hand-on-forend relation, frame the hold starts, frames of blend into it
    ('coop_dbs_tps_fire', 'viewmodel/shotgun/tps_fire_shotgun_idle.skc', 0, 0, 0),
    ('coop_dbs_tps_fire_crouch', 'viewmodel/shotgun/tps_fire_shotgun_stand.skc', 0, 0, 0),
    ('coop_dbs_tps_reload_end', 'viewmodel/shotgun/tps_reload_end.skc', -1, 8, 3),
]


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lh_x(W):
    return D.in_gun(W['tag_weapon_right'], W['Bip01 L Hand'][3, 0:3])


def main():
    os.makedirs(ODIR, exist_ok=True)
    for out, src, ref, f0, nb in JOBS:
        a = R.load(R.ANIM + src)
        n = a.numFrames
        Wr = R.evaluate(R.pose_dict(a, ref % n))
        HLrel = Wr['Bip01 L Hand'] @ R.inv(Wr['tag_weapon_right'])
        vals = []; xs0 = []; xs1 = []; clamps = 0
        for f in range(n):
            pd = R.pose_dict(a, f)
            W = R.evaluate(pd)
            xs0.append(lh_x(W)[0])
            w = 1.0 if nb == 0 and f >= f0 else ease((f - f0) / float(max(1, nb)))
            if w > 0:
                G = W['tag_weapon_right']
                HL = B.blend_H(W['Bip01 L Hand'], HLrel @ G, w)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    K.solve_arms(pd, W, W['Bip01 R Hand'], HL, G)
                clamps += buf.getvalue().count('IK clamp')
            xs1.append(lh_x(R.evaluate(pd))[0])
            row = []
            for c, nm in enumerate(a.names):
                v = np.asarray(pd[nm], float)
                if nm.endswith(' pos'):
                    v = np.array([v[0], v[1], v[2], 0.0])
                elif vals and float(v @ np.asarray(vals[-1][c])) < 0:
                    v = -v
                row.append(tuple(v))
            vals.append(row)
        b = a.frames[0]['bounds']
        data = X.build_skc(a.names, vals, a.frameTime, b[0:3], b[3:6], a.frames[0]['radius'])
        open(os.path.join(ODIR, out + '.skc'), 'wb').write(data)
        print('%-26s %2d frames, %d channels, IK clamps %d; left hand along the gun: retail %.1f..%.1f u, now %.1f..%.1f u (from frame %d)' % (
            out, n, len(a.names), clamps, min(xs0), max(xs0), min(xs1[f0 + nb:]), max(xs1[f0 + nb:]), f0 + nb))


if __name__ == '__main__':
    main()
