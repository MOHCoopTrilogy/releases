"""Weapon HD pass: upscale + authored-looking wear, baked into the diffuse, for one gun at a time.

    python weaponhd.py kar98 thompsonsmg colt45      # build the pilot guns into ../stage + previews
    python weaponhd.py --variant 1 kar98             # an alternative wear roll (seed + 1) - for Tier B

Pipeline per sheet (every number below is tunable per gun in GUNS):
  1. SOURCE = the best lossless art on disk: HRRTM's 1536 TGA when it exists, else the winning image.
     Never the shipped DXT5 (it is that same 1536 art resampled to 2048 and block-compressed).
  2. Real-ESRGAN x4plus (the project's tool, cached) -> Lanczos down to the target size. ESRGAN
     removes the source's JPEG crosshatch and sharpens edges/markings, but flattens metal into
     plastic - so step 4 puts material back.
  3. MASKS from the real mesh (skd.py): UV coverage, CONVEX edges (dihedral angle, outward-tested in
     bone space) for edge wear, CONCAVE edges for grime. Material (steel / wood / plastic) from the
     source colour, with per-gun rect overrides. Nothing is placed outside a UV island.
  4. MATERIAL MICRO-DETAIL: blued steel = fine polish grain; parkerized = coarser phosphate speckle;
     wood = pores streaked along the local grain direction (structure tensor); bakelite = none.
  5. WEAR (seeded per gun, so every gun differs and a re-run is identical): chipped edge wear to bare
     steel, contact/handling zones (rects), holster wear on pistols, fine scratches biased along the
     part, wood dents and edge rub, oil/grime in concave corners.
  6. NO TEXT IS ADDED. Existing real markings (HRRTM's Colt patent dates, Auto-Ordnance) are kept.
  7. DDS DXT1 (no alpha in any pilot sheet - measured), full box mip chain, encoded with the
     project's deterministic BC1 encoder with mean-hold (gen_terrain_pak_v4.bc1_encode_dc, bug-2953),
     per 256-row band.
QA gates (fail loudly): luma correlation vs source >= 0.90, mean luma shift within 6%, no NaN, decoded
DDS mean within 1.5 levels of level 0.
"""
import os, sys, io, json, math, struct, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
import vfs, skd
import gen_terrain_pak_v2 as V2
import gen_terrain_pak_v4 as V4

ESR = r"C:/mohaa-coop-dev/_tools/realesrgan/realesrgan-ncnn-vulkan.exe"
WORK = os.path.expandvars(r"%TEMP%\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\weaponhd")
STAGE = os.path.join(HERE, "..", os.environ.get("WHD_STAGE", "stage"))     # WHD_STAGE=stage_heavy for the heavy-wear option
PREV = os.path.join(HERE, "..", "previews")

# rects are in normalised UV (u0, v0, u1, v1) - same space as the skd texcoords
GUNS = {
    "kar98": dict(
        sheet="textures/models/weapons/kar98/kar98", skd="models/weapons/kar98/kar98.skd",
        surfaces=["KAR981", "KAR982"], size=(4096, 2048), seed=9811,
        steel="blued", wood="walnut",
        # bolt handle / receiver top and the wrist of the stock are what a hand works
        contact=[(0.20, 0.10, 0.36, 0.42, "wood", 0.55), (0.33, 0.37, 0.62, 0.62, "steel", 0.45)],
        holster=[], wear=1.0),
    "thompsonsmg": dict(
        sheet="textures/models/weapons/thompsonsmg/thompsonsmg", skd="models/weapons/thompsonsmg/thompsonsmg.skd",
        surfaces=["ThompsonSMG1", "ThompsonSMG2", "Clip"], size=(4096, 4096), seed=1928,
        steel="parkerized", wood="walnut",
        contact=[(0.50, 0.08, 0.68, 0.30, "wood", 0.6), (0.00, 0.08, 0.30, 0.34, "wood", 0.5)],
        holster=[], wear=1.0),
    "colt45": dict(
        sheet="textures/models/weapons/colt45/colt45", skd="models/weapons/colt45/colt45.skd",
        surfaces=["colt45", "clip"], size=(4096, 4096), seed=1911,
        steel="parkerized", wood=None, brown="plastic",   # M1911A1 grips are brown plastic, not wood
        contact=[(0.48, 0.06, 0.80, 0.60, "plastic", 0.5)],
        holster=[(0.62, 0.80, 0.98, 0.94, 0.8), (0.00, 0.03, 0.30, 0.13, 0.6)],   # slide flats, muzzle end
        wear=1.0),
}


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------------------------------ source
def source_image(cfg):
    stem = cfg["sheet"].lower()
    hr = vfs.index().get(stem + ".tga", [])
    hr = [x for x in hr if "HRRTM_Pak4c" in x[0]]
    if hr:
        p, n = hr[-1]
        b = vfs._zips[p].read(n); tag = "HRRTM_Pak4c tga"
    else:
        vp, w = vfs.resolve_image(stem)
        b = vfs._zips[w[0]].read(w[1]); tag = os.path.basename(w[0]) + " " + vp
    im = Image.open(io.BytesIO(b)).convert("RGB")
    return im, tag


