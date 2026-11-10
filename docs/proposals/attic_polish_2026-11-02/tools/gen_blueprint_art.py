"""gen_blueprint_art.py <out.png> - the General's blueprint (v1.10.66, user: "Give the general a blueprint instead of what he looks
at now on menu"): a 1940s cyanotype, white linework on Prussian blue, of a coastal gun casemate - floor plan (GRUNDRISS) with
hatched walls, the embrasure facing the sea, ammunition and crew rooms, an angled entrance, dimension lines; a section (SCHNITT
A-A) with the roof slab and earth cover; a north arrow, a 1:50 scale bar and a title block. All drawn here (PIL), no external
images. Lettering is short, real German drafting terms, set in Stencil (title) and Arial Narrow:
  ATLANTIKWALL - BAUPLAN | GESCHUETZSTAND | GRUNDRISS | SCHNITT A-A | MUNITION | BEREITSCHAFT | EINGANG | SCHARTE | MASSTAB 1:50 |
  BLATT 3 | 1943.
Sheet 0.88 x 0.62 m (the A1 ratio, a little short): 2816 x 1984 px, 3.2 px / mm."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = sys.argv[1]
W, H = 2816, 1984
PX = W / 880.0                      # px per mm of paper
FD = r"C:\Windows\Fonts"
rng = np.random.default_rng(1943)

# ---- the cyanotype ground: Prussian blue, uneven (brushed sensitiser), paper fibre, lighter at the edges where it was handled
base = np.array([24, 66, 128], np.float32)
low = np.asarray(Image.fromarray((rng.random((9, 13)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255 - 0.5
fib = rng.normal(0, 1, (H, W)).astype(np.float32)
fib = np.asarray(Image.fromarray(np.clip(fib * 40 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 - 0.5
yy, xx = np.mgrid[0:H, 0:W]
edge = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)).astype(np.float32)
fade = np.clip(1 - edge / 90.0, 0, 1) ** 2
img = base[None, None, :] * (1 + low[..., None] * 0.16 + fib[..., None] * 0.10) + fade[..., None] * np.array([30, 34, 30], np.float32)
ground = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")

# ---- the linework on its own layer (white, then softened and laid over with a little bleed, as a contact print does)
ink = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(ink)
mm = lambda v: int(round(v * PX))  # noqa: E731


def font(name, size_mm):
    return ImageFont.truetype(os.path.join(FD, name), max(8, mm(size_mm)))


def line(p, q, w=0.35):
    d.line([(mm(p[0]), mm(p[1])), (mm(q[0]), mm(q[1]))], fill=255, width=max(1, mm(w)))


def rect(x0, y0, x1, y1, w=0.35):
    d.rectangle([mm(x0), mm(y0), mm(x1), mm(y1)], outline=255, width=max(1, mm(w)))


def text(xy, s, f, anchor="la", fill=255):
    d.text((mm(xy[0]), mm(xy[1])), s, font=f, fill=fill, anchor=anchor)


def hatch(poly, step=4.0, w=0.25):
    """45-degree hatching inside a polygon (mm), drawn through a mask"""
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([(mm(x), mm(y)) for x, y in poly], fill=255)
    h = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(h)
    for k in range(-H, W, mm(step)):
        hd.line([(k, 0), (k + H, H)], fill=255, width=max(1, mm(w)))
    ink.paste(255, (0, 0), Image.fromarray((np.asarray(m) & np.asarray(h))))


def dim(p, q, label, off=8.0, f=None):
    """a dimension line parallel to p-q, offset `off` mm, with ticks and a centred figure"""
    p, q = np.array(p, float), np.array(q, float)
    t = (q - p) / np.linalg.norm(q - p)
    n = np.array([-t[1], t[0]])
    a, b = p + n * off, q + n * off
    line(p + n * 2, p + n * (off + 2), 0.2)
    line(q + n * 2, q + n * (off + 2), 0.2)
    line(a, b, 0.25)
    for e in (a, b):
        line(e - (t + n) * 1.6, e + (t + n) * 1.6, 0.3)
    c = (a + b) / 2 + n * 3.2
    ang = math.degrees(math.atan2(-t[1], t[0]))
    tf = f or font("ARIALN.TTF", 4.2)
    tw, th = int(d.textlength(label, font=tf)) + 8, mm(5.5)
    ti = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(ti).text((4, 0), label, font=tf, fill=255)
    ti = ti.rotate(ang, expand=True, resample=Image.BICUBIC)
    ink.paste(255, (mm(c[0]) - ti.width // 2, mm(c[1]) - ti.height // 2), ti)


# sheet frame + the drafting grid (10 mm, faint) inside the drawing field
rect(10, 10, 870, 610, 0.9)
rect(14, 14, 866, 606, 0.3)
grid = Image.new("L", (W, H), 0)
gd = ImageDraw.Draw(grid)
for x in range(20, 866, 10):
    gd.line([(mm(x), mm(14)), (mm(x), mm(606))], fill=60 if x % 50 else 95, width=1)
for y in range(20, 606, 10):
    gd.line([(mm(14), mm(y)), (mm(866), mm(y))], fill=60 if y % 50 else 95, width=1)

# ---- GRUNDRISS (plan), scale 1:50 - 1 m = 20 mm.  Origin of the plan at (70, 70) mm on the sheet; the sea (and the embrasure) at the top
ox, oy = 70.0, 95.0
M = lambda x, y: (ox + x * 20.0, oy + y * 20.0)  # noqa: E731     # metres -> sheet mm
outer = [M(0, 1.2), M(4.0, 0), M(10.0, 0), M(14.0, 1.2), M(14.0, 11.0), M(0, 11.0)]
inner_gun = [M(2.0, 2.6), M(5.0, 1.8), M(9.0, 1.8), M(12.0, 2.6), M(12.0, 6.0), M(2.0, 6.0)]
ammo = [M(2.0, 7.4), M(6.4, 7.4), M(6.4, 9.4), M(2.0, 9.4)]
crew = [M(7.6, 7.4), M(12.0, 7.4), M(12.0, 9.4), M(7.6, 9.4)]
corr = [M(6.4, 6.0), M(7.6, 6.0), M(7.6, 11.0), M(6.4, 11.0)]
d.polygon([(mm(x), mm(y)) for x, y in outer], outline=255, width=mm(0.7))
# the walls: everything inside the outer line that is not a room, hatched
wall = Image.new("L", (W, H), 0)
wd = ImageDraw.Draw(wall)
wd.polygon([(mm(x), mm(y)) for x, y in outer], fill=255)
for room in (inner_gun, ammo, crew, corr):
    wd.polygon([(mm(x), mm(y)) for x, y in room], fill=0)
# the embrasure (SCHARTE): a stepped slot through the sea-side wall
wd.polygon([(mm(x), mm(y)) for x, y in (M(5.4, 1.85), M(8.6, 1.85), M(9.6, -0.1), M(4.4, -0.1))], fill=0)
h = Image.new("L", (W, H), 0)
hd = ImageDraw.Draw(h)
for k in range(-H, W, mm(3.0)):
    hd.line([(k, 0), (k + H, H)], fill=200, width=max(1, mm(0.22)))
ink.paste(200, (0, 0), Image.fromarray(np.asarray(wall) & np.asarray(h)))
for room in (inner_gun, ammo, crew, corr):
    d.polygon([(mm(x), mm(y)) for x, y in room], outline=255, width=mm(0.5))
for a, b in ((M(5.4, 1.85), M(4.4, -0.1)), (M(8.6, 1.85), M(9.6, -0.1))):
    line(a, b, 0.5)
# doors (quarter swings) and the gun: a pivot circle and its traverse arc towards the embrasure
for (cx, cy, r, a0, a1) in ((6.4, 7.6, 0.9, 0, 90), (7.6, 7.6, 0.9, 90, 180), (6.4, 6.2, 0.9, 270, 360)):
    d.arc([mm(M(cx - r, cy - r)[0]), mm(M(cx - r, cy - r)[1]), mm(M(cx + r, cy + r)[0]), mm(M(cx + r, cy + r)[1])], a0, a1, fill=255, width=mm(0.25))
gx, gy = M(7.0, 4.2)
d.ellipse([mm(gx - 18), mm(gy - 18), mm(gx + 18), mm(gy + 18)], outline=255, width=mm(0.45))
d.ellipse([mm(gx - 4), mm(gy - 4), mm(gx + 4), mm(gy + 4)], outline=255, width=mm(0.45))
line((gx, gy), M(7.0, 0.4), 0.6)
d.arc([mm(gx - 46), mm(gy - 46), mm(gx + 46), mm(gy + 46)], 235, 305, fill=255, width=mm(0.25))
# the section line A-A through the gun room
line(M(-1.0, 4.2), M(15.0, 4.2), 0.3)
for xx_ in (-1.0, 15.0):
    line(M(xx_, 4.2), M(xx_, 3.4), 0.6)
f_lbl = font("ARIALNB.TTF", 5.0)
text(M(-1.4, 3.3), "A", f_lbl, "mb")
text(M(15.4, 3.3), "A", f_lbl, "mb")
# room names and the dimension chain
f_room = font("ARIALNB.TTF", 6.0)
text(M(7.0, 5.4), "GESCHUETZRAUM", f_room, "mm")
text(M(4.2, 8.4), "MUNITION", f_room, "mm")
text(M(9.8, 8.4), "BEREITSCHAFT", f_room, "mm")
text(M(7.0, 10.3), "EINGANG", f_room, "mm")
text(M(7.0, -0.9), "SCHARTE", f_room, "mm")
dim(M(0, 11.0), M(14.0, 11.0), "14.00", off=10)
dim(M(14.0, 11.0), M(14.0, 1.2), "9.80", off=10)
dim(M(4.0, 0), M(10.0, 0), "6.00", off=-8)
f_t = font("ARIALNB.TTF", 7.0)
text((ox, 40), "GRUNDRISS", f_t)
line((ox, 50), (ox + 78, 50), 0.4)

# ---- SCHNITT A-A (section) to the right of the plan, same scale
sx, sy = 420.0, 250.0
S = lambda x, z: (sx + x * 20.0, sy - z * 20.0)  # noqa: E731
# ground line, the earth cover (stippled), the roof slab and walls (hatched), the gun room inside
line(S(-2.0, 0), S(16.0, 0), 0.4)
cover = [S(-1.5, 0), S(0, 4.6), S(14.0, 4.6), S(15.5, 0)]
for k in range(320):                                    # earth cover stipple, kept inside the cover outline
    px_, pz_ = rng.uniform(0.6, 13.4), rng.uniform(4.75, 5.3)
    x_, y_ = S(px_, pz_)
    d.ellipse([mm(x_) - 2, mm(y_) - 2, mm(x_) + 2, mm(y_) + 2], fill=170)
d.line([(mm(S(-1.5, 0)[0]), mm(S(-1.5, 0)[1])), (mm(S(1.0, 5.4)[0]), mm(S(1.0, 5.4)[1])), (mm(S(13.0, 5.4)[0]), mm(S(13.0, 5.4)[1])),
        (mm(S(15.5, 0)[0]), mm(S(15.5, 0)[1]))], fill=255, width=mm(0.3))
slab = [S(0, 1.2), S(14.0, 1.2), S(14.0, 4.6), S(0, 4.6)]
hatch([S(0, -0.6), S(14.0, -0.6), S(14.0, 4.6), S(0, 4.6)], 3.0, 0.22)
room = [S(2.0, 0), S(12.0, 0), S(12.0, 2.6), S(2.0, 2.6)]
d.polygon([(mm(x), mm(y)) for x, y in room], fill=0, outline=255, width=mm(0.5))
d.polygon([(mm(x), mm(y)) for x, y in [S(0, -0.6), S(14.0, -0.6), S(14.0, 4.6), S(0, 4.6)]], outline=255, width=mm(0.7))
d.polygon([(mm(x), mm(y)) for x, y in [S(4.4, 0.8), S(9.6, 0.8), S(9.6, 2.0), S(4.4, 2.0)]], fill=0)   # the embrasure in section
rect(*S(4.4, 2.0), *S(9.6, 0.8), 0.4)
dim(S(14.0, -0.6), S(14.0, 4.6), "5.20", off=-10)
dim(S(0, 2.6), S(0, 4.6), "2.00", off=10)
text((sx, 112), "SCHNITT A-A", f_t)
line((sx, 122), (sx + 82, 122), 0.4)

# ---- north arrow, scale bar
nx, ny = 800.0, 80.0
d.polygon([(mm(nx), mm(ny - 22)), (mm(nx - 7), mm(ny + 8)), (mm(nx), mm(ny + 2))], fill=255)
d.polygon([(mm(nx), mm(ny - 22)), (mm(nx + 7), mm(ny + 8)), (mm(nx), mm(ny + 2))], outline=255, width=mm(0.35))
text((nx, ny - 26), "N", font("ARIALNB.TTF", 7.0), "mb")
bx, by = 420.0, 330.0
for k in range(5):
    x0 = bx + k * 20
    if k % 2 == 0:
        d.rectangle([mm(x0), mm(by), mm(x0 + 20), mm(by + 3)], fill=255)
    else:
        rect(x0, by, x0 + 20, by + 3, 0.3)
    text((x0, by + 5), str(k), font("ARIALN.TTF", 3.6), "ma")
text((bx + 100, by + 5), "5 m", font("ARIALN.TTF", 3.6), "ma")
text((bx, by - 3), "MASSTAB 1:50", font("ARIALNB.TTF", 4.4), "lb")

# ---- LAGEPLAN (site plan), lower left: the coastline, the beach, the casemate's footprint facing the sea, a communication
# trench zig-zagging inland to a second position, contour lines
lx, ly = 40.0, 360.0
text((lx + 10, ly), "LAGEPLAN", f_t)
line((lx + 10, ly + 10), (lx + 80, ly + 10), 0.4)
rect(lx + 10, ly + 18, lx + 330, ly + 232, 0.4)
pts = []
for i in range(0, 321, 4):                               # the coastline (wavy), sea above it
    pts.append((lx + 10 + i, ly + 58 + 9 * math.sin(i / 23.0) + 5 * math.sin(i / 7.3)))
d.line([(mm(x), mm(y)) for x, y in pts], fill=255, width=mm(0.5))
for k in range(1, 4):                                    # the beach line and two waves offshore
    d.line([(mm(x), mm(y + (k * 9 if k == 1 else -k * 9 + 9))) for x, y in pts], fill=150, width=mm(0.25))
text((lx + 290, ly + 32), "MEER", font("ARIALNB.TTF", 6.0), "mm")
text((lx + 290, ly + 82), "STRAND", f_room, "mm")
cl = Image.new("L", (W, H), 0)                          # contour lines inland, clipped to the site plan's frame
cd = ImageDraw.Draw(cl)
for r_ in (38, 62, 88):
    cd.arc([mm(lx + 140 - r_ * 2.2), mm(ly + 200 - r_), mm(lx + 140 + r_ * 2.2), mm(ly + 200 + r_ * 1.4)], 200, 340, fill=140, width=mm(0.25))
clip = Image.new("L", (W, H), 0)
ImageDraw.Draw(clip).rectangle([mm(lx + 11), mm(ly + 19), mm(lx + 329), mm(ly + 231)], fill=255)
ink.paste(cl, (0, 0), Image.fromarray(np.minimum(np.asarray(clip), np.asarray(cl) * 255)))
bxs, bys = lx + 120.0, ly + 104.0                        # the casemate (filled) and the second position
d.polygon([(mm(bxs), mm(bys)), (mm(bxs + 22), mm(bys)), (mm(bxs + 26), mm(bys + 16)), (mm(bxs - 4), mm(bys + 16))], fill=255)
d.rectangle([mm(lx + 232), mm(ly + 168), mm(lx + 250), mm(ly + 184)], fill=255)
tr = [(bxs + 11, bys + 16)]
for k in range(1, 9):                                    # zig-zag trench between them
    t_ = k / 8.0
    x_ = bxs + 11 + (lx + 241 - bxs - 11) * t_ + (7 if k % 2 else -7)
    y_ = bys + 16 + (ly + 168 - bys - 16) * t_
    tr.append((x_, y_))
d.line([(mm(x), mm(y)) for x, y in tr], fill=255, width=mm(0.7))
text((bxs + 11, bys + 26), "GESCHUETZSTAND", f_n if False else font("ARIALN.TTF", 4.6), "ma")
text((lx + 241, ly + 190), "MG-STAND", font("ARIALN.TTF", 4.6), "ma")

# ---- notes block (short, real)
f_n = font("ARIALN.TTF", 4.0)
notes = ["STAHLBETON B 300", "DECKE 2.00 M", "WAENDE 2.00 M", "ERDUEBERDECKUNG 1.00 M"]
for i, s in enumerate(notes):
    text((420, 380 + i * 8), s, f_n)

# ---- title block, bottom right
tx0, ty0, tx1, ty1 = 600.0, 470.0, 862.0, 602.0
rect(tx0, ty0, tx1, ty1, 0.7)
line((tx0, ty0 + 44), (tx1, ty0 + 44), 0.4)
line((tx0, ty0 + 78), (tx1, ty0 + 78), 0.4)
line((tx0 + 150, ty0 + 78), (tx0 + 150, ty1), 0.4)
line((tx0 + 210, ty0 + 78), (tx0 + 210, ty1), 0.4)
fst = ImageFont.truetype(os.path.join(FD, "STENCIL.TTF"), mm(17))
title = "ATLANTIKWALL - BAUPLAN"
while d.textlength(title, font=fst) > mm(tx1 - tx0 - 14):
    fst = ImageFont.truetype(os.path.join(FD, "STENCIL.TTF"), fst.size - 4)
text(((tx0 + tx1) / 2, ty0 + 24), title, fst, "mm")
text(((tx0 + tx1) / 2, ty0 + 61), "GESCHUETZSTAND", ImageFont.truetype(os.path.join(FD, "STENCIL.TTF"), mm(11)), "mm")
fsm = font("ARIALN.TTF", 4.2)
fbg = font("ARIALNB.TTF", 9.0)
text((tx0 + 5, ty0 + 84), "INHALT", fsm)
text((tx0 + 5, ty0 + 112), "GRUNDRISS / SCHNITT", font("ARIALNB.TTF", 6.0), "lm")
text((tx0 + 155, ty0 + 84), "BLATT", fsm)
text((tx0 + 180, ty0 + 112), "3", fbg, "mm")
text((tx0 + 215, ty0 + 84), "JAHR", fsm)
text((tx0 + 236, ty0 + 112), "1943", font("ARIALNB.TTF", 7.0), "mm")

# ---- print: the white lines bleed a little into the blue (contact print), the grid is faint, then two fold creases
ink = Image.fromarray(np.maximum(np.asarray(ink), np.asarray(grid)))
soft = np.asarray(ink.filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255
sharp = np.asarray(ink, np.float32) / 255
a = np.clip(sharp * 0.85 + soft * 0.35, 0, 1)
white = np.array([226, 236, 246], np.float32)
g = np.asarray(ground, np.float32)
o = g * (1 - a[..., None]) + white[None, None, :] * a[..., None]
for fx in (W // 2,):
    band = np.exp(-((xx - fx) / 6.0) ** 2)
    o += band[..., None] * 22
for fy in (H // 2,):
    band = np.exp(-((yy - fy) / 6.0) ** 2)
    o += band[..., None] * 16
Image.fromarray(np.clip(o, 0, 255).astype(np.uint8), "RGB").save(out)
print("blueprint ->", out, W, "x", H)
