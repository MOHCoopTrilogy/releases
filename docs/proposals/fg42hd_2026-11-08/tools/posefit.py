"""the shipped irons mesh: bone-local raw verts (skd) vs the gun-frame verts gungeo poses them to -> the affine map local -> gun frame
(least squares), then the new model's aperture / post tip through it. Run from docs/proposals/ads_bolt_2026-10-04/tools (vmcam path)."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.getcwd())
import vmcam as V
PR = V.PR
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import skd as K
import gen_wpnfix_pak as W
HERE = r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools"
sys.path.insert(0, HERE)
import fglib as L
g = PR.gungeo.load_gun('models/weapons/coop_fg42_irons.tik')
old = K.read(W.carriers('models/weapons/fg42/coop_fg42_irons.skd')[-1][1])
X, Y = [], []
for s, gs in zip(old['surfaces'], g['surfs']):
    if s['name'] == 'coop_handle':
        continue
    loc = np.array([v['pos'] for v in s['verts']]); P = np.asarray(gs['P'])
    if len(loc) != len(P):
        print('skip', s['name'], len(loc), len(P)); continue
    X.append(loc); Y.append(P)
X = np.vstack(X); Y = np.vstack(Y)
Xa = np.hstack([X, np.ones((len(X), 1))])
M, res, _, _ = np.linalg.lstsq(Xa, Y, rcond=None)
err = np.abs(Xa @ M - Y).max()
print('affine rows\n', np.round(M, 5), '\nmax err', round(float(err), 4))
for nm, p in (('aperture', L.to_raw(L.R_SRC)), ('ring', L.to_raw(L.RING_C)), ('post tip', L.to_raw(L.F_SRC))):
    print(nm, 'local', np.round(p, 3), 'gun', np.round(np.append(p, 1) @ M, 4))
