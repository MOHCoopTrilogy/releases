"""finishes2 - OFFLINE preview: every new finish on a few guns, side view, the gun's own texture composited in texture space the
way the in-game shaders will do it (a shared pattern / wear tile tiled over the UVs, a paint layer with the chip mask, one
decal placed on the stock by the UV->model affine fitted on the stock's side faces).

    python finish_sheet.py <out.jpg> <tik> [<tik> ...]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
IS = os.path.join(HERE, '..', '..', 'ironsights_2026-09-28', 'tools')
sys.path.insert(0, IS)
import gungeo, raster, uvview  # noqa: E402

TILES = os.path.join(HERE, '..', 'assets', 'tiles')
DECALS = os.path.join(HERE, '..', 'assets', 'decals')
TILE_REPEAT = 2.5                     # pattern repeats per UV unit (in game: tcMod scale 2.5 2.5)
GERMAN = ('kar98', 'mp40', 'mp44', 'g43', 'fg42', 'mg42', 'p38', 'luger', 'panzer', 'stg', 'walther', 'c96', 'gewehr')


def tile(name):
    return np.asarray(Image.open(os.path.join(TILES, name + '.png')).convert('RGBA'), float) / 255.0


def decal(name):
    return np.asarray(Image.open(os.path.join(DECALS, name + '.png')).convert('RGBA'), float) / 255.0


def tiled(t, H, W):
    """the tile laid over a W x H texture at TILE_REPEAT repeats across it (nearest sample, as GL_REPEAT does)"""
    th, tw = t.shape[:2]
    ys = (np.arange(H)[:, None] * TILE_REPEAT * th / H).astype(int) % th
    xs = (np.arange(W)[None, :] * TILE_REPEAT * tw / W).astype(int) % tw
    return t[ys, xs]


def lum(a):
    return a[..., :3] @ np.array([0.299, 0.587, 0.114])


def paint(base, rgb, chips_alpha, keep=0.35):
    """a paint coat: its colour shaded by the texture's own light/dark (keep), chipped where the chip mask is clear"""
    L = lum(base)[..., None]
    coat = np.array(rgb, float)[None, None, :] / 255.0 * (1 - keep + keep * L / max(L.mean(), 1e-3))
    a = chips_alpha[..., None]
    return base[..., :3] * (1 - a) + np.clip(coat, 0, 1) * a


def camo(base, pat):
    L = lum(base)[..., None]
    return np.clip(pat[..., :3] * (0.30 + 0.62 * L / max(L.mean(), 1e-3)), 0, 1)


FINISHES = ['battleworn', 'trenchart', 'parade', 'captured', 'airborne', 'ffi', 'dak', 'kriegsmarine',
            'splitter', 'pea', 'telo', 'amoeba', 'whitewash']
DECAL_OF = {'trenchart': 'crest', 'parade': 'plaque', 'airborne': 'ab82', 'ffi': 'lorraine', 'dak': 'dak_palm'}


