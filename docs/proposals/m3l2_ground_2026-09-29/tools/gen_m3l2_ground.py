# -*- coding: utf-8 -*-
"""m3l2 farmyard + road textures from the game's OWN retail photographs (no download, no upscaler, no AI).

    python gen_m3l2_ground.py OUTDIR [--seed N] [--quick]

FARMYARD (textures/hzm_m3l2/farmyard, 2048x2048, drawn world-projected at 1024 units per repeat):
  1. Exemplars = the packed-dirt parts of six retail ground photographs (pinned by sha256 below), resampled to
     1 unit per pixel and colour-normalised to one target, so they read as one soil.
  2. Periodic image quilting (quilt.py): a 1024x1024 tile where every pixel is a real exemplar pixel and patches
     meet on minimum-error cuts - seamless on the torus by construction. Patches carrying a strong low-frequency
     blob (a dark rut band, an orange straw clump) are penalised so nothing distinctive can mark a repeat;
     re-use of the same source spot is penalised so no clone reads.
  3. Grade: per-channel mean to the neighbours' dirt (set2 / set2rad dirt as shipped), luma contrast to the
     retail dirt's; a very low-contrast periodic macro variation (damp/dry, 150-400 u) so one repeat is not flat.
  4. 2x periodic Lanczos to 2048 (no sharpening) + a luma-only fine grain (0.5-2 u) at the amplitude of the
     neighbouring CC0 grass's own fine band, so the texel density near the feet matches the terrain around it.
ROAD (textures/hzm_m3l2/road, 1024x1024, the curve patches' own UVs: s along, t = 0..1 across):
  the same soil quilted along s, two faint compacted wheel tracks, and shoulders made of the neighbouring terrain
  grass itself (m3l3grass_1rough as shipped in zzzzzzzzz_coop_terrain.pk3) on an irregular, noise-perturbed edge.
Every filter is periodic (FFT or wrap-padded), so neither texture can gain a wrap seam.
"""
import argparse, hashlib, io, json, os, re, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene as SC          # noqa: E402
import quilt as Q           # noqa: E402

W = "textures/wilderness/"
# (base, retail pak (game\\pak), sha256 of that member, crop box (x0,y0,x1,y1) in px, world units per px)
EXEMPLARS = [
    (W + "m3l3grass_bocroad_new", "mainta\\pak1.pk3", ".jpg", (0, 165, 512, 320), 0.91),
    (W + "m3l3grass_bocroad", "main\\Pak2.pk3", ".jpg", (0, 165, 512, 285), 0.91),
    (W + "m3l3grass_set2", "main\\Pak2.pk3", ".jpg", (125, 0, 256, 512), 0.9),
    ("textures/misc_outside/bocroad", "main\\Pak2.pk3", ".jpg", (80, 0, 210, 512), 0.9),
    (W + "m3l3grass_set2rad", "main\\Pak2.pk3", ".jpg", (60, 300, 330, 512), 0.84),
    ("textures/misc_outside/dryearth1_rd", "main\\Pak2.pk3", ".jpg", (150, 0, 390, 512), 0.9),
    (W + "m3l3grass_bocroadt", "mainta\\pak1.pk3", ".jpg", (60, 40, 460, 470), 0.91),
    ("textures/misc_outside/bocroadadam", "main\\Pak2.pk3", ".jpg", (40, 0, 170, 512), 0.9),
]
ROAD_TARGET = np.array([118.0, 95.0, 70.0])   # a travelled lane: a little darker than the yard (wheel tracks darken the centre band further), gate: band within 6 levels
FARM_TEX = int(os.environ.get("HZM_FARM_TEX", "2048"))                # texture size in px (2048 / 512 u = 4 px/u)
FARM_PERIOD = int(os.environ.get("HZM_FARM_PERIOD", "512"))      # world units per farmyard repeat = quilt pixels at 1 u/px; bsp_patch.PERIOD must equal it
DIRT_TARGET = np.array([119.0, 96.0, 72.0])   # between shipped set2 dirt (121.4 99.5 74.6) and set2rad dirt (121.3 97.5 73.6)
MID_KEEP = float(os.environ.get("HZM_MID_KEEP", "0.65"))
LOW_U = 20.0
MACRO = 0.6
ROAD_MACRO = 0.2      # the road soil repeats every ~470 u along the road: a strong damp/dry blotch would mark each repeat
FINE_KEEP = 0.75
GRASS = (W + "m3l3grass_1rough", ".dds")        # live winner = zzzzzzzzz_coop_terrain.pk3 (CC0 Ground037)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


