"""The mod's finish set (gold chrome blued bloody camo_woodland camo_winter camo_desert) for the new C96 sheet.
Same recipe and numbers as docs/proposals/dbshotgun_2026-10-12/tools/dbs_finish.py (itself the mod's gen_skins.py /
bake_skins.py), with a texel position bake made here by rasterising the mesh into UV space (build/texel_bake.npz).

    python finishes.py bake      -> build/texel_bake.npz
    python finishes.py build     -> ship/textures/models/weapons/coop_c96n/*.jpg  + ship/scripts/coop_c96n.shader
    python finishes.py view      -> build/_fin_view.jpg
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c96lib as L

CM = 0.88                      # cm per raw unit (the gun is ~29 cm over all)
SIZE = 2048
TEXV = 'textures/models/weapons/coop_c96n/'
TDIR = os.path.join(L.STAGE, 'textures', 'models', 'weapons', 'coop_c96n')
ENVMAP = 'textures/coop_skins/env_sheen.tga'
FINISHES = [
    ('gold', 'stage', {'tint': (1.00, 0.78, 0.30), 'env': (0.40, 0.31, 0.12)}),
    ('chrome', 'stage', {'tint': (0.88, 0.92, 0.98), 'env': (0.55, 0.58, 0.64)}),
    ('blued', 'stage', {'tint': (0.44, 0.48, 0.64), 'env': (0.10, 0.12, 0.20)}),
    ('bloody', 'bake', {}),
    ('camo_woodland', 'bake', {'pal': [(58, 66, 40), (86, 92, 56), (44, 40, 30), (104, 98, 66)], 'seed': 3}),
    ('camo_winter', 'bake', {'pal': [(178, 182, 186), (140, 146, 152), (96, 102, 108), (206, 210, 213)], 'seed': 11}),
    ('camo_desert', 'bake', {'pal': [(176, 150, 104), (146, 120, 78), (198, 178, 138), (118, 98, 66)], 'seed': 5}),
]
BLOTCH_CM = 2.6


def bake():
    d = np.load(os.path.join(L.BUILD, 'tris.npz'))
    A, part = d['corners'], d['part']
    keep = np.isin(part, ['Root', 'Slide', 'Hammer', 'Trigger', 'Ring'])
    A = A[keep]
    pos = np.zeros((SIZE, SIZE, 3), np.float32); nrm = np.zeros((SIZE, SIZE, 3), np.float32)
    mask = np.zeros((SIZE, SIZE), bool)
    P = L.to_raw(A[:, :, :3]).astype(np.float64); N = L.nrm_raw(A[:, :, 3:6])
    U = A[:, :, 6] * SIZE; V = (1.0 - A[:, :, 7]) * SIZE
    for t in range(len(A)):
        x = U[t]; y = V[t]
        x0, x1 = int(np.floor(x.min())), int(np.ceil(x.max())); y0, y1 = int(np.floor(y.min())), int(np.ceil(y.max()))
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, SIZE - 1), min(y1, SIZE - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(den) < 1e-12:
            continue
        l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
        l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
        l2 = 1 - l0 - l1
        m = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
        if not m.any():
            continue
        yy, xx = np.nonzero(m)
        a, b, c = l0[m], l1[m], l2[m]
        pos[yy + y0, xx + x0] = (a[:, None] * P[t, 0] + b[:, None] * P[t, 1] + c[:, None] * P[t, 2])
        nrm[yy + y0, xx + x0] = (a[:, None] * N[t, 0] + b[:, None] * N[t, 1] + c[:, None] * N[t, 2])
        mask[yy + y0, xx + x0] = True
    dist, idx = ndi.distance_transform_edt(~mask, return_indices=True)
    np.savez_compressed(os.path.join(L.BUILD, 'texel_bake.npz'), pos=pos * CM, nrm=nrm, mask=mask, idx=idx.astype(np.int16), dist=dist.astype(np.float32))
    print('baked: %.1f %% of the sheet is gun' % (100 * mask.mean()))


def pad(col, M):
    idx = M['idx'].astype(np.int64)
    out = col[idx[0], idx[1]]
    return out


def luma(a):
    a = a / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def norm(l, m, lo=2, hi=98):
    a, b = np.percentile(l[m], lo), np.percentile(l[m], hi)
    return np.clip((l - a) / max(b - a, 1e-6), 0, 1)


def volume(pos, m, sigma_cm, seed, cell=0.5):
    lo = pos[m].min(0) - 3 * sigma_cm; hi = pos[m].max(0) + 3 * sigma_cm
    shp = np.ceil((hi - lo) / cell).astype(int) + 1
    v = np.random.default_rng(seed).random(tuple(shp)).astype(np.float32)
    v = ndi.gaussian_filter(v, sigma_cm / cell, mode='reflect')
    c = [(pos[..., k] - lo[k]) / cell for k in range(3)]
    return ndi.map_coordinates(v, c, order=1, mode='nearest')


def camo(base, pos, M, pal, seed):
    m = M['mask']
    l = norm(luma(base), m)
    low = ndi.gaussian_filter(l, SIZE // 64 / 2.0)
    detail = l - low
    shade = np.clip(low / max(low[m].mean(), 1e-6), 0.45, 1.55)[..., None]
    f = volume(pos, m, BLOTCH_CM, seed)
    edges = np.quantile(f[m], np.linspace(0, 1, len(pal) + 1)[1:-1])
    pat = np.array(pal, np.float32)[np.digitize(f, edges)]
    out = np.clip(pat * shade + detail[..., None] * 190.0, 0, 255)
    return pad(out, M)


def bloody(base, pos, nrm, M):
    m = M['mask']
    rng = np.random.default_rng(7)
    ys, xs = np.nonzero(m)
    Pp = pos[ys, xs]; Nn = nrm[ys, xs]
    msk = np.zeros(m.shape, np.float32)

    def pick():
        i = rng.integers(0, len(ys))
        return Pp[i], Nn[i]
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    for _ in range(70):
        c, n0 = pick(); r = rng.uniform(0.15, 0.5); v = rng.integers(120, 255) / 255.0
        dd = np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2)
        msk = np.maximum(msk, v * np.clip((r - dd) / 0.06 + 0.5, 0, 1))
    for k in range(20):
        c, n0 = pick(); rx, rz = rng.uniform(1.0, 3.5), rng.uniform(0.8, 2.6); v = rng.integers(70, 150) / 255.0
        dd = np.sqrt(((x - c[0]) / rx) ** 2 + ((y - c[1]) / 1.6) ** 2 + ((z - c[2]) / rz) ** 2)
        face = (nrm @ n0) > -0.1
        edge = 0.10 * volume(pos, m, 0.35, 100 + k)
        msk = np.maximum(msk, v * np.clip((1.0 - dd + edge * 4 - 0.2) / 0.12, 0, 1) * face)
    for k in range(24):
        c, n0 = pick(); ln = rng.uniform(1.5, 6.0); wd = rng.uniform(0.06, 0.15); v = rng.integers(90, 190) / 255.0
        across = np.sqrt((x - c[0]) ** 2 + ((y - c[1]) * (abs(n0[1]) < 0.6)) ** 2)
        face = ((nrm @ n0) > 0.2) & (np.abs(y - c[1]) < 1.2)
        along = (z - c[2])            # gun +z is DOWN: a run goes toward +z
        body = np.clip((wd - across) / 0.03 + 0.5, 0, 1) * np.clip(along / 0.1, 0, 1) * np.clip((ln - along) / (0.35 * ln), 0, 1)
        msk = np.maximum(msk, v * body * face)
    msk = ndi.gaussian_filter(msk, max(1, SIZE // 500) / 2.0)[..., None]
    blood = np.array([102, 12, 10], np.float32)
    out = base * 0.55 * msk + base * (1 - msk) + blood * msk * 0.75
    return pad(np.clip(out, 0, 255), M), float((msk[..., 0][m] > 0.2).mean())


def shader_block(name, tex, kind, params):
    Ls = ['', name, '{', '\tqer_editorimage %s' % tex, '\t{', '\t\tmap %s' % tex, '\t\trgbGen lightingSpherical', '\t}']
    if kind == 'stage':
        Ls += ['\t{', '\t\tmap $whiteimage', '\t\tblendFunc GL_DST_COLOR GL_ZERO', '\t\trgbGen const %.2f %.2f %.2f' % params['tint'], '\t}']
        Ls += ['\t{', '\t\tmap %s' % ENVMAP, '\t\tblendFunc add', '\t\ttcGen environment', '\t\trgbGen const %.2f %.2f %.2f' % params['env'], '\t}']
    Ls.append('}')
    return '\n'.join(Ls)


def build():
    base = np.asarray(Image.open(os.path.join(L.BUILD, 'c96_diffuse_final.png')).convert('RGB')).astype(np.float32)
    B = np.load(os.path.join(L.BUILD, 'texel_bake.npz'))
    M = {k: B[k] for k in B.files}
    pos, nrm = M['pos'], M['nrm']
    os.makedirs(TDIR, exist_ok=True)
    for key, kind, pr in FINISHES:
        if kind != 'bake':
            continue
        if key == 'bloody':
            out, cov = bloody(base, pos, nrm, M); print(key, 'blood on %.1f %%' % (100 * cov))
        else:
            out = camo(base, pos, M, pr['pal'], pr['seed'])
        im = Image.fromarray(out.astype(np.uint8))
        im.save(os.path.join(L.BUILD, 'fin_%s.png' % key))
        im.save(os.path.join(TDIR, 'coop_c96n_%s.jpg' % key), quality=92, subsampling=0)
    # base sheet: padded so no mip level bleeds the empty atlas into the gun
    pb = pad(base, M)
    pb[~M['mask']] = pb[~M['mask']]
    Image.fromarray(np.clip(pb, 0, 255).astype(np.uint8)).save(os.path.join(TDIR, 'coop_c96n.jpg'), quality=93, subsampling=0)
    blocks = ['// HZM coop: Mauser C96 (model "Mauser C96" by no12u, Sketchfab, CC BY 4.0) - base sheet + the finish set (tools/finishes.py)',
              '// NEW names, defined in this one file only (TRAPS T6)',
              shader_block('coop_c96n', TEXV + 'coop_c96n.jpg', 'plain', {})]
    for key, kind, pr in FINISHES:
        tex = TEXV + ('coop_c96n.jpg' if kind == 'stage' else 'coop_c96n_%s.jpg' % key)
        blocks.append(shader_block('coop_c96n_%s' % key, tex, kind, pr))
    os.makedirs(os.path.join(L.STAGE, 'scripts'), exist_ok=True)
    open(os.path.join(L.STAGE, 'scripts', 'coop_c96n.shader'), 'w', newline='\r\n').write('\n'.join(blocks) + '\n')
    print('shader + textures written')


def view():
    tiles = []
    for nm in ['base'] + [k for k, kd, _ in FINISHES if kd == 'bake']:
        p = os.path.join(L.BUILD, 'c96_diffuse_final.png') if nm == 'base' else os.path.join(L.BUILD, 'fin_%s.png' % nm)
        tiles.append(Image.open(p).convert('RGB').resize((640, 640), Image.LANCZOS))
    W = Image.new('RGB', (640 * len(tiles), 640))
    for i, t in enumerate(tiles):
        W.paste(t, (640 * i, 0))
    W.save(os.path.join(L.BUILD, '_fin_view.jpg'), quality=88)


if __name__ == '__main__':
    {'bake': bake, 'build': build, 'view': view}[sys.argv[1]]()
