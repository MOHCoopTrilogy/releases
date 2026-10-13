"""top profile of a gun mesh behind the rear sight, as the aiming eye sees it: for each x slice the highest point
(gun frame x fwd, y right, z DOWN) and its angle below the sight line from the eye (box bottom edge = 7.2 deg at 1280x720, wfov 96.4)"""
import sys, os, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
import gunside as GS
sj = json.load(open(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\sights.json'))
for key, relief in [a.split(':') for a in sys.argv[1:]]:
    s = sj[key]; F = np.array(s['F']); Rr = np.array(s['R']); relief = float(relief)
    d = (F - Rr) / np.linalg.norm(F - Rr)
    eye = Rr - d * relief
    g = GS.PR.gungeo.load_gun(s['tik'], anim='idle', frame=0)
    P = np.vstack([q['P'] for q in g['surfs']])
    print(key, 'eye at', np.round(eye, 2), 'verts', len(P))
    for x0 in np.arange(-6, 8, 1.0):
        sel = P[(P[:, 0] >= x0) & (P[:, 0] < x0 + 1.0)]
        if not len(sel): continue
        q = sel - eye
        fwd = q @ d
        up = -(q[:, 2] - fwd * d[2])           # height above the sight line (z is down)
        ok = fwd > 0.3
        if not ok.any(): print('  x %+.0f: behind the eye' % x0); continue
        ang = np.degrees(np.arctan2(up[ok], fwd[ok]))
        k = ang.argmax()
        print('  x %+3.0f..%+3.0f: top z %.2f, width y %.2f..%.2f | highest seen %.1f deg (below the line when negative), depth %.1f u' % (
            x0, x0 + 1, sel[:, 2].min(), sel[:, 1].min(), sel[:, 1].max(), ang[k], fwd[ok][k]))