TOE_LV = 12.0


def toe(x):
    """identity on [TOE_LV, 255-TOE_LV]; smooth exponential knees outside (value and slope continuous), so the
    darkest straw crevices keep their order instead of clamping flat to 0 (the v3 terrain recipe, wider knee)."""
    y = np.array(x, np.float64)
    lo = y < TOE_LV
    y[lo] = TOE_LV * np.exp((y[lo] - TOE_LV) / TOE_LV)
    hi = y > 255.0 - TOE_LV
    y[hi] = 255.0 - TOE_LV * np.exp((255.0 - TOE_LV - y[hi]) / TOE_LV)
    return y


def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def retail_member(base, pak, ext):
    st = SC.stack()
    for i, m in st.copies.get(base + ext, []):
        if st.name(i).lower() == pak.lower():
            b = st.read(i, m)
            return b, hashlib.sha256(b).hexdigest()
    raise SystemExit("missing retail " + base + ext + " in " + pak)


def periodic_noise(shape, sigma, rng):
    """zero-mean unit-std periodic Gaussian-filtered noise (sigma in px)."""
    n = rng.standard_normal(shape)
    f = np.fft.fft2(n)
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    g = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2))
    r = np.real(np.fft.ifft2(f * g))
    return (r - r.mean()) / (r.std() + 1e-12)


def periodic_resize(a, h2, w2):
    """Lanczos on a wrap-padded canvas, cropped back: periodic in, periodic out."""
    h, w = a.shape[:2]
    pad = 16
    big = np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode="wrap")
    sy, sx = h2 / h, w2 / w
    out = []
    for c in range(a.shape[2]):
        im = Image.fromarray(big[..., c].astype(np.float32), mode="F")
        im = im.resize((int(round(big.shape[1] * sx)), int(round(big.shape[0] * sy))), Image.LANCZOS)
        r = np.asarray(im)
        oy, ox = int(round(pad * sy)), int(round(pad * sx))
        out.append(r[oy:oy + h2, ox:ox + w2])
    return np.stack(out, -1)


def band_std(L, lo_px, hi_px):
    """std of the luma band between two Gaussian scales (periodic)."""
    a = ndimage.gaussian_filter(L, lo_px, mode="wrap")
    b = ndimage.gaussian_filter(L, hi_px, mode="wrap")
    return float((a - b).std())


def load_exemplars():
    ex, meta = [], []
    for base, pak, ext, box, upp in EXEMPLARS:
        b, h = retail_member(base, pak, ext)
        a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float64)
        x0, y0, x1, y1 = box
        c = a[y0:y1, x0:x1]
        # to 1 unit per pixel
        hh, ww = int(round(c.shape[0] * upp)), int(round(c.shape[1] * upp))
        c = np.stack([np.asarray(Image.fromarray(c[..., k].astype(np.float32), "F").resize((ww, hh), Image.LANCZOS))
                      for k in range(3)], -1)
        ex.append(c)
        meta.append(dict(base=base, pak=pak, ext=ext, sha256=h, box=box, units_per_px=upp))
    return ex, meta


