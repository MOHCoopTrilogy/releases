"""S&W M10: a swing-out cylinder for a mesh that had none.

  * the split skd (m10probe.py) gives the cylinder + crane + ejector rod their own bone `coop_cyl`;
  * this script finds the bone's origin in gun space (a rotation probe), keys the swing about the crane axis and writes
    the gun's own clips coop_m10_open (30 f) / coop_m10_single (16 f, 24 f slow) / coop_m10_close (16 f), the tik with
    reload / reload_single / reload_end, and prints the points of the OPEN cylinder the hands are keyed on.

    python m10build.py            (after m10probe.py; writes into stage/)
"""
import sys, os, subprocess, zipfile, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
np.set_printoptions(precision=3, suppress=True)
fr = json.load(open(os.path.join(HERE, 'm10_frame.json')))
A = np.array(fr['A'])                       # rows: local unit moves in gun space (scale 0.52 folded in)
S = float(np.linalg.norm(A[0]))
M = A / S                                   # orthonormal rows: local axes in gun space
tmpl = R.vfs.read('models/weapons/coop_m10/reload_colt45.skc')
STAGE = os.path.join(HERE, 'stage')
GD = os.path.join(STAGE, 'models', 'weapons', 'coop_m10')
SKD = os.path.join(GD, 'm10.skd')


def render(clipfile, frames, want=('Cylinder4',)):
    """gun-space vertices of some surfaces at frames of a clip, through the same loader the previews use"""
    tik = R.vfs.read('models/weapons/m10_revolver.tik').decode('latin-1').replace('reload\t\treload_colt45.skc', 'reload\t\t_probe.skc', 1)
    pk = os.path.join(HERE, '_m10tmp.pk3')
    with zipfile.ZipFile(pk, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(SKD, 'models/weapons/coop_m10/m10.skd')
        z.write(clipfile, 'models/weapons/coop_m10/_probe.skc')
        z.writestr('models/weapons/m10_revolver.tik', tik.encode('latin-1'))
    code = ("import sys,os,json\nT=r'C:\\mohaa-coop-dev\\docs\\proposals\\ads_bolt_2026-10-04\\tools'\nsys.path.insert(0,T);os.chdir(T)\n"
            "import vmcam as V\nPR=V.PR\nout={}\n"
            "for f in %r:\n    g=PR.gungeo.load_gun('models/weapons/m10_revolver.tik',anim='reload',frame=f)\n"
            "    out[f]={s['name']:s['P'].tolist() for s in g['surfs'] if s['name'] in %r}\nprint('JSON'+json.dumps(out))\n" % (list(frames), list(want)))
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=dict(os.environ, IRONSIGHT_EXTRA_PAKS=pk))
    line = [l for l in r.stdout.splitlines() if l.startswith('JSON')]
    assert line, r.stderr[-1500:]
    o = json.loads(line[0][4:])
    return {int(k): {n: np.array(p) for n, p in v.items()} for k, v in o.items()}


def local_of(Rg, Pg, o):
    """gun-space rigid move p' = (p - Pg) Rg + Pg  ->  the bone's local rotation rows and translation (local units)"""
    Rl = M @ Rg @ M.T
    tl = ((o - Pg) @ Rg + Pg - o) @ np.linalg.inv(A)
    return Rl, tl


# ---- 1. the bone's origin in gun space: two 90 deg local rotations, the fixed point of each fit
tmp = os.path.join(HERE, 'm10probe', '_rot.skc')
qx = R.rows_to_quat(R.axis_angle_rows((1, 0, 0), 90)); qz = R.rows_to_quat(R.axis_angle_rows((0, 0, 1), 90))
gunskc.write(tmp, tmpl, 3, {'coop_cyl pos': [[0, 0, 0, 0]] * 3, 'coop_cyl rot': [[0, 0, 0, 1], list(qx), list(qz)]})
P = render(tmp, (0, 1, 2))
rows_, rhs = [], []
fits = []
for f in (1, 2):
    X, Y = P[0]['Cylinder4'], P[f]['Cylinder4']
    Xc, Yc = X - X.mean(0), Y - Y.mean(0)
    U, s_, Vt = np.linalg.svd(Xc.T @ Yc)
    Rg = U @ Vt
    if np.linalg.det(Rg) < 0:
        U[:, -1] *= -1; Rg = U @ Vt
    fits.append(Rg)
    # Y = (X - o) Rg + o  ->  o (I - Rg) = Y.mean - X.mean Rg
    rows_.append((np.eye(3) - Rg).T); rhs.append(Y.mean(0) - X.mean(0) @ Rg)
o = np.linalg.lstsq(np.vstack(rows_), np.hstack(rhs), rcond=None)[0]
print('bone origin in gun space', o)
# convention check: does a local rotation Rl (rows) show up as M^T Rl M in gun space?
exp = M.T @ R.axis_angle_rows((1, 0, 0), 90) @ M
print('rotation convention error', float(np.abs(exp - fits[0]).max()), '(transpose:', float(np.abs(exp.T - fits[0]).max()), ')')
TRANSPOSE = np.abs(exp.T - fits[0]).max() < np.abs(exp - fits[0]).max()