def esrgan(name, im):
    d = os.path.join(WORK, "esr"); os.makedirs(d, exist_ok=True)
    src = os.path.join(d, name + "_in.png"); out = os.path.join(d, name + "_x4.png")
    if not os.path.exists(out):
        im.save(src)
        subprocess.run([ESR, "-i", src, "-o", out, "-s", "4", "-n", "realesrgan-x4plus", "-t", "256", "-j", "1:1:1"],
                       check=True, capture_output=True)
    e = Image.open(out).convert("RGB")
    a = np.asarray(e, np.float32)
    assert a.mean() > 2.0, "ESRGAN produced a black image (bug-247)"
    return e


# ------------------------------------------------------------------------------------------ masks
def mesh_masks(cfg, W, H):
    d = skd.read(vfs.read(cfg["skd"]))
    cover = Image.new("L", (W, H), 0); cd = ImageDraw.Draw(cover)
    convex = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(convex)
    concave = Image.new("L", (W, H), 0); kd = ImageDraw.Draw(concave)
    stats = dict(tris=0, convex_edges=0, concave_edges=0)
    for s in d["surfaces"]:
        if s["name"] not in cfg["surfaces"]:
            continue
        V = s["verts"]; T = s["tris"]
        uv = lambda i: (V[i]["uv"][0] * W, V[i]["uv"][1] * H)
        for t in T:
            cd.polygon([uv(i) for i in t], fill=255)
        stats["tris"] += len(T)
        # weld by (bone, position) so UV-split vertices share an id
        key = {}
        wid = []
        for v in V:
            k = (v["bone"],) + tuple(round(c, 3) for c in v["pos"])
            wid.append(key.setdefault(k, len(key)))
        P = np.array([v["pos"] for v in V], np.float64)
        N = np.array([v["n"] for v in V], np.float64)
        edges = {}
        fn = []
        for ti, t in enumerate(T):
            a, b, c = (P[i] for i in t)
            n = np.cross(b - a, c - a); ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-9 else n
            if np.dot(n, N[list(t)].sum(0)) < 0:        # orient by the authored vertex normals
                n = -n
            fn.append(n)
            for k in range(3):
                i, j = t[k], t[(k + 1) % 3]
                e = tuple(sorted((wid[i], wid[j])))
                edges.setdefault(e, []).append((ti, i, j, t[(k + 2) % 3]))
        for e, lst in edges.items():
            if len(lst) != 2:
                continue
            (t1, i1, j1, o1), (t2, i2, j2, o2) = lst
            if V[i1]["bone"] != V[o2]["bone"]:
                continue
            n1, n2 = fn[t1], fn[t2]
            ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(n1, n2))))))
            if ang < 28:
                continue
            # SMOOTH-SHADED facets are not edges: a low-poly barrel's 8 facets meet at 45 deg but the artist
            # gave them shared normals, and wearing every facet line drew evenly spaced dashes down the Thompson
            # barrel (caught in QA). A real edge is where the authored normals SPLIT.
            def nsplit(a, b):
                return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(N[a], N[b]) /
                                    max(np.linalg.norm(N[a]) * np.linalg.norm(N[b]), 1e-9))))))
            m_i = i2 if wid[i2] == wid[i1] else j2
            m_j = j2 if wid[j2] == wid[j1] else i2
            # ...but 2002 meshes are often smoothed EVERYWHERE (the Thompson has no split normal at all), so a
            # sharp enough fold counts on its own: box corners are ~90 deg, an 8-sided barrel's facets 45.
            if max(nsplit(i1, m_i), nsplit(j1, m_j)) < 20 and ang < 55:
                continue
            side = float(np.dot(n1, P[o2] - P[i1]))
            draw = vd if side < 0 else kd
            stats["convex_edges" if side < 0 else "concave_edges"] += 1
            wpx = max(2, int(round(W / 1024 * (1.0 + min(ang, 90) / 60))))
            for (ti, i, j, o) in lst:
                draw.line([uv(i), uv(j)], fill=255, width=wpx)
    cover = np.asarray(cover, np.float32) / 255
    convex = np.asarray(convex, np.float32) / 255 * cover
    concave = np.asarray(concave, np.float32) / 255 * cover
    return cover, convex, concave, stats