def finish_tex(fin, base, german):
    H, W = base.shape[:2]
    chips = tiled(tile('wear_chips'), H, W)[..., 3]
    if fin == 'battleworn':
        sc = 1 - tiled(tile('wear_scratch'), H, W)[..., 0] if tile('wear_scratch').ndim == 3 else None
        s = 1 - tiled(tile('wear_scratch'), H, W)[..., 0]
        out = base[..., :3] * 0.88
        bare = 1 - chips
        out = out * (1 - bare[..., None] * 0.7) + np.array([0.62, 0.6, 0.56]) * bare[..., None] * 0.7
        out = np.clip(out + s[..., None] * 1.6, 0, 1)
        return out
    if fin == 'trenchart':
        L = lum(base)[..., None]
        out = np.clip(np.array([0.86, 0.64, 0.28]) * (0.35 + 1.2 * L), 0, 1)
        v = tiled(tile('engrave_vines'), H, W)
        return out * (1 - v[..., 3:4] * 0.75)
    if fin == 'parade':
        rgb = base[..., :3]
        mx, mn = rgb.max(-1), rgb.min(-1)
        sat = (mx - mn) / np.maximum(mx, 1e-3)
        wood = np.clip((sat - 0.18) / 0.2, 0, 1)[..., None] * (rgb[..., 0:1] > rgb[..., 2:3])
        L = lum(base)[..., None]
        walnut = np.clip((rgb - 0.5) * 1.25 + 0.5, 0, 1) * np.array([1.02, 0.95, 0.88])
        nickel = np.clip(0.5 + 0.6 * (L - L.mean()) + 0.12, 0, 1) * np.array([0.92, 0.94, 0.97])
        return walnut * wood + nickel * (1 - wood)
    if fin == 'captured':
        return base[..., :3] * 0.95
    if fin == 'airborne':
        return paint(base, (92, 88, 56), chips)
    if fin == 'ffi':
        return base[..., :3] * (0.9 + 0.1 * chips[..., None])
    if fin == 'dak':
        worn = np.clip(chips * 1.0 - (1 - tiled(tile('camo_whitewash'), H, W)[..., 3]) * 0.25, 0, 1)
        return paint(base, (196, 168, 108), worn)
    if fin == 'kriegsmarine':
        out = paint(base, (116, 122, 128), chips)
        salt = tiled(tile('camo_pea'), H, W)
        spots = (lum(salt) > 0.62)[..., None]
        return np.clip(out * (1 - spots * 0.35) + spots * 0.35 * np.array([0.86, 0.87, 0.86]), 0, 1)
    if fin in ('splitter', 'pea', 'telo', 'amoeba'):
        return camo(base, tiled(tile('camo_' + fin), H, W))
    if fin == 'whitewash':
        w = tiled(tile('camo_whitewash'), H, W)
        L = lum(base)[..., None]
        white = np.clip(w[..., :3] * (0.7 + 0.5 * L / max(L.mean(), 1e-3)), 0, 1)
        a = np.clip(w[..., 3:4] * 1.4 - 0.62, 0, 1) * 0.85           # thinner: the gun shows through the brush gaps
        return base[..., :3] * (1 - a) + white * a
    raise KeyError(fin)


def stock_affine(g):
    """-> the decal's place on the gun, from its own mesh: the side-facing (|n_y| > 0.75, facing the viewer at -y) faces are
    split into connected UV islands; the biggest island whose centre lies in the rear 60 % of the gun wins (a rifle's
    butt, a pistol's grip panel or slide, an SMG's receiver side). Returns (area, shader, UV->(x,z) affine, centre, size,
    island triangles, UV)."""
    P = np.concatenate([s['P'] for s in g['surfs']])
    x0, x1 = P[:, 0].min(), P[:, 0].max()
    best = None
    for s in g['surfs']:
        V, UV, T = s['P'], s['UV'], s['tri']
        if len(T) == 0:
            continue
        n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        area = np.linalg.norm(n, axis=1)
        ny = n[:, 1] / np.maximum(area, 1e-9)
        idx = np.nonzero((ny < -0.75) & (area > 1e-6))[0]
        if len(idx) < 2:
            continue
        par = {}
        def find(a):
            while par.setdefault(a, a) != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        owner = {}
        for ti in idx:                                   # union triangles that share a vertex
            for vi in T[ti]:
                if vi in owner:
                    ra, rb = find(owner[vi]), find(ti)
                    if ra != rb:
                        par[ra] = rb
                else:
                    owner[vi] = ti
        groups = {}
        for ti in idx:
            groups.setdefault(find(ti), []).append(ti)
        for tl in groups.values():
            tl = np.array(tl)
            A = area[tl].sum()
            c = np.average(V[T[tl]].mean(1), axis=0, weights=area[tl])
            if c[0] > x0 + 0.6 * (x1 - x0) or len(tl) < 2:
                continue
            if best is None or A > best[0]:
                vi = np.unique(T[tl].ravel())
                aff, *_ = np.linalg.lstsq(np.c_[UV[vi], np.ones(len(vi))], V[vi][:, [0, 2]], rcond=None)
                size = 0.48 * min(np.ptp(V[vi][:, 2]), np.ptp(V[vi][:, 0]))
                best = (A, s['shader'], aff, (c[0], c[2]), size, T[tl], UV)
    return best


