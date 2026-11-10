"""[QA 2] the reach off the grip: try 'loww' keys (camera frame fwd, left, up) on the calm clip, render frames 2-16."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bren_reload2 as B2
src = 'A_W_Vickers_reload_fps.skc'
cfg = B2.CLIPS[src]
keys = dict(B2.KEYS['coop_bren_reload_fps.skc'])
lw = json.loads(sys.argv[1])
if lw:
    keys['loww'] = lw
out, clamps = B2.bake(src, cfg, keys)
p = r'H:\hzm_work\newguns\brenhands\sw\c3.skc'
open(p, 'wb').write(B2.R.skc_io.write(out))
c = B2.R.load(p)
print('clamps', sorted(set(f for _, f in clamps)))
rows = [(f,) + B2.coverage(c, 'reload', f) for f in range(0, 24, 2)]
print(' '.join('%d:%.1f/%.1f' % (f, 100 * a, 100 * b) for f, a, b in rows))
B2.sheet(c, 'reload', [4, 6, 8, 10, 12, 14, 16, 20], sys.argv[2], w=645, h=270)
