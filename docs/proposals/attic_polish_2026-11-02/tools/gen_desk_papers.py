"""gen_desk_papers.py <stock dir> - v1.10.66 crisp paper for the stock document prop (user: "all of the papers ... on the main menu tables
read as super low quality"). The stock `documents1a` (a string-tied manila envelope, a blue cloth-bound book, a typed form) carries
128 / 64 / 256 px textures; this redraws all three at 1024 / 512 / 1024 px in the SAME UV layout, so the stock mesh is kept:

  documents1a_0.png  the envelope: kraft paper with fibre and creases, the string-and-washer tie and the six eyelets where the stock
                     art has them
  documents1a_1.png  the book: the stock layout (two cover panels, page-edge strips, the spine) re-filled region by region - blue
                     buckram cloth weave, cream page edges with leaf lines
  documents1a_2.png  the form: a typed personnel-record page (the stock art is a German Wehrpass page) - ruled table, short real
                     typewritten entries in Courier, a round unit stamp and a pen signature. Lettering is real German, legible:
                     KOMMANDIERUNGEN / Datum / Truppenteil / Bemerkungen and dated entries.
Writes over <stock dir>/documents1a/documents1a_{0,1,2}.png (run on a COPY of the stock export)."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

d0 = os.path.join(sys.argv[1], "documents1a")
FD = r"C:\Windows\Fonts"
rng = np.random.default_rng(1944)


def noise(w, h, scale, amp, seed):
    r = np.random.default_rng(seed)
    lo = np.asarray(Image.fromarray((r.random((max(2, h // scale), max(2, w // scale))) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 - 0.5
    return lo * amp


def paper(w, h, base, seed, fibre=5.0, blot=14.0):
    g = np.random.default_rng(seed).normal(0, 1, (h, w)).astype(np.float32) * fibre
    a = np.array(base, np.float32)[None, None, :] + (g + noise(w, h, 64, blot, seed + 1) + noise(w, h, 9, blot * 0.4, seed + 2))[..., None]
    return a


# ---- 0: the envelope (1024): kraft, creases, the tie and the six eyelets at the stock positions
W = 1024
a = paper(W, W, (196, 128, 52), 11, 6.0, 26.0)
for k in range(9):                                       # soft creases: a light and a dark line side by side
    y = rng.uniform(0.05, 0.95) * W
    x0, x1 = rng.uniform(-0.2, 0.3) * W, rng.uniform(0.7, 1.2) * W
    t = np.clip(1 - np.abs(np.mgrid[0:W, 0:W][0] - (y + (np.mgrid[0:W, 0:W][1] - x0) * rng.uniform(-0.08, 0.08))) / 3.0, 0, 1)
    a += t[..., None] * rng.choice([-10, 10])
env = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
d = ImageDraw.Draw(env)
d.line([(0, int(0.155 * W)), (W, int(0.155 * W))], fill=(150, 92, 34), width=5)          # the flap's fold
for cx, cy in ((0.52, 0.10), (0.52, 0.31)):                                              # the tie: two washers on the flap and body
    x, y = cx * W, cy * W
    d.ellipse([x - 34, y - 34, x + 34, y + 34], fill=(182, 166, 132), outline=(120, 104, 74), width=4)
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(70, 50, 30))
pts = [(0.52, 0.10), (0.46, 0.14), (0.50, 0.19), (0.58, 0.22), (0.55, 0.27), (0.52, 0.31)]
d.line([(x * W, y * W) for x, y in pts], fill=(232, 222, 196), width=7, joint="curve")
for cx in (0.26, 0.74):                                                                   # the six eyelets
    for cy in (0.42, 0.63, 0.84):
        x, y = cx * W, cy * W
        d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(236, 232, 222), outline=(150, 140, 120), width=3)
env = env.filter(ImageFilter.GaussianBlur(0.7))
env.save(os.path.join(d0, "documents1a_0.png"))

# ---- 1: the book (512): keep the stock regions, re-fill them
st = Image.open(os.path.join(d0, "documents1a_1.png")).convert("RGB").resize((512, 512), Image.NEAREST)
s = np.asarray(st, np.float32)
blue = (s[..., 2] > s[..., 0] + 25) | (s.mean(-1) >= 230)                                # cloth (+ the stock art's white specks, which sit on the cover) vs page edges
grey = ~blue & (np.abs(s[..., 0] - s[..., 2]) < 30) & (s.mean(-1) < 230)
yy, xx = np.mgrid[0:512, 0:512]
weave = (np.sin(xx * 1.9) * np.sin(yy * 1.9)) * 7 + np.random.default_rng(3).normal(0, 5, (512, 512))
cloth = np.array([38, 62, 104], np.float32)[None, None, :] + (weave + noise(512, 512, 40, 22, 4))[..., None]
pages = np.array([212, 200, 172], np.float32)[None, None, :] + ((np.sin(yy * 3.1) * 9) + noise(512, 512, 30, 16, 5))[..., None]
# by region (the stock art's own pixels are too coarse to classify): the cover panels (top 60 %) are all cloth but for the gap between
# the front and back boards; below them every non-blue texel is page edges
yy0, xx0 = np.mgrid[0:512, 0:512]
cover = yy0 < 0.60 * 512
gap = cover & (np.abs(xx0 - 0.49 * 512) < 5)
out = np.where((cover & ~gap)[..., None] | (~cover & blue)[..., None], cloth, pages)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5)).save(os.path.join(d0, "documents1a_1.png"))

# ---- 2: the typed form (1024)
W = 1024
form = Image.fromarray(np.clip(paper(W, W, (226, 216, 186), 21, 4.0, 18.0), 0, 255).astype(np.uint8), "RGB")
d = ImageDraw.Draw(form)
ink = (60, 52, 46)
fb = ImageFont.truetype(os.path.join(FD, "timesbd.ttf"), 30)
fs = ImageFont.truetype(os.path.join(FD, "times.ttf"), 20)
ft = ImageFont.truetype(os.path.join(FD, "cour.ttf"), 25)
d.text((W / 2, 52), "KOMMANDIERUNGEN", font=fb, fill=ink, anchor="mm")
x0, x1, y0 = 40, W - 40, 90
cols = [x0, 190, 600, x1]
d.rectangle([x0, y0, x1, 900], outline=ink, width=3)
for x in cols[1:-1]:
    d.line([(x, y0), (x, 900)], fill=ink, width=2)
d.line([(x0, y0 + 50), (x1, y0 + 50)], fill=ink, width=2)
for k, h in enumerate(("Datum", "Truppenteil", "Bemerkungen")):
    d.text(((cols[k] + cols[k + 1]) / 2, y0 + 25), h, font=fs, fill=ink, anchor="mm")
for y in range(y0 + 50 + 38, 900, 38):
    d.line([(x0, y), (x1, y)], fill=(150, 140, 120), width=1)
rows = [("12.3.42", "Inf.Ers.Btl. 9", "eingezogen"), ("4.8.42", "Gren.Rgt. 192", "versetzt"), ("17.1.43", "Stab II./192", "Funker"),
        ("2.6.43", "Ln.Abt. 21", "Lehrgang"), ("9.11.43", "Kuestenart. 1260", "Einsatz"), ("25.4.44", "Stab 716. I.D.", "Normandie")]
typed = Image.new("L", (W, W), 0)
td = ImageDraw.Draw(typed)
for i, (dt, unit, note) in enumerate(rows):
    y = y0 + 50 + 38 * i + 19
    for x, txt in ((cols[0] + 14, dt), (cols[1] + 14, unit), (cols[2] + 14, note)):
        jx = rng.normal(0, 0.8)                                                          # a typewriter's uneven strike
        td.text((x + jx, y + rng.normal(0, 0.6)), txt, font=ft, fill=int(rng.uniform(200, 250)), anchor="lm")
typed = typed.filter(ImageFilter.GaussianBlur(0.6))
form.paste((44, 40, 52), (0, 0), typed)
# the round unit stamp (violet ink, slightly turned) and a pen signature
st_ = Image.new("L", (300, 300), 0)
sd = ImageDraw.Draw(st_)
sd.ellipse([10, 10, 290, 290], outline=255, width=8)
sd.ellipse([60, 60, 240, 240], outline=255, width=5)
fst = ImageFont.truetype(os.path.join(FD, "arialbd.ttf"), 30)
txt = "GREN. RGT. 192  *  STAB  *"
for k, ch in enumerate(txt):
    ang = -90 + k * 360 / len(txt)
    r = 118
    x, y = 150 + r * math.cos(math.radians(ang)), 150 + r * math.sin(math.radians(ang))
    ci = Image.new("L", (40, 40), 0)
    ImageDraw.Draw(ci).text((20, 20), ch, font=fst, fill=255, anchor="mm")
    ci = ci.rotate(-ang - 90, resample=Image.BICUBIC)
    st_.paste(255, (int(x - 20), int(y - 20)), ci)
st_ = st_.rotate(14, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))
m = (np.asarray(st_, np.float32) / 255 * (0.55 + noise(300, 300, 12, 0.5, 9) + 0.2)).clip(0, 1)
form.paste((96, 52, 128), (600, 640), Image.fromarray((m * 255).astype(np.uint8)))
sig = [(640, 960), (668, 930), (690, 968), (712, 935), (735, 962), (770, 940), (820, 950), (860, 942)]
d.line(sig, fill=(34, 40, 90), width=4, joint="curve")
d.text((80, 950), "Fuer die Richtigkeit:", font=fs, fill=ink, anchor="lm")
form.save(os.path.join(d0, "documents1a_2.png"))
print("documents1a: envelope 1024, book 512, form 1024 ->", d0)

# ---- the ink bottle's paper label (attic62_edit section 11), wrapped once round the bottle: 1024 x 128, "TINTE / blauschwarz"
if len(sys.argv) > 2:
    lab = Image.fromarray(np.clip(paper(1024, 128, (222, 210, 176), 31, 3.0, 10.0), 0, 255).astype(np.uint8), "RGB")
    ld = ImageDraw.Draw(lab)
    ld.rectangle([300, 8, 724, 120], outline=(40, 52, 96), width=4)
    ld.text((512, 52), "TINTE", font=ImageFont.truetype(os.path.join(FD, "timesbd.ttf"), 64), fill=(30, 40, 84), anchor="mm")
    ld.text((512, 100), "blauschwarz", font=ImageFont.truetype(os.path.join(FD, "timesi.ttf"), 30), fill=(30, 40, 84), anchor="mm")
    lab.save(os.path.join(sys.argv[2], "ink_label.png"))
    print("ink label ->", sys.argv[2])
    # the ledger's cover (attic62_edit section 12c): green buckram weave, darker spine band, worn lighter corners and edges; the
    # bottom strip is the page-edge colour the edges map onto
    W = 1024
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    weave = (np.sin(xx * 1.6) * np.sin(yy * 1.6)) * 6 + np.random.default_rng(41).normal(0, 4, (W, W))
    cl = np.array([46, 78, 52], np.float32)[None, None, :] + (weave + noise(W, W, 50, 7, 42) + noise(W, W, 12, 6, 44))[..., None]
    spine = (xx < 90)
    cl[spine] *= 0.78
    edge = np.minimum.reduce([xx, yy, W - 1 - xx, W - 1 - yy])
    corner = np.minimum(np.hypot(xx, yy), np.minimum(np.hypot(W - 1 - xx, yy), np.minimum(np.hypot(xx, W - 1 - yy), np.hypot(W - 1 - xx, W - 1 - yy))))
    wear = np.clip(1 - edge / 18.0, 0, 1) * 0.6 + np.clip(1 - corner / 70.0, 0, 1) * 0.9
    wear = np.clip(wear * (0.6 + noise(W, W, 6, 0.8, 43) + 0.4), 0, 1)
    cl = cl * (1 - wear[..., None]) + np.array([150, 150, 120], np.float32) * wear[..., None]
    cl[W - 40:] = (np.array([214, 202, 172], np.float32)[None, None, :] + (np.sin(yy[W - 40:] * 3.1) * 8)[..., None])
    Image.fromarray(np.clip(cl, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5)).save(os.path.join(sys.argv[2], "ledger_cloth.png"))
    print("ledger cloth ->", sys.argv[2])
