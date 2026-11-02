"""gen_theatremap.py <out.png> [--markers markers.json] - the attic wall map re-drawn as the Breakthrough theatre map: the central
Mediterranean from Tunisia over Sicily to mainland Italy (user 2026-11-02: the new game screen IS the attic's wall map, in 3D).

Same look as the shipped wall map (H:/hzm_archive/menuattic/rt/scripts/make_textures.py wallmap(): parchment, grid, buff land
on a grey-blue sea, contour hatching, inked coast, red grease-pencil front lines, landing arrows).  4096x3072, stretched by the
wall plane's UV onto 3.148 x 2.705 m, so the lon/lat window is chosen for TRUE proportions on the wall (lon span = lat span x
wall aspect / cos(mid lat)).  Coastlines are traced through real coastal towns and capes (lon/lat, approximate); every town
is real and spelled as on period Allied maps (NAPLES, SYRACUSE, LEGHORN not needed).  No filler text.
The campaign marker anchors (lon/lat) are written to markers.json for make_newgame3d.py."""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "wallmap_med.png"
FD = r"C:\Windows\Fonts"
W, H = 4096, 3072
WALL_W, WALL_H = 3.148, 2.705                       # the attic wallmap plane (BU m), u along +x, v along +z
LAT0, LAT1 = 34.70, 42.20
LON_SPAN = (LAT1 - LAT0) * (WALL_W / WALL_H) / math.cos(math.radians((LAT0 + LAT1) / 2))
LON0 = 7.95
LON1 = LON0 + LON_SPAN
random.seed(7)


