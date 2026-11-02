"""gen_srboard.py <out dir> - the SERVICE RECORD board of the 3D multiplayer hub (user 2026-11-02: "That board on the wall
would make for a good service record. But it should perhaps look more like a service record board.")

Writes srboard.png (2048x1462, the board face inside the noticeboard frame, 1.05 x 0.75 m) and srplaque.png (1024x160,
the header plaque on the top rail).  Period US Army look: olive-drab painted board, a rank insignia chart (WWII enlisted
chevrons + officer bars, drawn as shapes), a ribbon rack (stripe patterns of real US decorations), a typed service record
form with blank lines, and a card of the real WWII US campaign names the three games cover.  Every word is real, large and
set in a system font - no handwriting, no filler text (QA: no gibberish)."""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
F = r"C:\Windows\Fonts"
W, H = 2048, 1462
rnd = random.Random(7)


def font(name, size):
    return ImageFont.truetype(os.path.join(F, name), size)


STEN = "STENCIL.TTF"
TYPE = "courbd.ttf"
SERIF = "georgiab.ttf"
OD = (84, 88, 58)          # olive drab paint
KHAKI = (196, 178, 128)
CREAM = (232, 222, 196)
INK = (40, 34, 28)
GOLD = (196, 160, 70)
SILVER = (196, 198, 200)


def noise_rgb(w, h, base, amp, blur):
    a = np.random.default_rng(3).normal(0, 1, (h // 4 + 1, w // 4 + 1)).astype(np.float32)
    im = Image.fromarray(np.uint8(np.clip(128 + a * 40, 0, 255))).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    n = (np.asarray(im, np.float32) - 128) / 40.0
    g = np.random.default_rng(5).normal(0, 1, (h, w)).astype(np.float32) * 0.35
    rgb = np.array(base, np.float32)[None, None, :] + (n + g)[..., None] * amp
    return rgb


# ---- board: olive-drab painted plywood with a soft grain and edge darkening
bg = noise_rgb(W, H, OD, 6.0, 2)
yy, xx = np.mgrid[0:H, 0:W]
grain = np.sin(yy / 9.0 + np.sin(xx / 260.0) * 3.0) * 2.5
bg += grain[..., None]
vig = 1.0 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
bg *= vig[..., None]
board = Image.fromarray(np.uint8(np.clip(bg, 0, 255)))
d = ImageDraw.Draw(board)


def paper(w, h, tint=CREAM):
    a = noise_rgb(w, h, tint, 4.0, 3)
    p = Image.fromarray(np.uint8(np.clip(a, 0, 255))).convert("RGBA")
    return p


def pin_at(img, x, y, col):
    dd = ImageDraw.Draw(img)
    dd.ellipse((x - 13 + 5, y - 13 + 7, x + 13 + 5, y + 13 + 7), fill=(20, 20, 14))      # shadow
    dd.ellipse((x - 13, y - 13, x + 13, y + 13), fill=col)
    dd.ellipse((x - 6, y - 8, x + 2, y - 2), fill=tuple(min(255, c + 70) for c in col))


def place(img, x, y, angle, pins=((0.5, 0.06),), pincol=(170, 30, 26)):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 120))
    shr = sh.rotate(angle, expand=True, resample=Image.BICUBIC)
    r = img.rotate(angle, expand=True, resample=Image.BICUBIC)
    blur = shr.filter(ImageFilter.GaussianBlur(9))
    board.paste(blur, (x + 10, y + 14), blur)
    board.paste(r, (x, y), r)
    for px, py in pins:
        # pin position in the rotated image (small angles: near enough)
        pin_at(board, int(x + (r.size[0] - img.size[0]) / 2 + px * img.size[0]), int(y + (r.size[1] - img.size[1]) / 2 + py * img.size[1]), pincol)


def ctext(dd, cx, y, s, f, fill):
    w = dd.textlength(s, font=f)
    dd.text((cx - w / 2, y), s, font=f, fill=fill)


