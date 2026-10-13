"""MP18 skin generator: new diffuse sheets for models/weapons/coop_mp18/mp18.skd, painted into the mesh's own UV
islands (mesh, UVs, tik and shader untouched).

    python mp18skin.py            writes assets/textures/coop_mp18/{body,stuff,drum,clip}.jpg + front.JPG
    python mp18skin.py --preview  also evidence/sheet_<name>.jpg (1024 previews, old | new)

What it does
  * bakes position / normal / island id per texel from the mesh (islands.py),
  * WOOD (stock islands of Tube1): the Kar98 stock wood the engine already loads, sampled once per island at the
    Kar98's own physical scale (no tiling along the grain; rows stacked across the grain), graded darker,
  * STEEL (everything else): flat blued base, the MP40 sheet's own scratch / mottle detail (high-passed, mirror
    tiled), a baked top-light term from the mesh normals (these shaders are rgbGen lightingSpherical - no specular,
    so the sheen has to be in the diffuse like on the retail guns), worn convex edges and dark concave edges from the
    mesh's dihedral angles,
  * painted mechanism: cooling holes on the barrel jacket, ejection port, muzzle bore, butt plate,
  * the snail drum keeps the pack's own art (it has real detail, it was only crushed to black): levels lifted to the
    MP40's steel range.
Sources are read from the shipped pak set by srcdump.py (work/src/kar98.png, mp40.png). Seeded: same output every run.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
import islands
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PROP = os.path.abspath(os.path.join(HERE, ".."))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
OLD = os.path.join(MOD, "textures", "coop_mp18")
OUT = os.path.join(PROP, "assets", "textures", "coop_mp18")
SRC = os.path.join(PROP, "work", "src")
EVI = os.path.join(PROP, "evidence")

# ---- tunables -------------------------------------------------------------------------------------------------
WOOD_GAIN = 0.60          # Kar98 wood -> darker walnut
WOOD_SAT = 0.80
WOOD_SCALE = 1.5          # output px per Kar98 source px at 2048 (same px/cm as the Kar98 sheet)
STEEL_RGB = np.array([28.0, 28.5, 29.5])     # blued base, set from the MP40 tube (see steel_stats in main)
WEAR_RGB = np.array([104.0, 103.0, 99.0])
WOOD_ISL = {2: 1.0, 3: 1.45}                # Tube1 island -> across-grain squash of its unwrap
WOOD_DARK_ISL = {1}                          # inside of the fore-end
RS = np.random.RandomState(1918)


def noise(shape, sigma, seed):
    r = np.random.RandomState(seed).rand(*shape).astype(np.float32)
    g = ndi.gaussian_filter(r, sigma, mode="wrap")
    g -= g.mean(); g /= (g.std() + 1e-9)
    return g


def bake(s, N):
    """texel -> (pos, normal, island id); -1 where no triangle."""
    pos = np.zeros((N, N, 3), np.float32); nrm = np.zeros((N, N, 3), np.float32)
    isl = -np.ones((N, N), np.int32)
    uvp = s["uv"] * N
    for ti, t in enumerate(s["tris"]):
        a, b, c = uvp[t]
        x0 = max(0, int(np.floor(min(a[0], b[0], c[0])) - 1)); x1 = min(N, int(np.ceil(max(a[0], b[0], c[0])) + 2))
        y0 = max(0, int(np.floor(min(a[1], b[1], c[1])) - 1)); y1 = min(N, int(np.ceil(max(a[1], b[1], c[1])) + 2))
        if x1 <= x0 or y1 <= y0:
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -0.03) & (w1 >= -0.03) & (w2 >= -0.03)
        if not m.any():
            continue
        W = np.stack([w0, w1, w2], -1)[m]
        sub_p = pos[y0:y1, x0:x1]; sub_n = nrm[y0:y1, x0:x1]; sub_i = isl[y0:y1, x0:x1]
        sub_p[m] = W @ s["pos"][t]; sub_n[m] = W @ s["nrm"][t]; sub_i[m] = s["isl"][ti]
    l = np.linalg.norm(nrm, axis=2, keepdims=True)
    nrm = nrm / np.maximum(l, 1e-6)
    return pos, nrm, isl


def edge_masks(s, N):
    """(convex, concave) masks in UV space from the mesh's sharp edges (dihedral > 28 deg), welded by position."""
    P = s["pos"]; T = s["tris"]
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    fn /= (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-9)
    vn = s["nrm"][T].mean(1)
    fn *= np.sign((fn * vn).sum(1, keepdims=True) + 1e-9)        # outward = the side the vertex normals point to
    cen = P[T].mean(1)
    key = {}
    wid = np.zeros(len(P), int)
    for i, p in enumerate(P):
        wid[i] = key.setdefault(tuple(np.round(p, 2)), len(key))
    edges = {}
    for ti, t in enumerate(T):
        for k in range(3):
            i, j = int(t[k]), int(t[(k + 1) % 3])
            e = tuple(sorted((wid[i], wid[j])))
            edges.setdefault(e, []).append((ti, i, j))
    cv = Image.new("L", (N, N), 0); cc = Image.new("L", (N, N), 0)
    dv = ImageDraw.Draw(cv); dc = ImageDraw.Draw(cc)
    uvp = s["uv"] * N
    for e, lst in edges.items():
        if len(lst) != 2:
            continue
        (ta, ia, ja), (tb, ib, jb) = lst
        d = float((fn[ta] * fn[tb]).sum())
        if d > np.cos(np.radians(28)):
            continue
        # smooth-shaded facets (cylinders) are not edges: the two triangles must carry different normals there
        na = s["nrm"][ia] + s["nrm"][ja]; nb = s["nrm"][ib] + s["nrm"][jb]
        na /= (np.linalg.norm(na) + 1e-9); nb /= (np.linalg.norm(nb) + 1e-9)
        if float((na * nb).sum()) > np.cos(np.radians(20)):
            continue
        convex = float(((cen[tb] - cen[ta]) * fn[ta]).sum()) < 0
        for (i, j) in ((ia, ja), (ib, jb)):
            seg = [tuple(uvp[i]), tuple(uvp[j])]
            (dv if convex else dc).line(seg, fill=255, width=max(2, N // 512))
    return np.asarray(cv, np.float32) / 255, np.asarray(cc, np.float32) / 255


def wood_atlas():
    k = np.asarray(Image.open(os.path.join(SRC, "kar98.png")).convert("RGB"), np.float32)
    r2 = k[105:185, 1050:1740]                       # clean stock wood, 690 x 80
    r1 = k[10:95, 820:1370][:80]                     # darker band of the same stock, 550 x 80
    r1 = np.concatenate([r1, r1[:, ::-1][:, :140]], 1)
    r1 = r1 * (r2.mean((0, 1)) / r1.mean((0, 1)))   # same overall colour as r2
    blocks = [r2, r1, r2[::-1, ::-1], r1[::-1, ::-1]]
    ov = 12
    at = blocks[0]
    for b in blocks[1:]:
        w = np.linspace(0, 1, ov)[:, None, None]
        seam = at[-ov:] * (1 - w) + b[:ov] * w
        at = np.concatenate([at[:-ov], seam, b[ov:]], 0)
    return at                                        # 284 x 690


def sample(at, sy, sx):
    out = np.zeros(sy.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = ndi.map_coordinates(at[..., c], [sy, sx], order=1, mode="mirror")
    return out


def steel_detail(N):
    m = np.asarray(Image.open(os.path.join(SRC, "mp40.png")).convert("L"), np.float32)
    r = m[1055:1185, 520:1450]                       # lower receiver tube of the MP40 sheet: plain worn steel
    # keep its scratches (fine) and a little of its mottle, drop its baked highlight
    d = (r / (ndi.gaussian_filter(r, 5) + 1e-3)) ** 0.75 * (r / (ndi.gaussian_filter(r, 16) + 1e-3)) ** 0.35
    d = np.clip(d, 0.6, 1.7)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    sc = N / 2048.0
    return ndi.map_coordinates(d, [(yy / sc) * 0.9 + 7, (xx / sc) * 0.9 + 11], order=1, mode="mirror"), float(r.mean())


def pad(img, mask, px):
    """bleed island colours into the gutters (mips), nearest covered texel."""
    dist, idx = ndi.distance_transform_edt(~mask, return_distances=True, return_indices=True)
    out = img[idx[0], idx[1]]
    far = dist > px
    out[far] = out[far] * 0.0 + np.array([30.0, 30.0, 31.0])
    return out


def steel(N, pos, nrm, cv, cc, seed, detail, top=1.0):
    up = np.clip(-nrm[..., 2], 0, 1)
    mott = 0.02 * noise((N, N), N / 60, seed) + 0.04 * noise((N, N), N / 300, seed + 1)
    streak = 0.75 + 0.25 * ndi.gaussian_filter(np.random.RandomState(seed + 2).rand(N, N).astype(np.float32),
                                               (N / 900, N / 30), mode="wrap") * 2
    shade = 0.82 + 0.20 * up + top * 0.85 * (up ** 6) * streak
    lum = detail * (1 + mott) * shade
    col = STEEL_RGB[None, None, :] * lum[..., None]
    # worn convex edges: broken up by noise, never a uniform outline
    core = ndi.gaussian_filter(cv, N / 1700) * 1.5; halo = ndi.gaussian_filter(cv, N / 400) * 5
    brk = np.clip(0.55 + 0.22 * noise((N, N), N / 90, seed + 3) + 0.22 * noise((N, N), N / 500, seed + 4), 0.15, 1)
    wear = np.clip(core * 0.8 + halo * 0.12, 0, 1) * brk * (0.6 + 0.4 * detail)
    wear = np.clip(wear, 0, 0.5)
    col = col * (1 - wear[..., None]) + WEAR_RGB[None, None, :] * wear[..., None] * (0.75 + 0.25 * shade[..., None])
    dirt = np.clip(ndi.gaussian_filter(cc, N / 400) * 4, 0, 1)
    col *= (1 - 0.45 * dirt)[..., None]
    return col


def hole_paint(col, r, Y, m):
    """dark hole with a soft shadow and a lit lower lip. r = distance from the hole centre in hole radii, Y = the
    downward offset in radii (both per texel, in gun space), m = texels this may touch."""
    inside = np.clip((1.0 - r) / 0.10, 0, 1) * m
    halo = np.clip(1 - (r - 1) / 0.45, 0, 1) * (r >= 1) * m
    lip = np.clip(1 - np.abs(r - 1.07) / 0.09, 0, 1) * np.clip(Y, 0, 1) * m       # lower rim catches the light
    rimd = np.clip(1 - np.abs(r - 0.93) / 0.12, 0, 1) * np.clip(-Y, 0, 1) * m     # upper inner wall in shadow
    col *= (1 - 0.25 * halo)[..., None]
    col += (lip * 26)[..., None]
    inner = np.array([7.0, 7.0, 8.0])[None, None, :] * (1.0 + 0.5 * np.clip(Y, -1, 1))[..., None]
    col[:] = col * (1 - inside[..., None]) + inner * inside[..., None]
    col *= (1 - 0.35 * rimd * (1 - inside))[..., None]



def save(arr, name, N, q=93):
    os.makedirs(OUT, exist_ok=True)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    im.save(os.path.join(OUT, name), "JPEG", quality=q, subsampling=0)
    return im


def build_body(S, N, at, detail):
    s = S["Tube1"]
    pos, nrm, isl = bake(s, N)
    cv, cc = edge_masks(s, N)
    mask = isl >= 0
    st = steel(N, pos, nrm, cv, cc, 11, detail)
    col = st.copy()
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    k = N / 2048.0 * WOOD_SCALE
    warp = 5.0 * noise((N, N), N / 14, 21) + 9.0 * noise((N, N), N / 5, 22)
    sheen = 1 + 0.06 * noise((N, N), N / 12, 23) + 0.03 * noise((N, N), N / 80, 24)
    woodm = np.zeros((N, N), bool)
    for kisl, off in ((2, (0, 6)), (3, (150, 30)), (1, (90, 12))):
        m = isl == kisl
        if not m.any():
            continue
        ys, xs = np.nonzero(m if kisl == 1 else (isl == 2))
        x0, y0 = xs.min(), ys.min()
        an = 1.0
        off = off if kisl == 1 else (0, 6)
        sx = (xx - x0) / k + off[1]
        sy = (yy - y0) / k * an + off[0] + warp * an * 0.5
        w = sample(at, sy, sx)
        L = w.mean(2, keepdims=True)
        w = (L + (w - L) * WOOD_SAT) * WOOD_GAIN
        up = np.clip(-nrm[..., 2], 0, 1)
        w *= (sheen * (0.90 + 0.14 * up))[..., None]
        if kisl in WOOD_DARK_ISL:
            w *= 0.45
        col[m] = w[m]
        woodm |= m
    # handled wood: darker at the wrist and along the fore-end's grip, lighter rubbed convex edges, dark creases
    x = pos[..., 0]
    grip = np.exp(-((x + 9.0) / 5.5) ** 2) * 0.20 + np.exp(-((x - 12.0) / 7.0) ** 2) * 0.10
    grime = np.clip(0.6 + 0.5 * noise((N, N), N / 40, 25), 0, 1)
    wd = col * (1 - (grip * grime))[..., None]
    rub = np.clip(ndi.gaussian_filter(cv, N / 300) * 4, 0, 1) * np.clip(0.5 + 0.6 * noise((N, N), N / 70, 26), 0, 1)
    wd = wd * (1 + 0.12 * rub)[..., None]
    wd *= (1 - 0.40 * np.clip(ndi.gaussian_filter(cc, N / 350) * 4, 0, 1))[..., None]
    col[woodm] = wd[woodm]
    # steel butt plate: the last 0.9 u of the butt
    bp = (isl == 2) & (x < -38.35)
    col[bp] = (st[bp] * 1.15)
    edge = (isl == 2) & (x >= -38.35) & (x < -37.9)
    col[edge] *= 0.6
    col = pad(col, mask, 16)
    return col, mask


def build_stuff(S, N, detail):
    s = S["Cube1"]
    pos, nrm, isl = bake(s, N)
    cv, cc = edge_masks(s, N)
    mask = isl >= 0
    col = steel(N, pos, nrm, cv, cc, 31, detail)
    # barrel jacket + magazine collar (island 2). Its unwrap is a PLANAR side projection shared by both sides
    # (u linear in x, v linear in z), so everything on it is laid out in gun space from the baked positions:
    # axis y = -1.3, z = -5.96 + 0.0526 (x - 46.3); jacket radius 2.05 (x > 31.3), collar 2.4.
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    j = isl == 2
    x = pos[..., 0]
    zc = -5.96 + 0.0526 * (x - 46.3)
    th = np.arctan2(np.abs(pos[..., 1] + 1.3), -(pos[..., 2] - zc))          # 0 = top line, pi = bottom line
    # cooling holes: 6 rows round the jacket (38 / 90 / 142 deg each side), 8 per row, alternate rows staggered
    RJ, R, PITCH = 2.05, 0.60, 2.5
    rbest = np.full((N, N), 9.0, np.float32); ybest = np.zeros((N, N), np.float32)
    for row, deg in enumerate((38.0, 90.0, 142.0)):
        x0 = 33.8 + (PITCH / 2 if row % 2 else 0.0)
        nh = 8 if row % 2 == 0 else 7
        k = np.clip(np.round((x - x0) / PITCH), 0, nh - 1)
        dx = x - (x0 + k * PITCH)
        ds = (th - np.radians(deg)) * RJ
        r = np.hypot(dx, ds) / R
        better = r < rbest
        rbest[better] = r[better]; ybest[better] = (ds / R)[better]
    hole_paint(col, rbest, ybest, (j & (x > 31.6)).astype(np.float32))
    # dark step where the jacket meets the collar, worn bright muzzle ring
    step = np.exp(-((x - 31.35) / 0.14) ** 2)
    col[j] *= (1 - 0.5 * step)[j][..., None]
    ring = np.exp(-((x - 55.6) / 0.28) ** 2)
    col[j] += (ring * 22)[j][..., None]
    # ejection port on the collar's side (on the left this shared texel area sits behind the magazine housing)
    dxp = (x - 27.2) / 2.3; dsp = (th - np.radians(84.0)) * 2.4 / 0.85
    rp = (np.abs(dxp) ** 4 + np.abs(dsp) ** 4) ** 0.25
    hole_paint(col, rp / 1.0, dsp, (j & (x < 31.0)).astype(np.float32))
    # muzzle cap (island 1): bore
    m1 = isl == 1
    if m1.any():
        ys, xs = np.nonzero(m1)
        cx0, cy0 = xs.mean(), ys.mean(); rad = (xs.max() - xs.min()) / 2
        r = np.hypot(xx - cx0, yy - cy0) / rad
        bore = np.clip((0.36 - r) / 0.05, 0, 1)
        lip = np.clip(1 - np.abs(r - 0.42) / 0.06, 0, 1)
        col[m1] = (col * (1 - bore[..., None]) + 6 * bore[..., None] + (lip * 30)[..., None])[m1]
    col = pad(col, mask, 16)
    return col, mask


def build_drum(S, N, detail):
    """keep the pack's own drum art, lift its crushed levels into the MP40's steel range."""
    old = Image.open(os.path.join(OLD, "drum.jpg")).convert("RGB").resize((N, N), Image.LANCZOS)
    a = np.asarray(old, np.float32).mean(2)
    s = S["Cube3"]
    _, nrm, isl = bake(s, N)
    mask = isl >= 0
    lo, mid, hi = np.percentile(a[mask], [1, 50, 99.7])
    t = np.where(a < mid, 0.5 * (a - lo) / (mid - lo + 1e-6), 0.5 + 0.5 * (a - mid) / (hi - mid + 1e-6))
    t = np.clip(t, 0, 1.15)
    lum = 0.34 + 0.66 * t * 2.0                 # mid grey of the old art -> the flat steel base, lights -> x1.66
    lum = np.clip(lum, 0.30, 2.6)
    cv, cc = edge_masks(s, N)
    d = steel_detail(N)[0] if detail.shape[0] != N else detail
    col = STEEL_RGB[None, None, :] * (lum * d * (1 + 0.05 * noise((N, N), N / 60, 51)))[..., None]
    rub = np.clip(ndi.gaussian_filter(cv, N / 300) * 4, 0, 1) * np.clip(0.5 + 0.6 * noise((N, N), N / 70, 52), 0, 0.5)
    col = col * (1 - rub[..., None]) + WEAR_RGB[None, None, :] * rub[..., None]
    col = pad(col, mask, 12)
    return col, mask


def build_small(S, name, N, seed, gain=1.0):
    s = S[name]
    pos, nrm, isl = bake(s, N)
    cv, cc = edge_masks(s, N)
    mask = isl >= 0
    d = steel_detail(N)[0]
    col = steel(N, pos, nrm, cv, cc, seed, d) * gain
    return pad(col, mask, 2 * N), mask


def preview(name, new, oldfile):
    os.makedirs(EVI, exist_ok=True)
    o = Image.open(os.path.join(OLD, oldfile)).convert("RGB").resize((768, 768), Image.LANCZOS)
    n = Image.fromarray(np.clip(new, 0, 255).astype(np.uint8)).resize((768, 768), Image.LANCZOS)
    sh = Image.new("RGB", (1536, 768)); sh.paste(o, (0, 0)); sh.paste(n, (768, 0))
    sh.save(os.path.join(EVI, "sheet_%s.jpg" % name), quality=88)


def main():
    global STEEL_RGB
    pv = "--preview" in sys.argv
    S = islands.load()
    N = 2048
    at = wood_atlas()
    detail, mp40_mean = steel_detail(N)
    print("mp40 tube mean luma %.1f, kar98 wood mean %s" % (mp40_mean, at.mean((0, 1)).round(1)))
    body, _ = build_body(S, N, at, detail)
    save(body, "body.jpg", N)
    stuff, _ = build_stuff(S, N, detail)
    save(stuff, "stuff.jpg", N)
    drum, _ = build_drum(S, 1024, detail)
    save(drum, "drum.jpg", 1024)
    clip, _ = build_small(S, "Plane1", 512, 61, gain=1.25)
    save(clip, "clip.jpg", 512)
    front, _ = build_small(S, "Cylinde0", 512, 71)
    save(front, "front.JPG", 512)
    if pv:
        preview("body", body, "body.jpg"); preview("stuff", stuff, "stuff.jpg"); preview("drum", drum, "drum.jpg")
    for n in ("body.jpg", "stuff.jpg", "drum.jpg", "clip.jpg", "front.JPG"):
        p = os.path.join(OUT, n)
        a = np.asarray(Image.open(p), float)
        print(n, Image.open(p).size, os.path.getsize(p), "mean", a.mean((0, 1)).round(1))


if __name__ == "__main__":
    main()