def P(lon, lat):
    return ((lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H)


def fbm(h, w, octaves=6, base=4, seed=0):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = r.random((n + 1, int(n * w / h) + 1)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += np.asarray(im, np.float32) / 255 * amp
        tot += amp
        amp *= 0.5
    return acc / tot


def font(name, px):
    return ImageFont.truetype(os.path.join(FD, name), int(px))


ITALY = [(11.60, 42.60), (11.80, 42.09), (11.85, 42.03), (12.07, 41.95), (12.23, 41.77), (12.29, 41.73), (12.63, 41.45), (12.76, 41.41),
         (13.05, 41.23), (13.25, 41.29), (13.43, 41.26), (13.57, 41.21), (13.62, 41.26), (13.76, 41.23), (13.88, 41.12), (13.93, 41.02),
         (14.03, 40.87), (14.08, 40.78), (14.12, 40.82), (14.25, 40.84), (14.37, 40.78), (14.48, 40.70), (14.37, 40.63), (14.33, 40.57),
         (14.48, 40.62), (14.60, 40.63), (14.76, 40.68), (15.00, 40.42), (14.99, 40.35), (14.90, 40.25), (15.03, 40.18), (15.27, 40.03),
         (15.49, 40.05), (15.63, 40.07), (15.72, 39.99), (15.79, 39.81), (15.94, 39.52), (16.04, 39.36), (16.07, 39.13), (16.20, 38.90),
         (16.16, 38.73), (15.90, 38.68), (15.83, 38.62), (15.90, 38.43), (15.85, 38.36), (15.80, 38.29), (15.71, 38.25), (15.64, 38.22),
         (15.65, 38.11), (15.68, 37.95), (15.75, 37.92), (16.06, 37.92), (16.15, 38.09), (16.26, 38.24), (16.40, 38.32), (16.55, 38.69),
         (16.60, 38.82), (17.02, 38.91), (17.20, 39.03), (17.13, 39.08), (17.13, 39.37), (16.96, 39.50), (16.53, 39.73), (16.53, 39.87),
         (16.69, 40.20), (16.85, 40.37), (17.24, 40.47), (17.89, 40.25), (17.99, 40.06), (18.36, 39.80), (18.49, 40.15), (18.30, 40.39),
         (17.95, 40.64), (17.30, 40.95), (16.87, 41.13), (16.60, 41.20), (16.28, 41.32), (16.15, 41.38), (15.92, 41.63), (16.05, 41.71),
         (16.18, 41.88), (16.02, 41.95), (15.88, 41.93), (15.40, 41.92), (15.00, 42.00), (14.71, 42.12), (14.55, 42.60)]
SICILY = [(12.51, 38.02), (12.73, 38.18), (12.88, 38.03), (13.10, 38.20), (13.36, 38.12), (13.70, 37.98), (14.02, 38.04),
          (14.36, 38.02), (14.75, 38.15), (14.96, 38.14), (15.24, 38.22), (15.65, 38.27), (15.55, 38.19), (15.29, 37.85),
          (15.21, 37.73), (15.09, 37.50), (15.22, 37.23), (15.29, 37.07), (15.14, 36.91), (15.14, 36.69), (14.85, 36.73),
          (14.43, 36.89), (14.25, 37.07), (13.94, 37.10), (13.52, 37.29), (13.08, 37.51), (12.82, 37.58), (12.59, 37.65), (12.44, 37.80)]
SARDINIA = [(9.15, 41.24), (9.19, 41.24), (9.38, 41.18), (9.52, 41.15), (9.55, 40.92), (9.73, 40.84), (9.75, 40.58), (9.72, 40.38),
            (9.65, 40.28), (9.70, 39.94), (9.67, 39.83), (9.63, 39.30), (9.52, 39.10), (9.11, 39.21), (9.00, 38.98), (8.85, 38.88),
            (8.64, 38.87), (8.40, 39.00), (8.38, 39.20), (8.40, 39.45), (8.45, 39.75), (8.55, 39.88), (8.38, 40.04), (8.47, 40.30),
            (8.30, 40.56), (8.16, 40.57), (8.22, 40.94), (8.40, 40.84), (8.71, 40.91), (8.87, 41.01)]
CORSICA = [(9.16, 41.39), (9.28, 41.59), (9.40, 41.86), (9.50, 42.10), (9.55, 42.60), (8.60, 42.60), (8.60, 42.13), (8.74, 41.92),
           (8.66, 41.74), (8.90, 41.67), (8.98, 41.49)]
AFRICA = [(7.60, 36.93), (7.79, 36.97), (8.25, 36.95), (8.44, 36.90), (8.76, 36.96), (9.09, 37.11), (9.22, 37.23), (9.45, 37.17),
          (9.85, 37.34), (9.87, 37.27), (10.05, 37.25), (10.19, 37.17), (10.28, 37.18), (10.15, 37.06), (10.33, 36.88), (10.31, 36.81),
          (10.27, 36.77), (10.34, 36.73), (10.48, 36.71), (10.90, 37.02), (11.04, 37.08), (11.11, 36.85), (10.86, 36.57), (10.74, 36.45),
          (10.61, 36.40), (10.51, 36.03), (10.64, 35.83), (10.83, 35.77), (11.06, 35.50), (11.15, 35.24), (11.11, 35.23), (10.76, 34.74),
          (10.50, 34.20), (7.60, 34.20)]
ISLANDS = [(14.43, 35.89, 0.13, 0.06), (14.25, 36.04, 0.07, 0.035), (11.97, 36.79, 0.07, 0.045), (12.58, 35.51, 0.06, 0.025),
           (12.33, 37.93, 0.035, 0.03), (12.06, 37.96, 0.03, 0.025), (14.95, 38.47, 0.05, 0.035), (14.85, 38.57, 0.03, 0.025),
           (15.22, 38.79, 0.03, 0.025), (13.18, 38.71, 0.025, 0.02), (13.92, 40.73, 0.04, 0.03), (14.24, 40.55, 0.03, 0.02),
           (12.96, 40.90, 0.03, 0.02)]
TOWNS = [("TUNIS", 10.18, 36.80, "r"), ("BIZERTE", 9.87, 37.27, "l"), ("SOUSSE", 10.64, 35.83, "l"), ("KASSERINE", 8.84, 35.17, "r"),
         ("PALERMO", 13.36, 38.12, "r"), ("TRAPANI", 12.51, 38.02, "l"), ("MESSINA", 15.55, 38.19, "l"), ("CATANIA", 15.09, 37.50, "r"),
         ("SYRACUSE", 15.29, 37.07, "r"), ("GELA", 14.25, 37.07, "r"), ("LICATA", 13.94, 37.10, "l"),
         ("NAPLES", 14.25, 40.84, "l"), ("SALERNO", 14.76, 40.68, "r"), ("ROME", 12.50, 41.90, "r"), ("ANZIO", 12.63, 41.45, "l"),
         ("CASSINO", 13.83, 41.49, "r"), ("FOGGIA", 15.55, 41.46, "r"), ("BARI", 16.87, 41.13, "l"), ("TARANTO", 17.24, 40.47, "l"),
         ("REGGIO", 15.65, 38.11, "r"), ("CAGLIARI", 9.11, 39.21, "r")]
REGIONS = [("TUNISIA", 8.85, 35.95, -100), ("SICILY", 13.40, 37.75, 110), ("ITALY", 16.70, 40.75, 120),
           ("SARDINIA", 8.95, 40.10, 90), ("CORSICA", 9.05, 41.92, 64), ("MALTA", 14.43, 35.70, 60),
           ("TYRRHENIAN  SEA", 12.30, 39.60, 104), ("MEDITERRANEAN  SEA", 12.60, 35.30, 104), ("IONIAN  SEA", 17.60, 37.55, 104),
           ("ADRIATIC  SEA", 17.75, 41.85, 84)]
# campaign markers (make_newgame3d.py): the stock briefing room's three campaigns
MARKERS = {"tunisia": (9.15, 36.40), "sicily": (14.45, 37.35), "italy": (14.95, 41.20)}


def coast(poly, seed_, closed_off=False):
    rr_ = random.Random(seed_)
    pts_ = [P(*q) for q in poly]
    out = []
    n = len(pts_)
    for i in range(n):
        p0, p1, p2, p3 = pts_[i - 1], pts_[i], pts_[(i + 1) % n], pts_[(i + 2) % n]
        for k in range(10):
            t_ = k / 10
            t2, t3 = t_ * t_, t_ * t_ * t_
            x_ = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t_ + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y_ = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t_ + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x_, y_))
    wob = []
    for i, (x_, y_) in enumerate(out):
        xa, ya = out[i - 1]
        xb, yb = out[(i + 1) % len(out)]
        nx_, ny_ = -(yb - ya), (xb - xa)
        ln = math.hypot(nx_, ny_) or 1
        j = 4 * math.sin(i * 0.9 + seed_) + 3 * math.sin(i * 2.7) + rr_.uniform(-2, 2)
        wob.append((x_ + nx_ / ln * j, y_ + ny_ / ln * j))
    return wob


