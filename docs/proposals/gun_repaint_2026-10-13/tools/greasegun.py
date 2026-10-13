"""M3 grease gun repaint: textures/models/weapons/greasegun/greaser (today 512x512 .jpg) -> 2048x2048 DXT1 .dds on
the SAME UVs (greaser.skd = the mesh inside greasegun_silenced.skd, one bone; used by greasegun.tik,
greasegun_silenced.tik and the AI copy coop_greasegun_ai.tik through shader `greaser`). Mesh, tiks, shader untouched.

    python greasegun.py [--preview] [--draft] [--n 4096]      (staged: 4096; --n 2048 = same paint, 2.8 MB)

Why it is painted in GUN SPACE: the mesh does not follow the art of its sheet. The receiver halves share the top
strip, small parts sit on top of it, the lower receiver and the magazine sides are squeezed 7-11 : 1 into narrow
strips, and 269 of 2567 triangles have UVs thrown across the sheet (gg_probe.py). So nothing is laid out in sheet
space: every texel's bone-space position, normal, part and the texel density of its triangle are baked from the
mesh, and the material is a function of those:
  * solid (3D) noise for mottle and grain - a squeezed island cannot smear it; an octave that the triangle's coarse
    axis cannot hold is faded out instead (soft there, never streaked),
  * wear and dirt from the 3D distance to the mesh's hard convex / concave edges,
  * phosphate-grey stamped steel on receiver, housing, grip; the weld bead along the two receiver halves (top and
    bottom centre line), a crimp ring at the rear cap and at the barrel collar, a press line on the trigger housing
    and on the magazine housing's lip; turned barrel and collar (rings), worn muzzle; magazine in darker blued
    steel with rub bands; wire stock in bare worn steel with patina; rubbed grip straps with their seam,
  * parts that share texels: the more visible part wins (receiver strip first); thrown triangles never write. The
    gutters are filled with the nearest part's colour - no black anywhere (today's black gaps are the slashes on
    the magazine).
No source pixels; seeded; same output every run.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
import rplib as L
import gg_probe as G
import soft3d

STEM = "textures/models/weapons/greasegun/greaser"
SKD = G.SKD
SEED = 1942
YC = -1.775                    # the gun's centre plane (weld plane of the two receiver halves)
ZT, RT = -8.66, 2.375          # receiver tube axis height (z is DOWN in this mesh) and radius
X_TUBE0, X_TUBE1, X_COLLAR1 = -4.0, 29.5, 37.3
PHOS = np.array([50.0, 52.0, 50.0])     # zinc / manganese phosphate grey (64 in the first engine look: read as grey plastic)
PARK = np.array([39.0, 41.0, 42.0])     # barrel + collar: darker
BLUE = np.array([31.0, 33.0, 39.0])     # magazine
BARE = np.array([84.0, 83.0, 78.0])     # wire stock
PATINA = np.array([52.0, 46.0, 39.0])
DARK = np.array([38.0, 39.0, 41.0])     # trigger, oiler cap
WEAR = np.array([128.0, 126.0, 120.0])
# (part, surface, islands, material, priority) - higher priority wins a shared texel
B, S_, E, M, C = "bool_mesh", "skin1", "Mesh_MultiAttached4", "Mesh_MultiAttached", "Clip"
PARTS = [
    ("magbottom", M, [9, 10], "blue", 8), ("stockrod", M, [11, 12], "bare", 10), ("stockloop", S_, [5], "bare", 10),
    ("guide", M, [13, 14, 15, 16], "phos", 12), ("bracket", S_, [6, 7, 8, 9, 10, 11, 12, 13], "phos", 12),
    ("magcatch", M, [6], "phos", 14), ("oiler", S_, [15], "dark", 14), ("trigger", S_, [14], "dark", 14),
    ("guard", S_, [3, 4], "phos", 14), ("fsight", M, [7, 8], "phos", 16), ("port", B, [0], "dark", 18),
    ("grip2", S_, [2], "phos", 19), ("grip", S_, [1], "phos", 20), ("lower", S_, [0], "phos", 22), ("lower", M, [4], "phos", 24),
    ("mag", C, [0, 1, 2, 3, 4], "blue", 26), ("maghousing", M, [5], "phos", 28), ("rearcap", B, [5], "phos", 30),
    ("cover", E, [0, 1], "phos", 31), ("rsight", M, [0, 1, 2, 3], "phos", 32), ("tube", B, [3, 4], "phos", 40),
]
PNAMES = sorted(set(p[0] for p in PARTS))


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def tube_scratches():
    """handling scratches of the receiver tube on its unwrapped (x, theta) surface, 120 px per unit, periodic in
    theta: mostly along the tube, a few rub arcs round it."""
    W = int((X_TUBE1 - X_TUBE0) * 120); H = int(2 * np.pi * RT * 120)
    from PIL import ImageDraw
    rs = np.random.RandomState(SEED + 90)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for i in range(300):
        x0 = rs.uniform(0, W); y0 = rs.uniform(0, H)
        along = rs.rand() < 0.78
        ang = rs.normal(0, 0.10) if along else rs.normal(np.pi / 2, 0.15)
        ln = rs.uniform(30, 260) if rs.rand() < 0.8 else rs.uniform(260, 700)
        v = int(rs.uniform(45, 150)); dx = np.cos(ang) * ln; dy = np.sin(ang) * ln
        for oy in (-H, 0, H):
            d.line([(x0, y0 + oy), (x0 + dx, y0 + oy + dy)], fill=v, width=2 if rs.rand() < 0.75 else 3)
    for i in range(140):
        x0 = rs.uniform(0, W); y0 = rs.uniform(0, H); r = rs.uniform(1.5, 4.0)
        d.ellipse([x0 - 1.8 * r, y0 - r, x0 + 1.8 * r, y0 + r], fill=int(rs.uniform(70, 170)))
    return ndi.gaussian_filter(np.asarray(im, np.float32) / 255, 0.8)


def bake_all(S, N):
    """composite of all parts in priority order -> pos, nrm, part id (-1 none), dmin (px per unit, coarse axis)."""
    POS = np.zeros((N, N, 3), np.float32); NRM = np.zeros((N, N, 3), np.float32)
    PART = -np.ones((N, N), np.int32); DMIN = np.zeros((N, N), np.float32); CNT = np.zeros((N, N), np.int16)
    stats = {}
    for name, s in S.items():
        a3, au, sv, ext = G.tri_stats(s)
        ratio = sv[:, 0] / np.maximum(sv[:, 1], 1e-6)
        thrown = (ext > 0.30) & (ratio > 6) | (ratio > 25) & (ext > 0.12)
        stats[name] = (thrown, sv[:, 1] * (N / float(G.N)))
    for pname, sname, isls, mat, pri in sorted(PARTS, key=lambda p: p[4]):
        s = S[sname]
        thrown, dm = stats[sname]
        m = np.isin(s["isl"], isls) & ~thrown
        if not m.any():
            continue
        idx = np.nonzero(m)[0]
        sub = dict(s); sub["tris"] = s["tris"][m]; sub["isl"] = s["isl"][m]
        pos, nrm, isl, tid = L.bake(sub, N, N, want_tid=True)
        w = isl >= 0
        POS[w] = pos[w]; NRM[w] = nrm[w]; PART[w] = PNAMES.index(pname); DMIN[w] = dm[idx[tid[w]]]; CNT[w] += 1
    return POS, NRM, PART, DMIN, CNT


def edge_trees(S):
    cv, cc = [], []
    for name, s in S.items():
        a, b = L.hard_edge_points(s, deg=30, step=0.05)
        cv.append(a); cc.append(b)
    return cKDTree(np.concatenate(cv)), cKDTree(np.concatenate(cc))


def paint(S, N):
    POS, NRM, PART, DMIN, CNT = bake_all(S, N)
    mask = PART >= 0
    # texels that two parts share: plain material only there (a line or a worn edge of one would cross the other)
    own = (CNT[mask] <= 1).astype(np.float32)
    P = POS[mask].astype(np.float64); Nn = NRM[mask]; part = PART[mask]; dmin = np.maximum(DMIN[mask], 0.5)
    n = len(P)
    print("covered texels %d (%.1f %%), shared by two parts %.1f %%, parts %s" % (n, 100.0 * n / N / N, 100.0 * (1 - own.mean()), {k: int((part == i).sum()) for i, k in enumerate(PNAMES)}))
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    is_ = {k: part == i for i, k in enumerate(PNAMES)}
    own[is_["tube"]] = 1.0          # the receiver strip is painted in full: the small parts lying on it take its paint
    tcv, tcc = edge_trees(S)
    dcv = tcv.query(P, k=1, workers=4)[0].astype(np.float32)
    dcc = tcc.query(P, k=1, workers=4)[0].astype(np.float32)

    # ---- shared terms ------------------------------------------------------------------------------------------
    mott = L.fbm3(P, 0.30, 4, SEED, dmin)
    mott2 = L.fbm3(P, 1.7, 3, SEED + 10, dmin)
    wg = np.clip(dmin / 14.0, 0, 1) ** 1.5
    grain = (L.vnoise3(P * 21.0, SEED + 20) - 0.5) * 2 * wg + (L.vnoise3(P * 43.0, SEED + 21) - 0.5) * 2 * np.clip((dmin - 22) / 20, 0, 1)
    brk = np.clip(0.50 + 1.1 * L.fbm3(P, 2.2, 3, SEED + 30, dmin, floor=0.3), 0.05, 1.0)
    up = np.clip(-Nn[:, 2], 0, 1)
    shade = 0.83 + 0.22 * up + 0.04 * np.abs(Nn[:, 1])
    stain = np.clip((L.fbm3(P, 0.55, 3, SEED + 70, dmin) - 0.12) * 2.4, 0, 1)        # darker oil / handling stains
    lum = (1 + 0.15 * mott + 0.065 * mott2 + 0.05 * grain) * (1 - 0.17 * stain)
    chips = np.clip((L.vnoise3(P * 7.5, SEED + 22) - 0.875) * 10.0, 0, 1) * np.clip((dmin - 9) / 10, 0, 1)      # small bright chips
    base = np.zeros((n, 3), np.float32) + PHOS
    wear = np.zeros(n, np.float32)
    dirt = np.zeros(n, np.float32)
    # worn convex edges / dirty concave ones: 3D distance; on a coarse triangle the band is as wide as a texel there
    sig = np.maximum(0.085, 0.9 / dmin)
    ew = np.exp(-(dcv / sig) ** 2) * 0.55 + np.exp(-(dcv / (3.2 * sig)) ** 2) * 0.14
    # (a triangle with under ~4 texels per unit cannot hold an edge band at all: none there, or it comes out as swirls)
    wear += ew * (0.30 + 0.70 * brk) * np.clip(0.085 / sig, 0.35, 1.0) * 1.7 * own * np.clip((dmin - 3.5) / 8.0, 0, 1)
    wear += chips * 0.30 * own + 0.07 * np.clip(mott2, 0, 1) * brk * own
    dirt += np.exp(-(dcc / np.maximum(0.22, 1.2 / dmin)) ** 2) * 0.30 * (0.3 + 0.7 * own)

    # ---- receiver tube, collar, barrel (bool_mesh 3 / 4) --------------------------------------------------------
    t = is_["tube"]
    rec = t & (x < X_TUBE1); col_ = t & (x >= X_TUBE1) & (x < X_COLLAR1); bar = t & (x >= X_COLLAR1)
    zc = np.where(x < X_TUBE1, ZT, np.where(x < X_COLLAR1, -9.10, -9.60))
    th = np.arctan2(y - YC, -(z - zc))                          # 0 = top line, +-pi = bottom line
    strk = np.clip(1 + 0.9 * L.fbm3(P * np.array([0.05, 2.0, 2.0]), 1.0, 3, SEED + 44, dmin), 0.3, 1.8)
    at = np.abs(th)
    sh_t = (0.72 + 0.24 * np.clip(np.cos(th), 0, 1) + 0.40 * np.exp(-((at - 0.72) / 0.24) ** 2) * strk
            + 0.30 * np.exp(-((at - 0.70) / 0.075) ** 2) * strk ** 2 + 0.09 * np.exp(-((at - 2.5) / 0.4) ** 2))
    shade = np.where(t, sh_t, shade)
    draw = L.fbm3(P * np.array([0.10, 3.0, 3.0]), 1.0, 3, SEED + 40, dmin)           # long draw marks of the pressing
    lum = lum + np.where(rec, 0.035 * draw, 0)
    # weld bead of the two half shells: top and bottom centre line, rear cap to collar
    d = np.abs(y - YC)
    onseam = rec & (np.abs(z - ZT) > 1.3) & (x > X_TUBE0 + 0.5) & (x < X_TUBE1 - 0.35)
    rip = 0.5 + 0.5 * np.sin(2 * np.pi * x / 0.27 + 5.0 * L.vnoise3(np.stack([x * 0.8, 0 * x, 0 * x], 1), SEED + 41))
    bead = np.exp(-(d / 0.17) ** 2); toe = np.exp(-((d - 0.38) / 0.12) ** 2); halo = np.exp(-(d / 1.0) ** 2)
    lum = lum + np.where(onseam, bead * (0.16 + 0.13 * rip) - toe * 0.15 - halo * 0.05, 0)
    wear += np.where(onseam, bead * 0.16 * brk, 0)
    scr = tube_scratches()
    sx = (x - X_TUBE0) / (X_TUBE1 - X_TUBE0) * (scr.shape[1] - 1)
    sy = (th / (2 * np.pi)) % 1.0 * scr.shape[0]
    sc_ = ndi.map_coordinates(scr, [sy, np.clip(sx, 0, scr.shape[1] - 1)], order=1, mode="grid-wrap")
    wear += np.where(rec, sc_ * 0.55 * np.clip(dmin / 12.0, 0.35, 1.0), 0)
    # crimp ring at the rear cap, the step where the collar screws on
    for xr, wd in ((X_TUBE0 + 0.95, 0.07), (X_TUBE1 - 0.18, 0.08)):
        g = np.exp(-((x - xr) / wd) ** 2)
        lip = np.exp(-((x - xr - 2.2 * wd) / wd) ** 2)
        lum = lum + np.where(rec, -0.30 * g + 0.10 * lip, 0)
    # collar + barrel: turned parts
    ring = (L.vnoise3(np.stack([x * 9.0, 0 * x, 0 * x], 1), SEED + 42) - 0.5) * 2 \
        + 0.6 * (L.vnoise3(np.stack([x * 26.0, 0 * x, 0 * x], 1), SEED + 43) - 0.5) * 2
    base[col_ | bar] = PARK
    lum = lum + np.where(col_ | bar, 0.055 * ring, 0)
    lum = lum * np.where(col_, 1.08, 1.0)
    wear += np.where(bar, smooth(x, 50.15, 50.5) * 0.55 * (0.4 + 0.6 * brk), 0)
    wear += np.where(col_, 0.06 * brk, 0)

    # ---- rear cap: the disc the shooter looks at when aiming - a turned face, not a flat tone -------------------
    rc = is_["rearcap"]
    ry = y - YC; rz = z - ZT
    rr = np.hypot(ry, rz) / RT; ang = np.arctan2(ry, -rz)
    wr = np.clip(dmin / 20.0, 0.3, 1.0)
    rg = (L.vnoise3(np.stack([rr * 60.0, 0 * rr, 0 * rr], 1), SEED + 80) - 0.5) * 2 * wr \
        + (L.vnoise3(np.stack([rr * 15.0, 0 * rr, 0 * rr], 1), SEED + 81) - 0.5) * 2
    lobes = 0.11 * np.cos(2 * (ang - 0.55)) + 0.13 * np.cos(2 * (ang - 0.55)) ** 8        # the two-lobed sheen of a turned disc
    capl = 0.07 * rg + lobes * (0.35 + 0.65 * smooth(rr, 0.05, 0.5)) \
        - 0.32 * np.exp(-((rr - 0.74) / 0.022) ** 2) + 0.14 * np.exp(-((rr - 0.695) / 0.025) ** 2) \
        - 0.35 * (1 - smooth(rr, 0.035, 0.06)) + 0.10 * np.exp(-((rr - 0.10) / 0.03) ** 2)
    lum = lum + np.where(rc, capl, 0)
    lum = lum * np.where(rc, 0.94, 1.0)
    wear += np.where(rc, smooth(rr, 0.90, 0.985) * 0.50 * (0.35 + 0.65 * brk), 0)

    # ---- stamped housings ----------------------------------------------------------------------------------------
    lo = is_["lower"]
    for zr in (-4.55,):                                         # press line along the trigger housing
        dz = z - zr
        lum = lum + own * np.where(lo & (x > 8.5) & (x < 24.5), 0.09 * np.exp(-((dz + 0.10) / 0.10) ** 2) - 0.12 * np.exp(-((dz - 0.10) / 0.10) ** 2), 0)
    mh = is_["maghousing"]
    dz = z - 0.75                                               # the flared lip of the magazine housing
    lum = lum + own * np.where(mh, 0.10 * np.exp(-((dz + 0.12) / 0.11) ** 2) - 0.13 * np.exp(-((dz - 0.10) / 0.10) ** 2), 0)
    dirt += np.where(mh, smooth(z, 0.9, 1.4) * 0.10, 0)

    # ---- grip: rubbed straps, their seam, grime in the middle ---------------------------------------------------
    gr = is_["grip"] & (own > 0)
    strap = np.clip((np.abs(Nn[:, 0]) - 0.55) / 0.35, 0, 1)
    wear += np.where(gr, strap * 0.20 * brk, 0)
    lum = lum + np.where(gr, -0.07 * np.clip(0.5 + mott, 0, 1) * (1 - strap), 0)
    lum = lum + np.where(gr & (strap > 0.5), 0.10 * np.exp(-(d / 0.14) ** 2) - 0.10 * np.exp(-((d - 0.30) / 0.10) ** 2), 0)

    # ---- magazine: darker blued steel, rub bands across it, rubbed where it rides in the housing ---------------
    mg = is_["mag"] | is_["magbottom"]
    base[mg] = BLUE
    # the magazine's front / back faces share their texels with the stock's guide tubes (and a strip of the grip):
    # a tone between the two there - the faces read as a lighter flat of the magazine, the guides as shaded rails
    sh_mg = mg & (own < 0.5)
    base[sh_mg] = BLUE * 0.55 + PHOS * 0.45
    band = L.fbm3(P * np.array([0.15, 0.15, 1.0]), 2.4, 3, SEED + 50, None)
    lum = lum + np.where(mg, 0.035 * band, 0)

    # ---- wire stock: bare worn steel with patina ------------------------------------------------------------------
    st = is_["stockrod"] | is_["stockloop"]
    base[st] = BARE
    pat = np.clip(0.45 + 1.3 * L.fbm3(P, 0.9, 3, SEED + 60, None), 0, 1)
    spots = np.clip((L.fbm3(P, 3.5, 2, SEED + 61, None) - 0.25) * 3.0, 0, 1)
    k = np.clip(0.50 * pat + 0.35 * spots, 0, 0.75)
    base[st] = (BARE[None] * (1 - k[st, None]) + PATINA[None] * k[st, None])
    wear = np.where(st, wear * 0.4, wear)
    dk = is_["trigger"] | is_["oiler"] | is_["port"]
    base[dk] = DARK
    base[is_["port"]] = DARK * 0.62

    # ---- compose ---------------------------------------------------------------------------------------------------
    # shared texels: the other part sees this paint through its own, different unwrap - anything that depends on
    # position or normal would come out there as warped bands, so it is damped to a plain tone
    shade = 0.93 + (shade - 0.93) * (0.5 + 0.5 * own)
    g2 = is_["grip2"]                # the grip plates are unwrapped as fans: only a plain tone survives that
    shade = np.where(g2, 0.93, shade)
    lum = np.where(g2, 1 + (lum - 1) * 0.35, lum)
    col = base * (lum * shade)[:, None]
    wear = np.clip(wear, 0, 0.62)
    col = col * (1 - wear[:, None]) + WEAR[None] * (wear * (0.70 + 0.30 * np.clip(shade, 0, 1.3)))[:, None]
    col *= (1 - np.clip(dirt, 0, 0.5))[:, None]
    out = np.zeros((N, N, 3), np.float32)
    out[mask] = col
    out = L.pad(out, mask, None)
    return out, mask, PART


def preview(S, new, old, path, scale=17.0):
    parts_old = [(s, old) for s in S.values()]
    parts_new = [(s, new) for s in S.values()]
    views = [("right", 0, 90, 0), ("left", 180, 90, 0), ("top", 0, 0, 0), ("front34", 140, 65, 0), ("rear34", 40, 65, 0)]
    rows = []
    for name, yaw, pitch, roll in views:
        a = soft3d.render(parts_old, yaw, pitch, scale=scale, roll=roll, gain=1.45, bg=(150, 156, 160), wrap=True)
        b = soft3d.render(parts_new, yaw, pitch, scale=scale, roll=roll, gain=1.45, bg=(150, 156, 160), wrap=True)
        row = np.zeros((a.shape[0], a.shape[1] * 2 + 8, 3), np.float32) + 255
        row[:, :a.shape[1]] = a; row[:, a.shape[1] + 8:] = b
        rows.append(row)
    W = max(r.shape[1] for r in rows); H = sum(r.shape[0] + 6 for r in rows)
    sh = np.zeros((H, W, 3), np.float32) + 255; yy = 0
    for r in rows:
        sh[yy:yy + r.shape[0], :r.shape[1]] = r; yy += r.shape[0] + 6
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(sh.astype(np.uint8)).save(path, quality=90)


def zoom(S, new, path):
    """the repaint only, twice the size: right side, top, right from above, from behind and above (the rear cap)."""
    parts = [(s, new) for s in S.values()]
    tiles = [soft3d.render(parts, yaw, pitch, scale=30.0, roll=roll, gain=1.45, bg=(150, 156, 160), wrap=True)
             for yaw, pitch, roll in ((0, 90, 0), (0, 180, 0), (0, 135, 0), (90, 115, 0))]
    W = max(t.shape[1] for t in tiles); H = sum(t.shape[0] + 6 for t in tiles)
    sh = np.zeros((H, W, 3), np.float32) + 255; yy = 0
    for t in tiles:
        sh[yy:yy + t.shape[0], :t.shape[1]] = t; yy += t.shape[0] + 6
    Image.fromarray(sh.astype(np.uint8)).save(path, quality=90)


def main():
    N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4096      # the staged sheet is the 4096 one
    S = L.load_skd(SKD)
    A = L.load_skd("models/weapons/greasegun/greasegun_silenced.skd")
    for k in S:
        assert np.abs(S[k]["uv"] - A[k]["uv"]).max() < 1e-6 and np.abs(S[k]["pos"] - A[k]["pos"]).max() < 1e-6, k
    print("greaser.skd == the gun inside greasegun_silenced.skd (UVs and positions)")
    new, mask, PART = paint(S, N)
    if "--draft" in sys.argv:
        back = np.clip(new, 0, 255)
    else:
        p, nb = L.write_dds(new, STEM + ".dds")
        back = L.dds_decode_top(p)
        print("wrote", p, nb, "bytes; mean", new[mask].mean(0).round(1), "dxt err", float(np.abs(back - np.clip(new, 0, 255)).mean().round(2)))
    if "--preview" in sys.argv:
        old, vp, pak = L.read_image(STEM)
        print("today:", vp, pak, old.shape)
        oldu = np.asarray(Image.fromarray(old.astype(np.uint8)).resize((N, N), Image.BICUBIC), np.float32)
        L.side_by_side(oldu, back, os.path.join(L.EVI, "greasegun_sheet_old_new.jpg"), h=900,
                       labels=("today 512x512 jpg", "repaint %dx%d dds" % (N, N)))
        preview(S, back, oldu, os.path.join(L.EVI, "greasegun_soft3d.jpg"))
        zoom(S, back, os.path.join(L.EVI, "greasegun_soft3d_zoom.jpg"))


if __name__ == "__main__":
    main()
