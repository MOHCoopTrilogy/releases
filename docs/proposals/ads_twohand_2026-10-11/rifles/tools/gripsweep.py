"""OFFLINE sweep of the knob grip's offset: for each `knob_off` candidate bake the aimed bolt clip (to a scratch
suffix, the staged clip is not touched) and print the HANDS' centre-box maximum over every clip frame (rpart.py).

    cd rifles/assets; python ../tools/gripsweep.py <gun> "0,0.75,0.3" "0,0.9,0.4" ... [--rc k=v]
"""
import sys, os, copy, ast, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boltphys as BP
import rpart

gun = sys.argv[1]
cands = [a for a in sys.argv[2:] if not a.startswith('--')]
extra = {}
for i, a in enumerate(sys.argv):
    if a == '--rc':
        k, v = sys.argv[i + 1].split('=', 1); extra[k] = ast.literal_eval(v)
cands = [c for c in cands if '=' not in c]
base = copy.deepcopy(BP.GUNS[gun])
A = 'models/human/animation/'
for c in cands:
    g = copy.deepcopy(base)
    g.setdefault('rc', {}).update(extra)
    g['rc']['knob_off'] = tuple(float(x) for x in c.split(','))
    BP.GUNS[gun] = g
    with contextlib.redirect_stdout(io.StringIO()):
        dst = BP.bake(gun, '.', dict(BP.HOLD), 2.5, False, '_sw')
        o = rpart.measure(g['sight'], A + g['aim'], dst + '|' + g.get('anim', 'rechamber'), quiet=True)
    hs = [(sum(v for k, v in d['parts'].items() if 'hand' in k.lower()), d['f']) for d in o]
    mx = max(hs)
    print('%s knob_off=(%s): hands max %.1f %% at f%d; frames over 1 %%: %s' % (gun, c, mx[0], mx[1], ' '.join('%d:%.1f' % (f, h) for h, f in hs if h > 1.0)))
    os.remove(dst)
    if os.path.isfile(dst[:-4] + '_phys.json'):
        os.remove(dst[:-4] + '_phys.json')
BP.GUNS[gun] = base
