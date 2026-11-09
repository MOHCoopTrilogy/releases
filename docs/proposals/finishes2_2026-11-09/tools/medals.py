"""US WWII awards and badges as clean vector decals for the Customize bench (US government insignia: public domain).
Drawn at 4x and downsampled; written to assets/decals/<name>.png (RGBA). Shapes and colours after the regulation patterns:
  moh_army      Medal of Honor, Army 1944: light-blue neck pad with 13 white stars, eagle on the VALOR bar, inverted gold star
                over a green laurel wreath, oak leaves in the points, centre disc
  purple_heart  purple heart in a gold border, profile bust, arms shield between green sprigs, purple ribbon with white edges
  silver_star   gilt star with a small silver star in a laurel wreath; blue / white / red ribbon
  bronze_star   bronze star with a small raised star; red ribbon, blue centre stripe edged white, white edges
  cib           Combat Infantryman Badge: M1903 rifle on a light-blue bar over an oak wreath, silver
  jump_wings    Parachutist Badge: silver open parachute between upswept wings
    python medals.py
"""
import math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets', 'decals')
K = 4
GOLD = ((214, 176, 62), (150, 112, 32), (248, 222, 140))
SILV = ((196, 200, 206), (112, 116, 124), (238, 240, 244))
BRNZ = ((178, 120, 60), (106, 68, 32), (218, 166, 104))
WHITE, OUTL = (246, 246, 242), (40, 34, 26)


