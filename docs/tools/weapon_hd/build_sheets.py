"""Weapon HD sheet builder - upscale + period material + seeded wear, one sheet at a time, resumable.

    python docs/tools/weapon_hd/build_sheets.py --cls 1                 build every class-1 job (skips finished ones)
    python docs/tools/weapon_hd/build_sheets.py --cls 1 --only sten     only jobs whose stem contains "sten"
    python docs/tools/weapon_hd/build_sheets.py --cls 1 --preview      no DDS encode, previews only (fast iteration)
    python docs/tools/weapon_hd/build_sheets.py --cls 1 --variant 1    wear variant 1 (Tier B rows; seed + 7919*v)

Jobs come from jobs.json (jobs.py), finishes from finishes.json. Work, ESRGAN cache, stage and QA cards live on G:
(BUILD below) - C: is nearly full and a later session must be able to resume. Run it unattended at BELOW-NORMAL
priority on 4 cores (the quiet rule): `run_batch.ps1` does that.

Per sheet (the recipe proven by the 2026-10-05 pilot, docs/proposals/weapon_hd_2026-10-05):
 1 SOURCE = jobs.json's pick (HRRTM lossless TGA, else the original art, never an earlier AI upscale when an
   original exists). 2 Real-ESRGAN x4plus (project tool), Lanczos to the target; > 4x is ESRGAN x4 then Lanczos.
 3 HALLUCINATION GUARD - fall back to sharpened Lanczos where ESRGAN departs from the source (bug-3374), then a TONE
   MATCH so ESRGAN cannot darken dark art (bug-3375). 4 MASKS from every mesh that paints from the sheet (skd.py):
   coverage, convex edges (authored-normal split, or a fold > 55 deg - smooth facets never count), concave grime.
 5 MATERIAL: restore the source's own band-passed metal detail (ESRGAN airbrushes it), then blued / parkerized /
   painted grain; wood pores along the grain; bakelite untouched. 6 WEAR, seeded per sheet: chipped edge wear only
   where the ART also paints a highlight, grime only where it paints a crease (bug-3376: no wireframe tracing),
   scratches clustered at edges, wood dents. No text is ever generated.
 7 DDS: DXT1, or DXT5 when a shader reads alpha (alpha = Pillow's alpha blocks, colour = the project's mean-holding
   BC1 encoder, gen_terrain_pak_v4.bc1_encode_dc, bug-2953), full box-mip chain.
Gates (a failed sheet is recorded in failed.json and skipped, the batch continues): luma correlation vs source
>= 0.90, mean luma within 6%, no NaN, ESRGAN not black (bug-247), decoded DDS mean within 1.5 levels, added-speckle
density below a ceiling.
"""
import os, sys, io, re, json, math, time, struct, hashlib, argparse, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import vfs, skd
import gen_terrain_pak_v2 as V2
import gen_terrain_pak_v3 as V3
import gen_terrain_pak_v4 as V4

ESR = r"C:/mohaa-coop-dev/_tools/realesrgan/realesrgan-ncnn-vulkan.exe"
BUILD = os.environ.get("WHD_BUILD", r"C:/mohaa-weaponhd/build")   # moved off G: 2026-10-05 (G: filled up)
VERSION = "whd-3"          # whd-2: grain fades on bright paint, erase, same-art sources (QA round 1)           # bump when the recipe changes: finished sheets with another version are rebuilt
BELOW_NORMAL = 0x00004000


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(os.path.join(BUILD, "build.log"), "a", encoding="utf-8") as f:
        f.write(s + "\n")


def finish_for(stem):
    d = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8"))
    cfg = dict(d["default"])
    for rx, over in d["rules"]:
        if re.search(rx, stem):
            cfg.update(over)
    return cfg


def safe(stem):
    return stem.replace("/", "__")


# ------------------------------------------------------------------------------------------ source + ESRGAN
def load_source(job):
    # finishes.json "source_winner": use the image that loads TODAY as the source (an earlier upscale whose result is
    # cleaner than re-upscaling the original 8x - 30cal, QA round 2)
    if job["stem"] in json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8")).get("source_winner", []):
        im = Image.open(io.BytesIO(vfs.read(job["loads"])))
        im.load()
        return im
    src = job["source"]
    p = src["pakpath"]           # NOT the basename: main/mainta/maintt each have a pak1.pk3 (14 class-1 KeyErrors)
    vfs.index()
    im = Image.open(io.BytesIO(vfs._zips[p].read(src["name"])))
    im.load()
    return im


