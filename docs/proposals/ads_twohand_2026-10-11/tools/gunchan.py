"""Which channels of a gun clip move, and when.   python gunchan.py <game path of the .skc> [more ...]"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R
for p in sys.argv[1:]:
    try:
        a = R.load(p if os.path.isfile(p) else R.read_game(p)) if hasattr(R, 'read_game') else R.load(p)
    except Exception as e:
        print(p, 'load failed:', e); continue
    print(p, a.numFrames, 'frames x', round(a.frameTime, 4))
    for c, nm in enumerate(a.names):
        v = a.V[:, c, :3] if nm.endswith(' pos') else a.V[:, c, :]
        d = np.abs(v - v[0]).max(axis=1)
        if d.max() < 1e-3:
            continue
        mv = np.where(np.abs(np.diff(v, axis=0)).max(axis=1) > 1e-3)[0]
        print('  %-28s range %.3f  moves f%d..f%d  ' % (nm, d.max(), mv.min(), mv.max() + 1),
              ' '.join('%d:%.2f' % (f, d[f]) for f in range(0, a.numFrames, max(1, a.numFrames // 16))))