def normalise(ex):
    """each exemplar: per-channel mean -> DIRT_TARGET, luma std -> the pooled median (keeps each one's chroma)."""
    stds = [luma(e).std() for e in ex]
    tgt_std = float(np.median(stds))
    out = []
    for e, s in zip(ex, stds):
        m = e.reshape(-1, 3).mean(0)
        k = tgt_std / s
        out.append((e - m) * k + DIRT_TARGET)
    return out, tgt_std


def blob_map(e):
    L = luma(e)
    lp = ndimage.gaussian_filter(L, 9)
    return np.abs(lp - L.mean()) / (L.std() + 1e-9)


def fine_grain(shape, rng, amp, k=1.0):
    """luma-only grain: soil particles (sigma 0.7 px) + sparse pebbles (1-3 px), zero mean, periodic. k = texels per
    the 2 px/u the recipe was tuned at (k=2 for a 4 px/u texture: same world sizes, twice the pixels); k>1 adds a
    texel-level component (sigma 0.7 px) so the texels near the feet are not a smooth 2x magnification."""
    g = periodic_noise(shape, 0.7 * k, rng) * 0.75
    g += periodic_noise(shape, 1.6 * k, rng) * 0.45
    # pebbles: sparse points, blurred, both signs (light grit / dark crumbs)
    pts = np.zeros(shape)
    n = int(shape[0] * shape[1] * 0.004 / (k * k))
    ys, xs = rng.integers(0, shape[0], n), rng.integers(0, shape[1], n)
    pts[ys, xs] = rng.choice([-1.0, 1.0], n, p=[0.45, 0.55]) * rng.uniform(0.6, 1.4, n)
    pts = ndimage.gaussian_filter(pts, 0.9 * k, mode="wrap")
    pts /= (pts.std() + 1e-9)
    g += pts * float(os.environ.get("HZM_PEBBLE", "0.5"))
    if k > 1.0:
        g += periodic_noise(shape, 0.7, rng) * 0.35
    g = (g - g.mean()) / g.std()
    return g * amp


def equalise(q, size, rng, macro_amp=None):
    """(1) drop the quilt's own low frequencies (> LOW_U): patch-to-patch tone steps are what make a quilt look
    blocky; (2) put back a smooth periodic damp/dry field instead (very low contrast); (3) soften the mid band
    (8-64 u clumps and streaks that let the eye find a repeat) to MID_KEEP; (4) calm the crunchy 1-2 u JPEG edge
    band of the retail photographs to FINE_KEEP (the fine grain added after the 2x step restores texel detail)."""
    sc = 1.0                  # the quilt is 1 u/px: every sigma below is in world units
    blur = lambda a, sg: np.stack([ndimage.gaussian_filter(a[..., c], sg, mode="wrap") for c in range(3)], -1)
    low = blur(q, LOW_U * sc)
    q = q - low + DIRT_TARGET
    m1 = periodic_noise(q.shape[:2], 150.0 * sc, rng)
    m2 = periodic_noise(q.shape[:2], 60.0 * sc, rng)
    macro = 0.7 * m1 + 0.3 * m2
    macro /= macro.std()
    damp = np.array([0.93, 0.92, 0.90])
    dry = np.array([1.05, 1.05, 1.06])
    t = np.clip(macro * (MACRO if macro_amp is None else macro_amp), -1, 1)[..., None]
    q = q * np.where(t < 0, 1 + (-t) * (damp - 1), 1 + t * (dry - 1))
    lo, hi = blur(q, 4.0 * sc), blur(q, 32.0 * sc)
    q = q - (1 - MID_KEEP) * (lo - hi)
    f1 = blur(q, 0.8)
    q = f1 + FINE_KEEP * (q - f1)
    q = clean(q)
    return q - q.reshape(-1, 3).mean(0) + DIRT_TARGET


DESPECK_TH = 35.0


