"""finishes2 - OFFLINE preview, sheet 2: every new finish on a few guns, side view (the visible side), the gun's own texture
composited in texture space the way the in-game shaders will do it, now driven by the gun's own mesh (finishlib):
  * patterns at REAL size: tile repeats per UV = the sheet's model units per UV / the pattern's physical size (QA 3)
  * a per-gun wear mask: muzzle crown, bore and sights stay bare, UV-island edges worn through (QA 4)
  * decals at the verified spot (orient_check.place_verified: upright, unmirrored, whole) (QA: upside-down marks)
  * trench art = the gun's own wood and steel + brass plates (buttplate, the crest plate) (QA 1)
  * whitewash = mostly white hand-brushed coat worn to dark at the edges, neutral, no pink (QA 2)
  * Kriegsmarine = dark grey, salt bloom, rust run down from points of the receiver in world space (QA 5)
    python finish_sheet.py <out.jpg> <tik>:<class> [<tik>:<class> ...]   [FINISHES=a,b,c]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finishlib as fl  # noqa: E402
import orient_check as oc  # noqa: E402
import gungeo, raster, uvview  # noqa: E402

TILES = os.path.join(HERE, '..', 'assets', 'tiles')
DECALS = os.path.join(HERE, '..', 'assets', 'decals')
GERMAN = ('kar98', 'mp40', 'mp44', 'g43', 'fg42', 'mg42', 'p38', 'luger', 'panzer', 'stg', 'walther', 'c96', 'gewehr')
# physical size of one tile, cm (the in-game tcMod scale = world_per_uv / (cm * U_PER_CM))
TILE_CM = {'camo_splitter': 34, 'camo_pea': 22, 'camo_telo': 40, 'camo_amoeba': 44, 'camo_whitewash': 16,
           'wear_chips': 16, 'wear_scratch': 18, 'engrave_vines': 10}
FINISHES = ['battleworn', 'trenchart', 'parade', 'captured', 'airborne', 'airborne101', 'ffi', 'dak', 'kriegsmarine',
            'splitter', 'pea', 'telo', 'amoeba', 'whitewash']
DECAL_OF = {'trenchart': 'trench_plate', 'parade': 'plaque', 'airborne': 'ab82', 'airborne101': 'ab101', 'ffi': 'lorraine', 'dak': 'dak_palm'}
_T = {}


def tile(name):
    if name not in _T:
        _T[name] = np.asarray(Image.open(os.path.join(TILES, name + '.png')).convert('RGBA'), float) / 255.0
    return _T[name]


def decal(name):
    p = os.path.join(DECALS, name + '.png')
    if name == 'trench_plate' and not os.path.exists(p):
        make_trench_plate(p)
    im = Image.open(p).convert('RGBA')
    w, h = im.size                               # pad to a square, centred (the stage maps [0,1]^2)
    S = max(w, h)
    sq = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sq.paste(im, ((S - w) // 2, (S - h) // 2))
    return np.asarray(sq, float) / 255.0


def make_trench_plate(path):
    """a brass oval plate, engraved vine border, the crest engraved in the middle"""
    K, S = 4, 512
    im = Image.new('RGBA', (S * K, S * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = [S * K * 0.06, S * K * 0.14, S * K * 0.94, S * K * 0.86]
    d.ellipse(box, fill=(132, 92, 30, 255))
    inset = [box[0] + 10 * K, box[1] + 10 * K, box[2] - 10 * K, box[3] - 10 * K]
    d.ellipse(inset, fill=(214, 168, 78, 255))
    hl = [inset[0] + 40 * K, inset[1] + 24 * K, inset[2] - 120 * K, inset[1] + 120 * K]
    d.ellipse(hl, fill=(236, 200, 120, 255))
    d.ellipse([inset[0] + 46 * K, inset[1] + 70 * K, inset[2] - 46 * K, inset[3] - 10 * K], fill=(214, 168, 78, 255))
    ink = (88, 58, 18, 255)
    cx, cy = S * K / 2, S * K / 2
    rx, ry = (inset[2] - inset[0]) / 2 - 22 * K, (inset[3] - inset[1]) / 2 - 22 * K
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=ink, width=3 * K)
    for i in range(36):                          # the vine: a leaf pair every 10 degrees along the border
        a = 2 * math.pi * i / 36
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        for s in (-1, 1):
            b = a + math.pi / 2 + s * 0.7
            d.ellipse([x + math.cos(b) * 9 * K - 6 * K, y + math.sin(b) * 9 * K - 3 * K,
                       x + math.cos(b) * 9 * K + 6 * K, y + math.sin(b) * 9 * K + 3 * K], fill=ink)
    crest = Image.open(os.path.join(DECALS, 'crest.png')).convert('RGBA').resize((int(S * K * 0.5),) * 2, Image.LANCZOS)
    ca = np.asarray(crest).copy()
    ca[..., :3] = ink[:3]
    crest = Image.fromarray(ca)
    im.alpha_composite(crest, (int(cx - crest.width / 2), int(cy - crest.height / 2)))
    im.resize((S, S), Image.LANCZOS).save(path)


def tiled(t, H, W, rep):
    th, tw = t.shape[:2]
    ys = (np.arange(H)[:, None] * rep * th / H).astype(int) % th
    xs = (np.arange(W)[None, :] * rep * tw / W).astype(int) % tw
    return t[ys, xs]


def lum(a):
    return a[..., :3] @ np.array([0.299, 0.587, 0.114])


def shade(base):
    L = lum(base)[..., None]
    return L / max(float(np.median(L)), 1e-3)


def paint_shade(base):
    """how much of the gun's own light / dark shows THROUGH a coat of paint: only the broad shape (a heavy low-pass), and
    only a little - paint is opaque, so no wood grain, no tool marks (coordinator QA: the grain showed through)"""
    from scipy import ndimage as nd
    L = lum(base)
    broad = nd.gaussian_filter(L, max(2.0, base.shape[1] / 48.0))
    # plus ~35 % of the mid-scale light / dark (bevels, edges, the sheet's specular): blurred enough that wood grain and
    # tool marks are gone (coordinator QA: the coats looked flat and plasticky in the viewer)
    mid = nd.gaussian_filter(L, max(1.5, base.shape[1] / 220.0))
    med = max(float(np.median(L)), 1e-3)
    sh = np.clip(broad / med, 0.82, 1.06) * (1 + 0.35 * (mid - broad) / med)
    return np.clip(sh, 0.6, 1.3)[..., None]


def coat(base, rgb, keep=0.45):
    """a paint colour shaded by the texture's own light / dark (keep = how much of the shading survives the paint)"""
    return np.clip(np.array(rgb, float)[None, None, :] / 255.0 * paint_shade(base), 0, 1)