# ---- 1. rank insignia chart (left)
rc = paper(660, 1240, (226, 214, 184))
r = ImageDraw.Draw(rc)
ctext(r, 330, 26, "RANK INSIGNIA", font(STEN, 64), INK)
r.line((40, 104, 620, 104), fill=INK, width=4)
rows = [("PRIVATE FIRST CLASS", 1, 0, None), ("CORPORAL", 2, 0, None), ("SERGEANT", 3, 0, None), ("STAFF SERGEANT", 3, 1, None),
        ("TECHNICAL SERGEANT", 3, 2, None), ("FIRST SERGEANT", 3, 3, "diamond"), ("SECOND LIEUTENANT", 0, 0, "gold"),
        ("FIRST LIEUTENANT", 0, 0, "silver"), ("CAPTAIN", 0, 0, "silver2")]
fl = font(TYPE, 31)
y0, step = 128, 122


def chevrons(dd, cx, cy, n, rockers, extra):
    # WWII US enlisted: khaki chevrons point up on an olive patch, rockers (arcs) below
    pw, ph = 150, 112
    dd.rounded_rectangle((cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2), 14, fill=(64, 70, 44))
    top = cy - 40 if rockers else cy - 22 + (3 - n) * 7
    for i in range(n):
        ay = top + i * 15
        dd.line([(cx - 52, ay + 24), (cx, ay), (cx + 52, ay + 24)], fill=KHAKI, width=8, joint="curve")
    for i in range(rockers):
        rb = cy + 30 + i * 12
        dd.arc((cx - 56, rb - 34, cx + 56, rb), 25, 155, fill=KHAKI, width=7)
    if extra == "diamond":
        dd.polygon([(cx, top + 34), (cx + 8, top + 43), (cx, top + 52), (cx - 8, top + 43)], fill=KHAKI)


for i, (name, n, rk, kind) in enumerate(rows):
    cy = y0 + i * step + 52
    if kind in ("gold", "silver"):
        col = GOLD if kind == "gold" else SILVER
        r.rounded_rectangle((75 + 25, cy - 13, 75 + 125, cy + 13), 5, fill=col, outline=(90, 80, 60), width=2)
    elif kind == "silver2":
        for k in (-22, 22):
            r.rounded_rectangle((75 + 25, cy + k - 11, 75 + 125, cy + k + 11), 5, fill=SILVER, outline=(90, 80, 60), width=2)
    else:
        chevrons(r, 150, cy, n, rk, kind)
    r.text((250, cy - 17), name, font=fl, fill=INK)
    if i < len(rows) - 1:
        r.line((40, cy + 62, 620, cy + 62), fill=(150, 138, 112), width=2)
place(rc, 54, 140, 0.8, pins=((0.06, 0.012), (0.94, 0.012)), pincol=(176, 28, 24))

