"""retouch.py <bake dir> <out dir> - texel retouches of the attic's baked atlases (the bake stays; only these texels change).

Each op names its defect id from ../README.md.  Selection is by WORLD box (the Blender object bounds in <bake>/groups.json
"names") + triangle size, never by screen picks alone, so a re-bake of the same blend can re-run the same op.
Output: <out>/textures/menu/hzm_atc_<group>.jpg (quality 95, the same as build_models2.py writes)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

bake, out = sys.argv[1], sys.argv[2]
tdir = os.path.join(out, "textures", "menu")
os.makedirs(tdir, exist_ok=True)
NAMES = json.load(open(os.path.join(bake, "groups.json")))["names"]
cache = {}


def atlas(g):
    if g not in cache:
        cache[g] = np.asarray(Image.open(os.path.join(bake, g + ".png")).convert("RGB")).astype(np.float32) / 255
    return cache[g]


def tris(g, lo, hi, max_area=None, pad=0.01):
    d = np.load(os.path.join(bake, g + ".npz"))
    P, UV = d["pos"].astype(np.float64), d["uv"].astype(np.float64)
    c = P.mean(1)
    sel = np.all((c >= np.array(lo) - pad) & (c <= np.array(hi) + pad), 1)
    if max_area is not None:
        ar = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2
        sel &= ar <= max_area
    return UV[sel]


def uvmask(g, UVs, grow=3):
    H, W = atlas(g).shape[:2]
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for t in UVs:
        d.polygon([(u * W, (1 - v) * H) for u, v in t], fill=255)
    if grow:
        m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    return np.asarray(m) > 0


def bakelite(g, box, max_area, zmin=-1e9, skip_y=None):
    """D-A3: the long desk's telephones were candy red / white / green / teal, and the wall phone red - 1950s plastics in a 1943
    field office.  They become black bakelite: the bake's own shading (luminance) is kept, the colour goes, a hint of warm brown in
    the lit side the way old bakelite reads.  Every texel of the phones' small triangles above the shelf top changes; the leather
    case standing between the phones (BU y 3.92-4.30) is skipped (it is not a phone and stays brown)."""
    a = atlas(g)
    d = np.load(os.path.join(bake, g + ".npz"))
    P, UV = d["pos"].astype(np.float64), d["uv"].astype(np.float64)
    c = P.mean(1)
    ar = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2
    sel = np.all((c >= np.array(box[0]) - 0.01) & (c <= np.array(box[1]) + 0.01), 1) & (ar <= max_area) & (c[:, 2] > zmin)
    col = uvmask(g, UV[sel], grow=1)
    L = (a * np.array([0.30, 0.59, 0.11])).sum(2)
    k = 0.05 + 0.30 * np.power(L, 1.5)
    new = k[..., None] * np.array([1.0, 0.93, 0.84])
    a[col] = new[col]
    print("bakelite %s %s: %d texels" % (g, box, int(col.sum())))


def wall_silhouettes():
    """D-A1: the right-hand wall (bg tris 190624/5, x = 3.0 BU) carries a hard, oversized shadow of a chair back and a telephone
    handset inside the lamp pool, low on the wall behind the long desk; at 21:9 it reads as a phantom chair and phone, and at 16:9 as a
    black blob in the right corner.  The silhouettes are painted out of the pool (OpenCV Telea from the lit wall around them); the
    desk's own horizontal shadow band across the pool is kept.  Atlas box found with an exact z-buffer pick (README)."""
    import cv2
    a = atlas("bg")
    H, W = a.shape[:2]
    # v1.10.62: chosen by WORLD rectangle on the wall plane (x = 3.0 BU), not by atlas pixels, so a re-bake (a new UV layout) re-runs
    # it.  The rectangle is the v1.10.61 atlas box (1008 1435 1072 1672 in bake_s5) mapped back to the wall: y 1.87-4.09, z 0.31-0.90.
    Y0, Y1, Z0, Z1 = 1.868, 4.09, 0.307, 0.897
    BAND = (3.133, 3.46)                                 # the desk-edge shadow band across the pool (kept)
    d = np.load(os.path.join(bake, "bg.npz"))
    P, UV = d["pos"].astype(np.float64), d["uv"].astype(np.float64)
    c = P.mean(1)
    wall = np.where((abs(P[:, :, 0] - 3.0) < 0.005).all(1) & (c[:, 1] > Y0 - 0.5) & (c[:, 1] < Y1 + 0.5) & (c[:, 2] < Z1 + 0.5))[0]
    assert len(wall), "no wall tris at x = 3.0"
    # per wall triangle: an affine atlas px -> (y, z) map; every atlas texel inside the triangle gets its wall position
    Yw = np.full((H, W), np.nan, np.float32)
    Zw = np.full((H, W), np.nan, np.float32)
    for t in wall:
        px = np.stack([UV[t, :, 0] * W, (1 - UV[t, :, 1]) * H], 1)
        M = np.c_[px, np.ones(3)]
        if abs(np.linalg.det(M)) < 1e-6:
            continue
        cy, cz = np.linalg.solve(M, P[t, :, 1]), np.linalg.solve(M, P[t, :, 2])
        x0, y0 = np.floor(px.min(0)).astype(int)
        x1, y1 = np.ceil(px.max(0)).astype(int) + 1
        tm = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(tm).polygon([(u - x0, v - y0) for u, v in px], fill=255, outline=255)
        yy, xx = np.nonzero(np.asarray(tm))
        gx, gy = xx + x0 + 0.5, yy + y0 + 0.5
        Yw[yy + y0, xx + x0] = cy[0] * gx + cy[1] * gy + cy[2]
        Zw[yy + y0, xx + x0] = cz[0] * gx + cz[1] * gy + cz[2]
    inbox = (Yw >= Y0) & (Yw <= Y1) & (Zw >= Z0) & (Zw <= Z1)
    # the silhouettes are narrow dark shapes notched into the lamp pool; the dark wall beyond the pool's edge is broad.  A grey-level
    # closing (a 0.2 m disc) fills only the narrow ones, so (closing - image) marks the silhouettes and leaves the pool's edge alone
    L = (a.mean(2) * 255).astype(np.uint8)
    ys, xs = np.nonzero(inbox)
    bx0, by0, bx1, by1 = max(0, xs.min() - 60), max(0, ys.min() - 60), min(W, xs.max() + 61), min(H, ys.max() + 61)   # (v1.10.66: clamped - the wall's island can sit at the atlas edge)
    sub = L[by0:by1, bx0:bx1]
    tpm = (by1 - by0) / max(Y1 - Y0, Z1 - Z0) if (by1 - by0) > (bx1 - bx0) else (bx1 - bx0) / max(Y1 - Y0, Z1 - Z0)   # texels per metre
    r = max(5, int(round(0.10 * tpm)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    gap = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, k).astype(np.int16) - sub
    m = np.zeros(L.shape, bool)
    m[by0:by1, bx0:bx1] = gap > 10
    m &= inbox & ~((Yw >= BAND[0] - 0.02) & (Yw <= BAND[1] + 0.02))
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) & inbox.astype(np.uint8)
    full = (m * 255).astype(np.uint8)
    # fill = the closing itself (per channel, softened): the pool's own gradient carried over the notch, not an inpaint that drags
    # the dark wall beyond the edge into it
    rgb = (np.clip(a[by0:by1, bx0:bx1], 0, 1) * 255 + 0.5).astype(np.uint8)
    fill = np.stack([cv2.morphologyEx(rgb[:, :, ch], cv2.MORPH_CLOSE, k) for ch in range(3)], -1)
    fill = cv2.GaussianBlur(fill, (0, 0), 2.0).astype(np.float32) / 255
    soft = cv2.GaussianBlur(full[by0:by1, bx0:bx1].astype(np.float32) / 255, (0, 0), 1.5)[..., None]
    a[by0:by1, bx0:bx1] = a[by0:by1, bx0:bx1] * (1 - soft) + fill * soft
    print("wall silhouettes: %d texels" % int((full > 0).sum()))