parch = fbm(H, W, 7, 3, 1)
stain = fbm(H, W, 4, 2, 2)
base = np.array([196, 168, 112], np.float32)
sea = np.array([128, 140, 138], np.float32)
img = np.ones((H, W, 3), np.float32) * sea * (0.86 + 0.2 * parch[..., None]) * (0.9 + 0.15 * stain[..., None])
im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
landm = Image.new("L", (W, H), 0)
ld = ImageDraw.Draw(landm)
for k_, poly in enumerate((ITALY, SICILY, SARDINIA, CORSICA, AFRICA)):
    ld.polygon(coast(poly, 7 + k_), fill=255)
ri = random.Random(4)
for k_, (lo, la, rx, ry) in enumerate(ISLANDS):
    poly = [(lo + rx * math.cos(a_) * ri.uniform(0.8, 1.15), la + ry * math.sin(a_) * ri.uniform(0.8, 1.15)) for a_ in [2 * math.pi * q / 10 for q in range(10)]]
    ld.polygon(coast(poly, 20 + k_), fill=255)
landm = landm.filter(ImageFilter.GaussianBlur(3)).point(lambda v: 255 if v > 128 else 0)
landimg = Image.fromarray(np.clip(base * (0.84 + 0.3 * parch[..., None]) * (0.9 + 0.15 * stain[..., None]), 0, 255).astype(np.uint8))
im.paste(landimg, (0, 0), landm)
# relief: hatched contour rings inland (the Apennines, Etna, the Tunisian Dorsal) from a height field that is 0 at the coast
hill = fbm(H, W, 5, 3, 17) * (np.asarray(landm.filter(ImageFilter.GaussianBlur(50)), np.float32) / 255)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
for lo, la, s, a in ((15.0, 37.75, 70, 0.55), (15.6, 40.6, 160, 0.30), (14.4, 41.5, 150, 0.30), (16.2, 39.3, 110, 0.25), (8.9, 35.6, 150, 0.25)):
    ex, ey = P(lo, la)
    hill += a * np.exp(-(((xx - ex) ** 2 + (yy - ey) ** 2) / (2 * s ** 2)))
hill *= (np.asarray(landm, np.float32) / 255)
for lv in (0.35, 0.45, 0.55, 0.7):
    e2 = Image.fromarray((hill > lv).astype(np.uint8) * 255).filter(ImageFilter.FIND_EDGES)
    im.paste(Image.new("RGB", (W, H), (135, 100, 60)), (0, 0), e2.point(lambda v: 90 if v else 0))
cst = landm.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5))
im.paste(Image.new("RGB", (W, H), (60, 44, 28)), (0, 0), cst.point(lambda v: 190 if v else 0))
d = ImageDraw.Draw(im, "RGBA")
# the military grid, labelled along the edges (numbers only, as the shipped map)
fg = font("arialbd.ttf", 34)
for k, x in enumerate(range(0, W, 256)):
    d.line([(x, 0), (x, H)], fill=(80, 60, 40, 60), width=3)
    d.text((x + 8, 8), "%02d" % (40 + k), font=fg, fill=(70, 52, 34, 200))
for k, y in enumerate(range(0, H, 256)):
    d.line([(0, y), (W, y)], fill=(80, 60, 40, 60), width=3)
    d.text((8, y + 8), "%02d" % (60 - k), font=fg, fill=(70, 52, 34, 200))