def erase(rgb, stem):
    """finishes.json "erase": remove non-period markings from the SOURCE before anything else sees them.
    Harmonic (Laplace) fill from the rect's whole border - column interpolation streaked wherever a border row crossed
    detail (QA) - plus per-pixel noise drawn from a ring around the rect, so the patch has the surrounding grain."""
    rects = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8")).get("erase", {}).get(stem, [])
    if not rects:
        return rgb
    a = np.asarray(rgb, np.float32).copy()
    H, W = a.shape[:2]
    rng = np.random.default_rng(1)
    for (u0, v0, u1, v1) in rects:
        x0, y0 = max(1, int(u0 * W)), max(1, int(v0 * H))
        x1, y1 = min(W - 1, int(math.ceil(u1 * W))), min(H - 1, int(math.ceil(v1 * H)))
        blk = a[y0 - 1:y1 + 1, x0 - 1:x1 + 1].copy()
        inner = blk[1:-1, 1:-1]
        inner[:] = blk[[0, -1]].mean((0, 1))
        for _ in range(1500):
            inner[:] = 0.25 * (blk[:-2, 1:-1] + blk[2:, 1:-1] + blk[1:-1, :-2] + blk[1:-1, 2:])
        ring = a[max(0, y0 - 8):min(H, y1 + 8), max(0, x0 - 8):min(W, x1 + 8)]
        hp = ring - ndimage.gaussian_filter(ring, (1.5, 1.5, 0))
        ys = rng.integers(hp.shape[0], size=inner.shape[:2]); xs = rng.integers(hp.shape[1], size=inner.shape[:2])
        inner += 0.45 * hp[ys, xs] * min(1.0, float(inner.mean()) / 40.0)     # no grain on a black backdrop
        a[y0:y1, x0:x1] = inner
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def esrgan(stem, rgb):
    d = os.path.join(BUILD, "esr"); os.makedirs(d, exist_ok=True)
    key = hashlib.md5(rgb.tobytes()).hexdigest()[:10]
    src = os.path.join(d, safe(stem) + "_" + key + "_in.png"); out = os.path.join(d, safe(stem) + "_" + key + "_x4.png")
    if not os.path.exists(out):
        rgb.save(src)
        subprocess.run([ESR, "-i", src, "-o", out, "-s", "4", "-n", "realesrgan-x4plus", "-t", "256", "-j", "1:1:1"],
                       check=True, capture_output=True, creationflags=BELOW_NORMAL)
        os.remove(src)
    e = Image.open(out).convert("RGB")
    assert np.asarray(e, np.float32).mean() > 2.0 or np.asarray(rgb, np.float32).mean() < 4.0, \
        "ESRGAN produced a black image (bug-247)"
    return e


# ------------------------------------------------------------------------------------------ masks
def surf_match(name, wanted):
    n = name.lower()
    for w in wanted:
        w = w.lower()
        if w == "all" or w == n or (w.endswith("*") and n.startswith(w[:-1])):
            return True
    return False


def mesh_masks(job, W, H):
    cover = Image.new("L", (W, H), 0); cd = ImageDraw.Draw(cover)
    convex = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(convex)
    concave = Image.new("L", (W, H), 0); kd = ImageDraw.Draw(concave)
    st = dict(tris=0, convex=0, concave=0, meshes=0)
    seen = set()
    for u in job["users"]:
        for sp in u["skd"]:
            key = (sp, tuple(sorted(s.lower() for s in u["surfaces"])))
            if key in seen:
                continue
            seen.add(key)
            try:
                d = skd.read(vfs.read(sp))
            except Exception as ex:
                log("   skd unreadable", sp, ex)
                continue
            st["meshes"] += 1
            for s in d["surfaces"]:
                if not surf_match(s["name"], u["surfaces"]):
                    continue
                V = s["verts"]; T = s["tris"]
                uv = lambda i: (V[i]["uv"][0] * W, V[i]["uv"][1] * H)
                for t in T:
                    cd.polygon([uv(i) for i in t], fill=255)
                st["tris"] += len(T)
                kmap, wid = {}, []
                for v in V:
                    wid.append(kmap.setdefault((v["bone"],) + tuple(round(c, 3) for c in v["pos"]), len(kmap)))
                P = np.array([v["pos"] for v in V], np.float64); N = np.array([v["n"] for v in V], np.float64)
                edges, fn = {}, []
                for ti, t in enumerate(T):
                    a, b, c = (P[i] for i in t)
                    n = np.cross(b - a, c - a); ln = np.linalg.norm(n)
                    n = n / ln if ln > 1e-9 else n
                    if np.dot(n, N[list(t)].sum(0)) < 0:
                        n = -n
                    fn.append(n)
                    for k in range(3):
                        i, j = t[k], t[(k + 1) % 3]
                        edges.setdefault(tuple(sorted((wid[i], wid[j]))), []).append((ti, i, j, t[(k + 2) % 3]))

                def nsplit(a, b):
                    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(N[a], N[b]) /
                                        max(np.linalg.norm(N[a]) * np.linalg.norm(N[b]), 1e-9))))))
                for e, lst in edges.items():
                    if len(lst) != 2:
                        continue
                    (t1, i1, j1, o1), (t2, i2, j2, o2) = lst
                    if V[i1]["bone"] != V[o2]["bone"]:
                        continue
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(fn[t1], fn[t2]))))))
                    if ang < 28:
                        continue
                    m_i = i2 if wid[i2] == wid[i1] else j2
                    m_j = j2 if wid[j2] == wid[j1] else i2
                    if max(nsplit(i1, m_i), nsplit(j1, m_j)) < 20 and ang < 55:
                        continue                         # smooth-shaded facets are not edges (bug-3376)
                    side = float(np.dot(fn[t1], P[o2] - P[i1]))
                    st["convex" if side < 0 else "concave"] += 1
                    wpx = max(2, int(round(W / 1024 * (1.0 + min(ang, 90) / 60))))
                    for (ti, i, j, o) in lst:
                        (vd if side < 0 else kd).line([uv(i), uv(j)], fill=255, width=wpx)
    cover = np.asarray(cover, np.float32) / 255
    if st["tris"] == 0:
        cover = np.ones((H, W), np.float32)      # no mesh resolved: treat the sheet as all-used, no edge wear
    return cover, np.asarray(convex, np.float32) / 255 * cover, np.asarray(concave, np.float32) / 255 * cover, st


