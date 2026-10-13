"""The mod's standard FINISH SET for the double-barrel shotgun: gold, chrome, blued, bloody, woodland, winter, desert -
the seven the pump gun has (models/weapons/shotgun_<finish>.tik, armory FINISH row fid 1-7), made from OUR sheet
(tools/dbs_skin.py), never from the author's.

    python tools/dbs_finish.py            textures + shader file + 7 tiks under assets/
    python tools/dbs_finish.py view       build/_fin_view.jpg  (offline look at the four baked sheets, both sides)

THE MOD'S RECIPE (docs/tools/gen_skins.py + bake_skins.py + gen_weapon_skins.py; read, not run, not changed):
  gold / chrome / blued   "stage" finishes: no texture, three shader stages - the gun's own diffuse, a flat tint
                          multiplied over it (blendFunc GL_DST_COLOR GL_ZERO, rgbGen const), the shared sphere map
                          textures/coop_skins/env_sheen.tga added through tcGen environment. Same tint / env numbers.
  bloody / camo x 3       "bake" finishes: a real sheet computed from the base sheet - camo() keeps the base's low
                          frequency shading (x the pattern colour) and adds its high frequency detail back (x 190);
                          bloody() darkens to 0.55 and adds (102, 12, 10) x 0.75 under a spatter / soak / run mask.
                          Same palettes, same numbers.
  the tik                 the base tik with ONLY the rank and the reskinned surfaces changed (gen_skins.variant_tik).

WHAT IS DIFFERENT HERE, AND WHY
  * the PATTERN (camo blotches, blood) is laid out in GUN SPACE from build/skin_bake.npz (position and normal per
    texel), not in UV space: this sheet is a smart-projected atlas of many islands, a UV-space pattern would break at
    every seam and the mod's vertical "runs" would point anywhere. The colour maths is the mod's, line for line.
  * what must stay READABLE keeps the base sheet's pixels on the baked finishes: the bores, the barrels' breech faces,
    the standing breech and the muzzle faces (build/skin_masks.npz, written by dbs_skin.py paint). On the stage
    finishes a fourth shader stage multiplies a mask sheet (white; dark inside the bores) so the added sheen does not
    fill the bores. The bead and the shells are the second surface (coop_dbshotgun_parts): untouched on every finish.
  * the NAME stays "Shotgun (Double Barrel)" on all eight tiks. The mod names a finish "<Gun> (<Finish>)" and strips
    at the first " (" - this gun's name already carries a " (" (that is how it inherits every Shotgun row), so a
    second suffix would resolve to the PUMP gun's hands / torso rows / sight row. One name = one sight row, one set
    of hands rows, one loot picture, the same torso state rows; the armory tells finishes apart by tik path
    (coop_skinGive / coop_skinBase), never by name. Ranks are unique (a shared rank hides a gun on the wheel).
"""
import os, sys, re, io, glob
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import dbslib as L

NAME = 'coop_dbshotgun'
CM = 13.25
TDIR = os.path.join(L.ASSETS, 'textures', 'models', 'weapons', NAME)
TEXV = 'textures/models/weapons/%s/' % NAME
ENVMAP = 'textures/coop_skins/env_sheen.tga'
# key, armory fid, kind, params  - gen_skins.FINISHES / bake_skins.BAKED, copied
FINISHES = [
    ('gold', 1, 'stage', {'tint': (1.00, 0.78, 0.30), 'env': (0.40, 0.31, 0.12)}),
    ('chrome', 2, 'stage', {'tint': (0.88, 0.92, 0.98), 'env': (0.55, 0.58, 0.64)}),
    ('blued', 3, 'stage', {'tint': (0.44, 0.48, 0.64), 'env': (0.10, 0.12, 0.20)}),
    ('bloody', 4, 'bake', {}),
    ('camo_woodland', 5, 'bake', {'pal': [(58, 66, 40), (86, 92, 56), (44, 40, 30), (104, 98, 66)], 'seed': 3}),
    ('camo_winter', 6, 'bake', {'pal': [(178, 182, 186), (140, 146, 152), (96, 102, 108), (206, 210, 213)], 'seed': 11}),
    ('camo_desert', 7, 'bake', {'pal': [(176, 150, 104), (146, 120, 78), (198, 178, 138), (118, 98, 66)], 'seed': 5}),
]
BLOTCH_CM = 2.6          # camo blotch size (sigma of the noise the pattern is cut from), cm on the gun
BORE_MASK = 0.16         # stage finishes: what is left of tint + sheen inside the bores


