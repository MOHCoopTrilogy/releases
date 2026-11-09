"""Nose art, take 2: recreated from PUBLIC-DOMAIN WWII photographs (US government / NARA / USAAF via Wikimedia Commons; the
source list with URLs and licences is assets/noseart_sources.tsv and docs/SKIN_CREDITS.md). The artwork's own shapes are
lifted from the photos - the sign painter's actual letterforms and the actual AVG shark mouth - and repainted in a period
palette with a brush-paint finish: streaky coverage, a softly irregular edge, chips down to the metal, faded.
No modern fonts are used anywhere in this set.

  shark_mouth    the AVG P-40 shark mouth and eye (NARA 535531, c.1942)
  liberty_belle  "LIBERTY BELLE" in the B-24's own hand-painted capitals (41-23920, c.1943); BELLE is set from the same
                 painter's B, E and L because the figure covers part of the original word
  bonnie         "Bonnie" in the original sign-painter script (B-24, Library of Congress, c.1945)
  bomb_tally     mission tally: painted bomb silhouettes in rows, after the tallies on the same aircraft

    python -E -P noseart2.py <download dir>        (read the downloads isolated: no module search in their directory)
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets', 'decals')
MEDIA = os.path.join(HERE, '..', 'media')
# a 1940s sign-painter's kit: lacquers as they look after a season in the sun
PAL = dict(white=(226, 220, 198), yellow=(214, 172, 56), red=(160, 40, 34), black=(30, 28, 26), blue=(58, 84, 122),
           od=(84, 82, 52))


def load(src, name):
    return Image.open(os.path.join(src, name)).convert('L')


# ---------------------------------------------------------------------------------------------------------- the finish
def paint(masks, seed, size=None, fade=0.18, chip=0.035):
    """masks: [(alpha float HxW, rgb, tone float HxW or None)], drawn in order. Returns RGBA uint8.
    tone carries the photo's own light/dark inside the shape (brush ridges, grime) at a low gain; on top a streaky brush
    texture along the painter's stroke, chips through to the metal (transparent, with a pale burnished rim) and an overall
    fade toward warm grey."""
    rng = np.random.default_rng(seed)
    H, W = masks[0][0].shape
    rgb = np.zeros((H, W, 3))
    a = np.zeros((H, W))
    streak = rng.normal(0, 1, (H, W))
    streak = nd.gaussian_filter(streak, (0.6, 9.0))                 # long along x: horizontal brush strokes
    streak = streak / (streak.std() + 1e-6)
    for m, col, tone in masks:
        c = np.array(col, float)[None, None, :] / 255.0
        if tone is None:
            t = 1.0
        else:                       # the photo's paint texture only (high-pass): not the light falling on the curved skin
            t = (1.0 + 0.45 * (tone - nd.gaussian_filter(tone, 10)))[..., None]
        layer = np.clip(c * t * (1 + 0.05 * streak[..., None]), 0, 1)
        rgb = rgb * (1 - m[..., None]) + layer * m[..., None]
        a = np.maximum(a, m)
    # irregular brushed edge
    n = nd.gaussian_filter(rng.random((H, W)), 1.2)
    a = np.clip((nd.gaussian_filter(a, 0.8) - 0.5 + 0.35 * (n - 0.5)) * 3 + 0.5, 0, 1) * (a > 0.02)
    # chips: flakes where a noise field peaks, more toward the edges of the shape
    flakes = nd.gaussian_filter(rng.random((H, W)), max(3.0, min(H, W) / 160))
    thr = np.quantile(flakes, 1 - chip)
    edge = nd.gaussian_filter((a > 0.5).astype(float), 6)
    holes = (flakes > thr - 0.02 * (1 - edge)) & (a > 0.5)
    holes = nd.binary_opening(holes, iterations=1)
    rim = nd.binary_dilation(holes, iterations=2) & ~holes & (a > 0.5)
    rgb[rim] = rgb[rim] * 0.5 + np.array([0.80, 0.80, 0.78]) * 0.5
    a[holes] = 0
    # fade: toward a warm grey, blacks lifted
    L = rgb @ np.array([0.3, 0.59, 0.11])
    rgb = rgb * (1 - fade) + (L[..., None] * np.array([1.02, 1.0, 0.94])) * fade
    rgb = 0.04 + rgb * 0.94
    out = Image.fromarray(np.dstack([np.clip(rgb, 0, 1) * 255, a * 255]).astype(np.uint8), 'RGBA')
    if size:
        out = out.resize(size, Image.LANCZOS)
    return out


def trim(im, pad=6):
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > 8)
    return im.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, im.width), min(ys.max() + pad, im.height)))


# ---------------------------------------------------------------------------------------------------------- the pieces
# the mouth's outer edge on NARA 535531, traced by hand on the crop (160, 20)-(1130, 650) of the 1920 px copy; the front
# end is closed straight at the cowl seam (the photo's mouth wraps round the cowling there)
SHARK_POLY = [(12, 522), (60, 470), (120, 410), (180, 360), (250, 307), (330, 266), (420, 236), (520, 214), (620, 200),
              (720, 194), (825, 198), (826, 470), (800, 482), (750, 512), (650, 550), (550, 580), (450, 598), (350, 604),
              (250, 598), (150, 580), (60, 553)]


def shark_mouth(src):
    """NARA 535531: the nearest P-40's mouth and eye. Inside the traced outline: a black band (the painted outline), the
    white teeth where the photo is bright, the red mouth everywhere else; the eye is the white teardrop above."""
    up = 2
    G = np.asarray(load(src, '01.jpg').crop((160, 20, 1130, 650)), float)
    G = nd.zoom(G, up, order=1)
    H, W = G.shape
    pm = Image.new('L', (W, H), 0)
    ImageDraw.Draw(pm).polygon([(x * up, y * up) for x, y in SHARK_POLY], fill=255)
    poly = np.asarray(pm) > 0
    inner = nd.binary_erosion(poly, iterations=13 * up)
    outline = poly & ~inner
    hp = G - nd.gaussian_filter(G, 22 * up)            # bright against the local light: the teeth (the cowl's shading is not)
    teeth = inner & (hp > 20)
    teeth = nd.binary_opening(teeth, iterations=3)
    lab2, n2 = nd.label(teeth)
    sz = nd.sum(teeth, lab2, range(1, n2 + 1))
    teeth = np.isin(lab2, [i + 1 for i, s_ in enumerate(sz) if s_ > 250 * up * up])
    teeth = nd.binary_closing(teeth, iterations=2)
    mouth = inner & ~teeth
    # the eye: a white teardrop with a dark pupil, traced on the same photo
    em = Image.new('L', (W, H), 0)
    ed = ImageDraw.Draw(em)
    ed.polygon([(x * up, y * up) for x, y in ((625, 62), (660, 40), (700, 25), (750, 18), (790, 20), (805, 35), (795, 60),
                                             (760, 75), (710, 80), (660, 75))], fill=255)
    eye = np.asarray(em) > 0
    pm2 = Image.new('L', (W, H), 0)
    ImageDraw.Draw(pm2).ellipse([(728 * up, 31 * up), (756 * up, 59 * up)], fill=255)
    pupil = np.asarray(pm2) > 0
    eye_rim = nd.binary_dilation(eye, iterations=2 * up) & ~eye
    tone = G / 255.0
    m = lambda b: nd.gaussian_filter(b.astype(float), 0.8)
    im = paint([(m(outline | eye_rim), PAL['black'], None), (m(mouth), PAL['red'], tone), (m(teeth), PAL['white'], tone),
                (m(eye), PAL['white'], tone), (m(pupil), PAL['black'], None)], seed=21)
    return trim(im)


def _glyphs(src):
    """LIBERTY from 41-23920: each letter as (mask crop, tone crop, centroid, tangent angle)"""
    G = np.asarray(load(src, '02.jpg').crop((600, 370, 900, 610)), float)
    up = 3
    G = nd.zoom(G, up, order=3)
    m = G > 105
    m[:150 * up, 236 * up:] = False                           # the dancer's drape (Y sits below it)
    m = nd.binary_closing(m, structure=np.ones((5, 2)), iterations=1)   # the panel seam that cuts E and R
    # letters that touch (B-E): split on eroded cores, then give every pixel back to its nearest core
    core = nd.binary_erosion(m, iterations=2 * up)
    cl, cn = nd.label(core)
    csz = nd.sum(core, cl, range(1, cn + 1))
    cl = np.where(np.isin(cl, [i + 1 for i, s_ in enumerate(csz) if s_ > 25 * up * up]), cl, 0)
    _d, (iy, ix) = nd.distance_transform_edt(cl == 0, return_indices=True)
    lab = np.where(m, cl[iy, ix], 0)
    n = int(lab.max())
    sz = nd.sum(m, lab, range(1, n + 1))
    comps = [i + 1 for i, s in enumerate(sz) if s > 120 * up * up]
    objs = nd.find_objects(lab)
    cents = sorted([(nd.center_of_mass(lab == k), k) for k in comps], key=lambda t: t[0][1])
    # merge fragments: a part whose centroid is within ~18 px (source) of a bigger one belongs to that letter
    letters = []
    for (cy, cx), k in cents:
        if letters and abs(cx - letters[-1][0][1]) < 14 * up and sz[k - 1] < sz[letters[-1][1][0] - 1]:
            letters[-1][1].append(k)
        else:
            letters.append(((cy, cx), [k]))
    areas = [sum(sz[k - 1] for k in ks) for _c, ks in letters]
    letters = [l for l, ar in zip(letters, areas) if ar > 0.3 * np.median(areas)]     # drop crumbs (the drape's tip)
    out = []
    pts = np.array([c for c, _ in letters])
    slope = np.polyfit(pts[:, 1], pts[:, 0], 1)[0]               # the word's own baseline, one angle for every letter
    for i, (c, ks) in enumerate(letters):
        ang = math.degrees(math.atan(slope))
        mask = nd.binary_fill_holes(nd.binary_closing(np.isin(lab, ks), structure=np.ones((3, 3)), iterations=2))             if False else nd.binary_closing(np.isin(lab, ks), structure=np.ones((3, 3)), iterations=2)   # the seam across R
        ys, xs = np.nonzero(mask)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        out.append((mask[y0:y1, x0:x1], G[y0:y1, x0:x1], ang))
    return out


def liberty_belle(src):
    """the painter's LIBERTY, turned level as one piece (each letter keeps its own hand-set lean), then BELLE set from his
    own B, E and L on the same baseline with his own letter spacing"""
    G = np.asarray(load(src, '02.jpg').crop((600, 370, 900, 610)), float)
    up = 3
    G = nd.zoom(G, up, order=3)
    m = G > 105
    m[:150 * up, 236 * up:] = False
    m = nd.binary_closing(m, structure=np.ones((3, 3)), iterations=2)
    lab, n = nd.label(m)
    sz = nd.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s_ in enumerate(sz) if s_ > 300 * up * up]
    pts = np.array([nd.center_of_mass(lab == k) for k in keep])
    ang = math.degrees(math.atan(np.polyfit(pts[:, 1], pts[:, 0], 1)[0]))
    mk = np.asarray(Image.fromarray((np.isin(lab, keep) * 255).astype(np.uint8)).rotate(ang, resample=Image.BICUBIC, expand=True), float) / 255
    tn = np.asarray(Image.fromarray(np.clip(G, 0, 255).astype(np.uint8)).rotate(ang, resample=Image.BICUBIC, expand=True), float)
    # letters in the levelled word as their own pixels (italic letters overlap in x, so no column slicing)
    on = mk > 0.5
    rl, rn = nd.label(on)
    rs = nd.sum(on, rl, range(1, rn + 1))
    comps = [i + 1 for i, s_ in enumerate(rs) if s_ > 0.15 * np.median(rs[rs > 50 * up])]
    comps.sort(key=lambda k: nd.center_of_mass(rl == k)[1])
    letters = [rl == k for k in comps]
    areas = [L.sum() for L in letters]
    med = np.median(areas)
    big = [L for L, ar in zip(letters, areas) if ar >= 0.35 * med]
    for L, ar in zip(letters, areas):                      # crumbs (a stroke cut by the panel seam) join the nearest letter
        if ar < 0.35 * med:
            cxs = nd.center_of_mass(L)[1]
            j = min(range(len(big)), key=lambda k: abs(nd.center_of_mass(big[k])[1] - cxs))
            if abs(nd.center_of_mass(big[j])[1] - cxs) < 30 * up:
                big[j] = big[j] | L
    letters = big
    while len(letters) < 7:                                # B and E touch: split the widest piece at its thinnest column
        i = max(range(len(letters)), key=lambda k: np.ptp(np.nonzero(letters[k].any(0))[0]))
        cx = np.nonzero(letters[i].any(0))[0]
        a_, b_ = cx.min(), cx.max()
        c = letters[i].sum(0)
        mid = a_ + (b_ - a_) // 4 + int(np.argmin(c[a_ + (b_ - a_) // 4: b_ - (b_ - a_) // 4]))
        left = letters[i].copy(); left[:, mid:] = False
        right = letters[i].copy(); right[:, :mid] = False
        letters[i:i + 1] = [left, right]
    if len(letters) != 7:
        raise SystemExit('LIBERTY: %d letters' % len(letters))
    rows = np.nonzero(on.any(1))[0]
    top, base = rows.min(), rows.max()
    glyph, spans = [], []
    for L in letters:
        cx = np.nonzero(L.any(0))[0]
        a_, b_ = cx.min(), cx.max() + 1
        glyph.append(((L[top:base + 1, a_:b_]) * mk[top:base + 1, a_:b_], tn[top:base + 1, a_:b_]))
        spans.append((a_, b_))
    gap = max(2 * up, int(np.median([spans[i + 1][0] - spans[i][1] for i in range(6)])) + 2 * up)
    L_, I_, B_, E_, R_, T_, Y_ = glyph
    seq = [L_, I_, B_, E_, R_, T_, Y_, None, B_, E_, L_, L_, E_]
    Hh = base - top + 1
    bot = int(np.median([np.nonzero(g[0].max(1) > 0.5)[0].max() for g in glyph]))
    W = sum((g[0].shape[1] + gap) if g is not None else 3 * gap + Hh // 3 for g in seq)
    A = np.zeros((Hh, W))
    T = np.zeros((Hh, W))
    x = 0
    for g in seq:
        if g is None:
            x += 3 * gap + Hh // 3
            continue
        w = g[0].shape[1]
        rr = np.nonzero(g[0].max(1) > 0.5)[0]
        dy = int(np.clip(bot - rr.max(), -rr.min(), Hh - 1 - rr.max()))   # sit every letter on the common baseline
        gm, gt = np.roll(g[0], dy, 0), np.roll(g[1], dy, 0)
        A[:, x:x + w] = np.maximum(A[:, x:x + w], gm)
        T[:, x:x + w] = np.where(gm > 0.5, gt, T[:, x:x + w])
        x += w + gap
    A = np.pad(A, 12)
    T = np.pad(T, 12)
    im = paint([(A, PAL['white'], T / 255.0)], seed=22)
    return trim(im)


def bonnie(src):
    """the sign-painter's script from the B-24 photo; the seated figure beside it is cut away (it is not used)"""
    G = np.asarray(load(src, '08.jpg').crop((188, 236, 328, 322)), float)
    up = 5
    G = nd.zoom(G, up, order=3)
    m = G > 172
    xx = np.arange(m.shape[1])[None, :]
    m |= (xx > (298 - 188) * up) & (G > 150)                  # the 'e' is painted thinner and sits in the window's shadow
    m[(np.arange(m.shape[0])[:, None] > (268 - 236) * up) & (np.arange(m.shape[1])[None, :] > (286 - 188) * up)] = False
    m = nd.binary_opening(m, structure=np.ones((1, 2 * up)))  # the thin vertical drip line from the window above "ie"
    lab, n = nd.label(m)
    sz = nd.sum(m, lab, range(1, n + 1))
    m = np.isin(lab, [i + 1 for i, s_ in enumerate(sz) if s_ > 40 * up * up])
    m = nd.binary_closing(m, iterations=2)
    # restore what the window's drip line took: the dot of the i, and the eye of the e (dark again)
    dm = Image.fromarray((m * 255).astype(np.uint8))
    dd = ImageDraw.Draw(dm)
    dd.ellipse([((300.5 - 188) * up, (240 - 236) * up), ((304.5 - 188) * up, (244 - 236) * up)], fill=255)
    dd.ellipse([((309.5 - 188) * up, (254.5 - 236) * up), ((313.5 - 188) * up, (259 - 236) * up)], fill=0)
    m = np.asarray(dm) > 0
    A = nd.gaussian_filter(m.astype(float), 1.2)
    im = paint([(A, PAL['white'], G / 255.0)], seed=23, chip=0.05)
    return trim(im)