def material_masks(src_rgb, fin, W, H):
    hsv = np.asarray(src_rgb.convert("HSV"), np.float32) / 255
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    brown = ((h < 0.13) | (h > 0.97)) & (s > 0.32) & (v > 0.10)
    brown = ndimage.binary_opening(brown, iterations=2)
    brown = ndimage.gaussian_filter(brown.astype(np.float32), 2.0)
    brown = np.asarray(Image.fromarray((brown * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    z = np.zeros((H, W), np.float32)
    wood, plastic = {"wood": (brown, z), "plastic": (z, brown), "none": (z, z)}[fin.get("brown", "wood")]
    # BRASS / bright yellow metal (FG42 parts, cartridges, sight blades): no steel grain, no bluing wear - it is
    # handled like plastic (left as painted). Steel grain on it read as sensor noise in QA.
    brass = (h > 0.08) & (h < 0.19) & (s > 0.26) & (v > 0.24)      # whd-3: desaturated cartridge brass (m1clip)
    brass = ndimage.gaussian_filter(ndimage.binary_opening(brass, iterations=2).astype(np.float32), 2.0)
    brass = np.asarray(Image.fromarray((brass * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    wood = wood * (1 - brass)
    plastic = np.clip(plastic + brass, 0, 1)
    return np.clip(1 - wood - plastic, 0, 1), wood, plastic


# ------------------------------------------------------------------------------------------ detail
def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def grain(rng, H, W, sigma):
    n = rng.standard_normal((H, W)).astype(np.float32)
    n = ndimage.gaussian_filter(n, sigma)
    return n / (n.std() + 1e-6)


def oriented_streaks(rng, L, H, W):
    gx = ndimage.sobel(L, 1); gy = ndimage.sobel(L, 0)
    jxx = ndimage.gaussian_filter(gx * gx, 6.0); jyy = ndimage.gaussian_filter(gy * gy, 6.0)
    jxy = ndimage.gaussian_filter(gx * gy, 6.0)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    base = rng.standard_normal((H, W)).astype(np.float32)
    out = np.zeros((H, W), np.float32); wsum = np.zeros((H, W), np.float32)
    for k in range(4):
        ang = k * np.pi / 4
        sm = ndimage.gaussian_filter(base, (0.6 + 9 * abs(math.sin(ang)), 0.6 + 9 * abs(math.cos(ang))))
        sm /= sm.std() + 1e-6
        w = np.cos(theta - ang) ** 8
        out += sm * w; wsum += w
    return out / (wsum + 1e-6)


def scratches(rng, W, H, mask, count, lmin, lmax, weight):
    bright = Image.new("L", (W, H), 0); dark = Image.new("L", (W, H), 0)
    db, dd = ImageDraw.Draw(bright), ImageDraw.Draw(dark)
    ys, xs = np.nonzero(mask > 0.5)
    if len(xs) == 0 or count <= 0:
        return np.zeros((H, W), np.float32), np.zeros((H, W), np.float32)
    pw = weight[ys, xs].astype(np.float64) + 1e-9
    for i in rng.choice(len(xs), size=count, p=pw / pw.sum()):
        x, y = float(xs[i]), float(ys[i])
        ang = rng.normal(0, 0.45) if rng.random() < 0.9 else rng.uniform(0, np.pi)
        L = rng.uniform(lmin, lmax) * (W / 4096)
        mx, my = x + math.cos(ang) * L / 2, y + math.sin(ang) * L / 2
        a2 = ang + rng.normal(0, 0.08)
        ex, ey = mx + math.cos(a2) * L / 2, my + math.sin(a2) * L / 2
        a = int(rng.uniform(90, 255))
        db.line([(x, y), (mx, my), (ex, ey)], fill=a, width=1)
        ox, oy = -math.sin(ang), math.cos(ang)
        dd.line([(x + ox, y + oy), (mx + ox, my + oy), (ex + ox, ey + oy)], fill=a // 2, width=1)
    return (np.asarray(bright.filter(ImageFilter.GaussianBlur(0.45)), np.float32) / 255 * mask,
            np.asarray(dark.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255 * mask)


def dents(rng, W, H, mask, count):
    m = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(m)
    ys, xs = np.nonzero(mask > 0.5)
    if len(xs) == 0 or count <= 0:
        return np.zeros((H, W), np.float32)
    for i in rng.integers(len(xs), size=count):
        x, y = float(xs[i]), float(ys[i])
        r = rng.uniform(2, 9) * W / 4096; e = rng.uniform(0.4, 1.0)
        dr.ellipse([x - r, y - r * e, x + r, y + r * e], fill=int(rng.uniform(120, 255)))
    return np.asarray(m.filter(ImageFilter.GaussianBlur(1.2 * W / 4096)), np.float32) / 255 * mask


STEEL = {   # micro grain (mult), additive matte floor, edge-wear strength, bare-metal colour
    "blued":      dict(g=(0.028, 0.6, 0.012, 3.0), floor=1.8, amt=0.55, bare=(150, 150, 148), tint=(0.99, 0.995, 1.01)),
    # parkerized was 0.085 / sigma 1.0 / floor 5 in the pilot: at 8x (512 -> 4096 sources) that read as digital sensor
    # noise in ADS (FG42 QA card); a coarser, weaker grain still reads as matte phosphate
    "parkerized": dict(g=(0.050, 1.4, 0.025, 3.0), floor=3.0, amt=0.38, bare=(128, 128, 124), tint=(0.985, 1.0, 0.985)),
    "painted":    dict(g=(0.030, 1.6, 0.020, 4.0), floor=2.0, amt=0.50, bare=(138, 136, 130), tint=(1.0, 1.0, 1.0)),
}


# ------------------------------------------------------------------------------------------ build one
def build(job, variant=0, preview=False):
    stem = job["stem"]
    W, H = job["target"]
    fin = finish_for(stem)
    seed = int(hashlib.md5(stem.encode()).hexdigest()[:8], 16) + 7919 * variant
    rng = np.random.default_rng(seed)
    src_im = load_source(job)
    src = erase(src_im.convert("RGB"), stem)
    alpha = None
    if job["alpha"]:
        alpha = np.asarray(src_im.convert("RGBA").resize((W, H), Image.LANCZOS), np.float32)[..., 3]
    e = esrgan(stem, src)
    base = np.asarray(e.resize((W, H), Image.LANCZOS), np.float32)
    lz = np.asarray(src.resize((W, H), Image.LANCZOS), np.float32)
    # finishes.json "esr": per-sheet ESRGAN weight (default 1). Sheets whose art ESRGAN exaggerates (30cal: the painted
    # chip "drips" became worm-like blobs, QA round 2) get a Lanczos+unsharp share instead.
    ew = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8")).get("esr", {}).get(stem, 1.0)
    if ew < 1.0:
        lzu = np.asarray(Image.fromarray(lz.astype(np.uint8)).filter(ImageFilter.UnsharpMask(1.5 * W / 4096 + 0.5, 60, 2)), np.float32)
        base = base * ew + lzu * (1 - ew)
    S = W / 4096.0
    dmap = ndimage.gaussian_filter(np.abs(luma(base) - luma(lz)), 3.0 * S)
    gw = ndimage.gaussian_filter(np.clip((dmap - 10.0) / 10.0, 0, 1), 4.0 * S)[..., None]
    lzs = np.asarray(Image.fromarray(lz.astype(np.uint8)).filter(ImageFilter.UnsharpMask(max(1.0, 2.0 * S), 80, 2)), np.float32)
    base = base * (1 - gw) + lzs * gw
    guard = float((gw > 0.5).mean())
    sg = 16.0 * S
    gain = np.stack([ndimage.gaussian_filter(lz[..., c], sg) / np.maximum(ndimage.gaussian_filter(base[..., c], sg), 1.0)
                     for c in range(3)], -1)
    base = base * np.clip(gain, 0.8, 1.25)
    cover, convex, concave, st = mesh_masks(job, W, H)
    steel, wood, plastic = material_masks(src, fin, W, H)
    L = luma(base)
    out = base.copy()
    cfgj = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8"))
    k = float(cfgj.get("wear", {}).get(stem, 1.0))           # per-sheet wear strength (0 = upscale + material only)
    tame = float(cfgj.get("tame", {}).get(stem, 0.0))
    if tame > 0:
        # TAME painted bright streaks/blotches on dark metal (30cal: white drippy paint-chip art that read as upscaler
        # hallucination, coordinator QA): positive local contrast above 10 levels is compressed by `tame`.
        lb = ndimage.gaussian_filter(base, (6.0 * S, 6.0 * S, 0))
        hp = base - lb
        lum_hp = luma(hp)[..., None]
        over = np.clip(lum_hp - 10.0, 0, None)
        scale = np.where(lum_hp > 10.0, (10.0 + over * (1 - tame)) / np.maximum(lum_hp, 1e-3), 1.0)
        base = lb + hp * scale
        L = luma(base)
        out = base.copy()
    P = STEEL[fin["steel"]]
    sm = (steel * cover)[..., None] * (1 - gw)
    bp = ndimage.gaussian_filter(lz, (0.6 * S, 0.6 * S, 0)) - ndimage.gaussian_filter(lz, (4.0 * S, 4.0 * S, 0))
    out += bp * 0.55 * sm
    g = P["g"][0] * grain(rng, H, W, P["g"][1] * S) + P["g"][2] * grain(rng, H, W, P["g"][3] * S)
    # grain FADES on bright painted highlights: a matte phosphate grain over the artist's specular streak read as
    # digital sensor noise (QA round 1, s93_colt magazine); the dark finish keeps the full grain
    fade = np.clip(1.0 - 0.9 * (L / 255.0) ** 0.7, 0.15, 1.0)     # whd-3: stronger (s93_colt / colt45s2 highlights)
    out *= (1 + g * steel * cover * fade)[..., None]
    out += (grain(rng, H, W, 0.9 * S) * P["floor"] * steel * cover * fade)[..., None]
    tint = np.array(P["tint"], np.float32)
    out = out * (1 - steel[..., None] * cover[..., None] * 0.35) + out * tint * steel[..., None] * cover[..., None] * 0.35
    if wood.max() > 0:
        out *= (1 + 0.07 * oriented_streaks(rng, L, H, W) * wood * cover)[..., None]
    # wear
    chip = grain(rng, H, W, 2.5 * S); chip2 = grain(rng, H, W, 1.6 * S)
    edge = ndimage.gaussian_filter(convex, 2.0 * S)
    patches = np.clip((grain(rng, H, W, 12.0 * S) - 0.35) * 1.4, 0, 1)
    edge = np.clip(edge * 1.8 - 0.15 + 0.3 * chip2 + 0.25 * chip, 0, 1) * patches * np.clip(edge * 6.0, 0, 1)
    ridge = ndimage.gaussian_filter(np.clip((L - ndimage.gaussian_filter(L, 5.0 * S)) / 18.0, 0, 1), 1.5 * S)
    edge = edge * (0.15 + 0.85 * np.clip(ridge * 1.5, 0, 1))
    bare = np.array(P["bare"], np.float32)
    se = edge * steel * P["amt"] * k * (1 - np.clip(ndimage.gaussian_filter(plastic, 4.0 * S) * 3, 0, 1))
    out = out * (1 - se[..., None]) + (bare * (0.6 + 0.4 * L[..., None] / 255)) * se[..., None]
    we = edge * wood * 0.30 * k
    out = out * (1 - we[..., None]) + np.clip(out * 1.45 + 8, 0, 255) * we[..., None]
    sw = 0.12 + 0.6 * np.clip(ndimage.gaussian_filter(convex, 10.0 * S) * 4, 0, 1)
    area = W * H / 4096 ** 2 * 2
    sb, sd = scratches(rng, W, H, steel * cover, int(110 * k * area), 8, 55, sw)
    out += (sb * 20 * k)[..., None] - (sd * 7 * k)[..., None]
    wb, _ = scratches(rng, W, H, wood * cover, int(120 * k * area), 5, 35, sw)
    out += (wb * 16 * k)[..., None] * np.array([1.0, 0.85, 0.65], np.float32)
    out *= (1 - 0.22 * dents(rng, W, H, wood * cover, int(90 * k * area)) * k)[..., None]
    gm = np.clip(ndimage.gaussian_filter(concave, 4.0 * S) * 1.8, 0, 1) * (0.7 + 0.3 * np.clip(chip * 0.5 + 0.5, 0, 1))
    valley = np.clip((ndimage.gaussian_filter(L, 5.0 * S) - L) / 18.0, 0, 1)
    gm = gm * (0.25 + 0.75 * np.clip(ndimage.gaussian_filter(valley, 2.0 * S) * 1.5, 0, 1))
    grime = np.array([0.62, 0.58, 0.52], np.float32)
    out = out * (1 - 0.45 * gm[..., None] * k) + out * grime * 0.45 * gm[..., None] * k
    # finishes.json "keep": rects that get the upscale ONLY - no material grain, wear or grime (art the pass harms:
    # m1clip's cartridge brass smeared under the steel recipe, QA round 2)
    keep = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8")).get("keep", {}).get(stem, [])
    if keep:
        km = Image.new("L", (W, H), 0); kd = ImageDraw.Draw(km)
        for (u0, v0, u1, v1) in keep:
            kd.rectangle([u0 * W, v0 * H, u1 * W, v1 * H], fill=255)
        km = np.asarray(km.filter(ImageFilter.GaussianBlur(2.0 * S)), np.float32)[..., None] / 255
        out = out * (1 - km) + base * km
    prot = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8")).get("protect", {}).get(stem, [])
    if prot:                        # single-texel UV sample points (added mesh parts): keep the original art there
        pm = Image.new("L", (W, H), 0); pd = ImageDraw.Draw(pm)
        r = 0.006 * W
        for (u, v) in prot:
            pd.ellipse([u * W - r, v * H - r, u * W + r, v * H + r], fill=255)
        pm = np.asarray(pm.filter(ImageFilter.GaussianBlur(r / 3)), np.float32)[..., None] / 255
        out = out * (1 - pm) + base * pm
    out = np.clip(out, 0, 255)

    # ---- gates
    rep = dict(stem=stem, cls=job["cls"], target=[W, H], finish=fin, mesh=st, guard=round(guard, 4),
               source=job["source"]["pak"] + ":" + job["source"]["name"], variant=variant, version=VERSION)
    if not np.isfinite(out).all():
        raise ValueError("NaN in output")
    ls, lo = luma(lz), luma(out)
    small = lambda a: np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((256, max(1, 256 * H // W)), Image.BOX), np.float32)
    corr = float(np.corrcoef(small(ls).ravel(), small(lo).ravel())[0, 1]) if ls.std() > 1 else 1.0
    shift = float((lo.mean() - ls.mean()) / max(ls.mean(), 4.0))
    def specks(a):          # isolated bright dots (1-3 px) per million texels
        hp = a - ndimage.gaussian_filter(a, 2.0)
        m = hp > 24
        return float((m & (ndimage.gaussian_filter(m.astype(np.float32), 3.0) < 0.08)).mean() * 1e6)
    # ADDED speckle only: the source's own dots (JPEG noise, painted pitting) come back through the detail restore
    speck = specks(lo) - specks(luma(lzs))
    rep.update(corr=round(corr, 4), shift=round(shift, 4), speckle_ppm=round(speck, 1))
    fails = []
    if corr < 0.90 and ls.std() >= 6.0:   # a near-black featureless sheet has no structure to correlate (welrod)
        fails.append("corr %.3f < 0.90" % corr)
    # SAME ART AS TODAY: the source picker once chose a different 64 px shell from a lower-priority pak (QA, Webley
    # shell). Correlate with what the engine loads TODAY too - an earlier upscale of the same art stays far above this.
    try:
        tday = Image.open(io.BytesIO(vfs.read(job["loads"]))).convert("L").resize((256, max(1, 256 * H // W)), Image.BOX)
        ct = float(np.corrcoef(np.asarray(tday, np.float32).ravel(), small(lo).ravel())[0, 1])
    except Exception:
        ct = None
    rep["corr_today"] = None if ct is None else round(ct, 4)
    if ct is not None and ct < 0.80: fails.append("corr_today %.3f < 0.80 (different art from what loads today?)" % ct)
    if abs(lo.mean() - ls.mean()) > max(0.06 * ls.mean(), 2.0):      # near-black sheets: 2 levels absolute
        fails.append("brightness %+.1f%% (%.1f levels)" % (shift * 100, lo.mean() - ls.mean()))
    if speck > 600: fails.append("speckle %.0f ppm > 600" % speck)
    # REVIEWED OVERRIDES: a gate failure a human crop review judged a false positive (accepted.json: stem -> {gate,
    # reason}). Only the named gate is waived, and only for that stem; every other gate still applies.
    acc = json.load(open(os.path.join(HERE, "accepted.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "accepted.json")) else {}
    if stem in acc:
        fails = [f for f in fails if not f.startswith(acc[stem]["gate"])]
        rep["accepted"] = acc[stem]
    rep["fails"] = fails
    tag = "" if variant == 0 else "_w%d" % variant
    png = os.path.join(BUILD, "png", safe(stem) + tag + ".png")
    os.makedirs(os.path.dirname(png), exist_ok=True)
    Image.fromarray(out.astype(np.uint8)).save(png)
    qa_card(job, out, lz, edge * steel, gw[..., 0], tag)
    if fails or preview:
        return rep
    rgba = out if alpha is None else np.dstack([out, alpha])
    dds = encode_mipped(rgba)
    dec = V2.dds_decode_level(dds, V2.dds_parse(dds), 0)[..., :3].astype(np.float32)
    lean = dec.reshape(-1, 3).mean(0) - out.reshape(-1, 3).mean(0)
    rep["lean"] = [round(float(x), 2) for x in lean]
    if np.abs(lean).max() >= 1.5:          # single-pass bands summed to a lean: redo every band with the mean-hold encoder
        dds = encode_mipped(rgba, strict=True)
        dec = V2.dds_decode_level(dds, V2.dds_parse(dds), 0)[..., :3].astype(np.float32)
        lean = dec.reshape(-1, 3).mean(0) - out.reshape(-1, 3).mean(0)
        rep["lean"] = [round(float(x), 2) for x in lean]; rep["strict_encode"] = True
    if np.abs(lean).max() >= 1.5 and alpha is None:     # last resort on flat sheets: Pillow's BC1 per level
        hdr, _ = V2.encode_level(np.zeros((4, 4, 3), np.uint8), "DXT1")
        o2, cur = bytearray(dds[:128]), out.astype(np.float64)
        for k2 in range(V2.full_mips(W, H)):
            if k2:
                cur = V2.box_half(cur)
            o2 += V2.encode_level(np.round(np.clip(cur, 0, 255)).astype(np.uint8), "DXT1")[1]
        dec2 = V2.dds_decode_level(bytes(o2), V2.dds_parse(bytes(o2)), 0)[..., :3].astype(np.float32)
        lean2 = dec2.reshape(-1, 3).mean(0) - out.reshape(-1, 3).mean(0)
        if np.abs(lean2).max() < np.abs(lean).max():
            dds, lean = bytes(o2), lean2
            rep["lean"] = [round(float(x), 2) for x in lean]; rep["pillow_encode"] = True
    if np.abs(lean).max() >= 1.5:
        rep["fails"].append("DDS lean %s" % rep["lean"])
        return rep
    rel = stem + tag + ".dds"
    p = os.path.join(BUILD, "stage", ("cls%d" % job["cls"]) if variant == 0 else "wear", *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(dds)
    rep.update(dds=rel, bytes=len(dds), md5=hashlib.md5(dds).hexdigest(), fmt="DXT5" if alpha is not None else "DXT1")
    return rep


def bc1(img):
    """Single-pass deterministic BC1 (V3.bc1_encode); the mean-holding bisect (V4.bc1_encode_dc, bug-2953) only when
    this band's decoded mean leans more than 0.6 levels. Measured on gun art: single pass leans ~0.2 levels and is 7x
    faster than the bisect, which was built for flat saturated terrain where the lean reached 1.8."""
    blk = V3.bc1_encode(img)
    lean = (V4.bc1_exact_decode(blk, img.shape[0], img.shape[1]) - img).reshape(-1, 3).mean(0)
    if float(np.abs(lean).max()) <= 0.6:
        return blk
    return V4.bc1_encode_dc(img)


def encode_mipped(level0, strict=False):
    H, W = level0.shape[:2]
    has_a = level0.shape[2] == 4
    fmt = "DXT5" if has_a else "DXT1"
    hdr, _ = V2.encode_level(np.zeros((4, 4, 4 if has_a else 3), np.uint8), fmt)
    hdr = bytearray(hdr)
    n = V2.full_mips(W, H)
    bpb = 16 if has_a else 8
    struct.pack_into("<II", hdr, 12, H, W)
    struct.pack_into("<I", hdr, 8, struct.unpack_from("<I", hdr, 8)[0] | V2.DDSD_MIPMAPCOUNT | V2.DDSD_LINEARSIZE)
    struct.pack_into("<I", hdr, 20, max(1, (W + 3) // 4) * max(1, (H + 3) // 4) * bpb)
    struct.pack_into("<I", hdr, 28, n)
    struct.pack_into("<I", hdr, 108, struct.unpack_from("<I", hdr, 108)[0] | V2.DDSCAPS_COMPLEX | V2.DDSCAPS_MIPMAP)
    out, cur = bytearray(hdr), level0.astype(np.float64)
    for k in range(n):
        if k:
            cur = V2.box_half(cur)
        h = cur.shape[0]
        band = 256 if h >= 256 else h
        for y in range(0, h, band):
            part = np.clip(cur[y:y + band], 0, 255)
            colour = np.frombuffer((V4.bc1_encode_dc if strict else bc1)(part[..., :3]), np.uint8).reshape(-1, 8)
            if has_a:
                _, ab = V2.encode_level(np.round(part).astype(np.uint8), "DXT5")
                ab = np.frombuffer(ab, np.uint8).reshape(-1, 16)[:, :8]
                assert ab.shape[0] == colour.shape[0]
                out += np.concatenate([ab, colour], axis=1).tobytes()
            else:
                out += colour.tobytes()
    info = V2.dds_parse(bytes(out))
    assert info["end"] == len(out) and info["levels"][-1][:2] == (1, 1)
    return bytes(out)


# ------------------------------------------------------------------------------------------ QA card
def qa_card(job, out, lz, wear, guard, tag):
    """overview today|new + three 1:1 crops (most wear, most ESRGAN fallback, most fine contrast = markings)."""
    H, W = out.shape[:2]
    today = vfs.read(job["loads"])
    try:
        t = Image.open(io.BytesIO(today)).convert("RGB")
    except Exception:
        t = Image.fromarray(lz.astype(np.uint8))
    new = Image.fromarray(out.astype(np.uint8))
    ov = 640
    oh = max(64, ov * H // W)
    card = Image.new("RGB", (ov * 2 + 10 + 3 * 330, max(oh, 660)), (255, 255, 255))
    card.paste(t.resize((ov, oh), Image.LANCZOS), (0, 0)); card.paste(new.resize((ov, oh), Image.LANCZOS), (ov + 10, 0))
    c = 320
    told = t.resize((W, H), Image.BICUBIC)
    fine = np.abs(luma(out) - ndimage.gaussian_filter(luma(out), 1.5))
    picks = []
    for m in (wear, guard, fine):
        sm = ndimage.uniform_filter(m, c // 2)
        for y0, x0 in picks:
            sm[max(0, y0 - c):y0 + c, max(0, x0 - c):x0 + c] = -1
        y, x = np.unravel_index(int(np.argmax(sm)), sm.shape)
        picks.append((int(min(max(0, y - c // 2), H - c)), int(min(max(0, x - c // 2), W - c))))
    for i, (y, x) in enumerate(picks):
        bx = (x, y, x + c, y + c)
        card.paste(told.crop(bx), (2 * ov + 10 + i * 330, 0)); card.paste(new.crop(bx), (2 * ov + 10 + i * 330, 330))
    d = ImageDraw.Draw(card)
    d.text((4, 4), job["stem"] + tag, fill=(255, 255, 0))
    p = os.path.join(BUILD, "qa", "cls%d" % job["cls"], safe(job["stem"]) + tag + ".jpg")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    card.save(p, quality=86)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cls", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--variant", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--mains", action="store_true", help="select the per-gun MAIN sheets (any class) - wear variants")
    a = ap.parse_args()
    os.makedirs(BUILD, exist_ok=True)
    alljobs = json.load(open(os.path.join(HERE, "jobs.json")))
    if a.mains:
        import gen_wear_tiks
        ms = set(gen_wear_tiks.mains(require_built=False).values())
        jobs = [j for j in alljobs if j["stem"] in ms and a.only in j["stem"]]
    else:
        jobs = [j for j in alljobs if j["cls"] == a.cls and a.only in j["stem"]]
    rp = os.path.join(BUILD, "report_%s%s.json" % ("mains" if a.mains else "cls%d" % a.cls, "" if a.variant == 0 else "_w%d" % a.variant))
    reports = json.load(open(rp)) if os.path.exists(rp) else {}
    log("cls %d: %d jobs (variant %d, preview %s)" % (a.cls, len(jobs), a.variant, a.preview))
    fin_cfg = json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8"))
    for n, job in enumerate(jobs):
        if job["stem"] in fin_cfg.get("skip", {}):
            reports[job["stem"]] = dict(stem=job["stem"], skipped="finishes.json skip: " + fin_cfg["skip"][job["stem"]])
            continue
        if max(job["target"]) < max(job["win"]):
            reports[job["stem"]] = dict(stem=job["stem"], skipped="target %s below what loads today %s - keep today's" %
                                        (job["target"], job["win"]))
            continue
        r = reports.get(job["stem"])
        if r and r.get("version") == VERSION and r.get("md5") and not a.force and not a.preview:
            continue
        t0 = time.time()
        try:
            r = build(job, a.variant, a.preview)
        except Exception as ex:
            import traceback
            r = dict(stem=job["stem"], fails=["exception %r" % ex], tb=traceback.format_exc()[-600:])
        r["secs"] = round(time.time() - t0)
        reports[job["stem"]] = r
        log("[%d/%d] %s %s corr=%s shift=%s speck=%s guard=%s %s %ss" % (
            n + 1, len(jobs), job["stem"], "x".join(map(str, job["target"])), r.get("corr"), r.get("shift"),
            r.get("speckle_ppm"), r.get("guard"), ("FAIL " + "; ".join(r["fails"])) if r.get("fails") else "ok", r["secs"]))
        json.dump(reports, open(rp, "w"), indent=1)


if __name__ == "__main__":
    main()