# ---- 2. ribbon rack (centre top): real US decorations as stripe patterns (left -> right = width fractions, colours)
BLUE, LBLUE, WHITE, RED, PURP, SCAR = (34, 56, 120), (120, 170, 220), (238, 236, 228), (178, 30, 36), (96, 36, 104), (190, 30, 34)
RIBBONS = {
    "MEDAL OF HONOR": [(1.0, LBLUE)],
    "DISTINGUISHED SERVICE CROSS": [(0.08, RED), (0.06, WHITE), (0.72, BLUE), (0.06, WHITE), (0.08, RED)],
    "SILVER STAR": [(0.10, BLUE), (0.06, WHITE), (0.12, BLUE), (0.06, WHITE), (0.32, RED), (0.06, WHITE), (0.12, BLUE), (0.06, WHITE), (0.10, BLUE)],
    "BRONZE STAR": [(0.04, WHITE), (0.40, RED), (0.04, WHITE), (0.04, BLUE), (0.04, WHITE), (0.40, RED), (0.04, WHITE)],
    "PURPLE HEART": [(0.10, WHITE), (0.80, PURP), (0.10, WHITE)],
    "GOOD CONDUCT": [(0.16, SCAR), (0.04, WHITE), (0.04, SCAR), (0.04, WHITE), (0.04, SCAR), (0.04, WHITE), (0.28, SCAR), (0.04, WHITE), (0.04, SCAR), (0.04, WHITE), (0.04, SCAR), (0.04, WHITE), (0.16, SCAR)],
}
rr = paper(700, 560, (222, 210, 178))
q = ImageDraw.Draw(rr)
ctext(q, 350, 22, "DECORATIONS", font(STEN, 64), INK)
q.line((40, 100, 660, 100), fill=INK, width=4)
names = list(RIBBONS)
RW, RH = 190, 54
fn = font(TYPE, 20)
for i, nm in enumerate(names):
    col, row = i % 3, i // 3
    x = 40 + col * 214
    y = 140 + row * 190
    xx_ = x
    for frac, c in RIBBONS[nm]:
        w = frac * RW
        q.rectangle((xx_, y, xx_ + w, y + RH), fill=c)
        xx_ += w
    if nm == "MEDAL OF HONOR":       # thirteen white stars
        for k in range(13):
            sx, sy = x + 14 + (k % 7) * 27 + (13 if k >= 7 else 0), y + 15 + (k // 7) * 24
            pts = []
            for j in range(10):
                rad = 8 if j % 2 == 0 else 3.4
                a = -math.pi / 2 + j * math.pi / 5
                pts.append((sx + rad * math.cos(a), sy + rad * math.sin(a)))
            q.polygon(pts, fill=WHITE)
    q.rectangle((x, y, x + RW, y + RH), outline=(60, 50, 40), width=2)
    words = nm.split(" ")
    lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else [nm]
    for k, ln in enumerate(lines):
        ctext(q, x + RW / 2, y + RH + 12 + k * 24, ln, fn, INK)
place(rr, 700, 70, -0.6, pins=((0.035, 0.03), (0.965, 0.03)), pincol=(196, 160, 60))

# ---- 3. typed service record form (right)
fm = paper(560, 820, (236, 230, 212))
g = ImageDraw.Draw(fm)
ctext(g, 280, 30, "WAR DEPARTMENT", font(TYPE, 30), INK)
ctext(g, 280, 74, "SOLDIER'S", font(SERIF, 44), INK)
ctext(g, 280, 126, "SERVICE RECORD", font(SERIF, 44), INK)
g.line((30, 188, 530, 188), fill=INK, width=3)
ft = font(TYPE, 27)
FIELDS = ["NAME", "SERIAL NO.", "GRADE", "ORGANIZATION", "CAMPAIGNS", "DECORATIONS", "MISSIONS", "REMARKS"]
for i, f_ in enumerate(FIELDS):
    y = 222 + i * 70
    g.text((34, y), f_, font=ft, fill=INK)
    x0 = 34 + g.textlength(f_, font=ft) + 14
    g.line((x0, y + 30, 526, y + 30), fill=(90, 80, 70), width=2)
g.rectangle((12, 12, 548, 808), outline=(120, 108, 90), width=3)
place(fm, 1440, 104, 1.4, pins=((0.06, 0.016), (0.94, 0.016)), pincol=(176, 28, 24))

# ---- 4. campaigns card (centre bottom): the real WWII US campaign names the three games play in
cc = paper(700, 470, (214, 200, 160))
k = ImageDraw.Draw(cc)
ctext(k, 350, 22, "CAMPAIGNS", font(STEN, 60), INK)
k.line((40, 96, 660, 96), fill=INK, width=4)
CAMPS = ["ALGERIA-FRENCH MOROCCO", "TUNISIA", "SICILY", "NAPLES-FOGGIA", "NORMANDY", "NORTHERN FRANCE", "ARDENNES-ALSACE", "CENTRAL EUROPE"]
fc = font(TYPE, 27)
for i, c in enumerate(CAMPS):
    k.text((70, 116 + i * 42), "* " + c, font=fc, fill=INK)
place(cc, 700, 760, 0.9, pins=((0.04, 0.03), (0.96, 0.03)), pincol=(176, 28, 24))

board = board.convert("RGB")
board.save(os.path.join(OUT, "srboard.png"))

# ---- header plaque: dark varnished wood, cream stencil letters
pw, ph = 1024, 160
wood = noise_rgb(pw, ph, (70, 46, 28), 7.0, 1)
gy = np.mgrid[0:ph, 0:pw][0]
wood += (np.sin(gy / 3.0 + np.sin(np.arange(pw)[None, :] / 90.0) * 2) * 5)[..., None]
pl = Image.fromarray(np.uint8(np.clip(wood, 0, 255)))
p = ImageDraw.Draw(pl)
p.rectangle((6, 6, pw - 7, ph - 7), outline=(150, 120, 70), width=5)
f = font(STEN, 104)
ctext(p, pw / 2, 20, "SERVICE RECORD", f, (226, 214, 180))
pl.save(os.path.join(OUT, "srplaque.png"))
print("srboard", board.size, "srplaque", pl.size, "->", OUT)
