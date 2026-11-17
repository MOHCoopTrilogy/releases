"""Bake one rifle's aimed reload with several hold overrides and print the offline figures (vmeasure) per variant.
    cd rifles/assets; python ../m1_reload_fix/tools/sweep.py garand <outroot> "push.drop=2,push.pitch=3;..." --frames 12,20,30,36,44
"""
import sys, os, io, contextlib, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vmeasure as VM
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import upreload
RR = upreload.RR

ap = argparse.ArgumentParser()
ap.add_argument('gun'); ap.add_argument('root'); ap.add_argument('variants'); ap.add_argument('--frames', default='12,20,30,36,44')
a = ap.parse_args()
fr = [int(x) for x in a.frames.split(',')]
for i, var in enumerate(a.variants.split(';')):
    sets = [s for s in var.split(',') if s]
    root = os.path.join(a.root, 'v%d' % i)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        dst = RR.bake(a.gun, root, 2.5, sets)
    r = VM.measure(a.gun, dst, fr)
    print('v%d %s' % (i, var))
    print('   ' + '  '.join('f%d F%.3f R%.3f box %.1f' % (f, v['fy'], v['ry'], v['box']) for f, v in r.items()))