def load():
    base = np.asarray(Image.open(os.path.join(L.BUILD, 'dbs_diffuse.png')).convert('RGB')).astype(np.float32)
    B = np.load(os.path.join(L.BUILD, 'skin_bake.npz'))
    M = np.load(os.path.join(L.BUILD, 'skin_masks.npz'))
    pos = B['pos'].astype(np.float32) * CM
    nrm = B['nrm'].astype(np.float32)
    return base, pos, nrm, M


def luma(a):
    a = a / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def norm(l, m, lo=2, hi=98):
    a, b = np.percentile(l[m], lo), np.percentile(l[m], hi)          # the gun's texels only (the mod: the whole sheet)
    return np.clip((l - a) / max(b - a, 1e-6), 0, 1)


def volume(pos, m, sigma_cm, seed, cell=0.5):
    """a smooth random field in gun space, sampled at every texel: random values on a `cell` cm grid, blurred"""
    lo = pos[m].min(0) - 3 * sigma_cm; hi = pos[m].max(0) + 3 * sigma_cm
    shp = np.ceil((hi - lo) / cell).astype(int) + 1
    v = np.random.default_rng(seed).random(tuple(shp)).astype(np.float32)
    v = ndi.gaussian_filter(v, sigma_cm / cell, mode='reflect')
    c = [(pos[..., k] - lo[k]) / cell for k in range(3)]
    return ndi.map_coordinates(v, c, order=1, mode='nearest')


def pad(col, M):
    """the base sheet's padding rule: every empty texel takes its nearest gun texel (seams), far ones the flat grey"""
    idx = M['idx'].astype(np.int64); dist = M['dist'].astype(np.float32)
    out = col[idx[0], idx[1]]
    out[dist > 24] = np.array([30.0, 30.0, 31.0])
    return out


def keep(M):
    return M['bore'] | M['bre'] | M['sbre'] | M['muz']


