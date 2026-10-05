import sys
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import vfs, gungeo, skdlib, numpy as np
for tik in sys.argv[1:]:
    t = gungeo.parse_tik(tik); cp = gungeo._res(t, t['anims']['reload'])
    a = skdlib.read_skc(vfs.read(cp)); nf = a.numFrames
    g0 = gungeo.load_gun(tik, anim='reload', frame=0)
    mats0 = None
    # bone motion: compare bone world positions across frames
    skd = skdlib.read_skd(vfs.read(gungeo._res(t, t['skel'][0])))
    _, m0 = gungeo.bone_world(skd, a, 0)
    mx = {}
    for f in range(0, nf, max(1, nf // 12)):
        _, mf = gungeo.bone_world(skd, a, f)
        for k in m0:
            d = float(np.linalg.norm(np.array(mf[k])[3] - np.array(m0[k])[3])) + float(np.abs(np.array(mf[k])[:3] - np.array(m0[k])[:3]).max()) * 10
            mx[k] = max(mx.get(k, 0), d)
    print(tik, cp, 'frames', nf, 'ft %.4f' % a.frameTime, {k: round(v, 1) for k, v in mx.items() if v > 0.05})
