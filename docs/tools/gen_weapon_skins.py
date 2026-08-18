"""Generate weapon skin variants from our real base textures.

The whole trick is to keep the ORIGINAL's luminance detail and only replace its colour. A gun
texture carries all its readability in that detail - screw heads, wood grain, wear along the
receiver, the seam where the stock meets metal. Flood-filling a hue over the top gives you the
flat plastic look that makes most reskins on the file sites look cheap. So every variant here
re-maps the base luminance through a palette instead of tinting the pixels.

    python mkskins.py            # writes previews + a contact sheet
"""
import glob
import io
import os
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = "_skins"
GUNS = [
    ("Thompson", "textures/models/weapons/ThompsonSMG/ThompsonSMG.jpg"),
    ("M1 Garand", "textures/models/weapons/M1Garand/GARAND.jpg"),
    ("MP40", "textures/models/weapons/MP40/MP40.jpg"),
    ("BAR", "textures/models/weapons/Bar/bar.jpg"),
]


def from_paks(vpath):
    for f in sorted(glob.glob(r"G:/GOG/Medal of Honor - Allied Assault War Chest/main*/*.pk3")):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower().replace("\\", "/") == vpath.lower():
                return Image.open(io.BytesIO(z.read(n))).convert("RGB")
    return None


def luma(img):
    a = np.asarray(img).astype(np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def ramp(l, stops):
    """Map luminance through a colour ramp. stops = [(pos, (r,g,b)), ...] 0..1, 0..255."""
    pos = np.array([s[0] for s in stops], dtype=np.float32)
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    out = np.zeros(l.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(l, pos, cols[:, c])
    return out


def norm(l, lo=2, hi=98):
    a, b = np.percentile(l, lo), np.percentile(l, hi)
    return np.clip((l - a) / max(b - a, 1e-6), 0, 1)


def gold(img):
    # Deep bronze in the shadows through to near-white on the highlights - the highlight blowout
    # is what actually reads as metal rather than yellow paint.
    l = norm(luma(img)) ** 0.85
    return ramp(l, [(0.0, (28, 16, 4)), (0.35, (120, 78, 16)),
                    (0.65, (212, 160, 40)), (0.88, (245, 214, 120)), (1.0, (255, 248, 214))])


def chrome(img):
    # First pass used a 2.1x S-curve and crushed the texture to near black-and-white - a
    # photocopy, not chrome. Chrome is not high CONTRAST, it is high SPECULARITY: a compressed
    # midtone with a bright rolloff. Gentle curve, midtones kept, cool cast in the shadows.
    l = norm(luma(img))
    s = np.clip((l - 0.5) * 1.25 + 0.5, 0, 1)
    return ramp(s, [(0.0, (48, 54, 64)), (0.25, (104, 112, 126)), (0.5, (156, 164, 178)),
                    (0.72, (198, 206, 218)), (0.9, (232, 238, 246)), (1.0, (252, 254, 255))])


def blued(img):
    l = norm(luma(img)) ** 0.95
    return ramp(l, [(0.0, (10, 12, 18)), (0.45, (36, 44, 66)),
                    (0.75, (78, 92, 124)), (1.0, (186, 198, 220))])


def bloody(img):
    """Base texture with blood worked into it - spatter, run-off and a darkened soak."""
    base = np.asarray(img).astype(np.float32)
    h, w = base.shape[:2]
    rng = np.random.default_rng(7)
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for _ in range(90):                       # spatter
        x, y = rng.integers(0, w), rng.integers(0, h)
        r = int(rng.integers(3, max(4, w // 90)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.integers(120, 255)))
    for _ in range(26):                       # soak patches
        x, y = rng.integers(0, w), rng.integers(0, h)
        rx, ry = int(rng.integers(w // 40, w // 12)), int(rng.integers(h // 40, h // 12))
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=int(rng.integers(70, 150)))
    for _ in range(30):                       # runs
        x, y = rng.integers(0, w), rng.integers(0, h)
        ln = int(rng.integers(h // 22, h // 6))
        wd = int(rng.integers(2, max(3, w // 220)))
        d.rectangle([x, y, x + wd, min(h - 1, y + ln)], fill=int(rng.integers(90, 190)))
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(max(1, w // 500)))).astype(np.float32) / 255.0
    m = m[..., None]
    blood = np.array([102, 12, 10], dtype=np.float32)
    dark = base * 0.55                        # blood soaks and darkens what it sits on
    return dark * m + base * (1 - m) * 1.0 + (blood - blood) + (blood * m * 0.75)


def camo(img, palette, scale=4, seed=3):
    """Paint camo ONTO the gun - keep its shading and every hard edge.

    The first attempt blended a pattern over the top with shade = 0.45 + 0.75*l, which lifted the
    shadows so far that the receiver, the screws and the wood grain all vanished under what looked
    like camo wallpaper. The fix is to split the base into two parts and treat them differently:
    a LOW-frequency shading term normalised around 1.0, which multiplies the pattern so the gun's
    own light and wear survive, and a HIGH-frequency detail term added back on top, which is what
    carries the edges and screw heads. The pattern only ever supplies hue.
    """
    l = norm(luma(img))
    h, w = l.shape
    blur_r = max(2, w // 64)
    low = np.asarray(Image.fromarray((l * 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(blur_r))).astype(np.float32) / 255.0
    detail = l - low                                   # edges, screws, grain
    shade = np.clip(low / max(low.mean(), 1e-6), 0.45, 1.55)[..., None]

    rng = np.random.default_rng(seed)
    small = rng.random((max(3, h // (scale * 6)), max(3, w // (scale * 6))))
    field = np.asarray(Image.fromarray((small * 255).astype(np.uint8))
                       .resize((w, h), Image.BICUBIC)).astype(np.float32) / 255.0
    field = np.asarray(Image.fromarray((field * 255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(max(1, w // 420)))).astype(np.float32) / 255.0
    idx = np.digitize(field, np.linspace(field.min(), field.max(), len(palette) + 1)[1:-1])
    pat = np.array(palette, dtype=np.float32)[idx]

    # 340 was too strong and rang a faint halo along every hard edge. 190 keeps the
    # screws and grain readable without outlining them.
    return np.clip(pat * shade + detail[..., None] * 190.0, 0, 255)


VARIANTS = [
    ("gold", gold),
    ("chrome", chrome),
    ("blued", blued),
    ("bloody", bloody),
    ("camo_woodland", lambda im: camo(im, [(58, 66, 40), (86, 92, 56), (44, 40, 30), (104, 98, 66)])),
        # Winter was blown out - it read as overexposed rather than painted white. A real
    # whitewashed weapon is dirty off-white over grey, so the palette drops well below 255.
    ("camo_winter", lambda im: camo(im, [(178, 182, 186), (140, 146, 152), (96, 102, 108), (206, 210, 213)], seed=11)),
    ("camo_desert", lambda im: camo(im, [(176, 150, 104), (146, 120, 78), (198, 178, 138), (118, 98, 66)], seed=5)),
]

os.makedirs(OUT, exist_ok=True)
THUMB = 190
rows = []
for name, vpath in GUNS:
    img = from_paks(vpath)
    if img is None:
        print("  %-12s base texture not found" % name)
        continue
    key = name.lower().replace(" ", "_")
    cells = [("original", img)]
    for vname, fn in VARIANTS:
        arr = np.clip(fn(img), 0, 255).astype(np.uint8)
        out = Image.fromarray(arr)
        out.save(os.path.join(OUT, "%s_%s.jpg" % (key, vname)), quality=92)
        cells.append((vname, out))
    rows.append((name, cells))
    print("  %-12s %dx%d  ->  %d variants" % (name, img.width, img.height, len(VARIANTS)))

if rows:
    cols = len(rows[0][1])
    pad, lab, hdr, side = 8, 16, 22, 84
    W = side + cols * (THUMB + pad) + pad
    H = hdr + len(rows) * (THUMB + lab + pad) + pad
    sheet = Image.new("RGB", (W, H), (22, 24, 20))
    dr = ImageDraw.Draw(sheet)
    for ci, (cname, _) in enumerate(rows[0][1]):
        dr.text((side + ci * (THUMB + pad) + 2, 6), cname, fill=(228, 228, 214))
    for ri, (gname, cells) in enumerate(rows):
        y = hdr + ri * (THUMB + lab + pad)
        dr.text((6, y + THUMB // 2), gname, fill=(228, 228, 214))
        for ci, (cname, im) in enumerate(cells):
            sheet.paste(im.resize((THUMB, THUMB), Image.LANCZOS),
                        (side + ci * (THUMB + pad), y))
    sheet.save(os.path.join(OUT, "contact_sheet.png"))
    print("\n  contact sheet -> %s/contact_sheet.png  (%dx%d)" % (OUT, W, H))