def camo(base, pos, M, pal, seed):
    m = M['mask']
    l = norm(luma(base), m)
    w = l.shape[1]
    low = ndi.gaussian_filter(l, max(2, w // 64) / 2.0)            # PIL's GaussianBlur(r) ~ sigma r; half: this atlas is ~3 x denser per cm, its islands are small
    detail = l - low
    shade = np.clip(low / max(low[m].mean(), 1e-6), 0.45, 1.55)[..., None]
    f = volume(pos, m, BLOTCH_CM, seed)
    fm = f[m]
    edges = np.quantile(fm, np.linspace(0, 1, len(pal) + 1)[1:-1])   # equal areas (the mod cuts linspace(min, max): same idea, uneven areas)
    pat = np.array(pal, np.float32)[np.digitize(f, edges)]
    out = np.clip(pat * shade + detail[..., None] * 190.0, 0, 255)
    k = keep(M)
    out[k] = base[k]
    return pad(out, M)


def bloody(base, pos, nrm, M):
    m = M['mask']
    rng = np.random.default_rng(7)
    ys, xs = np.nonzero(m & ~keep(M))
    P = pos[ys, xs]; Nn = nrm[ys, xs]
    msk = np.zeros(m.shape, np.float32)

    def pick():
        i = rng.integers(0, len(ys))
        return P[i], Nn[i]
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    for _ in range(70):                       # spatter: drops 1.5 - 5 mm
        c, n0 = pick(); r = rng.uniform(0.15, 0.5); v = rng.integers(120, 255) / 255.0
        d = np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2)
        msk = np.maximum(msk, v * np.clip((r - d) / 0.06 + 0.5, 0, 1))
    for _ in range(20):                       # soak patches: 1 - 3.5 cm, on the side they landed on
        c, n0 = pick(); rx, rz = rng.uniform(1.0, 3.5), rng.uniform(0.8, 2.6); v = rng.integers(70, 150) / 255.0
        d = np.sqrt(((x - c[0]) / rx) ** 2 + ((y - c[1]) / 1.6) ** 2 + ((z - c[2]) / rz) ** 2)
        face = (nrm @ n0) > -0.1
        edge = 0.10 * volume(pos, m, 0.35, 100 + _)          # an uneven rim
        msk = np.maximum(msk, v * np.clip((1.0 - d + edge * 4 - 0.2) / 0.12, 0, 1) * face)
    for _ in range(24):                       # runs: down the gun (gun -z), 1.5 - 6 cm, 1.2 - 3 mm wide
        c, n0 = pick(); ln = rng.uniform(1.5, 6.0); wd = rng.uniform(0.06, 0.15); v = rng.integers(90, 190) / 255.0
        across = np.sqrt((x - c[0]) ** 2 + ((y - c[1]) * (abs(n0[1]) < 0.6)) ** 2)
        face = ((nrm @ n0) > 0.2) & (np.abs(y - c[1]) < 1.2)
        along = (c[2] - z)
        body = np.clip((wd - across) / 0.03 + 0.5, 0, 1) * np.clip(along / 0.1, 0, 1) * np.clip((ln - along) / (0.35 * ln), 0, 1)
        msk = np.maximum(msk, v * body * face)
    msk = ndi.gaussian_filter(msk, max(1, m.shape[1] // 500) / 2.0)[..., None]
    blood = np.array([102, 12, 10], np.float32)
    out = base * 0.55 * msk + base * (1 - msk) + blood * msk * 0.75
    k = keep(M)
    out[k] = base[k]
    return pad(np.clip(out, 0, 255), M), float((msk[..., 0][m] > 0.2).mean())


def shader_block(name, tex, kind, params):
    Ls = ['', name, '{', '\tqer_editorimage %s' % tex, '\t{', '\t\tmap %s' % tex, '\t\trgbGen lightingSpherical', '\t}']
    if kind == 'stage':
        Ls += ['\t{', '\t\tmap $whiteimage', '\t\tblendFunc GL_DST_COLOR GL_ZERO', '\t\trgbGen const %.2f %.2f %.2f' % params['tint'], '\t}']
        Ls += ['\t{', '\t\tmap %s' % ENVMAP, '\t\tblendFunc add', '\t\ttcGen environment', '\t\trgbGen const %.2f %.2f %.2f' % params['env'], '\t}']
        # ours: the bores stay dark holes under the tint and the sheen
        Ls += ['\t{', '\t\tmap %s%s_fmask.jpg' % (TEXV, NAME), '\t\tblendFunc GL_DST_COLOR GL_ZERO', '\t}']
    Ls.append('}')
    return '\n'.join(Ls)


def used_ranks():
    ranks = set()
    pats = [os.path.join(L.DOCS, '..', 'hzm-mohaa-coop-mod', 'models', 'weapons', '*.tik'),
            os.path.join(L.DOCS, 'proposals', '*', 'assets', 'models', 'weapons', '*.tik'),
            os.path.join(L.DOCS, 'proposals', '*', '*', 'assets', 'models', 'weapons', '*.tik')]
    mine = re.compile(r'%s_[a-z_]+\.tik$' % NAME)
    for pat in pats:
        for p in glob.glob(pat):
            if mine.search(os.path.basename(p)):
                continue                                             # our own finish tiks are rewritten below
            for mm in re.finditer(r'(?mi)^\s*rank\s+(\d+)', io.open(p, encoding='latin-1', errors='replace').read()):
                ranks.add(int(mm.group(1)))
    return ranks


def variant_tik(base_text, rank, key):
    t, n1 = re.subn(r'(?mi)^(\s*rank\s+)\d+\s+\d+', lambda m: '%s%d %d' % (m.group(1), rank, rank), base_text, count=1)
    t, n2 = re.subn(r'(?mi)^(\s*surface\s+dbs\d+\s+shader\s+)%s[ \t]*$' % NAME, lambda m: '%s%s_%s' % (m.group(1), NAME, key), t)
    assert n1 == 1 and n2 == 12, (n1, n2)
    assert 'surface dbsx1 shader %s_parts' % NAME in t
    return t


def build():
    base, pos, nrm, M = load()
    os.makedirs(TDIR, exist_ok=True)
    m = M['mask']
    for key, fid, kind, pr in FINISHES:
        if kind != 'bake':
            continue
        if key == 'bloody':
            out, cov = bloody(base, pos, nrm, M)
            print('%-14s blood on %.1f %% of the gun' % (key, 100 * cov))
        else:
            out = camo(base, pos, M, pr['pal'], pr['seed'])
            print('%-14s mean rgb of the gun %s' % (key, out[m].mean(0).round(1)))
        im = Image.fromarray(out.astype(np.uint8))
        im.save(os.path.join(L.BUILD, 'dbs_%s.png' % key))
        im.save(os.path.join(TDIR, '%s_%s.jpg' % (NAME, key)), quality=92, subsampling=0)
    # the stage finishes' bore mask (1024: the bores are large on the atlas)
    fm = np.where(M['bore'], BORE_MASK, 1.0).astype(np.float32)
    fm = ndi.gaussian_filter(pad(np.repeat(fm[..., None], 3, 2) * 255.0, M)[..., 0], 1.2)
    fm[M['dist'].astype(np.float32) > 24] = 255.0
    Image.fromarray(fm.astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).convert('RGB').save(os.path.join(TDIR, NAME + '_fmask.jpg'), quality=92)
    # shaders
    blocks = ['// HZM coop: double-barrel shotgun - the FINISH SET (tools/dbs_finish.py; the mod\'s recipe, gen_skins.py)',
              '// NEW names, defined in this one file only (TRAPS T6)']
    for key, fid, kind, pr in FINISHES:
        tex = TEXV + (NAME + '.jpg' if kind == 'stage' else '%s_%s.jpg' % (NAME, key))
        blocks.append(shader_block('%s_%s' % (NAME, key), tex, kind, pr))
    open(os.path.join(L.ASSETS, 'scripts', NAME + '_finish.shader'), 'w', newline='\r\n').write('\n'.join(blocks) + '\n')
    # tiks
    bt = io.open(os.path.join(L.ASSETS, 'models', 'weapons', NAME + '.tik'), encoding='latin-1', newline='').read()
    taken = used_ranks()
    rank = max(3000, max(taken) + 1)
    for key, fid, kind, pr in FINISHES:
        while rank in taken:
            rank += 1
        taken.add(rank)
        io.open(os.path.join(L.ASSETS, 'models', 'weapons', '%s_%s.tik' % (NAME, key)), 'w', encoding='latin-1', newline='').write(variant_tik(bt, rank, key))
        print('%s_%s.tik  fid %d  rank %d  %s' % (NAME, key, fid, rank, kind))


def view():
    """offline: the base and the four baked sheets, flat, side by side (small)"""
    tiles = []
    for nm in ['diffuse'] + [k for k, _, kd, _ in FINISHES if kd == 'bake']:
        tiles.append(Image.open(os.path.join(L.BUILD, 'dbs_%s.png' % nm)).convert('RGB').resize((640, 640), Image.LANCZOS))
    W = Image.new('RGB', (640 * len(tiles), 640))
    for i, t in enumerate(tiles):
        W.paste(t, (640 * i, 0))
    W.save(os.path.join(L.BUILD, '_fin_view.jpg'), quality=88)
    print('wrote build/_fin_view.jpg')


if __name__ == '__main__':
    view() if 'view' in sys.argv[1:] else build()
