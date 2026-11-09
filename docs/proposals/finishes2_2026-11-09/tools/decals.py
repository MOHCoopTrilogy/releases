"""finishes2 - the insignia / marking DECALS, drawn as clean vector shapes (PIL polygons at 8x, box-filtered; text only from a
real font, short and checked) - no hand-waved emblems. Each is RGBA, transparent around it, square, 512 px.

  ab82.png        82nd Airborne "AA" shoulder patch: red square, blue disc, white double A (period 1942 design)
  lorraine.png    Cross of Lorraine as FFI fighters brushed it on: white, two bars, rough brush edges
  dak_palm.png    Afrika Korps palm (the palm only - the period emblem's swastika is deliberately left out), black on sand
  crest.png       trench-art crest: laurel wreath around a shield, the date 1944 under it, engraved line work
  plaque.png      presentation plaque: an oval nickel plate with a rope border and engraved lines (no text)
  waa.png         Waffenamt acceptance stamp for a captured Allied gun: a small eagle-less "WaA 214" stamp (the real stamps
                  carry an eagle; a 512 px decal shrinks to a few mm on the gun, so the text-only form reads better)
  souvenir.png    a GI's scratched initials and "SOUVENIR" on a captured German gun
    python decals.py [out dir]      default ../assets/decals
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'assets', 'decals')
N, SS = 512, 8
FONT_B = r"C:\Windows\Fonts\arialbd.ttf"
FONT_C = r"C:\Windows\Fonts\courbd.ttf"


def canvas():
    im = Image.new('RGBA', (N * SS, N * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def S(v):
    return v * N * SS


def fin(im):
    return im.resize((N, N), Image.LANCZOS)


def ab82():
    im, d = canvas()
    d.rectangle((S(0.12), S(0.12), S(0.88), S(0.88)), fill=(178, 34, 40, 255))
    d.ellipse((S(0.2), S(0.2), S(0.8), S(0.8)), fill=(30, 50, 110, 255))
    f = ImageFont.truetype(FONT_B, int(S(0.34)))
    for dx in (-0.115, 0.115):                               # two A side by side, white
        bb = d.textbbox((0, 0), 'A', font=f)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        d.text((S(0.5 + dx) - w / 2 - bb[0], S(0.5) - h / 2 - bb[1]), 'A', font=f, fill=(245, 245, 240, 255))
    return fin(im)


def lorraine():
    im, d = canvas()
    w = 0.075
    col = (238, 236, 228, 255)
    d.rectangle((S(0.5 - w / 2), S(0.1), S(0.5 + w / 2), S(0.9)), fill=col)        # upright
    d.rectangle((S(0.36), S(0.25 - w / 2), S(0.64), S(0.25 + w / 2)), fill=col)     # short upper bar
    d.rectangle((S(0.26), S(0.43 - w / 2), S(0.74), S(0.43 + w / 2)), fill=col)     # long lower bar
    a = im.split()[3].filter(ImageFilter.GaussianBlur(SS * 1.2))
    import random
    rng = random.Random(1944)
    px = a.load()
    for _ in range(6000):                                    # dry-brush: ragged edges, a few skips
        x, y = rng.randrange(a.size[0]), rng.randrange(a.size[1])
        if 30 < px[x, y] < 225:
            ImageDraw.Draw(a).ellipse((x - SS * 2, y - SS * 2, x + SS * 2, y + SS * 2), fill=0 if rng.random() < 0.5 else 255)
    a = a.point(lambda v: 255 if v > 128 else 0)
    im.putalpha(a)
    return fin(im)


def dak_palm():
    im, d = canvas()
    col = (28, 24, 20, 255)
    # trunk: a slightly curved tapering band
    pts_l, pts_r = [], []
    for i in range(20):
        t = i / 19.0
        x = 0.5 + 0.03 * math.sin(t * 2.5)
        y = 0.88 - t * 0.5
        w = 0.035 - 0.015 * t
        pts_l.append((S(x - w), S(y)))
        pts_r.append((S(x + w), S(y)))
    d.polygon(pts_l + pts_r[::-1], fill=col)
    top = (0.5 + 0.03 * math.sin(2.5), 0.38)
    for ang in (-160, -125, -95, -60, -25, 10, 45):          # seven fronds: curved leaf blades
        a = math.radians(ang)
        L = 0.28
        outline = []
        for i in range(16):
            t = i / 15.0
            r = L * t
            droop = 0.10 * t * t
            x = top[0] + r * math.cos(a)
            y = top[1] + r * math.sin(a) * 0.55 + droop
            outline.append((x, y))
        up = [(x + 0.02 * math.sin(math.pi * i / 15.0) * math.sin(a), y - 0.03 * math.sin(math.pi * i / 15.0)) for i, (x, y) in enumerate(outline)]
        dn = [(x, y + 0.01 * math.sin(math.pi * i / 15.0)) for i, (x, y) in enumerate(outline)]
        d.polygon([(S(x), S(y)) for x, y in up + dn[::-1]], fill=col)
    d.rectangle((S(0.3), S(0.88), S(0.7), S(0.91)), fill=col)                    # the ground line
    return fin(im)


def crest():
    im, d = canvas()
    ink = (40, 30, 18, 255)
    lw = int(SS * 6)
    # shield
    sh = [(0.38, 0.22), (0.62, 0.22), (0.62, 0.44), (0.5, 0.56), (0.38, 0.44)]
    d.line([(S(x), S(y)) for x, y in sh + sh[:1]], fill=ink, width=lw, joint='curve')
    d.line([(S(0.5), S(0.24)), (S(0.5), S(0.53))], fill=ink, width=lw)
    d.line([(S(0.4), S(0.33)), (S(0.6), S(0.33))], fill=ink, width=lw)
    # laurel: two branches of paired, pointed leaves (lens shapes) curving up round the shield
    def leaf(cx, cy, ang, L=0.05, W=0.016):
        pts = []
        for i in range(13):
            t = i / 12.0
            x, y = (t - 0.5) * L, W * math.sin(math.pi * t)
            pts.append((x, y))
        pts += [(x, -y) for x, y in pts[::-1]]
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([(S(cx + x * ca - y * sa), S(cy + x * sa + y * ca)) for x, y in pts], fill=ink)
    for side in (-1, 1):
        stem = []
        for k in range(10):
            t = k / 9.0
            a = math.radians(110 + 150 * t) if side < 0 else math.radians(70 - 150 * t)
            stem.append((0.5 + 0.21 * math.cos(a), 0.40 - 0.21 * math.sin(a)))
        d.line([(S(x), S(y)) for x, y in stem], fill=ink, width=int(SS * 4))
        for k in range(1, 9):
            (x0, y0), (x1, y1) = stem[k], stem[k + 1]
            tang = math.atan2(y1 - y0, x1 - x0)
            for s_ in (-1, 1):
                ang = tang + s_ * 0.7
                leaf(x0 + 0.028 * math.cos(ang), y0 + 0.028 * math.sin(ang), ang)
    f = ImageFont.truetype(FONT_B, int(S(0.11)))
    bb = d.textbbox((0, 0), '1944', font=f)
    d.text((S(0.5) - (bb[2] - bb[0]) / 2 - bb[0], S(0.66)), '1944', font=f, fill=ink)
    return fin(im)


def plaque():
    im, d = canvas()
    d.ellipse((S(0.12), S(0.3), S(0.88), S(0.7)), fill=(196, 198, 200, 255))
    d.ellipse((S(0.12), S(0.3), S(0.88), S(0.7)), outline=(120, 122, 126, 255), width=int(SS * 10))
    for k in range(48):                                      # rope border: short slanted ticks round the rim
        a = 2 * math.pi * k / 48
        x, y = 0.5 + 0.35 * math.cos(a), 0.5 + 0.17 * math.sin(a)
        d.line([(S(x - 0.01), S(y - 0.01)), (S(x + 0.01), S(y + 0.01))], fill=(150, 152, 156, 255), width=int(SS * 4))
    for k, w in enumerate((0.36, 0.44, 0.30)):               # engraved lines (no lettering)
        y = 0.42 + k * 0.08
        d.line([(S(0.5 - w / 2), S(y)), (S(0.5 + w / 2), S(y))], fill=(110, 112, 118, 255), width=int(SS * 3))
    return fin(im)


def stamp_text(text, font, box, ink):
    im, d = canvas()
    f = ImageFont.truetype(font, int(S(box)))
    bb = d.textbbox((0, 0), text, font=f)
    d.text((S(0.5) - (bb[2] - bb[0]) / 2 - bb[0], S(0.5) - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=ink)
    return im, d


def waa():
    im, d = stamp_text('WaA214', FONT_C, 0.16, (34, 32, 30, 230))
    d.ellipse((S(0.12), S(0.32), S(0.88), S(0.68)), outline=(34, 32, 30, 230), width=int(SS * 6))
    return fin(im)


def souvenir():
    im, d = canvas()
    f1 = ImageFont.truetype(FONT_C, int(S(0.16)))
    f2 = ImageFont.truetype(FONT_C, int(S(0.11)))
    ink = (222, 214, 196, 235)                               # scratched into the finish: bare-metal light lines
    for txt, f, y in (('J.M.', f1, 0.36), ('SOUVENIR', f2, 0.58)):
        bb = d.textbbox((0, 0), txt, font=f)
        d.text((S(0.5) - (bb[2] - bb[0]) / 2 - bb[0], S(y) - (bb[3] - bb[1]) / 2 - bb[1]), txt, font=f, fill=ink)
    return fin(im)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (('ab82', ab82), ('lorraine', lorraine), ('dak_palm', dak_palm), ('crest', crest), ('plaque', plaque),
                     ('waa', waa), ('souvenir', souvenir)):
        im = fn()
        p = os.path.join(OUT, name + '.png')
        im.save(p, optimize=True)
        print('%-10s %d KB' % (name, os.path.getsize(p) // 1024))


if __name__ == '__main__':
    main()