def rect_mask(W, H, rects, feather):
    m = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(m)
    for r in rects:
        dr.rectangle([r[0] * W, r[1] * H, r[2] * W, r[3] * H], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather))
    return np.asarray(m, np.float32) / 255


def zone_mask(W, H, r, rng):
    """A handling/holster zone: a soft ELLIPSE inside the rect with a noise-warped boundary. A feathered rectangle
    left straight edges across UV islands that read as a pasted patch (caught in QA on the Kar98 receiver)."""
    cx, cy = (r[0] + r[2]) / 2 * W, (r[1] + r[3]) / 2 * H
    rx, ry = max(1.0, (r[2] - r[0]) / 2 * W), max(1.0, (r[3] - r[1]) / 2 * H)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    warp = grain(rng, H, W, 40.0 * W / 4096) * 0.18
    return np.clip((1.0 - (d + warp)) / 0.45, 0, 1) ** 1.5


def material_masks(src_small, cfg, W, H):
    """steel / wood / plastic weights at target size, from the 1536 source colour (smooth, not per-pixel)."""
    hsv = np.asarray(src_small.convert("HSV"), np.float32) / 255
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    wood = ((h < 0.13) | (h > 0.97)) & (s > 0.32) & (v > 0.10)
    wood = ndimage.binary_opening(wood, iterations=2)
    wood = ndimage.gaussian_filter(wood.astype(np.float32), 2.0)
    wood = np.asarray(Image.fromarray((wood * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    plastic = np.zeros((H, W), np.float32)
    if cfg.get("brown") == "plastic":
        plastic, wood = wood, wood * 0
    steel = np.clip(1 - wood - plastic, 0, 1)
    return steel, wood, plastic


# ------------------------------------------------------------------------------------------ detail
def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def grain(rng, H, W, sigma):
    n = rng.standard_normal((H, W)).astype(np.float32)
    n = ndimage.gaussian_filter(n, sigma)
    return n / (n.std() + 1e-6)


def oriented_streaks(rng, L, H, W):
    """wood pores: noise smeared along the local grain direction (structure tensor of the art)."""
    gx = ndimage.sobel(L, 1); gy = ndimage.sobel(L, 0)
    s = 6.0
    jxx = ndimage.gaussian_filter(gx * gx, s); jyy = ndimage.gaussian_filter(gy * gy, s); jxy = ndimage.gaussian_filter(gx * gy, s)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2          # along the grain, not across it
    base = rng.standard_normal((H, W)).astype(np.float32)
    out = np.zeros((H, W), np.float32); wsum = np.zeros((H, W), np.float32)
    for k in range(4):
        ang = k * np.pi / 4
        sm = ndimage.gaussian_filter(base, (0.6 + 9 * abs(math.sin(ang)), 0.6 + 9 * abs(math.cos(ang))))
        sm /= sm.std() + 1e-6
        w = np.cos(theta - ang) ** 8
        out += sm * w; wsum += w
    return out / (wsum + 1e-6)


def scratches(rng, W, H, mask, count, lmin, lmax, axis_bias, weight=None):
    """1 px bright cores with a darker shoulder; directions biased along `axis_bias` radians. With `weight`, start
    points are drawn in proportion to it (contact zones and edges) - an even scatter read as procedural rain
    in review."""
    bright = Image.new("L", (W, H), 0); dark = Image.new("L", (W, H), 0)
    db, dd = ImageDraw.Draw(bright), ImageDraw.Draw(dark)
    ys, xs = np.nonzero(mask > 0.5)
    if len(xs) == 0:
        return np.zeros((H, W), np.float32), np.zeros((H, W), np.float32)
    pw = None
    if weight is not None:
        pw = weight[ys, xs].astype(np.float64) + 1e-9
        pw /= pw.sum()
    picks = rng.choice(len(xs), size=count, p=pw)
    for i in picks:
        x, y = float(xs[i]), float(ys[i])
        ang = axis_bias + rng.normal(0, 0.45) if rng.random() < 0.9 else rng.uniform(0, np.pi)
        L = rng.uniform(lmin, lmax) * (W / 4096)
        # slightly curved: two segments
        mx, my = x + math.cos(ang) * L / 2, y + math.sin(ang) * L / 2
        ang2 = ang + rng.normal(0, 0.08)
        ex, ey = mx + math.cos(ang2) * L / 2, my + math.sin(ang2) * L / 2
        a = int(rng.uniform(90, 255))
        db.line([(x, y), (mx, my), (ex, ey)], fill=a, width=1)
        ox, oy = -math.sin(ang), math.cos(ang)
        dd.line([(x + ox, y + oy), (mx + ox, my + oy), (ex + ox, ey + oy)], fill=a // 2, width=1)
    b = np.asarray(bright.filter(ImageFilter.GaussianBlur(0.45)), np.float32) / 255
    d = np.asarray(dark.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    return b * mask, d * mask


def dents(rng, W, H, mask, count):
    m = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(m)
    ys, xs = np.nonzero(mask > 0.5)
    if len(xs) == 0:
        return np.zeros((H, W), np.float32)
    for _ in range(count):
        i = rng.integers(len(xs)); x, y = float(xs[i]), float(ys[i])
        r = rng.uniform(2, 9) * W / 4096; e = rng.uniform(0.4, 1.0)
        dr.ellipse([x - r, y - r * e, x + r, y + r * e], fill=int(rng.uniform(120, 255)))
    return np.asarray(m.filter(ImageFilter.GaussianBlur(1.2 * W / 4096)), np.float32) / 255 * mask


def build(name, variant=0):
    cfg = GUNS[name]
    W, H = cfg["size"]
    rng = np.random.default_rng(cfg["seed"] + 7919 * variant)
    t0 = time.time()
    src, tag = source_image(cfg)
    log(name, "source", tag, src.size)
    e = esrgan(name, src)
    base = np.asarray(e.resize((W, H), Image.LANCZOS), np.float32)
    lz = np.asarray(src.resize((W, H), Image.LANCZOS), np.float32)
    # HALLUCINATION GUARD: where ESRGAN's picture departs from the source's own (Lanczos) picture by more
    # than a soft threshold, fall back to a sharpened Lanczos. Caught on the Colt rear-sight serrations,
    # which ESRGAN turned into crackle (same family as bug-1129's worm noise).
    dmap = ndimage.gaussian_filter(np.abs(luma(base) - luma(lz)), 3.0 * W / 4096)
    gw = np.clip((dmap - 10.0) / 10.0, 0, 1)
    gw = ndimage.gaussian_filter(gw, 4.0 * W / 4096)[..., None]
    lzs = np.asarray(Image.fromarray(lz.astype(np.uint8)).filter(ImageFilter.UnsharpMask(2.0 * W / 4096, 80, 2)), np.float32)
    base = base * (1 - gw) + lzs * gw
    log("  guard: %.2f%% of texels fell back to Lanczos" % (float((gw > 0.5).mean()) * 100))
    # TONE MATCH: ESRGAN drops the source's bright speckle/crosshatch and so darkens dark art (Thompson -7.5%).
    # Restore the source's local tone with a smooth per-channel gain; detail above ~16 px is ESRGAN's.
    sg = 16.0 * W / 4096
    gain = np.stack([ndimage.gaussian_filter(lz[..., c], sg) / np.maximum(ndimage.gaussian_filter(base[..., c], sg), 1.0)
                     for c in range(3)], -1)
    base = base * np.clip(gain, 0.8, 1.25)
    cover, convex, concave, st = mesh_masks(cfg, W, H)
    log("  mesh", st, "cover %.1f%%" % (cover.mean() * 100))
    steel, wood, plastic = material_masks(src, cfg, W, H)
    L = luma(base)
    out = base.copy()
    m0 = luma(lz).mean()
    stage = lambda tag: log("    mean %-8s %+.1f%%" % (tag, (luma(out).mean() / m0 - 1) * 100))
    stage("esrgan")
    k = cfg["wear"] * float(os.environ.get("WHD_WEAR", "1"))      # global wear strength (option B = 1.8)

    # ---- 4. material micro-detail (multiplicative on luma, so hue is kept)
    # RESTORE THE SOURCE'S OWN METAL TEXTURE: ESRGAN smoothed parkerizing into flat blue-black plastic (review:
    # Colt slide, Kar98 top metal). Put back the band-passed source detail on steel, except where the
    # hallucination guard already fell back to Lanczos.
    sm = (steel * cover)[..., None] * (1 - gw)
    bp = ndimage.gaussian_filter(lz, (0.6 * W / 4096, 0.6 * W / 4096, 0)) - ndimage.gaussian_filter(lz, (4.0 * W / 4096, 4.0 * W / 4096, 0))
    out += bp * 0.55 * sm
    if cfg["steel"] == "parkerized":
        g = 0.085 * grain(rng, H, W, 1.0 * W / 4096) + 0.03 * grain(rng, H, W, 2.6 * W / 4096)
        # phosphate: flat, a touch grey-green, never glossy
        tint = np.array([0.985, 1.0, 0.985], np.float32)
    else:
        g = 0.028 * grain(rng, H, W, 0.6) + 0.012 * grain(rng, H, W, 3.0)
        tint = np.array([0.99, 0.995, 1.01], np.float32)            # blue-black
    out *= (1 + g * steel * cover)[..., None]
    # ...and an ADDITIVE floor: on near-black finishes (luma ~25-35) a multiplicative grain is +-2 levels and
    # invisible, which is why review still saw the Colt slide as smooth plastic. Parkerizing is a visible matte
    # speckle even on black; bluing is close to smooth.
    lv = 5.0 if cfg["steel"] == "parkerized" else 1.8
    out += (grain(rng, H, W, 0.9 * W / 4096) * lv * steel * cover)[..., None]
    out = out * (1 - steel[..., None] * cover[..., None] * 0.35) + out * tint * steel[..., None] * cover[..., None] * 0.35
    if cfg.get("wood"):
        ws = oriented_streaks(rng, L, H, W)
        out *= (1 + 0.07 * ws * wood * cover)[..., None]

    stage("material")
    # ---- 5. wear
    chip = grain(rng, H, W, 2.5 * W / 4096)
    chip2 = grain(rng, H, W, 1.6 * W / 4096)
    edge = ndimage.gaussian_filter(convex, 2.0 * W / 4096)
    # wear is broken up into chips along the edge, never a continuous outline: only where a coarse
    # noise field is high (~30% of the edge length), with a fine noise ragging the chip boundary
    patches = np.clip((grain(rng, H, W, 12.0 * W / 4096) - 0.35) * 1.4, 0, 1)
    edge = np.clip(edge * 1.8 - 0.15 + 0.3 * chip2 + 0.25 * chip, 0, 1) * patches * np.clip(edge * 6.0, 0, 1)   # gated to the edge band
    # AGREE WITH THE ART: the mesh is faceted (a round rim is an octagon), the painting is not. Wear follows the
    # mesh edge only where the art itself paints a highlight there; elsewhere it is faint. Without this the
    # Kar98's round parts got straight dashed octagon outlines (caught in QA).
    ridge = np.clip((L - ndimage.gaussian_filter(L, 5.0 * W / 4096)) / 18.0, 0, 1)
    ridge = ndimage.gaussian_filter(ridge, 1.5 * W / 4096)
    edge = edge * (0.15 + 0.85 * np.clip(ridge * 1.5, 0, 1))
    # bare steel: lift toward a cool silver-grey, scaled by how dark the finish was
    bare = np.array([150, 150, 148], np.float32) if cfg["steel"] == "blued" else np.array([128, 128, 124], np.float32)
    amt = (0.55 if cfg["steel"] == "blued" else 0.38) * k
    se = edge * steel * amt * (1 - np.clip(ndimage.gaussian_filter(plastic, 4.0 * W / 4096) * 3, 0, 1))
    out = out * (1 - se[..., None]) + (bare * (0.6 + 0.4 * L[..., None] / 255)) * se[..., None]
    # wood edge rub: lighter, worn through the finish
    we = edge * wood * 0.30 * k
    out = out * (1 - we[..., None]) + np.clip(out * 1.45 + 8, 0, 255) * we[..., None]
    # contact / handling zones
    zones = np.zeros((H, W), np.float32)
    for (u0, v0, u1, v1, mat, s_) in cfg["contact"]:
        cm = zone_mask(W, H, (u0, v0, u1, v1), rng) * cover
        zones += cm
        m2 = np.clip(cm * (0.6 + 0.5 * grain(rng, H, W, 18 * W / 4096)), 0, 1) * s_ * k
        if mat == "steel":
            # thinned bluing turns brown-plum and lighter
            tgt = out * np.array([1.18, 1.08, 1.02], np.float32) + 10
            out = out * (1 - (m2 * steel)[..., None]) + tgt * (m2 * steel)[..., None]
        elif mat == "wood":
            # hand oil and dirt darken and warm the stock
            tgt = out * np.array([0.80, 0.74, 0.70], np.float32)
            out = out * (1 - (m2 * wood)[..., None]) + tgt * (m2 * wood)[..., None]
        else:
            tgt = out * 1.08 + 2                                     # bakelite polished by the palm (subtle: review nit)
            out = out * (1 - (m2 * plastic)[..., None] * 0.4) + tgt * (m2 * plastic)[..., None] * 0.4
    for (u0, v0, u1, v1, s_) in cfg["holster"]:
        hm = zone_mask(W, H, (u0, v0, u1, v1), rng) * cover * steel
        zones += hm
        m2 = np.clip(hm * (0.4 + 0.6 * np.clip(grain(rng, H, W, 30 * W / 4096) * 0.5 + 0.5, 0, 1)), 0, 1) * s_ * 0.35 * k
        tgt = bare * (0.55 + 0.45 * L[..., None] / 255)
        out = out * (1 - m2[..., None]) + tgt * m2[..., None]
    stage("edges+zones")
    # scratches
    sw = 0.12 + np.clip(zones, 0, 1) + 0.6 * np.clip(ndimage.gaussian_filter(convex, 10.0 * W / 4096) * 4, 0, 1)
    sb, sd = scratches(rng, W, H, steel * cover, int(110 * k * W * H / 4096 ** 2 * 2), 8, 55, 0.0, sw)
    out += (sb * 20 * k)[..., None] - (sd * 7 * k)[..., None]
    wb, wd = scratches(rng, W, H, wood * cover, int(120 * k * W * H / 4096 ** 2 * 2), 5, 35, 0.0, sw)
    out += (wb * 16 * k)[..., None] * np.array([1.0, 0.85, 0.65], np.float32)
    dn = dents(rng, W, H, wood * cover, int(90 * k * W * H / 4096 ** 2 * 2))
    out *= (1 - 0.22 * dn * k)[..., None]
    stage("scratch")
    # grime/oil in concave corners
    gm = ndimage.gaussian_filter(concave, 4.0 * W / 4096)
    gm = np.clip(gm * 1.8, 0, 1) * (0.7 + 0.3 * np.clip(chip * 0.5 + 0.5, 0, 1))
    # same art-agreement rule as the edge wear: grime only where the painting already has a crease/valley
    valley = np.clip((ndimage.gaussian_filter(L, 5.0 * W / 4096) - L) / 18.0, 0, 1)
    gm = gm * (0.25 + 0.75 * np.clip(ndimage.gaussian_filter(valley, 2.0 * W / 4096) * 1.5, 0, 1))
    grime = np.array([0.62, 0.58, 0.52], np.float32)
    out = out * (1 - 0.45 * gm[..., None] * k) + out * grime * 0.45 * gm[..., None] * k
    out = np.clip(out, 0, 255)

    # ---- QA gates
    assert np.isfinite(out).all()
    ls, lo = luma(lz), luma(out)
    sm = lambda a: np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((512, 512 * H // W), Image.BOX), np.float32)
    corr = float(np.corrcoef(sm(ls).ravel(), sm(lo).ravel())[0, 1])
    shift = float((lo.mean() - ls.mean()) / max(ls.mean(), 1e-6))
    log("  QA corr %.3f  mean shift %+.1f%%" % (corr, shift * 100))
    assert corr >= 0.90, "detail pass drifted from the art"
    assert abs(shift) <= 0.06, "brightness gate"
    tagv = "" if variant == 0 else "_v%d" % variant
    os.makedirs(PREV, exist_ok=True)
    ptag = tagv + os.environ.get("WHD_TAG", "")
    Image.fromarray(out.astype(np.uint8)).save(os.path.join(WORK, name + ptag + "_final.png"))
    dbg = np.stack([edge * steel * 255, gm * 255, wood * 255], -1).astype(np.uint8)
    Image.fromarray(dbg).resize((W // 4, H // 4)).save(os.path.join(PREV, name + tagv + "_masks.jpg"), quality=85)
    # ---- DDS
    if os.environ.get("WHD_NOENC"):
        return dict(name=name, corr=corr, shift=shift, mesh=st, source=tag)
    dds = encode_dxt1_mipped(out)
    rel = cfg["sheet"] + tagv + ".dds"
    p = os.path.join(STAGE, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(dds)
    dec = V2.dds_decode_level(dds, V2.dds_parse(dds), 0)[..., :3].astype(np.float32)
    lean = (dec.reshape(-1, 3).mean(0) - out.reshape(-1, 3).mean(0))
    log("  DDS %s  %.1f MB  lean %s  %.0fs" % (rel, len(dds) / 1e6, np.round(lean, 2), time.time() - t0))
    assert np.abs(lean).max() < 1.5
    return dict(name=name, rel=rel, bytes=len(dds), corr=corr, shift=shift, lean=lean.tolist(), mesh=st, source=tag)


def encode_dxt1_mipped(level0):
    H, W = level0.shape[:2]
    hdr, _ = V2.encode_level(np.zeros((4, 4, 3), np.uint8), "DXT1")
    hdr = bytearray(hdr)
    n = V2.full_mips(W, H)
    struct.pack_into("<II", hdr, 12, H, W)
    struct.pack_into("<I", hdr, 8, struct.unpack_from("<I", hdr, 8)[0] | V2.DDSD_MIPMAPCOUNT | V2.DDSD_LINEARSIZE)
    struct.pack_into("<I", hdr, 20, max(1, (W + 3) // 4) * max(1, (H + 3) // 4) * 8)
    struct.pack_into("<I", hdr, 28, n)
    struct.pack_into("<I", hdr, 108, struct.unpack_from("<I", hdr, 108)[0] | V2.DDSCAPS_COMPLEX | V2.DDSCAPS_MIPMAP)
    out, cur = bytearray(hdr), level0.astype(np.float64)
    for k in range(n):
        if k:
            cur = V2.box_half(cur)
        h = cur.shape[0]
        band = 256 if h >= 256 else h
        for y in range(0, h, band):
            out += V4.bc1_encode_dc(np.clip(cur[y:y + band], 0, 255))
    info = V2.dds_parse(bytes(out))
    assert info["end"] == len(out) and info["levels"][-1][:2] == (1, 1)
    return bytes(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    var = 0
    if args and args[0] == "--variant":
        var = int(args[1]); args = args[2:]
    res = [build(g, var) for g in args]
    json.dump(res, open(os.path.join(HERE, "..", "build_report%s.json" % ("" if var == 0 else "_v%d" % var)), "w"), indent=1)