def clean(q):
    """(v6) remove the retail JPEG's single-pixel coloured/white/black specks (a 3x3 median replaces any pixel more than
    DESPECK_TH from its median), smooth chroma at sigma 1.5 (JPEG 4:2:0 colour noise) and soften the 1-2 u oversharpened
    'worm' band to half (sigma 0.9). All periodic (wrap), so no seam can appear."""
    med = np.stack([ndimage.median_filter(q[..., c], 3, mode="wrap") for c in range(3)], -1)
    bad = (np.abs(luma(q) - luma(med)) > DESPECK_TH) | (np.abs(q - med).max(-1) > DESPECK_TH)
    q = np.where(bad[..., None], med, q)
    l = luma(q)[..., None]
    ch = q - l
    ch = np.stack([ndimage.gaussian_filter(ch[..., c], 1.5, mode="wrap") for c in range(3)], -1)
    q = l + ch
    lo = np.stack([ndimage.gaussian_filter(q[..., c], 0.9, mode="wrap") for c in range(3)], -1)
    return lo + 0.5 * (q - lo)


def build_farmyard(seed, quick=False):
    ex, meta = load_exemplars()
    ex, tgt_std = normalise(ex)
    bm = [blob_map(e) for e in ex]
    size = 256 if quick else FARM_PERIOD
    log("quilting %d" % size)
    qstats = {}
    q = Q.quilt(ex, size=size, P=88, O=24, stats=qstats, seed=seed, blob_w=3.0, blob_maps=bm, reuse_w=40.0, tol=0.10,
                log=log)
    rng = np.random.default_rng(seed + 100)
    q = equalise(q, size, rng)
    ppu = FARM_TEX // FARM_PERIOD                              # texels per world unit (2 -> 1024 px, 4 -> 2048 px)
    up = periodic_resize(q, FARM_TEX, FARM_TEX)
    # fine grain at the neighbouring grass's own fine-band amplitude (relative), measured at 2 px/u
    grass = grass_rgb()
    gL = luma(periodic_resize(grass, 1024, 1024))             # 1rough 2048 px / 512 u -> 2 px/u
    grass_fine = band_std(gL, 0.5, 2.0) / gL.mean()
    uL = luma(up)
    k = ppu / 2.0
    have = band_std(uL, 0.5 * k, 2.0 * k) / uL.mean()
    need = max(0.0, grass_fine * 0.85 - have)
    g = fine_grain(up.shape[:2], rng, need, k)
    up = up * (1 + g[..., None])
    rep = dict(exemplars=meta, quilt=qstats, period_u=size, luma_std_target=tgt_std, grass_fine=grass_fine, fine_before=have, grain_amp=need)
    return up, q, rep


_GRASS = None


def grass_rgb():
    global _GRASS
    if _GRASS is None:
        rgb, src = SC.live_image(GRASS[0])
        _GRASS = np.asarray(rgb, np.float64)
    return _GRASS


def soil_tile(seed, size, ex, bm):
    q = Q.quilt(ex, size=size, P=88, O=24, seed=seed, blob_w=3.0, blob_maps=bm, reuse_w=40.0, tol=0.10, log=log)
    q = equalise(q, 1024, np.random.default_rng(seed + 101), macro_amp=ROAD_MACRO)
    return q - q.reshape(-1, 3).mean(0) + ROAD_TARGET