def canvas(w, h):
    im = Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def done(im, name):
    w, h = im.size
    im = im.resize((w * 2 // K, h * 2 // K), Image.LANCZOS)          # 2x: the bench exports up to 512 without upscaling
    im.save(os.path.join(OUT, name + '.png'))
    return im


def P(pts):
    return [(x * K, y * K) for x, y in pts]


def star(cx, cy, R, r, rot=-90):
    return [(cx + (R if i % 2 == 0 else r) * math.cos(math.radians(rot + 36 * i)),
             cy + (R if i % 2 == 0 else r) * math.sin(math.radians(rot + 36 * i))) for i in range(10)]


def metal(d, pts, pal, w=2):
    """a raised metal shape: dark rim, base, and a lighter inset toward the upper left (struck-medal bevel)"""
    base, dark, light = pal
    d.polygon(P(pts), fill=dark)
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    inner = [(cx + (x - cx) * 0.9, cy + (y - cy) * 0.9) for x, y in pts]
    d.polygon(P(inner), fill=base)
    hi = [(cx + (x - cx) * 0.62 - 1.0, cy + (y - cy) * 0.62 - 1.0) for x, y in pts]
    d.polygon(P(hi), fill=light)
    hi2 = [(cx + (x - cx) * 0.5, cy + (y - cy) * 0.5) for x, y in pts]
    d.polygon(P(hi2), fill=base)


def ribbon(d, x0, y0, w, h, stripes):
    """vertical stripes, widths in parts; a thin dark outline and a soft fold shadow at the bottom"""
    tot = sum(a for a, _ in stripes)
    x = x0
    for a, col in stripes:
        ww = w * a / tot
        d.rectangle(P([(x, y0), (x + ww, y0 + h)]), fill=col)
        x += ww
    d.rectangle(P([(x0, y0), (x0 + w, y0 + h)]), outline=(30, 30, 30), width=K)
    d.rectangle(P([(x0, y0 + h - 3), (x0 + w, y0 + h)]), fill=(0, 0, 0, 70))


def leaf(d, cx, cy, ang, L, W, col, edge):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(13):
        t = i / 12
        x = -L / 2 + L * t
        y = W / 2 * math.sin(math.pi * t)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    for i in range(13):
        t = 1 - i / 12
        x = -L / 2 + L * t
        y = -W / 2 * math.sin(math.pi * t)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    d.polygon(P(pts), fill=col, outline=edge)


def wreath_ring(d, cx, cy, R, n, col, edge, L=11, W=5):
    for i in range(n):
        a = 2 * math.pi * i / n
        for off in (-0.16, 0.16):
            x = cx + R * math.cos(a) + off * L * math.cos(a)
            y = cy + R * math.sin(a) + off * L * math.sin(a)
            leaf(d, x, y, a + math.pi / 2 + (0.55 if off > 0 else -0.55), L, W, col, edge)


def font(sz):
    for f in ('arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(os.path.join('C:' + os.sep, 'Windows', 'Fonts', f), sz * K)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------------------------------------------- awards
def moh_army():
    W, H = 200, 300
    im, d = canvas(W, H)
    # the light-blue octagonal neck pad, 13 white stars (4-5-4)
    pad = [(60, 6), (140, 6), (156, 22), (156, 70), (140, 86), (60, 86), (44, 70), (44, 22)]
    d.polygon(P(pad), fill=(118, 170, 222), outline=(36, 70, 120))
    d.line(P(pad + pad[:1]), fill=(36, 70, 120), width=2 * K)
    for row, (n, y) in enumerate(((4, 27), (5, 46), (4, 65))):
        for i in range(n):
            x = 100 + (i - (n - 1) / 2) * 20
            d.polygon(P(star(x, y, 7, 2.8)), fill=WHITE)
    # neck ribbon ends
    d.rectangle(P([(88, 86), (112, 100)]), fill=(118, 170, 222), outline=(36, 70, 120))
    # eagle with spread wings standing on the VALOR bar
    ex, ey, s = 100, 150, 54
    wing = [(-0.10, -0.45), (-0.40, -0.80), (-0.95, -0.98), (-0.82, -0.72), (-0.98, -0.62), (-0.80, -0.48), (-0.92, -0.36),
            (-0.66, -0.26), (-0.72, -0.12), (-0.40, -0.10), (-0.14, -0.18)]
    body = [(-0.14, -0.18), (-0.18, 0.02), (-0.06, 0.12), (0.06, 0.12), (0.18, 0.02), (0.14, -0.18)]
    for sgn in (-1, 1):
        pts = [(ex + sgn * x * s, ey + y * s) for x, y in wing]
        d.polygon(P(pts), fill=GOLD[0], outline=GOLD[1])
        d.line(P(pts + pts[:1]), fill=GOLD[1], width=K)
        for (x0, y0), (x1, y1) in (((-0.82, -0.72), (-0.30, -0.42)), ((-0.80, -0.48), (-0.26, -0.30)), ((-0.66, -0.26), (-0.22, -0.20))):
            d.line(P([(ex + sgn * x0 * s, ey + y0 * s), (ex + sgn * x1 * s, ey + y1 * s)]), fill=GOLD[1], width=K)
        d.line(P([(ex + sgn * 0.16 * s, ey - 0.47 * s), (ex + sgn * 0.88 * s, ey - 0.93 * s)]), fill=GOLD[2], width=2 * K)
    metal(d, [(ex + x * s, ey + y * s) for x, y in body] + [(ex + 0.1 * s, ey - 0.46 * s), (ex - 0.1 * s, ey - 0.46 * s)], GOLD)
    d.ellipse(P([(ex - 0.11 * s, ey - 0.62 * s), (ex + 0.11 * s, ey - 0.40 * s)]), fill=GOLD[0], outline=GOLD[1], width=K)
    d.polygon(P([(ex - 0.10 * s, ey - 0.54 * s), (ex - 0.22 * s, ey - 0.50 * s), (ex - 0.09 * s, ey - 0.47 * s)]), fill=GOLD[1])
    # the bar
    bx0, by0, bx1, by1 = 50, ey + 0.12 * s, 150, ey + 0.12 * s + 20
    d.rectangle(P([(bx0, by0), (bx1, by1)]), fill=GOLD[1])
    d.rectangle(P([(bx0 + 2, by0 + 2), (bx1 - 2, by1 - 2)]), fill=GOLD[0])
    for x in (bx0 + 5, bx1 - 5):
        d.ellipse(P([(x - 2.5, (by0 + by1) / 2 - 2.5), (x + 2.5, (by0 + by1) / 2 + 2.5)]), fill=GOLD[2])
    f = font(13)
    tw = d.textlength('VALOR', font=f) / K
    d.text(P([(100 - tw / 2, by0 + 2)])[0], 'VALOR', font=f, fill=(92, 64, 16))
    # link + the inverted star over the green laurel wreath
    cy = by1 + 62
    d.rectangle(P([(97, by1), (103, by1 + 10)]), fill=GOLD[1])
    wreath_ring(d, 100, cy + 2, 37, 24, (54, 128, 66), (24, 70, 34), L=15, W=7)
    pts = star(100, cy, 56, 22, rot=90)
    metal(d, pts, GOLD)
    for i in range(5):                            # an oak leaf in every point
        a = math.radians(90 + 72 * i)
        leaf(d, 100 + 38 * math.cos(a), cy + 38 * math.sin(a), a, 15, 6, (56, 130, 70), (24, 70, 34))
    d.ellipse(P([(100 - 17, cy - 17), (100 + 17, cy + 17)]), fill=GOLD[1])
    d.ellipse(P([(100 - 14, cy - 14), (100 + 14, cy + 14)]), fill=GOLD[0])
    d.ellipse(P([(100 - 9, cy - 9), (100 + 9, cy + 9)]), fill=GOLD[2], outline=GOLD[1], width=K)
    return done(im, 'moh_army')


def heart_pts(cx, cy, s):
    pts = []
    for i in range(120):
        t = 2 * math.pi * i / 120
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts


def purple_heart():
    W, H = 180, 260
    im, d = canvas(W, H)
    ribbon(d, 50, 4, 80, 74, [(1, WHITE), (8, (98, 34, 120)), (1, WHITE)])
    d.rectangle(P([(84, 78), (96, 92)]), fill=GOLD[1])
    cx, cy = 90, 168
    d.polygon(P(heart_pts(cx, cy, 4.9)), fill=GOLD[1])
    d.polygon(P(heart_pts(cx, cy - 1, 4.6)), fill=GOLD[0])
    d.polygon(P(heart_pts(cx, cy, 3.95)), fill=(108, 38, 132))
    # the arms above: a small white shield with red bars and stars, between green sprigs
    sx, sy = cx, 106
    for sgn in (-1, 1):
        for k in range(4):
            leaf(d, sx + sgn * (14 + 5 * k), sy + 2 - 2 * k, math.radians(-90 + sgn * 60), 9, 4, (60, 130, 60), (26, 70, 30))
    sh = [(sx - 9, sy - 9), (sx + 9, sy - 9), (sx + 9, sy + 2), (sx, sy + 11), (sx - 9, sy + 2)]
    d.polygon(P(sh), fill=WHITE, outline=GOLD[1])
    for y in (sy - 1, sy + 4):
        d.rectangle(P([(sx - 8, y), (sx + 8, y + 2)]), fill=(178, 34, 40))
    for x in (sx - 5, sx, sx + 5):
        d.polygon(P(star(x, sy - 6, 2.2, 0.9)), fill=(178, 34, 40))
    # the profile bust (facing left), struck in gold
    bust = [(98, 130), (90, 128), (84, 131), (80, 137), (79, 142), (76, 147), (79, 149), (78, 153), (80, 156), (79, 160),
            (83, 163), (86, 165), (87, 171), (84, 176), (78, 180), (74, 187), (72, 196), (110, 196), (110, 188), (104, 180),
            (106, 172), (109, 164), (110, 152), (108, 140), (104, 133)]
    d.polygon(P(bust), fill=GOLD[1])
    d.polygon(P([(x + 1.0, y + 0.6) for x, y in bust][:-3]), fill=GOLD[0])
    d.line(P([(96, 140), (104, 146), (106, 156)]), fill=GOLD[1], width=K)            # hair / queue line
    d.ellipse(P([(101, 150), (106, 157)]), fill=GOLD[1])
    return done(im, 'purple_heart')


def star_medal(name, pal, ribbon_stripes, inner):
    W, H = 180, 250
    im, d = canvas(W, H)
    ribbon(d, 50, 4, 80, 74, ribbon_stripes)
    d.rectangle(P([(84, 78), (96, 96)]), fill=pal[1])
    d.ellipse(P([(84, 88), (96, 100)]), outline=pal[1], width=3 * K)
    cx, cy = 90, 164
    metal(d, star(cx, cy, 62, 25), pal)
    for i in range(5):                             # ridges down each point
        a = math.radians(-90 + 72 * i)
        d.line(P([(cx + 20 * math.cos(a), cy + 20 * math.sin(a)), (cx + 58 * math.cos(a), cy + 58 * math.sin(a))]),
               fill=pal[1], width=K)
    inner(d, cx, cy)
    return done(im, name)


def silver_star():
    BL, RD = (32, 52, 128), (184, 32, 40)

    def inner(d, cx, cy):
        wreath_ring(d, cx, cy, 15, 12, GOLD[0], GOLD[1], L=8, W=3.5)
        metal(d, star(cx, cy, 11, 4.5), SILV)
    return star_medal('silver_star', GOLD, [(1, BL), (1, WHITE), (5, BL), (1, WHITE), (4, RD), (1, WHITE), (5, BL), (1, WHITE),
                                           (1, BL)], inner)


def bronze_star():
    RD, BL = (172, 30, 40), (32, 52, 128)

    def inner(d, cx, cy):
        metal(d, star(cx, cy, 15, 6), BRNZ)
    return star_medal('bronze_star', BRNZ, [(1, WHITE), (14, RD), (1, WHITE), (3, BL), (1, WHITE), (14, RD), (1, WHITE)], inner)


# ---------------------------------------------------------------------------------------------------------------- badges
def cib():
    W, H = 300, 140
    im, d = canvas(W, H)
    # oak wreath: an elliptical arc hanging under the bar, end to end, leaves in pairs along it, tied at the bottom
    cx, cy, rx, ry = 150, 44, 124, 76
    n = 26
    for i in range(n):
        t = math.radians(188 + (352 - 188) * i / (n - 1))
        x, y = cx + rx * math.cos(t), cy - ry * math.sin(t)
        a = math.atan2(ry * math.cos(t), -rx * math.sin(t)) if False else math.atan2(-ry * math.cos(t), -rx * math.sin(t))
        for off in (-1, 1):
            leaf(d, x + off * 5 * math.sin(a), y - off * 5 * math.cos(a), a + off * 0.55, 17, 8, SILV[0], SILV[1])
    d.ellipse(P([(cx - 8, cy + ry - 8), (cx + 8, cy + ry + 6)]), fill=SILV[2], outline=SILV[1], width=K)
    # the blue enamel bar with its silver rim
    d.rectangle(P([(12, 22), (288, 62)]), fill=SILV[1])
    d.rectangle(P([(15, 25), (285, 59)]), fill=SILV[2])
    d.rectangle(P([(20, 30), (280, 54)]), fill=(98, 152, 204))
    # the M1903 rifle, muzzle to the left: barrel, upper band, stock with a straight wrist and a butt
    r = [(24, 40), (150, 39), (150, 37), (196, 37), (206, 35), (216, 37), (232, 38), (252, 40), (272, 39), (278, 41),
         (278, 50), (262, 50), (244, 47), (228, 46), (222, 49), (214, 49), (206, 46), (150, 45), (60, 44), (24, 43)]
    d.polygon(P(r), fill=SILV[2], outline=SILV[1])
    d.line(P([(60, 44), (150, 45)]), fill=SILV[1], width=K)                                  # stock line under the barrel
    d.rectangle(P([(96, 38), (100, 45)]), fill=SILV[1])                                      # band
    d.rectangle(P([(198, 32), (204, 36)]), fill=SILV[2], outline=SILV[1])                    # rear sight
    d.line(P([(200, 37), (194, 32), (190, 33)]), fill=SILV[1], width=2 * K)                  # bolt handle
    d.arc(P([(206, 43), (220, 53)]), 0, 180, fill=SILV[1], width=K)                          # trigger guard
    d.rectangle(P([(26, 37), (29, 40)]), fill=SILV[1])                                       # front sight
    return done(im, 'cib')


def jump_wings():
    W, H = 300, 120
    im, d = canvas(W, H)
    cx = 150
    for sgn in (-1, 1):
        # one smooth wing: upper edge rising to a raised tip, lower edge of rounded feather ends, two feather rows inside
        up = [(cx + sgn * (14 + 128 * t), 76 - 54 * t ** 1.6) for t in [i / 20 for i in range(21)]]
        low = []
        nf = 9
        for k in range(nf, -1, -1):
            t = k / nf
            x = cx + sgn * (14 + 124 * t)
            y = 76 - 54 * t ** 1.6 + 32 * (1 - t) + 10
            low.append((x, y))
            if k > 0:
                tm = (k - 0.5) / nf
                low.append((cx + sgn * (14 + 124 * tm), 76 - 54 * tm ** 1.6 + 32 * (1 - tm) + 14))
        pts = up + low
        d.polygon(P(pts), fill=SILV[0], outline=SILV[1])
        for f in (0.33, 0.66):                                   # feather-row lines
            row = [(cx + sgn * (14 + 126 * t), 76 - 54 * t ** 1.6 + (32 * (1 - t) + 11) * f) for t in [i / 20 for i in range(21)]]
            d.line(P(row), fill=SILV[1], width=K)
        for k in range(1, nf):                                   # feather separations
            t = k / nf
            x = cx + sgn * (14 + 124 * t)
            y0 = 76 - 54 * t ** 1.6
            d.line(P([(x - sgn * 3, y0 + 2), (x, y0 + 32 * (1 - t) + 10)]), fill=SILV[1], width=K)
        hl = [(cx + sgn * (16 + 120 * t), 77 - 54 * t ** 1.6 + 2) for t in [i / 20 for i in range(21)]]
        d.line(P(hl), fill=SILV[2], width=2 * K)
    # parachute: canopy with gores and a scalloped skirt, shroud lines down to the risers
    top, skirt, half = 6, 46, 28
    can = [(cx + half * math.cos(math.radians(a)), skirt - (skirt - top) * math.sin(math.radians(a))) for a in range(0, 181, 6)]
    sc = []
    for k in range(6):
        x0 = cx - half + k * (2 * half / 6)
        for j in range(7):
            t = j / 6
            sc.append((x0 + t * 2 * half / 6, skirt + 4 * math.sin(math.pi * t)))
    d.polygon(P(can + sc), fill=SILV[2], outline=SILV[1])
    for k in range(1, 6):
        x = cx - half + k * (2 * half / 6)
        d.line(P([(cx + (x - cx) * 0.25, top + 2), (x, skirt + 1)]), fill=SILV[1], width=K)
    bot = (cx, 96)
    for k in range(7):
        x = cx - half + k * (2 * half / 6)
        d.line(P([(x, skirt + 2), bot]), fill=SILV[1], width=K)
    d.rectangle(P([(cx - 4, 92), (cx + 4, 106)]), fill=SILV[0], outline=SILV[1])
    return done(im, 'jump_wings')


def smooth(pts, n=8, closed=False):
    """Catmull-Rom through the points: hand-placed outline points -> a clean curve (no faceted polygon)"""
    out = []
    m = len(pts)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = pts[(i - 1) % m] if closed or i > 0 else pts[i]
        p1, p2 = pts[i], pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if closed or i + 2 < m else p2
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


def ab101():
    """101st Airborne shoulder sleeve insignia (US Army SSI, public domain): black shield with a white eagle's head facing
    left, gold beak open on a red tongue, under a black arched AIRBORNE tab with gold letters"""
    W, H = 220, 290
    im, d = canvas(W, H)
    BLACK, GOLDL, RED = (22, 22, 22), (238, 196, 60), (196, 34, 36)
    cx = 110
    # the arched tab
    R0, R1, cy0 = 150, 182, 196
    tab = [(cx + R1 * math.cos(math.radians(a)), cy0 - R1 * math.sin(math.radians(a))) for a in range(118, 61, -2)]
    tab += [(cx + R0 * math.cos(math.radians(a)), cy0 - R0 * math.sin(math.radians(a))) for a in range(62, 119, 2)]
    d.polygon(P(tab), fill=BLACK, outline=GOLDL)
    d.line(P(tab + tab[:1]), fill=(70, 70, 70), width=K)
    f = font(21)
    word = 'AIRBORNE'
    span = 40.0
    adv = [d.textlength(ch, font=f) / K + 2.5 for ch in word]        # letters spaced by their own widths
    tot = sum(adv)
    acc = 0.0
    for i, ch in enumerate(word):
        a = math.radians(90 + span / 2 - span * (acc + adv[i] / 2) / tot)
        acc += adv[i]
        r = (R0 + R1) / 2 - 1
        x, y = cx + r * math.cos(a), cy0 - r * math.sin(a)
        g = Image.new('RGBA', (40 * K, 40 * K), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        tw = gd.textlength(ch, font=f)
        gd.text((20 * K - tw / 2, 20 * K - 12 * K), ch, font=f, fill=GOLDL)
        g = g.rotate(math.degrees(a) - 90, resample=Image.BICUBIC)
        im.alpha_composite(g, (int(x * K - 20 * K), int(y * K - 20 * K)))
    # the shield: arched top, straight sides, curving to a point
    top = [(cx + 90 * math.cos(math.radians(a)), 70 - 14 * math.sin(math.radians(a))) for a in range(180, -1, -5)]
    right = [(200, 70), (200, 170)] + [(cx + 90 * math.cos(math.radians(a)), 170 + 104 * math.sin(math.radians(a)) ** 1.4)
                                       for a in range(0, 91, 5)]
    left = [(cx - 90 * math.cos(math.radians(a)), 170 + 104 * math.sin(math.radians(a)) ** 1.4) for a in range(90, -1, -5)]
    shield = top + right + left + [(20, 70)]
    d.polygon(P(shield), fill=BLACK)
    d.line(P(shield + shield[:1]), fill=(70, 70, 70), width=2 * K)
    # the eagle's head (a 100-unit design box mapped onto the shield), facing left
    ox, oy, sc = 34, 66, 1.58

    def T(pts):
        return [(ox + x * sc, oy + y * sc) for x, y in pts]
    head = [(22, 96), (22, 78), (25, 64), (29, 56), (31, 52), (33, 46), (32, 38), (36, 28), (46, 20), (58, 18), (68, 22),
            (76, 32), (80, 46), (82, 62), (86, 80), (92, 96)]
    serr = []
    for k in range(8):                                   # feather tips along the bottom of the neck
        x0 = 92 - k * (70 / 8)
        serr += [(x0 - 3, 106 - (k % 2) * 3), (x0 - 8.75, 96)]
    d.polygon(P(T(smooth(head) + serr)), fill=WHITE)
    # beak: upper mandible hooked, lower open, red tongue between
    upper = smooth([(36, 34), (25, 35), (14, 39), (7, 46), (6, 54)]) + smooth([(6, 54), (11, 50), (18, 47), (27, 47), (35, 49), (38, 42), (36, 34)])
    lower = smooth([(33, 53), (24, 55), (15, 59), (11, 64)]) + smooth([(11, 64), (19, 62), (27, 60), (34, 58)])
    tongue = smooth([(33, 49), (22, 51), (14, 56)]) + smooth([(14, 56), (23, 56), (33, 54)])
    d.polygon(P(T(tongue)), fill=RED)
    d.polygon(P(T(upper)), fill=GOLDL, outline=BLACK)
    d.polygon(P(T(lower)), fill=GOLDL, outline=BLACK)
    d.line(P(T([(26, 41), (33, 42)])), fill=BLACK, width=K)                      # nostril
    # eye and brow
    ex, ey = T([(42, 36)])[0]
    d.ellipse(P([(ex - 3.6, ey - 3.6), (ex + 3.6, ey + 3.6)]), fill=BLACK)
    d.ellipse(P([(ex - 1.2, ey - 2.2), (ex + 0.4, ey - 0.6)]), fill=WHITE)
    d.line(P(T([(35, 31), (43, 30), (52, 33)])), fill=BLACK, width=2 * K)
    # neck feather lines
    for (x0, y0), (x1, y1), (x2, y2) in (((50, 48), (56, 62), (54, 78)), ((62, 44), (68, 60), (68, 80)),
                                         ((40, 62), (44, 74), (42, 88)), ((72, 56), (76, 72), (80, 88))):
        d.line(P(T([(x0, y0), (x1, y1), (x2, y2)])), fill=(120, 120, 120), width=K)
    return done(im, 'ab101')


ALL = [ab101, moh_army, purple_heart, silver_star, bronze_star, cib, jump_wings]

if __name__ == '__main__':
    ims = [f() for f in ALL]
    W = sum(i.width + 16 for i in ims) + 16
    H = max(i.height for i in ims) + 32
    sh = Image.new('RGB', (W, H), (64, 66, 70))
    x = 16
    for i in ims:
        sh.paste(i, (x, 16), i)
        x += i.width + 16
    sh.save(os.path.join(HERE, '..', 'media', 'medals_sheet.png'))
    print('wrote', len(ims))