def stamp(img, shader_hit, best, dec):
    """composite the decal into the texture over the stock's side faces (their UV triangles), sampled through the affine"""
    A_, shader, aff, (cx, cz), size, tris, UV = best
    H, W = img.shape[:2]
    mask = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(mask)
    for t in tris:
        dr.polygon([(UV[i][0] % 1.0 * W, UV[i][1] % 1.0 * H) for i in t], fill=255)
    m = np.asarray(mask) > 0
    ys, xs = np.nonzero(m)
    u, v = xs / W, ys / H
    xz = np.c_[u, v, np.ones(len(u))] @ aff
    du = (xz[:, 0] - cx) / size + 0.5
    dv = 0.5 - (xz[:, 1] - cz) / size
    ok = (du >= 0) & (du < 1) & (dv >= 0) & (dv < 1)
    dh, dw = dec.shape[:2]
    px = dec[(dv[ok] * dh).astype(int), (du[ok] * dw).astype(int)]
    a = px[:, 3:4]
    img[ys[ok], xs[ok], :3] = img[ys[ok], xs[ok], :3] * (1 - a) + px[:, :3] * a
    return img


def render(tik, fin, W=520, H=200):
    g = gungeo.load_gun(tik)
    german = any(k in tik.lower() for k in GERMAN)
    best = stock_affine(g)
    dname = DECAL_OF.get(fin) or (('souvenir' if german else 'waa') if fin == 'captured' else None)
    cache = {}
    real = uvview.shader_image

    def shader_image(sh):
        if sh not in cache:
            m, p, pk, im, blk = real(sh)
            if im is None:
                cache[sh] = (m, p, pk, im, blk)
            else:
                base = np.asarray(im.convert('RGBA'), float) / 255.0
                out = finish_tex(fin, base, german)
                img = np.dstack([out, base[..., 3:4]])
                if dname and best is not None and sh == best[1]:
                    img = stamp(img, sh, best, decal(dname))
                cache[sh] = (m, p, pk, Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA'), blk)
        return cache[sh]
    uvview.shader_image = shader_image
    try:
        P = np.concatenate([s['P'] for s in g['surfs']])
        c = (P.min(0) + P.max(0)) / 2
        ext = max(np.ptp(P[:, 0]), np.ptp(P[:, 2]) * W / H)
        dist = ext * 6.0
        eye = c + np.array([0, -dist, 0])
        rgb, ids, dep = raster.render(g, eye, c, np.array([0, 0, 1.0]), fov=2 * math.degrees(math.atan(ext * 0.55 / dist)), W=W, H=H,
                                      tex=True, bg=(58, 60, 64))
    finally:
        uvview.shader_image = real
    return Image.fromarray(rgb)


def main():
    out, tiks = sys.argv[1], sys.argv[2:]
    W, H = 420, 160
    fins = FINISHES
    sheet = Image.new('RGB', (len(tiks) * (W + 6) + 110, len(fins) * (H + 4)), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    for j, f in enumerate(fins):
        d.text((6, j * (H + 4) + H // 2 - 6), f, fill=(235, 210, 120))
        for i, t in enumerate(tiks):
            try:
                im = render(t, f, W, H)
                sheet.paste(im, (110 + i * (W + 6), j * (H + 4)))
            except Exception as e:
                d.text((110 + i * (W + 6) + 6, j * (H + 4) + 6), 'ERR %s' % repr(e)[:60], fill=(255, 80, 80))
        print(f, flush=True)
    sheet.save(out, quality=86)
    print('wrote', out)


if __name__ == '__main__':
    main()
