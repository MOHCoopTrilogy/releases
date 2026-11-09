"""finishes2 core - everything a finish needs from ONE gun's own mesh, shared by the offline previews, the orientation check and
the shader generator (so the preview, the check and the shipped shader can never disagree):

  texel_world(g, shader, W, H)   per texel of a texture sheet: the model-space point it is painted on (NaN = unused) and the
                                 face normal there - rasterised from the gun's triangles in UV space
  world_per_uv(g, shader)        median model units per UV unit on that sheet -> the pattern tile scale (tcMod scale) that
                                 puts a pattern at its REAL size on every gun (QA 1: shapes were noise on the Kar98k)
  wear_mask(...)                 1 = painted / patterned, 0 = bare: the muzzle crown and bore, the sights, worn edges of every
                                 UV island (where hands and holsters rub) - one small per-sheet mask shared by every paint and
                                 camo finish of that gun (QA 4)
  place(g, kind)                 the decal's island and transform: kind 'butt' (rifle butt, else grip), 'grip', 'receiver';
                                 the decal is fitted INSIDE the island and laid upright in model space (x muzzle-ward, z up),
                                 on the -y (left) side; orientation_ok() is the build gate (QA: decals read upside down)
Units: MOHAA model units (16 per foot: 1 u = 1.9 cm).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'ironsights_2026-09-28', 'tools'))
import gungeo  # noqa: E402
gungeo.ROOT_APPLY = True
import re as _re  # noqa: E402
import texload, uvview  # noqa: E402

_real_shader_image = uvview.shader_image


def diffuse_image(shader):
    """uvview.shader_image takes the FIRST map of a shader, which on the s93_* chrome-gloss shaders is the environment
    stage (textures/effects/s93_gloss*.tga, 100x100) and not the gun: take the first map of a stage that is not
    tcGen environment*"""
    for pak, k, maps, blk in reversed(texload.shader_maps(shader)):
        for st in _re.findall(r'\{([^{}]*)\}', blk or ''):
            if 'environment' in st.lower():
                continue
            mm = _re.search(r'\b(?:clamp)?map\s+(\S+)', st, _re.I)
            if mm and not mm.group(1).startswith('$'):
                p, pk, im = texload.load(mm.group(1))
                if im is not None:
                    return mm.group(1), p, pk, im, blk
    return _real_shader_image(shader)


uvview.shader_image = diffuse_image

# The skd frame gungeo returns is the gun ROLLED 180 deg about its barrel axis (grips, magazines and the rifle butts point
# UP, bolt handles at +y). Measured over all 70 guns (media/frame_check.jpg), and a roll, not a mirror: the bolt handles of
# the Kar98k / Springfield / Enfield come out on +y = the gun's right once rolled back. Every finishes tool works in the TRUE
# frame: x towards the muzzle, y = the gun's LEFT, z up (bug-10666).
ROLL = np.array([1.0, -1.0, -1.0])
ARMORY = -1              # the gun's RIGHT side, muzzle to the right: what the Armory and the weapon viewer show
FIRSTPERSON = +1         # the gun's LEFT side: what the first-person view shows (receiver / slide; a rifle's butt is off-screen)
VISIBLE = ARMORY


def load_gun(tik):
    g = gungeo.load_gun(tik)
    if not g.get('_true_frame'):
        for s in g['surfs']:
            s['P'] = s['P'] * ROLL
        g['_true_frame'] = True
    return g      # the engine applies a flipped root (Carcano: its idle frame lies along y otherwise)

U_PER_CM = 16.0 / 30.48


def surfs_of(g, shader):
    return [s for s in g['surfs'] if s['shader'] == shader and len(s['tri'])]


def world_per_uv(g, shader):
    r = []
    for s in surfs_of(g, shader):
        V, UV, T = s['P'], s['UV'], s['tri']
        for a, b in ((0, 1), (1, 2), (2, 0)):
            dw = np.linalg.norm(V[T[:, a]] - V[T[:, b]], axis=1)
            du = np.linalg.norm(UV[T[:, a]] - UV[T[:, b]], axis=1)
            ok = du > 1e-4
            r.append(dw[ok] / du[ok])
    r = np.concatenate(r) if r else np.array([40.0])
    return float(np.median(r))


def texel_world(g, shader, W, H):
    """-> (P [H,W,3] model point or NaN, N [H,W,3] unit face normal, boundary [H,W] bool: texel on a UV island's edge)"""
    P = np.full((H, W, 3), np.nan)
    Nn = np.zeros((H, W, 3))
    edge = np.zeros((H, W), bool)
    for s in surfs_of(g, shader):
        V, UV, T = s['P'], s['UV'], s['tri']
        uv = np.c_[(UV[:, 0] % 1.0) * W, (UV[:, 1] % 1.0) * H]
        # island boundary edges: an edge used by one triangle only (in UV space)
        cnt = {}
        for t in T:
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (min(a, b), max(a, b))
                cnt[k] = cnt.get(k, 0) + 1
        for t in T:
            p = uv[t]
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W - 1), min(y1, H - 1)
            if x1 < x0 or y1 < y0:
                continue
            ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            px, py = xs + 0.5, ys + 0.5
            (ax, ay), (bx, by), (cx, cy) = p
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9:
                continue
            w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
            w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -0.01) & (w1 >= -0.01) & (w2 >= -0.01)
            if not m.any():
                continue
            pt = w0[m, None] * V[t[0]] + w1[m, None] * V[t[1]] + w2[m, None] * V[t[2]]
            P[ys[m], xs[m]] = pt
            n = np.cross(V[t[1]] - V[t[0]], V[t[2]] - V[t[0]])
            Nn[ys[m], xs[m]] = -n / max(np.linalg.norm(n), 1e-9)      # outward (clockwise winding)
        im = Image.new('L', (W, H), 0)
        dr = ImageDraw.Draw(im)
        for (a, b), c in cnt.items():
            if c == 1:
                dr.line([tuple(uv[a]), tuple(uv[b])], fill=255, width=max(2, W // 170))
        edge |= np.asarray(im) > 0
    return P, Nn, edge


def gun_box(g):
    P = np.concatenate([s['P'] for s in g['surfs']])
    return P.min(0), P.max(0)


def wear_mask(g, shader, W, H, P=None, edge=None):
    """1 = the finish covers it, 0 = bare. Muzzle: the front 3 % (crown, bore, front sight); sights: anything standing above
    the gun's top line in the front or rear 12 %; island edges: worn to bare in a soft 1-3 px band."""
    if P is None:
        P, _n, edge = texel_world(g, shader, W, H)
    lo, hi = gun_box(g)
    L = hi[0] - lo[0]
    m = np.ones((H, W))
    x, z = P[..., 0], P[..., 2]
    bare = np.zeros((H, W), bool)
    with np.errstate(invalid='ignore'):
        bare |= x > hi[0] - 0.03 * L
        top = np.nanpercentile(z, 92) if np.isfinite(z).any() else hi[2]
        bare |= ((x > hi[0] - 0.12 * L) | (x < lo[0] + 0.12 * L)) & (z > top) & (L > 25)
    m[bare] = 0.0
    if edge is not None:
        from PIL import ImageFilter
        e = Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
        m *= 1 - 0.85 * (np.asarray(e, float) / 255.0)
    return m


# ---------------------------------------------------------------------------------------------------------- decals
def islands(g, side=VISIBLE):
    """side-facing (outward n_y * side > 0.75; side -1 = the gun's left, the side the viewer, the Armory and first person show) connected
    UV islands of every sheet: [(area, shader, tris, surf, centre xyz, extent xz)]"""
    out = []
    for s in g['surfs']:
        V, UV, T = s['P'], s['UV'], s['tri']
        if not len(T):
            continue
        n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        area = np.linalg.norm(n, axis=1)
        ny = n[:, 1] / np.maximum(area, 1e-9)
        idx = np.nonzero((-ny * side > 0.75) & (area > 1e-6))[0]     # MOHAA winding is clockwise: outward = -cross
        par = {}

        def find(a):
            while par.setdefault(a, a) != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        owner = {}
        for ti in idx:
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
            if len(tl) < 2:
                continue
            vs = V[np.unique(T[tl].ravel())]
            c = np.average(V[T[tl]].mean(1), axis=0, weights=area[tl])
            out.append((float(area[tl].sum()), s['shader'], tl, s, c, (np.ptp(vs[:, 0]), np.ptp(vs[:, 2]))))
    return out


def uv_mask(g, shader, side, W=256, H=256):
    """texels of `shader` painted by faces facing `side` (+1 / -1 in y) - to find islands whose UVs are SHARED with the other
    side (a mirrored copy: a decal there reads mirror-imaged on the far side, so those islands are not eligible)"""
    im = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(im)
    for s in surfs_of(g, shader):
        V, UV, T = s['P'], s['UV'], s['tri']
        n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        ny = n[:, 1] / np.maximum(np.linalg.norm(n, axis=1), 1e-9)
        for t in T[-ny * side > 0.3]:
            dr.polygon([((UV[i][0] % 1.0) * W, (UV[i][1] % 1.0) * H) for i in t], fill=255)
    return np.asarray(im) > 0


def shared_fraction(isl, other):
    area, shader, tl, s, *_ = isl
    W, H = other.shape[1], other.shape[0]
    im = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(im)
    for t in s['tri'][tl]:
        dr.polygon([((s['UV'][i][0] % 1.0) * W, (s['UV'][i][1] % 1.0) * H) for i in t], fill=255)
    m = np.asarray(im) > 0
    return float((m & other).sum()) / max(m.sum(), 1)


def inscribed_square(V, tris, n=300, region=None):
    """the largest axis-aligned (x along the gun, z up) square inside the island's side outline -> ((cx, cz), half side).
    The outline is the island's triangles projected on the x-z plane, rasterised; the square comes from the chessboard
    distance transform (ties: nearest the island's area centre). region = (xmin, xmax, zmin, zmax): where the square's
    CENTRE may sit (the square itself only has to be inside the island)"""
    from scipy import ndimage
    P = V[np.unique(tris.ravel())][:, [0, 2]]
    lo, hi = P.min(0), P.max(0)
    res = max(max(hi - lo) / n, 1e-3)
    w, h = int((hi[0] - lo[0]) / res) + 3, int((hi[1] - lo[1]) / res) + 3
    im = Image.new('L', (w, h), 0)
    dr = ImageDraw.Draw(im)
    for t in tris:
        q = (V[t][:, [0, 2]] - lo) / res + 1
        dr.polygon([(float(a), float(h - 1 - b)) for a, b in q], fill=255)
    m = np.asarray(im) > 0
    if not m.any():
        return (float(P[:, 0].mean()), float(P[:, 1].mean())), 0.0
    d = ndimage.distance_transform_cdt(m, metric='chessboard').astype(float)
    X = lo[0] + (np.arange(w) - 0.5) * res
    Z = lo[1] + (h - 1 - np.arange(h) - 0.5) * res
    if region is not None:
        x0, x1, z0, z1 = region
        d[:, (X < x0) | (X > x1)] = 0
        d[(Z < z0) | (Z > z1), :] = 0
    ys, xs = np.nonzero(m)
    score = d - 1e-3 * np.hypot(np.arange(h)[:, None] - ys.mean(), np.arange(w)[None, :] - xs.mean())
    iy, ix = np.unravel_index(np.argmax(score), score.shape)
    return (float(X[ix]), float(Z[iy])), float(max(d[iy, ix] - 0.5, 0) * res)


def visible_tris(g, side, W=1600):
    """seen straight from `side` (a far camera, near-orthographic): ({(surface index, triangle index): visible pixels}, the id
    image, pixel -> model (x, z) mapping). An island under a grip panel, a sling swivel or a trigger guard is not a place for
    a decal, and neither is the hidden PART of an island: the decal square is fitted on the visible pixels themselves."""
    cache = g.setdefault('_vis', {})                 # on the gun itself: an id() key is reused once a gun is freed
    if side in cache:
        return cache[side]
    import raster
    lo, hi = gun_box(g)
    c = (lo + hi) / 2
    ext = max(hi[0] - lo[0], hi[2] - lo[2]) * 1.05
    H = min(W, max(64, int(W * (hi[2] - lo[2]) / max(ext, 1e-3) * 1.05) + 8))
    dist = ext * 40
    _rgb, ids, _d = raster.render(g, c + np.array([0, side * dist, 0]), c, np.array([0, 0, 1.0]),
                                  fov=2 * math.degrees(math.atan(ext * 0.5 / dist)), W=W, H=H, tex=False, znear=1.0)
    v, n = np.unique(ids[ids >= 0], return_counts=True)
    res = ext / W
    X = c[0] + (-side) * (np.arange(W) + 0.5 - W / 2) * res      # seen from -y, screen right = +x
    Z = c[2] + (H / 2 - np.arange(H) - 0.5) * res
    cache[side] = ({(int(a // 1000000), int(a % 1000000)): int(b) for a, b in zip(v, n)}, ids, X, Z, res)
    return cache[side]


def pixel_square(ids, X, Z, res, keys, region=None):
    """the largest axis-aligned square on the visible pixels of one island (ids in `keys`) -> ((cx, cz), half side)"""
    from scipy import ndimage
    m = np.isin(ids, keys)
    if not m.any():
        return (0.0, 0.0), 0.0
    d = ndimage.distance_transform_cdt(np.pad(m, 1), metric='chessboard')[1:-1, 1:-1].astype(float)
    if region is not None:
        x0, x1, z0, z1 = region
        d[:, (X < x0) | (X > x1)] = 0
        d[(Z < z0) | (Z > z1), :] = 0
    ys, xs = np.nonzero(m)
    score = d - 1e-3 * np.hypot(np.arange(m.shape[0])[:, None] - ys.mean(), np.arange(m.shape[1])[None, :] - xs.mean())
    iy, ix = np.unravel_index(np.argmax(score), score.shape)
    return (float(X[ix]), float(Z[iy])), float(max(d[iy, ix] - 0.5, 0) * res)


def place(g, kind='butt', fill=0.8, side=VISIBLE, allow_shared=True, rank=0):
    """-> dict(shader, tris, surf, aff (UV->model xz 3x2), centre (x,z), size) or None. The island: 'butt' = the rear-most big
    island of a long gun with a butt, else the grip; 'grip' = the lowest island in the rear 60 %; 'receiver' = the biggest
    island in the middle third. The decal is a square of side `size` centred on the island's largest inscribed square
    (approximated: fill x the smaller of its x / z extents)."""
    lo, hi = gun_box(g)
    L = hi[0] - lo[0]
    isl = islands(g, side)
    other = {}
    keep, shared = [], {}
    for i in isl:                                   # islands whose UVs the far side reuses (mirrored copies - most stocks)
        if i[1] not in other:
            other[i[1]] = uv_mask(g, i[1], -side)
        shared[id(i)] = shared_fraction(i, other[i[1]])
        if allow_shared or shared[id(i)] < 0.15:
            keep.append(i)
    vis, ids, VX, VZ, vres = visible_tris(g, side)
    sidx = {id(x): k for k, x in enumerate(g['surfs'])}
    seen = []
    for (area, sh, tl, sf, c, ext) in keep:         # keep only the triangles the eye actually reaches
        si = sidx[id(sf)]
        px = np.array([vis.get((si, int(t)), 0) for t in tl])
        tv = tl[px > 0]
        if len(tv) >= 1 and px.sum() > 30:
            i2 = (float(px.sum()), sh, tv, sf, c, ext, tl, si)          # tl: the whole island (the stamp covers all of it)
            shared[id(i2)] = shared_fraction(i2, other[sh])
            seen.append(i2)
    isl = seen
    if not isl:
        return None
    big = max(a for a, *_ in isl)
    lz = (lo[2] + hi[2]) / 2
    if kind == 'butt' and L > 30:
        regions = [(lo[0], lo[0] + 0.3 * L, -1e9, 1e9)]                 # the butt end
    elif kind in ('butt', 'grip'):
        regions = [(lo[0], lo[0] + 0.55 * L, -1e9, lz)]                 # the grip: rear half, below the gun's middle
    else:
        regions = []
    regions.append((lo[0] + 0.15 * L, lo[0] + 0.85 * L, -1e9, 1e9))     # fallback: the receiver / body side
    found = []                                       # every (region, island) square, best region first, biggest first
    for ri, reg in enumerate(regions):
        for cand in sorted(isl, key=lambda i: -i[0])[:14]:
            if cand[0] < 0.02 * big:
                continue
            (cx, cz), half = pixel_square(ids, VX, VZ, vres, cand[7] * 1000000 + cand[2], region=reg)
            if half * 2 >= min(1.0, 0.03 * L):
                found.append((ri, -half, len(found), cand, cx, cz, half))
    found.sort(key=lambda f: f[:3])
    if rank >= len(found):
        return None
    _ri, _h, _k, cand, cx, cz, half = found[rank]
    area, shader, tv, s, c, (ex, ez), tl, _si = cand
    V, UV, T = s['P'], s['UV'], s['tri']
    vi = np.unique(T[tv].ravel())
    # RAW texcoords (no per-vertex wrap: an island across u = 1 would tear) - exactly what the in-game tcMod stage sees.
    # Weighted toward the decal's spot (a curved or skewed island stays square where the decal is), but over the WHOLE
    # island so the fit is never ill-conditioned (a local subset can be nearly collinear in UV: bug-10664)
    dist = np.max(np.abs(V[vi][:, [0, 2]] - (cx, cz)), axis=1)
    w = np.sqrt(np.exp(-(dist / (1.5 * half + 1.0)) ** 2) + 1e-3)[:, None]
    Xa = np.c_[UV[vi], np.ones(len(vi))]
    aff, *_ = np.linalg.lstsq(Xa * w, V[vi][:, [0, 2]] * w, rcond=None)
    near = vi[dist < 1.2 * half + 0.5]
    vi = near if len(near) >= 3 else vi
    resid = np.abs(np.c_[UV[vi], np.ones(len(vi))] @ aff - V[vi][:, [0, 2]]).max()
    return dict(shader=shader, tris=T[tl], surf=s, aff=aff, centre=(cx, cz), size=float(fill * 2 * half),
                side=side, shared=shared[id(cand)], fit_err=float(resid))


def decal_uv_transform(pl):
    """the in-game tcMod for the decal stage: texcoord' = M (u, v) + t such that the decal square [0,1]^2 lands upright on the
    island (decal +s = model +x, decal +t = model -z i.e. down). -> (m00, m01, m10, m11, t0, t1) for `tcMod transform`"""
    aff = pl['aff']                                   # [u v 1] @ aff = (x, z)
    cx, cz = pl['centre']
    S = pl['size']
    # s = k (x - cx)/S + 0.5 ; t = 0.5 - (z - cz)/S   with k = +1 seen from -y (muzzle screen-right), -1 seen from +y
    k = -float(pl.get('side', -1))
    A = np.array([[aff[0, 0], aff[0, 1]], [aff[1, 0], aff[1, 1]]])    # (x,z) per (u,v)
    b = aff[2]
    ms = k * A[:, 0] / S
    mt = -A[:, 1] / S
    return (ms[0], ms[1], mt[0], mt[1], k * (b[0] - cx) / S + 0.5, 0.5 - (b[1] - cz) / S)


def stamp(img, pl, dec):
    """composite the decal into a sheet texture through decal_uv_transform (exactly what the shader stage does), limited to the
    island's own triangles (the clamp edge cannot spill onto another part)"""
    H, W = img.shape[:2]
    UV = pl['surf']['UV']
    tri_uv = UV[pl['tris']]                                      # [n,3,2] raw
    off = np.floor(tri_uv.reshape(-1, 2).mean(0))
    m00, m01, m10, m11, t0, t1 = decal_uv_transform(pl)
    dh, dw = dec.shape[:2]
    for ku in (-1, 0, 1):                                        # the island may cross the texture edge: every wrap copy
        for kv in (-1, 0, 1):
            mask = Image.new('L', (W, H), 0)
            dr = ImageDraw.Draw(mask)
            for t in tri_uv:
                dr.polygon([((a - off[0] + ku) * W, (b - off[1] + kv) * H) for a, b in t], fill=255)
            ys, xs = np.nonzero(np.asarray(mask) > 0)
            if not len(ys):
                continue
            u = (xs + 0.5) / W - ku + off[0]
            v = (ys + 0.5) / H - kv + off[1]
            ds, dt = m00 * u + m01 * v + t0, m10 * u + m11 * v + t1
            ok = (ds >= 0) & (ds < 1) & (dt >= 0) & (dt < 1)
            px = dec[(dt[ok] * dh).astype(int), (ds[ok] * dw).astype(int)]
            a_ = px[:, 3:4]
            img[ys[ok], xs[ok], :3] = img[ys[ok], xs[ok], :3] * (1 - a_) + px[:, :3] * a_
    return img


def decal_texels(pl, W=512, H=512):
    """texels (on a W x H grid of the sheet) the placement's decal square covers - two placements that share any texel would
    paint each other"""
    img = np.zeros((H, W, 3))
    sq = np.ones((8, 8, 4))
    stamp(img, pl, sq)
    return img[..., 0] > 0.5


def orientation_ok(pl):
    """the build gate, analytic: on the decal's island, model +x (towards the muzzle = screen RIGHT in the left-side view)
    must map to decal +s, and model +z (up) to decal -t; a mirrored or flipped island fails. Also verified by rendering the
    'F + up arrow' glyph (orient_check.py)."""
    m00, m01, m10, m11, t0, t1 = decal_uv_transform(pl)
    aff = pl['aff']
    A = np.array([[aff[0, 0], aff[0, 1]], [aff[1, 0], aff[1, 1]]])      # rows: d(x,z)/du, d(x,z)/dv
    # decal coords per model (x, z): invert
    Ai = np.linalg.inv(A)                                               # d(u,v)/d(x,z) rows x / z
    ds_dx = m00 * Ai[0, 0] + m01 * Ai[0, 1]
    dt_dz = m10 * Ai[1, 0] + m11 * Ai[1, 1]
    return ds_dx * -pl.get('side', -1) > 0 and dt_dz < 0
