"""M10 step 1: split the cylinder assembly into its own bone and find how that bone's local axes sit in gun space.
Writes stage/models/weapons/coop_m10/m10.skd (split), a probe clip and a probe pk3; prints the local->gun matrix.
"""
import sys, os, subprocess, zipfile, glob, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, HERE)
SKD = 'models/weapons/coop_m10/m10.skd'
out_skd = os.path.join(HERE, 'stage', SKD.replace('/', os.sep))
os.makedirs(os.path.dirname(out_skd), exist_ok=True)
r = subprocess.run([sys.executable, os.path.join(T, 'split_bone.py'), SKD, out_skd, 'coop_cyl',
                    '--surface', 'Cylinder4', '--surface', 'Cylinder5', '--surface', 'Cylinder2'], cwd=T, capture_output=True, text=True)
print(r.stdout[-600:], r.stderr[-600:])
import gunskc
R = gunskc.R
tmpl = R.vfs.read('models/weapons/coop_m10/reload_colt45.skc')
probe = os.path.join(HERE, 'm10probe', 'models', 'weapons', 'coop_m10', 'coop_m10_probe.skc')
pos = [[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
names = gunskc.write(probe, tmpl, 4, {'coop_cyl pos': pos, 'coop_cyl rot': [[0, 0, 0, 1]] * 4})
print('template channels', names)
tik = R.vfs.read('models/weapons/m10_revolver.tik').decode('latin-1')
assert 'reload\t\treload_colt45.skc' in tik
tik = tik.replace('reload\t\treload_colt45.skc', 'reload\t\tcoop_m10_probe.skc', 1)
pk = os.path.join(HERE, 'm10probe.pk3')
with zipfile.ZipFile(pk, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(out_skd, SKD)
    z.write(probe, 'models/weapons/coop_m10/coop_m10_probe.skc')
    z.writestr('models/weapons/m10_revolver.tik', tik.encode('latin-1'))
code = r'''
import sys, os, json
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); os.chdir(T)
import vmcam as V
PR = V.PR
tik = 'models/weapons/m10_revolver.tik'
P = [{s['name']: s['P'] for s in PR.gungeo.load_gun(tik, anim='reload', frame=f)['surfs']} for f in range(4)]
out = {}
for f in (1, 2, 3):
    d = P[f]['Cylinder4'] - P[0]['Cylinder4']
    out[f] = d.mean(0).tolist(); out['sd%d' % f] = float(d.std(0).max())
    out['other%d' % f] = float(max(np.abs(P[f][n] - P[0][n]).max() for n in P[0] if n not in ('Cylinder4', 'Cylinder5', 'Cylinder2')))
c = P[0]['Cylinder4']
out['cyl_min'] = c.min(0).tolist(); out['cyl_max'] = c.max(0).tolist()
out['rod_min'] = P[0]['Cylinder5'].min(0).tolist(); out['rod_max'] = P[0]['Cylinder5'].max(0).tolist()
out['crane_min'] = P[0]['Cylinder2'].min(0).tolist(); out['crane_max'] = P[0]['Cylinder2'].max(0).tolist()
print('JSON' + json.dumps(out))
'''
env = dict(os.environ, IRONSIGHT_EXTRA_PAKS=pk)
r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env)
line = [l for l in r.stdout.splitlines() if l.startswith('JSON')]
if not line:
    print(r.stdout[-800:], r.stderr[-1500:]); sys.exit(1)
o = json.loads(line[0][4:])
A = np.array([o['1'], o['2'], o['3']])
np.set_printoptions(precision=3, suppress=True)
print('local unit moves in gun space (rows = local x, y, z):'); print(A)
print('spread', o['sd1'], o['sd2'], o['sd3'], 'other parts moved', o['other1'], o['other2'], o['other3'])
print('cylinder bbox', np.round(o['cyl_min'], 2), np.round(o['cyl_max'], 2))
print('rod bbox', np.round(o['rod_min'], 2), np.round(o['rod_max'], 2), 'crane bbox', np.round(o['crane_min'], 2), np.round(o['crane_max'], 2))
json.dump(dict(A=A.tolist(), **o), open(os.path.join(HERE, 'm10_frame.json'), 'w'))