def bomb_tally(src):
    """painted silhouettes: drawn by a 'brush' (a polygon dabbed many times with small jitter), yellow with a red nose
    band, in two staggered rows - the style of the tallies on the period aircraft photographed in this set"""
    rng = np.random.default_rng(24)
    K = 4
    W, H = 300 * K, 130 * K
    A = Image.new('L', (W, H), 0)
    Bd = Image.new('L', (W, H), 0)
    da, db = ImageDraw.Draw(A), ImageDraw.Draw(Bd)

    def dab(d, pts, n=6, j=1.4):
        for _ in range(n):
            o = rng.normal(0, j * K, 2)
            d.polygon([(x + o[0] + rng.normal(0, 0.6 * K), y + o[1] + rng.normal(0, 0.6 * K)) for x, y in pts], fill=255)

    def bomb(x, y, s):
        prof = [(17, 0), (16, 3.2), (13, 5.6), (8, 7.0), (-5, 7.0), (-12, 5.0), (-18, 2.0)]
        body = [((x + px * s) * K, (y - py * s) * K) for px, py in prof] + [((x + px * s) * K, (y + py * s) * K) for px, py in reversed(prof)]
        dab(da, body)
        fins = [((x - 17 * s) * K, (y - 2.6 * s) * K), ((x - 21 * s) * K, (y - 7.2 * s) * K), ((x - 28 * s) * K, (y - 7.2 * s) * K),
                ((x - 28 * s) * K, (y + 7.2 * s) * K), ((x - 21 * s) * K, (y + 7.2 * s) * K), ((x - 17 * s) * K, (y + 2.6 * s) * K)]
        dab(da, fins)
        band = [((x + 9 * s) * K, (y - 6.8 * s) * K), ((x + 12 * s) * K, (y - 6.2 * s) * K), ((x + 12 * s) * K, (y + 6.2 * s) * K),
                ((x + 9 * s) * K, (y + 6.8 * s) * K)]
        dab(db, band, n=3, j=0.6)
    for r in range(2):
        for k in range(3):
            bomb(64 + k * 90 + r * 20 + rng.normal(0, 1.5), 36 + r * 58 + rng.normal(0, 1.2), 1.45)
    a = np.asarray(A.filter(ImageFilter.GaussianBlur(K * 0.5)), float) / 255
    b = np.asarray(Bd.filter(ImageFilter.GaussianBlur(K * 0.4)), float) / 255 * (a > 0.5)
    im = paint([(a, PAL['yellow'], None), (b, PAL['red'], None)], seed=24, chip=0.05)
    return trim(im.resize((W // 2, H // 2), Image.LANCZOS))


# bonnie() is kept for reference but not shipped: the photo's 'ie' is lost under the window's drip line and reads 'ic'
ALL = [('na_shark_mouth', shark_mouth), ('na_liberty_belle', liberty_belle), ('na_bomb_tally', bomb_tally)]

if __name__ == '__main__':
    src = sys.argv[1]
    only = sys.argv[2:]
    ims = []
    for name, f in ALL:
        if only and name not in only:
            continue
        im = f(src)
        k = 640 / max(im.size)                           # a common working size: 640 on the long side
        im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
        im.save(os.path.join(OUT, name + '.png'))
        ims.append((name, im))
        print(name, im.size)
    # the QA sheet: each on olive drab and on dark gun steel
    W = sum(i.width + 24 for _n, i in ims) + 24
    H = max(i.height for _n, i in ims) * 2 + 72
    sh = Image.new('RGB', (W, H), (40, 40, 40))
    x = 24
    for _n, i in ims:
        for r, bg in enumerate(((92, 96, 66), (52, 54, 58))):
            y = 24 + r * (H // 2)
            sh.paste(Image.new('RGB', (i.width + 12, i.height + 12), bg), (x - 6, y - 6))
            sh.paste(i, (x, y), i)
        x += i.width + 24
    sh.save(os.path.join(MEDIA, 'noseart2_sheet.png'))
