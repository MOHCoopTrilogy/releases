"""Moving parts cut out of a gun mesh onto NEW bones, and their channels for a motion given in GUN space.

split_bone.py makes the new bone a child of the bone the vertices were weighted to, at identity - so the new bone's
frame IS the parent's. That frame is fitted here from the mesh itself: for the parent's vertices,
gun-space position = local offset @ A + o (A 3x3 rows, o the bone origin; least squares, residual printed).

    split(tik, skd game path, {bone: [(surface, vertex count, min x), ...]}, out skd file)   islands as _meshsurvey.py prints them
    A, o = fit(tik, parent bone)                 (the ORIGINAL mesh: the frame does not change with the split)
    pos4, quat4 = chan(A, o, Rg, pivot, move)    the part turned by Rg (3x3 rows, gun space) about `pivot` (gun u) and
                                                  moved by `move` (gun u). The engine applies a bone quaternion as rows
                                                  (measured on the Welrod bolt: gunview, the knob stayed on the bore).
"""
import sys, os, json, math, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, HERE)
import gunskc
V = gunskc.V
R = V.R
PR = V.PR


def islands_of(g):
    out = {}
    for s in g['surfs']:
        P = np.asarray(s['P']); key = {}; w = []
        for p in P:
            w.append(key.setdefault(tuple(np.round(p, 2)), len(key)))
        par = list(range(len(key)))

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        for t in np.asarray(s['tri']):
            a = find(w[t[0]]); par[find(w[t[1]])] = a; par[find(w[t[2]])] = a
        comp = {}
        for i in range(len(P)):
            comp.setdefault(find(w[i]), []).append(i)
        out[s['name'].lower()] = [(idx, P[idx]) for idx in comp.values()]
    return out


def split(tik, skd, parts, out_skd):
    g = PR.gungeo.load_gun(tik)
    isl = islands_of(g)
    sel = {}
    for bone, lst in parts.items():
        want = []
        for sname, cnt, minx in lst:
            hit = [(idx, P) for idx, P in isl[sname.lower()] if len(idx) == cnt and abs(P[:, 0].min() - minx) < 0.05]
            assert len(hit) == 1, (tik, sname, cnt, minx, sorted((len(i), round(float(P[:, 0].min()), 2)) for i, P in isl[sname.lower()]))
            want += [[sname.lower(), int(vi)] for vi in hit[0][0]]
        sel[bone] = want
    sj = os.path.join(HERE, '_split_sel.json')
    json.dump(dict(sel=sel, skd=skd, out=os.path.abspath(out_skd)), open(sj, 'w'))
    os.makedirs(os.path.dirname(os.path.abspath(out_skd)), exist_ok=True)
    code = ("import sys, json\nsys.path.insert(0, r'%s')\nimport split_bone as S\n"
            "d = json.load(open(r'%s'))\ndata = S.R.vfs.read(d['skd'])\n"
            "for bone, lst in d['sel'].items():\n"
            "    want = set((s, v) for s, v in lst)\n"
            "    data, parent, n = S.split(data, bone, lambda s, vi, p, want=want: (s.name.lower(), vi) in want)\n"
            "    print('SPLIT', bone, n, 'of', len(want), 'from', parent)\n"
            "    assert n == len(want)\n"
            "open(d['out'], 'wb').write(data)\n" % (T, sj))
    env = dict(os.environ); env.pop('IRONSIGHT_EXTRA_PAKS', None)        # the ORIGINAL mesh: a staged (already split) one in an overlay would be split again
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=T, env=env)
    print(r.stdout.strip()); print(r.stderr.strip()[-800:])
    assert r.returncode == 0
    assert 'from coop_' not in r.stdout, 'split of an already split mesh'


def fit(tik, parent):
    g = PR.gungeo.load_gun(tik)
    skd = PR.skdlib.read_skd(PR.gungeo.vfs.read(g['skd']))
    bi = [b.name for b in skd.bones].index(parent)
    X, Y = [], []
    for s, gs in zip(skd.surfaces, g['surfs']):
        for vi, v in enumerate(s.verts):
            wl = v[2]
            if len(wl) == 1 and wl[0][0] == bi:
                X.append(list(wl[0][2]) + [1.0]); Y.append(gs['P'][vi])
    X = np.array(X); Y = np.array(Y)
    M, res, _, _ = np.linalg.lstsq(X, Y, rcond=None)
    err = float(np.abs(X @ M - Y).max())
    A, o = M[:3], M[3]
    print('fit %s bone %s: %d verts, max residual %.4f u, scale %.3f, origin %s' % (os.path.basename(tik), parent, len(X), err, np.linalg.norm(A[0]), np.round(o, 2)))
    assert err < 0.02
    return A, o


def rot_rows(axis, deg):
    """3x3 for row vectors: a turn of `deg` about `axis`; +deg about gun +y (right) lifts the FRONT (+x goes to -z = up)"""
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    Rc = np.eye(3) + s * K + (1 - c) * (K @ K)                 # column convention
    return Rc.T


def mat_quat(m):
    """standard quaternion (x, y, z, w) of a column-convention rotation matrix"""
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2; q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    return [float(x) for x in q]


def chan(A, o, Rg, pivot, move=(0.0, 0.0, 0.0)):
    Ai = np.linalg.inv(A)
    Rl = A @ np.asarray(Rg, float) @ Ai                        # rows, local
    c = (np.asarray(pivot, float) - o) @ Ai
    p = c - c @ Rl + np.asarray(move, float) @ Ai
    return [float(p[0]), float(p[1]), float(p[2]), 0.0], mat_quat(Rl)      # the engine's matrix of q, used on rows, is Rl
