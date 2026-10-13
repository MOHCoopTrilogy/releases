"""Give a pistol whose mesh has no slide bone a working slide (user 2026-10-12: "functioning slides, bolts").

The slide is cut out as mesh ISLANDS (connected parts, vertices welded by position - a box would also catch the barrel
and the frame under it) and put on a new bone `coop_slide` (split_bone.py: vertex order, UVs, surfaces untouched; with
no channel for the bone the gun renders as before). Then the bone's local axes are measured in gun space with a probe
clip, offline, and written to slide_<gun>.json for pistolgun.py.

    python slidesplit.py <gun|all>          -> stage/<skd path>, slide_<gun>.json
"""
import sys, os, json, subprocess, zipfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R

GUNS = {
    # islands: (surface, vertex count, min x of the island) - from meshparts.py
    'p38': dict(tik='models/weapons/p38.tik', skd='models/weapons/P38/p38.skd', clip='models/weapons/P38/P38_reload.skc',
                islands=[('P381', 115, -0.64), ('P381', 48, 0.17), ('P382', 62, 6.62)], travel=2.3),
    # the Welrod's bolt + rear knob (surface Cylinder3 = shader WR_bolt): turned and pulled by hand after every shot
    'welrod': dict(tik='models/weapons/welrod.tik', skd=None, clip='models/weapons/welrod/welrod_pistol_reload.skc',
                   islands=[('Cylinder3', 98, -4.21), ('Cylinder3', 73, -3.15)], travel=2.2),
    'histandard': dict(tik='models/weapons/silencedpistol.tik', skd=None, clip='models/weapons/highstandard/hs_pistol_reload.skc',
                       islands=[('pistol2', 58, -1.04), ('pistol2', 64, 0.52)], travel=2.2),
}


def islands(tik):
    code = ("import sys, os, json\nimport numpy as np\nT = r'%s'\nsys.path.insert(0, T); os.chdir(T)\nimport vmcam as V\n"
            "g = V.PR.gungeo.load_gun(%r)\nprint('JSON' + json.dumps({s['name']: [np.asarray(s['P']).tolist(), np.asarray(s['tri']).tolist()] for s in g['surfs']}))\n" % (T, tik))
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    d = json.loads([l for l in r.stdout.splitlines() if l.startswith('JSON')][0][4:])
    out = {}
    for name, (P, tri) in d.items():
        P = np.array(P); key = {}; w = []
        for p in P:
            w.append(key.setdefault(tuple(np.round(p, 2)), len(key)))
        par = list(range(len(key)))

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        for t in tri:
            a = find(w[t[0]]); par[find(w[t[1]])] = a; par[find(w[t[2]])] = a
        comp = {}
        for i in range(len(P)):
            comp.setdefault(find(w[i]), []).append(i)
        out[name] = [(idx, P[idx]) for idx in comp.values()]
    return out


def run(name):
    g = GUNS[name]
    tik = R.vfs.read(g['tik']).decode('latin-1')
    import re
    path = re.search(r'(?m)^\s*path\s+(\S+)', tik).group(1)
    skd = g['skd'] or (path + '/' + re.search(r'(?m)^\s*skelmodel\s+(\S+)', tik).group(1))
    isl = islands(g['tik'])
    want = set()
    for sname, cnt, minx in g['islands']:
        hit = [(idx, P) for idx, P in isl[sname] if len(idx) == cnt and abs(P[:, 0].min() - minx) < 0.05]
        assert len(hit) == 1, (sname, cnt, minx, [(len(i), round(float(P[:, 0].min()), 2)) for i, P in isl[sname]])
        for vi in hit[0][0]:                       # by vertex INDEX: gungeo keeps the skd's vertex order per surface
            want.add((sname.lower(), int(vi)))
    out_skd = os.path.join(HERE, 'stage', skd.replace('/', os.sep))
    os.makedirs(os.path.dirname(out_skd), exist_ok=True)
    sel = os.path.join(HERE, 'slidesel_%s.json' % name)
    json.dump(sorted([s, v] for s, v in want), open(sel, 'w'))
    code = ("import sys, json, numpy as np\nsys.path.insert(0, r'%s')\nimport split_bone as S\n"
            "want = set((s, v) for s, v in json.load(open(r'%s')))\n"
            "data = S.R.vfs.read(%r)\nn_ = [0]\n"
            "def pick(s, vi, p):\n    return (s.name.lower(), vi) in want\n"
            "out, parent, n = S.split(data, 'coop_slide', pick)\nopen(r'%s', 'wb').write(out)\nprint('SPLIT', n, parent)\n" % (T, sel, skd, out_skd))
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=T)
    print(name, r.stdout.strip()[-200:], r.stderr.strip()[-600:])
    nsel = int(r.stdout.split('SPLIT')[1].split()[0])
    assert nsel == sum(c for _, c, _ in g['islands']), ('selected', nsel)
    # ---- probe: the bone's local axes in gun space
    tmpl = R.vfs.read(g['clip'])
    probe = os.path.join(HERE, 'slideprobe', name, 'probe.skc')
    gunskc.write(probe, tmpl, 4, {'coop_slide pos': [[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], 'coop_slide rot': [[0, 0, 0, 1]] * 4})
    clipname = g['clip'].split('/')[-1]
    pk = os.path.join(HERE, 'slideprobe_%s.pk3' % name)
    with zipfile.ZipFile(pk, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(out_skd, skd)
        z.write(probe, path + '/coop_slide_probe.skc')
        z.writestr(g['tik'], re.sub(r'(?m)^(\s*reload\s+)%s' % re.escape(clipname), r'\1coop_slide_probe.skc', tik, count=1).encode('latin-1'))
    s0 = g['islands'][0][0]
    code = ("import sys, os, json\nimport numpy as np\nT = r'%s'\nsys.path.insert(0, T); os.chdir(T)\nimport vmcam as V\n"
            "P = [{s['name']: np.asarray(s['P']) for s in V.PR.gungeo.load_gun(%r, anim='reload', frame=f)['surfs']} for f in range(4)]\n"
            "o = {}\n"
            "for f in (1, 2, 3):\n    d = P[f][%r] - P[0][%r]\n    m = np.abs(d).max(1) > 1e-4\n    o[str(f)] = d[m].mean(0).tolist(); o['n%%d' %% f] = int(m.sum())\n"
            "print('JSON' + json.dumps(o))\n" % (T, g['tik'], s0, s0))
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=dict(os.environ, IRONSIGHT_EXTRA_PAKS=pk))
    ln = [l for l in r.stdout.splitlines() if l.startswith('JSON')]
    if not ln:
        print(r.stdout[-500:], r.stderr[-1200:]); sys.exit(1)
    o = json.loads(ln[0][4:])
    A = np.array([o['1'], o['2'], o['3']])                 # rows: a local unit move of x, y, z seen in gun space
    back = np.linalg.solve(A.T, np.array([-1.0, 0.0, 0.0]))    # the local move that is 1 u straight back in gun space
    np.set_printoptions(precision=3, suppress=True)
    print(name, 'verts moved by the probe', o['n1'], '| local axes in gun space:\n', A, '\n local vector for 1 u back:', back)
    json.dump(dict(skd=skd, path=path, bone='coop_slide', back=back.tolist(), travel=g['travel'], verts=nsel, A=A.tolist(), tik=g['tik'], clip=g['clip']), open(os.path.join(HERE, 'slide_%s.json' % name), 'w'))


if __name__ == '__main__':
    for nm in (list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(',')):
        run(nm)