def build_road(seed, quick=False):
    """1024x1024, s = columns (along the road), t = rows (0..1 across). Curve patches: ~470 u along x ~390 u across
    per repeat (BSP-measured median), grass shoulders at both t edges meet the terrain grass."""
    N = 512 if quick else 1024
    ACROSS_U = 390.0
    ex, meta = load_exemplars()
    ex, tgt_std = normalise(ex)
    bm = [blob_map(e) for e in ex]
    soil = soil_tile(seed + 300, 448, ex, bm)                    # periodic 448 u -> one road repeat along s
    soil = soil[:int(ACROSS_U)]                                  # across: rows 0..390 u (edges are grass)
    soil = periodic_resize(soil, N, N)
    rng = np.random.default_rng(seed + 200)
    t = (np.arange(N) + 0.5) / N
    s = (np.arange(N) + 0.5) / N
    Tt, Ss = np.meshgrid(t, s, indexing="ij")
    # wheel tracks: two compacted bands 75 u apart (cart / truck gauge), gently meandering (periodic in s)
    gauge = 75.0 / ACROSS_U
    mea = 0.012 * np.sin(2 * np.pi * Ss + 1.3) + 0.006 * np.sin(4 * np.pi * Ss + 0.4)
    w = 13.0 / ACROSS_U
    track = (np.exp(-((Tt - 0.5 + gauge / 2 - mea) / w) ** 2) + np.exp(-((Tt - 0.5 - gauge / 2 - mea) / w) ** 2))
    tv = periodic_noise((N, N), N / 90.0, rng) * 0.5 + 0.5          # tracks fade in and out along the road
    track *= np.clip(0.55 + 0.45 * tv, 0, 1)
    L = luma(soil)
    fine = L - ndimage.gaussian_filter(L, 1.5, mode="wrap")
    soil = soil - (0.35 * track * fine)[..., None]                   # compacted: smoother
    soil = soil * (1 - 0.07 * track)[..., None]                      # and a little darker
    # shoulders: the terrain grass itself, anisotropically resampled so it stays periodic along s
    gr = grass_rgb()
    gh = int(round(gr.shape[0] * ACROSS_U / 512.0))
    grass = periodic_resize(gr[:gh], N, N) if False else np.stack(
        [np.asarray(Image.fromarray(gr[:gh, :, c].astype(np.float32), "F").resize((N, N), Image.LANCZOS))
         for c in range(3)], -1)
    # ragged edge: position along s from periodic noise, ragged at 5-20 u
    e_big = periodic_noise((1, N), N / 40.0, rng)[0]
    e_mid = periodic_noise((N, N), N / 160.0, rng)
    e_fine = periodic_noise((N, N), N / 700.0, rng)
    edge = 0.155 + 0.03 * e_big[None, :]
    dist = np.minimum(Tt, 1 - Tt)                                    # 0 at the patch edge
    field = (dist - edge) / 0.045 + 0.55 * e_mid + 0.25 * e_fine
    gw = np.clip(0.5 - field, 0, 1)
    gw = ndimage.gaussian_filter(gw, (1.2, 1.2), mode="wrap")
    # a trampled verge: the soil next to the grass carries a little dry grass colour
    verge = np.clip(1 - np.abs(field - 0.5) / 1.2, 0, 1) * 0.25
    dry = soil * (1 - verge[..., None]) + (0.6 * soil + 0.4 * grass) * verge[..., None]
    road = dry * (1 - gw[..., None]) + grass * gw[..., None]
    return road, dict(exemplars=meta, across_u=ACROSS_U, along_u=470, gauge_u=75)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fy, q, rep = build_farmyard(a.seed, a.quick)
    Image.fromarray(np.clip(np.round(toe(fy)), 0, 255).astype(np.uint8)).save(os.path.join(a.out, "farmyard.png"))
    np.save(os.path.join(a.out, "farmyard_1u.npy"), q.astype(np.float32))
    with open(os.path.join(a.out, "farmyard_report.json"), "w") as fh:
        json.dump(rep, fh, indent=1, default=float)
    log("farmyard done", rep["grass_fine"], rep["fine_before"], rep["grain_amp"])
    rd, rrep = build_road(a.seed, a.quick)
    Image.fromarray(np.clip(np.round(toe(rd)), 0, 255).astype(np.uint8)).save(os.path.join(a.out, "road.png"))
    with open(os.path.join(a.out, "road_report.json"), "w") as fh:
        json.dump(rrep, fh, indent=1, default=float)
    log("road done")


if __name__ == "__main__":
    main()