# ---- 2. the swing: about the crane axis (parallel to the bore, under the cylinder, a little left)
c0 = (np.array(fr['cyl_min']) + np.array(fr['cyl_max'])) / 2
rad = (fr['cyl_max'][2] - fr['cyl_min'][2]) / 2
Pg = np.array([c0[0], c0[1] - 0.17, c0[2] + rad + 0.08])
ANG = 92.0
cands = [R.axis_angle_rows((1, 0, 0), s * ANG) for s in (1, -1)]
Rg_open = min(cands, key=lambda Rg: ((c0 - Pg) @ Rg + Pg)[1])           # the one that carries the centre to the LEFT (-y)
c1 = (c0 - Pg) @ Rg_open + Pg
print('cylinder centre closed', c0, 'open', c1, 'radius', round(rad, 2), 'crane pivot', Pg)


def keys(n, w_of_f):
    pos, rot = [], []
    for f in range(n):
        w = w_of_f(f)
        w = w * w * (3 - 2 * w)
        Rg = R.axis_angle_rows((1, 0, 0), (ANG if Rg_open is cands[0] else -ANG) * w)
        Rl, tl = local_of(Rg, Pg, o)
        q = R.rows_to_quat(Rl.T if TRANSPOSE else Rl)
        pos.append([tl[0], tl[1], tl[2], 0.0]); rot.append(list(q))
    return {'coop_cyl pos': pos, 'coop_cyl rot': rot}


ramp = lambda a, b: (lambda f: max(0.0, min(1.0, (f - a) / float(b - a))))
clips = {'coop_m10_open.skc': (30, ramp(9, 16)), 'coop_m10_single.skc': (16, lambda f: 1.0),
         'coop_m10_single_slow.skc': (24, lambda f: 1.0), 'coop_m10_close.skc': (16, lambda f: 1.0 - ramp(5, 11)(f))}
for name, (n, wf) in clips.items():
    gunskc.write(os.path.join(GD, name), tmpl, n, keys(n, wf), frame_time=1.0 / 30.0)
# verify the open pose through the preview loader
P = render(os.path.join(GD, 'coop_m10_open.skc'), (0, 29), ('Cylinder4', 'Cylinder5', 'Cube1'))
co = (P[29]['Cylinder4'].min(0) + P[29]['Cylinder4'].max(0)) / 2
print('rendered open centre', co, 'expected', c1, '| frame f0 unchanged', float(np.abs(P[0]['Cylinder4'].mean(0) - c0).max()) < 0.2)
rod = P[29]['Cylinder5']
pts = dict(c_closed=c0.tolist(), c_open=co.tolist(), radius=rad, rear_x=float(P[29]['Cylinder4'][:, 0].min()),
           front_x=float(P[29]['Cylinder4'][:, 0].max()), rod_tip=[float(rod[:, 0].max()), float(rod[:, 1].mean()), float(rod[:, 2].mean())],
           frame_left_y=float(P[0]['Cube1'][:, 1].min()))
json.dump(pts, open(os.path.join(HERE, 'm10_points.json'), 'w'), indent=1)
print(pts)

# ---- 3. the tik: reload / reload_single / reload_end on the new clips
raw = R.vfs.read('models/weapons/m10_revolver.tik').decode('latin-1')
crlf = '\r\n' in raw
t = raw.replace('\r\n', '\n')
old = ("\treload\t\treload_colt45.skc\n\t{\n\t\tserver\n\t\t{\n\t\t\t19 surface clip\t+nodraw\n\t\t\t40 surface clip -nodraw\n\t\t\tlast idle\n\t\t}\n"
       "\t\tclient\n\t\t{\n\t\t\t\tentry sound colt45_snd_reload item\n\t\t}\n\t}\n")
assert old in t
new = ("\t// HZM coop [revolver reload 2026-10-12] the cylinder + crane + ejector rod swing out on their own bone (coop_cyl,\n"
       "\t// split out of the mesh): open / one round at a time / close, as the Webley's start / single / end.\n"
       "\treload\t\tcoop_m10_open.skc\n\t{\n\t\tclient\n\t\t{\n\t\t\t\tentry sound colt45_snd_reload item\n\t\t}\n\t}\n"
       "\treload_single\tcoop_m10_single.skc\n"
       "\treload_end\tcoop_m10_close.skc\n\t{\n\t\tserver\n\t\t{\n\t\t\tlast idle\n\t\t}\n\t}\n")
t = t.replace(old, new, 1)
p = os.path.join(STAGE, 'models', 'weapons', 'm10_revolver.tik')
open(p, 'wb').write((t.replace('\n', '\r\n') if crlf else t).encode('latin-1'))
print('wrote', p)