def keylamp_residue():
    """D-A4: a black speck on the left roof slope of the home view: what is left of the Blender key-light lamp (object 'keylamp',
    a lighting-rig prop) after build_models2's CUT_BOXES (the shipped models keep its hook / cord tris).  Its texels are painted the
    colour of the roof boards behind it (the median of the slope's own atlas texels around the speck, found with atlas_pick.zpick),
    so it vanishes against the roof without touching the models."""
    a = atlas("bg")
    k = NAMES["keylamp"]
    m = uvmask("bg", tris("bg", k["min"], k["max"], max_area=0.01, pad=0.06), grow=2)
    # the roof right around the speck, as the engine draws it (fullbright: screen colour == texel colour); the home view of the
    # untouched build, 1080p: the speck sits at ~(65, 250)
    ref = os.environ.get("KEYLAMP_REF", r"H:\hzm_work\attic_polish\runs\sv_before_1080\sv_before_1080_00idle.tga")
    s = np.asarray(Image.open(ref).convert("RGB")).astype(np.float32)[225:275, 40:95] / 255
    L = s.mean(2)
    col = np.median(s[L > np.median(L) - 0.02], 0)
    a[m] = col
    # the speck's core is the lamp's shadow BAKED INTO the roof board (bg tri 189484): each dark pixel of the speck is ray-cast
    # to the roof texel it shows (atlas_pick.raycast - the roof straddles the camera plane, so zpick culls it) and those texels
    # are inpainted from the boards around them
    import cv2
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import atlas_pick as AP
    roi = (40, 225, 95, 280)
    sc = np.asarray(Image.open(ref).convert("L")).astype(np.float32)[roi[1]:roi[3], roi[0]:roi[2]]
    ys, xs = np.nonzero(sc < np.median(sc) - 20)
    hits = AP.raycast(AP.HOME, 1920, 1080, [(x + roi[0], y + roi[1]) for x, y in zip(xs, ys)])
    H, W = a.shape[:2]
    m2 = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(m2)
    for t, uv in hits:
        if uv is not None:
            x, y = uv[0] * W, (1 - uv[1]) * H
            dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=255)
    m2 = np.asarray(m2)
    img = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    fix = cv2.inpaint(img[:, :, ::-1].copy(), m2, 5, cv2.INPAINT_TELEA)[:, :, ::-1]
    a[m2 > 0] = fix[m2 > 0].astype(np.float32) / 255
    m = m | (m2 > 0)
    print("keylamp residue: %d texels -> %s" % (int(m.sum()), np.round(col, 3)))