land_np = np.asarray(landm) > 0
er_np = np.asarray(landm.filter(ImageFilter.MinFilter(13))) > 0


def arrow(lo, la, dx, dy, col):
    x, y = P(lo, la)
    d.line([(x + dx, y + dy), (x, y)], fill=col, width=16)
    ang = math.atan2(-dy, -dx)
    tip = [(x, y), (x - 60 * math.cos(ang - 0.45), y - 60 * math.sin(ang - 0.45)), (x - 60 * math.cos(ang + 0.45), y - 60 * math.sin(ang + 0.45))]
    d.polygon(tip, fill=col)


# front lines in red grease pencil: Tunisia (February 1943, the Eastern Dorsal down to Kasserine), Sicily (the August Etna line),
# Italy (the Gustav Line, Garigliano - Cassino - the Sangro)
RED = (150, 30, 25, 205)
for line in ([(9.66, 37.10), (9.60, 36.65), (9.50, 36.25), (9.70, 35.75), (9.62, 35.30), (9.55, 34.95), (9.10, 34.70)],
             [(14.60, 38.05), (14.62, 37.90), (14.60, 37.79), (14.83, 37.66), (15.02, 37.55), (15.09, 37.48)],
             [(13.76, 41.24), (13.80, 41.40), (13.83, 41.49), (14.00, 41.65), (14.20, 41.85), (14.45, 42.10), (14.55, 42.25)]):
    d.line([P(*q) for q in line], fill=RED, width=12, joint="curve")
# landings: Sicily 10 July 1943 (US blue from the south, British red from the south-east), Salerno 9 September 1943, Anzio 22 January 1944
for lo, la in ((13.94, 37.08), (14.25, 37.05), (14.45, 36.88)):
    arrow(lo, la, 0, 230, (40, 60, 130, 210))
for lo, la in ((15.12, 36.70), (15.14, 36.90), (15.28, 37.05)):
    arrow(lo, la, 150, 180, (150, 30, 25, 210))
for lo, la in ((14.88, 40.52), (14.98, 40.40)):
    arrow(lo, la, -230, 150, (40, 60, 130, 210))
arrow(12.65, 41.43, -230, 150, (40, 60, 130, 210))
ft = font("arialbd.ttf", 62)
for n, lo, la, side in TOWNS:
    x, y = P(lo, la)
    if not er_np[int(y), int(x)]:            # coastal towns: the dot moves onto the land (nearest point 6 px inside the coast)
        x0, y0 = max(0, int(x) - 160), max(0, int(y) - 160)
        ys, xs = np.nonzero(er_np[y0:int(y) + 160, x0:int(x) + 160])
        assert len(xs), n + " is far out at sea"
        k = np.argmin((xs + x0 - x) ** 2 + (ys + y0 - y) ** 2)
        x, y = float(x0 + xs[k]), float(y0 + ys[k])
    d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(40, 30, 20, 235))
    tw_ = d.textlength(n, font=ft)
    if side == "l":
        d.text((x - 24 - tw_, y - 34), n, font=ft, fill=(40, 30, 20, 225))
    elif side == "b":
        d.text((x - tw_ / 2, y + 20), n, font=ft, fill=(40, 30, 20, 225))
    else:
        d.text((x + 24, y - 34), n, font=ft, fill=(40, 30, 20, 225))
for n, lo, la, px in REGIONS:
    x, y = P(lo, la)
    f = font("georgiab.ttf", abs(px))
    sp = " ".join(n) if px > 0 else n            # px < 0: unspaced (a tight spot)
    px = abs(px)
    tw_ = d.textlength(sp, font=f)
    sea_ = "SEA" in n
    d.text((x - tw_ / 2, y - px / 2), sp, font=f, fill=(52, 66, 78, 170) if sea_ else (78, 52, 30, 170))
v = np.asarray(im, np.float32)
vig = 1 - 0.30 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
v *= np.clip(vig, 0.55, 1)[..., None]
Image.fromarray(np.clip(v, 0, 255).astype(np.uint8)).save(OUT)
mk = {k: {"lonlat": v_, "uv": [P(*v_)[0] / W, 1.0 - P(*v_)[1] / H]} for k, v_ in MARKERS.items()}
for k, m in mk.items():
    x, y = P(*m["lonlat"])
    assert land_np[int(y), int(x)], k + " marker in the sea"
json.dump({"lon": [LON0, LON1], "lat": [LAT0, LAT1], "markers": mk}, open(os.path.splitext(OUT)[0] + "_markers.json", "w"), indent=1)
print("theatre map", OUT, "lon %.2f-%.2f lat %.2f-%.2f" % (LON0, LON1, LAT0, LAT1))