def over(a, b, m):
    m = m[..., None] if m.ndim == 2 else m
    return a * (1 - m) + b * m


def rust_runs(P, lo, hi, seed=7):
    """rust streaks running DOWN the gun from a few points on the receiver, in model space (so they hang the right way on
    every UV island): strength per texel"""
    rng = np.random.default_rng(seed)
    L = hi[0] - lo[0]
    out = np.zeros(P.shape[:2])
    x, z = P[..., 0], P[..., 2]
    ok = np.isfinite(x)
    x, z = np.where(ok, x, 0), np.where(ok, z, 0)
    for _ in range(9):
        xs = lo[0] + L * rng.uniform(0.25, 0.8)
        zs = lo[2] + (hi[2] - lo[2]) * rng.uniform(0.45, 0.85)
        w = L * rng.uniform(0.004, 0.008)
        ln = (hi[2] - lo[2]) * rng.uniform(0.15, 0.4)
        dz = zs - z
        s = np.exp(-((x - xs) / w) ** 2) * (dz > 0) * np.exp(-np.maximum(dz, 0) / ln)
        out = np.maximum(out, s)
    return out * ok


def finish_tex(fin, base, ctx):
    """base RGBA [H,W,4] float -> RGB. ctx: rep(name) tile repeats on this sheet, mask (1 = finish, 0 = bare), P (texel
    model points), lo/hi"""
    H, W = base.shape[:2]
    rgb = base[..., :3]
    m = ctx['mask']
    chips = tiled(tile('wear_chips'), H, W, ctx['rep']('wear_chips'))[..., 3]
    paint_m = m * chips                                        # where a coat survives
    if fin == 'battleworn':
        s = tiled(tile('wear_scratch'), H, W, ctx['rep']('wear_scratch'))[..., 0]
        out = rgb * 0.84
        bare = (1 - m) * 0.85 + (1 - chips) * 0.5
        out = over(out, np.clip(0.55 + 0.5 * (shade(base) - 1), 0.3, 0.8) * np.array([1.0, 0.98, 0.94]), np.clip(bare, 0, 0.8))
        return np.clip(out + (1 - s)[..., None] * 0.45, 0, 1)
    if fin == 'trenchart':
        P = ctx['P']
        lo, hi = ctx['lo'], ctx['hi']
        L = hi[0] - lo[0]
        butt = np.nan_to_num(P[..., 0], nan=1e9) < lo[0] + 0.025 * L          # the buttplate / grip cap: brass
        brass = np.clip(np.array([0.86, 0.66, 0.30]) * (0.45 + 0.75 * lum(base)[..., None] / max(lum(base).mean(), 1e-3) * 0.6), 0, 1)
        v = tiled(tile('engrave_vines'), H, W, ctx['rep']('engrave_vines'))[..., 3]
        brass_e = brass * (1 - 0.6 * v[..., None])
        return over(rgb, brass_e, butt * 1.0)
    if fin == 'parade':
        mx, mn = rgb.max(-1), rgb.min(-1)
        sat = (mx - mn) / np.maximum(mx, 1e-3)
        wood = np.clip((sat - 0.18) / 0.2, 0, 1)[..., None] * (rgb[..., 0:1] > rgb[..., 2:3])
        L = lum(base)[..., None]
        walnut = np.clip((rgb - 0.5) * 1.25 + 0.5, 0, 1) * np.array([1.02, 0.95, 0.88])
        nickel = np.clip(0.5 + 0.6 * (L - L.mean()) + 0.12, 0, 1) * np.array([0.92, 0.94, 0.97])
        return walnut * wood + nickel * (1 - wood)
    if fin == 'captured':
        return rgb * 0.95
    if fin in ('airborne', 'airborne101'):
        return over(rgb, coat(base, (88, 86, 56)), paint_m)
    if fin == 'ffi':
        return rgb * (0.88 + 0.12 * chips[..., None])
    if fin == 'dak':
        return over(rgb, coat(base, (194, 166, 106)), paint_m)
    if fin == 'kriegsmarine':
        out = over(rgb, coat(base, (52, 56, 60), keep=0.45), paint_m)
        salt = np.asarray(Image.fromarray((tiled(tile('camo_pea'), H, W, ctx['rep']('camo_pea'))[..., 0] * 255).astype(np.uint8))
                          .filter(ImageFilter.GaussianBlur(max(2, W // 120))), float) / 255.0
        bloom = np.clip((salt - 0.55) * 3.0, 0, 1) * 0.45 * m
        out = over(out, np.array([0.84, 0.86, 0.85]), bloom)
        r = rust_runs(ctx['P'], ctx['lo'], ctx['hi'])
        return over(out, np.array([0.46, 0.24, 0.11]) * (0.7 + 0.3 * shade(base)), np.clip(r * 0.75, 0, 0.75))
    if fin in ('splitter', 'pea', 'telo', 'amoeba'):
        pat = tiled(tile('camo_' + fin), H, W, ctx['rep']('camo_' + fin))[..., :3]
        pat = np.clip(pat * {'splitter': 1.0, 'pea': 1.0, 'telo': 1.0, 'amoeba': 1.0}[fin], 0, 1)
        cam = np.clip(pat * paint_shade(base), 0, 1)
        return over(rgb, cam, paint_m)
    if fin == 'whitewash':
        w = tiled(tile('camo_whitewash'), H, W, ctx['rep']('camo_whitewash'))[..., 3]
        white = np.clip(np.array([0.84, 0.84, 0.82]) * paint_shade(base) * (0.88 + 0.12 * w[..., None]), 0, 1)
        cover = np.clip(0.30 + 0.85 * w, 0, 1) * m ** 2 * (0.55 + 0.45 * chips)        # brushed, worn at the edges
        return over(rgb * 0.8, white, np.clip(cover, 0, 0.96))
    raise KeyError(fin)


def build_ctx(g, sh, H, W):
    wpu = fl.world_per_uv(g, sh)
    Hs, Ws = min(H, 512), min(W, 512)
    P, _N, edge = fl.texel_world(g, sh, Ws, Hs)
    m = fl.wear_mask(g, sh, Ws, Hs, P=P, edge=edge)
    if (Hs, Ws) != (H, W):
        m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), float) / 255.0
        P = np.stack([np.asarray(Image.fromarray(np.nan_to_num(P[..., i], nan=1e9).astype(np.float32)).resize((W, H), Image.NEAREST))
                      for i in range(3)], -1)
        P[P > 1e8] = np.nan
    lo, hi = fl.gun_box(g)
    return dict(mask=m, P=P, lo=lo, hi=hi, wpu=wpu, rep=lambda name: wpu / (TILE_CM[name] * fl.U_PER_CM))


def render(tik, cls, fin, W=520, H=200, pl_cache={}, side=None):
    g = fl.load_gun(tik)
    german = any(k in tik.lower() for k in GERMAN)
    dname = DECAL_OF.get(fin) or (('souvenir' if german else 'waa') if fin == 'captured' else None)
    if dname:
        key = (tik, 'receiver' if fin == 'captured' and not german else oc.KIND.get(cls, 'grip'))
        if key not in pl_cache:                  # the Armory-side decal, then the first-person-side one (no shared texel)
            pa = oc.place_verified(g, key[1], side=fl.ARMORY)[0]
            pf = oc.place_verified(g, 'receiver', side=fl.FIRSTPERSON, avoid=[pa] if pa else [], allow_shared=False)[0]
            pl_cache[key] = [p for p in (pa, pf) if p]
        pls = pl_cache[key]
    else:
        pls = []
    cache = {}
    real = uvview.shader_image

    def shader_image(sh):
        if sh not in cache:
            m, p, pk, im, blk = real(sh)
            if im is None:
                cache[sh] = (m, p, pk, im, blk)
            else:
                base = np.asarray(im.convert('RGBA'), float) / 255.0
                ctx = build_ctx(g, sh, *base.shape[:2])
                img = np.dstack([finish_tex(fin, base, ctx), base[..., 3:4]])
                for pl in pls:
                    if sh != pl['shader']:
                        continue
                    dec = decal(dname)
                    if dname == 'waa':                       # a die-struck mark on blued steel reads bright, not inked
                        dec = dec.copy()
                        dec[..., :3] = np.array([0.80, 0.80, 0.76])
                    img = fl.stamp(img, pl, dec)
                cache[sh] = (m, p, pk, Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA'), blk)
        return cache[sh]
    uvview.shader_image = shader_image
    try:
        lo, hi = fl.gun_box(g)
        c = (lo + hi) / 2
        ext = max(hi[0] - lo[0], (hi[2] - lo[2]) * W / H)
        dist = ext * 6.0
        rgb, ids, dep = raster.render(g, c + np.array([0, (side or fl.ARMORY) * dist, 0]), c, np.array([0, 0, 1.0]),
                                      fov=2 * math.degrees(math.atan(ext * 0.55 / dist)), W=W, H=H, tex=True, bg=(58, 60, 64))
    finally:
        uvview.shader_image = real
    return Image.fromarray(rgb)


def main():
    out, guns = sys.argv[1], [a.split(':') for a in sys.argv[2:]]
    fins = os.environ.get('FINISHES', ','.join(FINISHES)).split(',')
    W, H = 420, 160
    sheet = Image.new('RGB', (len(guns) * (W + 6) + 110, len(fins) * (H + 4)), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    for j, f in enumerate(fins):
        d.text((6, j * (H + 4) + H // 2 - 6), f, fill=(235, 210, 120))
        for i, (t, cls) in enumerate(guns):
            try:
                sheet.paste(render(t, cls, f, W, H), (110 + i * (W + 6), j * (H + 4)))
            except Exception as e:
                d.text((110 + i * (W + 6) + 6, j * (H + 4) + 6), 'ERR %s' % repr(e)[:60], fill=(255, 80, 80))
        print(f, flush=True)
    sheet.save(out, quality=88)
    print('wrote', out)


if __name__ == '__main__':
    main()