# RETOUCH_OPS selects the ops (default: all, for the v1.10.61 bake_s5).  The v1.10.62 re-bake removes the key lamp in the scene
# (attic62_edit.py), so it runs "floor_lm,floor_alb,wall,phones": every op selects by world box, so it re-runs on a new UV layout
# (the scene's bak_* material swap did not reach the handsets - they baked red / green again - so the phones op stays).
OPS = set(os.environ.get("RETOUCH_OPS", "keylamp,wall,phones,floor_lm,floor_alb").split(","))
if "keylamp" in OPS:
    keylamp_residue()
if "wall" in OPS:
    wall_silhouettes()
if "phones" in OPS:
    # v1.10.66: the phones bake into their own "desk" atlas now (attic62_edit section 12)
    PG = "desk" if os.path.exists(os.path.join(bake, "desk.npz")) else "bg"
    ph = NAMES["phone"]
    bakelite(PG, (ph["min"], ph["max"]), 0.004, zmin=1.02, skip_y=(3.92, 4.30))
    wp = NAMES["wallphone"]
    bakelite(PG, (wp["min"], wp["max"]), 0.004)



def dial_art(N=1024):
    """a 1940s rotary dial seen face-on, in the unit disc (centre N/2): the finger wheel (black bakelite, 10 finger holes on a ring)
    over a cream number card whose digits show through the holes, a cream centre label with a ring, the chrome plate's rim outside
    the wheel and the steel finger stop. Returns RGB float and the radius (px) of the unit circle"""
    from PIL import ImageFont
    S = 2
    W = N * S
    im = Image.new("RGB", (W, W), (150, 152, 156))                 # the plate (chrome, read as grey)
    d = ImageDraw.Draw(im)
    c, R = W / 2, W / 2 - 2
    d.ellipse([c - R, c - R, c + R, c + R], fill=(150, 152, 156), outline=(70, 72, 76), width=6 * S)
    rw = R * 0.90
    d.ellipse([c - rw, c - rw, c + rw, c + rw], fill=(18, 18, 20))                 # the finger wheel
    fnt = ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", "arialbd.ttf"), int(R * 0.20))
    import math as _m
    for k, dg in enumerate("1234567890"):
        ang = _m.radians(60 + 30 * k)                                              # 1 at upper right, counter-clockwise to 0
        hx, hy = c + R * 0.63 * _m.cos(ang), c - R * 0.63 * _m.sin(ang)
        hr = R * 0.155
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(196, 186, 158), outline=(8, 8, 8), width=3 * S)
        d.text((hx, hy), dg, font=fnt, fill=(24, 22, 20), anchor="mm")
    rc = R * 0.30                                                                   # the centre label
    d.ellipse([c - rc, c - rc, c + rc, c + rc], fill=(204, 196, 170), outline=(120, 110, 90), width=3 * S)
    d.ellipse([c - rc * 0.80, c - rc * 0.80, c + rc * 0.80, c + rc * 0.80], outline=(150, 40, 30), width=2 * S)
    ang = _m.radians(15)                                                            # the finger stop at lower right
    fx, fy = c + R * 0.80 * _m.cos(-ang), c - R * 0.80 * _m.sin(-ang)
    d.line([(c + R * 0.66 * _m.cos(-ang), c - R * 0.66 * _m.sin(-ang)), (fx, fy)], fill=(190, 192, 196), width=int(R * 0.06))
    im = im.resize((N, N), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255, N / 2 - 1


def dials():
    """v1.10.66 (coordinator: the dials baked as stark white splats with jagged edges): every texel of every dial's triangles (plate,
    card, wheel, finger holes, centre) is repainted from ONE drawn dial (dial_art) by its own position on the dial plane - so the card
    shows through the holes on whichever layer it lies - under a single light level from the bake around it; the islands' bake margin
    is refilled from the painted texels (no white fringe)."""
    import cv2
    DJ = json.load(open(os.environ.get("DIALS_JSON", os.path.join(os.path.dirname(os.path.normpath(bake)), "dials.json"))))
    g = "desk"
    a = atlas(g)
    H, W = a.shape[:2]
    d = np.load(os.path.join(bake, g + ".npz"))
    P, UV = d["pos"].astype(np.float64), d["uv"].astype(np.float64)
    cen = P.mean(1)
    art, R0 = dial_art()
    AN = art.shape[0]
    allm = uvmask(g, UV, grow=0)
    painted = np.zeros((H, W), bool)
    for name, dd in DJ.items():
        c = np.array(dd["c"])
        rp = dd["r_plate"]
        near = np.linalg.norm(cen - c, axis=1) < rp * 1.05
        # only the dial's own parts: every corner of the triangle inside the plate's radius (the phone body's top around the dial
        # also has its centroid near - painting it gave a jagged grey square round each dial)
        near &= (np.linalg.norm(P - c, axis=2) < rp * 1.03).all(1)
        if not near.any():
            continue
        # the dial plane: the card's own vertices fit best; take the plane of the near tris' points (least-variance axis)
        pts = P[near].reshape(-1, 3)
        q = pts - pts.mean(0)
        n = np.linalg.svd(q, full_matrices=False)[2][2]
        n /= np.linalg.norm(n)
        sel = near & (np.abs((cen - c) @ n) < 0.02)
        up = np.array([0, 0, 1.0]) - n * n[2]
        if np.linalg.norm(up) < 1e-3:
            up = np.array([0, 1.0, 0]) - n * n[1]
        up /= np.linalg.norm(up)
        if n @ (np.array([-0.40, -0.70, 1.95]) - c) < 0:                            # face the home camera
            n = -n
        right = np.cross(up, n)
        # the light level: the baked luminance on these tris, heavily averaged (the white splat's own value would be too bright)
        m = uvmask(g, UV[sel], grow=0)
        Lb = float(np.median((a[m] * np.array([0.30, 0.59, 0.11])).sum(1))) if m.any() else 0.6
        shade = float(np.clip(0.35 + 0.65 * Lb, 0.55, 1.0))
        for t in np.where(sel)[0]:
            px = np.stack([UV[t, :, 0] * W, (1 - UV[t, :, 1]) * H], 1)
            M = np.c_[px, np.ones(3)]
            if abs(np.linalg.det(M)) < 1e-9:
                continue
            k = np.linalg.solve(M, P[t])                                            # 3 x 3: atlas px -> world
            x0, y0 = np.floor(px.min(0)).astype(int)
            x1, y1 = np.ceil(px.max(0)).astype(int) + 1
            tm = Image.new("L", (max(1, x1 - x0), max(1, y1 - y0)), 0)
            ImageDraw.Draw(tm).polygon([(u - x0, v - y0) for u, v in px], fill=255, outline=255)
            yy, xx = np.nonzero(np.asarray(tm))
            if not len(yy):
                continue
            gx, gy = xx + x0 + 0.5, yy + y0 + 0.5
            wp = np.c_[gx, gy, np.ones_like(gx)] @ k
            rel = wp - c
            u = rel @ right / rp
            v = rel @ up / rp
            ix = np.clip(AN / 2 + u * R0, 0, AN - 1.001)
            iy = np.clip(AN / 2 - v * R0, 0, AN - 1.001)
            i0x, i0y = ix.astype(int), iy.astype(int)
            fx, fy = (ix - i0x)[:, None], (iy - i0y)[:, None]
            col = (art[i0y, i0x] * (1 - fx) * (1 - fy) + art[i0y, i0x + 1] * fx * (1 - fy) + art[i0y + 1, i0x] * (1 - fx) * fy + art[i0y + 1, i0x + 1] * fx * fy)
            ok = (yy + y0 < H) & (xx + x0 < W) & (u * u + v * v <= 1.0)
            a[(yy + y0)[ok], (xx + x0)[ok]] = col[ok] * shade
            painted[(yy + y0)[ok], (xx + x0)[ok]] = True
    # the bake margin around the repainted islands: grow the painted colours outwards over texels that belong to no triangle
    img = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    done = painted.copy()
    for _ in range(8):
        grown = cv2.dilate(done.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~done & ~allm
        if not grown.any():
            break
        blur = cv2.blur(img * done[..., None], (3, 3)).astype(np.float32)
        cnt = cv2.blur(done.astype(np.float32), (3, 3))[..., None]
        fill = (blur / np.maximum(cnt, 1e-6)).clip(0, 255).astype(np.uint8)
        img[grown] = fill[grown]
        done |= grown
    a[:] = img.astype(np.float32) / 255
    print("dials: %d texels painted on %d dials" % (int(painted.sum()), len(DJ)))


if "dials" in OPS:
    dials()

for g, a in cache.items():
    TEXTY = g in ("wallmap", "blueprint", "desk", "desk2")      # = build_models2.py (q97 4:4:4 on hold: screenshots lost with a 4:4:4 atlas)
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(tdir, "hzm_atc_%s.jpg" % g), quality=95)
    print("wrote", g)


def floor_lm_denoise():
    """D-A6: the floor's separate 256 px lightmap (bake floor_lm.png, multiplied over the tiling planks) is low-spp speckle; under
    bilinear magnification, near the camera a cluster of bright texels in the lamp pool reads as faint white lettering ('X...') on
    the boards left of the chair, and dark texels as specks.  Denoised (non-local means, then a 3 px median), shadows kept."""
    import cv2
    src = (np.asarray(Image.open(os.path.join(bake, "floor_lm.png")).convert("RGB"))).copy()
    den = cv2.fastNlMeansDenoisingColored(src[:, :, ::-1].copy(), None, 9, 9, 5, 15)[:, :, ::-1]
    den = cv2.medianBlur(den, 3)
    Image.fromarray(den).save(os.path.join(tdir, "hzm_atc_floor_lm.jpg"), quality=95)
    print("floor lightmap denoised")


if "floor_lm" in OPS:
    floor_lm_denoise()


def floor_albedo_flatten():
    """D-A6 (the real cause): the tiling plank albedo (ambientCG WoodFloor043, CC0) has a pale diagonal flame-grain streak across two
    planks (around texel 1700, 220).  Foreshortened near the camera and mip-filtered it reads as a white 'X' with faint letters on the
    boards left of the chair - it survived the lightmap denoise and every lighting toggle (r_dynamiclight / r_dlightMode /
    r_sunlightMode / r_postprocess).  The albedo's low-frequency brightness is evened out (wrap-around blur, 70 %), so no broad pale
    or dark blotch survives at any distance; plank seams, knots and grain (the high frequencies) are untouched."""
    import cv2
    import io, zipfile
    # the albedo exactly as build_models2.py wrote it into the pak (its own tone processing included)
    z = zipfile.ZipFile(os.environ.get("FLOOR_ALB_PAK", r"H:\hzm_work\mphub3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3"))
    img = np.asarray(Image.open(io.BytesIO(z.read("textures/menu/hzm_atc_floor_alb.jpg"))).convert("RGB")).astype(np.float32)
    L = img.mean(2)
    p = 96                                                        # wrap-around padding: the texture tiles, so must its correction
    # The ghost's texels were MEASURED in the engine (an overlay albedo coloured by its own x / y: texels ~1450-1700, 150-370) and
    # sit on a pale diagonal grain streak crossing two planks, from about (1810, 150) to (1370, 390).  Near the camera the planks are
    # minified ~15x, so the streak plus the pale plank edge it meets read as a white "X".  Take the streak's excess brightness out
    # along that line (feathered), then a mild even-out of the broad tone so no other patch stands out; grain, knots and seams stay.
    out = img.copy()
    L = out.mean(2)
    mid = cv2.GaussianBlur(np.pad(L, p, mode="wrap"), (0, 0), 6)[p:-p, p:-p]
    wide = cv2.GaussianBlur(np.pad(L, p, mode="wrap"), (0, 0), 50)[p:-p, p:-p]
    band = np.zeros(L.shape, np.uint8)
    cv2.line(band, (1810, 150), (1370, 390), 255, 80)
    band = cv2.GaussianBlur(band.astype(np.float32) / 255, (0, 0), 18)
    excess = np.maximum(mid - wide, 0) * band
    out = out - excess[..., None] * (out / np.maximum(L, 1.0)[..., None])
    L = out.mean(2)
    low = cv2.GaussianBlur(np.pad(L, p, mode="wrap"), (0, 0), 40)[p:-p, p:-p]
    out = np.clip(out * ((low.mean() / np.maximum(low, 1.0)) ** 0.5)[..., None], 0, 255)
    Image.fromarray(out.astype(np.uint8)).save(os.path.join(tdir, "hzm_atc_floor_alb.jpg"), quality=95)
    print("floor albedo flattened")


if "floor_alb" in OPS:
    floor_albedo_flatten()
