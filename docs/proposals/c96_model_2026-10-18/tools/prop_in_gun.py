"""Where does the server's stripper-clip prop stand in the GUN's raw frame at a given hands-clip frame (offline, c96view scene)?
Fits the rigid map raw -> viewmodel world from the origin-bone surfaces, then maps the prop's bbox back.
    IRONSIGHT_EXTRA_PAKS=<ov.pk3> python prop_in_gun.py <hands clip> <gun anim> <frame> [<frame> ...]
"""
import sys, os
import numpy as np
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\tools')
sys.path.insert(1, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import c96view as CV
import skdlib as S
V, R = CV.V, CV.R
SKD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ship', 'models', 'weapons', 'coop_c96n', 'c96n.skd')


def main():
    clip, anim = sys.argv[1], sys.argv[2]
    frames = [int(x) for x in sys.argv[3:]]
    aimp = 'models/human/animation/viewmodel/pistol/coop_c96_ads2h.skc'
    aim = R.load(aimp); sight = V.SIGHTS['mauser_c96']
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CV.CTL), sight)
    c = R.load(clip)
    m = S.read_skd(open(SKD, 'rb').read())
    raw = {s.name: np.array([v[2][0][2] for v in s.verts]) for s in m.surfaces if all(v[2][0][0] == 0 for v in s.verts)}
    for f in frames:
        surfs, E = CV.scene(R.pose_dict(c, f), 'mauser_c96', sight['tik'], anim, f * c.frameTime, corr, True)
        X, Y, props = [], [], []
        for s in surfs:
            if s.get('gun') and s['name'] in raw and len(s['P']) == len(raw[s['name']]):
                X.append(np.c_[raw[s['name']], np.ones(len(s['P']))]); Y.append(s['P'])
            elif s.get('gun') and s['name'].startswith('prop_'):
                props.append(s['P'])
        if not X:
            print('f%d: no gun surfaces matched (names %s)' % (f, [s['name'] for s in surfs if s.get('gun')][:6])); continue
        X = np.vstack(X); Y = np.vstack(Y)
        M, *_ = np.linalg.lstsq(X, Y, rcond=None)
        err = np.abs(X @ M - Y).max()
        A, t = M[:3], M[3]
        Ai = np.linalg.inv(A)
        print('f%d fit err %.4f scale %.3f' % (f, err, np.linalg.norm(A[0])))
        for P in props:
            Q = (P - t) @ Ai
            print('   prop bbox raw  min %s max %s  centre %s' % (np.round(Q.min(0), 1), np.round(Q.max(0), 1), np.round((Q.min(0) + Q.max(0)) / 2, 1)))


if __name__ == '__main__':
    main()
