import sys
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import vfs, gungeo, skdlib, numpy as np
tik = sys.argv[1]; anim = sys.argv[2] if len(sys.argv) > 2 else 'reload'
t = gungeo.parse_tik(tik); cp = gungeo._res(t, t['anims'][anim]); a = skdlib.read_skc(vfs.read(cp))
skd = skdlib.read_skd(vfs.read(gungeo._res(t, t['skel'][0])))
_, m0 = gungeo.bone_world(skd, a, 0)
print(cp, a.numFrames, a.frameTime)
for f in range(0, a.numFrames, 4):
    _, mf = gungeo.bone_world(skd, a, f)
    print('f%3d %.2fs ' % (f, f * a.frameTime) + ' '.join('%s:%.1f' % (k, np.linalg.norm(np.array(mf[k])[3] - np.array(m0[k])[3]) + 10 * np.abs(np.array(mf[k])[:3] - np.array(m0[k])[:3]).max()) for k in m0 if k not in ('origin',)))
