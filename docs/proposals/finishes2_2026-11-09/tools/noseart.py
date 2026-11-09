"""Nose-art decals for the Nose Art finish and the Customize bench: ORIGINAL artwork in the period style (no copied pin-up,
no real aircraft's art, no nudity) - lettering, emblems and tallies hand-painted on metal: a slightly rough brush edge and
paint chipped off at random. Drawn at 4x, saved at 2x into assets/decals/<name>.png.
  shark_mouth   shark mouth and eye (faces the MUZZLE on the gun's right side; the bench mirrors it for the left)
  lucky_lady    "Lucky Lady" in sign-painter script over a horseshoe and a pair of dice
  ace_spades    an ace of spades card with an ACE banner
  bomb_tally    mission tally: two rows of small yellow bombs
    python noseart.py
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets', 'decals')
K = 4
FONTS = os.path.join('C:' + os.sep, 'Windows', 'Fonts')
RED, DRED, YEL, WHITE, BLACK = (200, 36, 36), (110, 18, 18), (244, 196, 48), (244, 242, 232), (24, 22, 22)


def canvas(w, h):
    im = Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def P(pts):
    return [(x * K, y * K) for x, y in pts]


def font(name, sz):
    return ImageFont.truetype(os.path.join(FONTS, name), int(sz * K))


def weather(im, seed, chips=26, rough=1.2):
    """brush-painted on metal: the edge roughened a little (blur + noisy threshold) and paint chipped off in small flakes"""
    rng = np.random.default_rng(seed)
    a = np.asarray(im)[..., 3].astype(float)
    noise = rng.random(a.shape)
    noise = np.asarray(Image.fromarray((noise * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(K * 0.7)), float) / 255
    soft = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(K * rough)), float)
    a2 = np.where(soft > 255 * (0.35 + 0.3 * (noise - 0.5) * 2), np.maximum(a, 0), 0) * (a > 0)
    mask = Image.new('L', im.size, 255)
    md = ImageDraw.Draw(mask)
    H, W = a.shape
    ys, xs = np.nonzero(a > 128)
    if len(ys):
        for _ in range(chips):
            i = rng.integers(len(ys))
            r = rng.uniform(0.6, 2.2) * K
            pts = [(xs[i] + r * rng.uniform(0.6, 1.3) * math.cos(t), ys[i] + r * rng.uniform(0.6, 1.3) * math.sin(t))
                   for t in np.linspace(0, 2 * math.pi, 7, endpoint=False)]
            md.polygon(pts, fill=0)
    a2 = a2 * (np.asarray(mask, float) / 255)
    arr = np.asarray(im).copy()
    arr[..., 3] = np.clip(a2, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def done(im, name, seed):
    im = weather(im, seed)
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im.save(os.path.join(OUT, name + '.png'))
    return im


def outlined_text(d, xy, txt, f, fill, outline, ow):
    x, y = xy
    for dx in range(-ow, ow + 1, max(1, ow // 3)):
        for dy in range(-ow, ow + 1, max(1, ow // 3)):
            if dx * dx + dy * dy <= ow * ow:
                d.text((x + dx, y + dy), txt, font=f, fill=outline)
    d.text((x, y), txt, font=f, fill=fill)


# ---------------------------------------------------------------------------------------------------------------- art
def shark_mouth():
    W, H = 300, 160
    im, d = canvas(W, H)
    # the mouth: a wedge from a point at the back (left) to a wide gape at the front (right, the muzzle), upper jaw
    # nearly straight, lower jaw a deep curve; dark rim, red inside
    def jaws(inset):
        top = [(18 + inset + (270 - inset * 2) * t, 70 - 34 * t ** 1.3 + inset * 0.6) for t in np.linspace(0, 1, 32)]
        bot = [(18 + inset + (270 - inset * 2) * t, 74 + 70 * math.sin(math.pi * 0.5 * t) ** 1.2 - 8 * t ** 3 - inset * 0.6)
               for t in np.linspace(1, 0, 32)]
        return top, bot
    top, bot = jaws(0)
    d.polygon(P(top + bot), fill=BLACK)
    it, ib = jaws(7)
    d.polygon(P(it + ib), fill=RED)
    for k in range(10):                                         # teeth, bigger towards the front
        t = 0.14 + 0.8 * k / 9
        x = 25 + 256 * t
        yt = 70 - 34 * t ** 1.3 + 4.2
        yb = 74 + 70 * math.sin(math.pi * 0.5 * t) ** 1.2 - 8 * t ** 3 - 4.2
        w = 4 + 6 * t
        L = 8 + 14 * t
        d.polygon(P([(x - w, yt), (x + w, yt), (x, yt + L)]), fill=WHITE, outline=BLACK)
        d.polygon(P([(x - w + w, yb), (x + w + w, yb), (x + w, yb - L)]), fill=WHITE, outline=BLACK)
    # the eye: above the jaw, a third of the way back from the gape
    ex, ey = 196, 18
    d.ellipse(P([(ex - 18, ey - 11), (ex + 18, ey + 11)]), fill=WHITE, outline=BLACK, width=2 * K)
    d.ellipse(P([(ex + 2, ey - 9), (ex + 17, ey + 9)]), fill=BLACK)
    d.ellipse(P([(ex + 6, ey - 6), (ex + 10, ey - 2)]), fill=WHITE)
    d.line(P([(ex - 22, ey - 14), (ex + 6, ey - 16), (ex + 22, ey - 10)]), fill=BLACK, width=2 * K)    # brow
    return done(im, 'shark_mouth', 11)


def lucky_lady():
    W, H = 420, 190
    im, d = canvas(W, H)
    # horseshoe (open end up = luck held in), nail holes
    cx, cy, R = 300, 122, 44
    arc_o = [(cx + R * math.cos(a), cy + R * 1.08 * math.sin(a)) for a in np.linspace(math.radians(-40), math.radians(220), 40)]
    arc_i = [(cx + (R - 15) * math.cos(a), cy + (R - 15) * 1.08 * math.sin(a)) for a in np.linspace(math.radians(220), math.radians(-40), 40)]
    d.polygon(P(arc_o + arc_i), fill=(170, 172, 176), outline=BLACK)
    for a in np.linspace(math.radians(-10), math.radians(190), 7):
        x, y = cx + (R - 7.5) * math.cos(a), cy + (R - 7.5) * 1.08 * math.sin(a)
        d.ellipse(P([(x - 2.2, y - 2.2), (x + 2.2, y + 2.2)]), fill=BLACK)
    # a pair of dice showing seven
    for (x0, y0, ang, pips) in ((96, 120, -12, 3), (148, 132, 9, 4)):
        s = 36
        c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        sq = [(x0 + u * c - v * sn, y0 + u * sn + v * c) for u, v in ((-s / 2, -s / 2), (s / 2, -s / 2), (s / 2, s / 2), (-s / 2, s / 2))]
        d.polygon(P(sq), fill=WHITE, outline=BLACK)
        d.line(P(sq + sq[:1]), fill=BLACK, width=2 * K)
        spots = {3: ((-1, -1), (0, 0), (1, 1)), 4: ((-1, -1), (1, -1), (-1, 1), (1, 1))}[pips]
        for u, v in spots:
            px, py = x0 + (u * 10) * c - (v * 10) * sn, y0 + (u * 10) * sn + (v * 10) * c
            d.ellipse(P([(px - 3.4, py - 3.4), (px + 3.4, py + 3.4)]), fill=RED if pips == 3 else BLACK)
    # the name, sign-painter script, yellow with a dark red outline and a black drop shadow
    f = font('segoescb.ttf', 58)
    txt = 'Lucky Lady'
    tw = d.textlength(txt, font=f) / K
    x, y = (W - tw) / 2, 14
    d.text(((x + 3) * K, (y + 4) * K), txt, font=f, fill=BLACK)
    outlined_text(d, (x * K, y * K), txt, f, YEL, DRED, 3 * K)
    return done(im, 'lucky_lady', 12)


def ace_spades():
    W, H = 200, 250
    im, d = canvas(W, H)
    card = Image.new('RGBA', (120 * K, 170 * K), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, 120 * K - 1, 170 * K - 1], radius=12 * K, fill=WHITE, outline=BLACK, width=3 * K)
    # the spade: an inverted heart with a flared stem
    sx, sy, s = 60, 82, 2.3
    pts = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        hx = 16 * math.sin(t) ** 3
        hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(((sx + hx * s) * K, (sy + hy * s - 6) * K))
    cd.polygon(pts, fill=BLACK)
    cd.polygon([((sx - 5) * K, (sy + 14) * K), ((sx + 5) * K, (sy + 14) * K), ((sx + 14) * K, (sy + 44) * K), ((sx - 14) * K, (sy + 44) * K)], fill=BLACK)
    fa = font('impact.ttf', 26)
    cd.text((10 * K, 6 * K), 'A', font=fa, fill=BLACK)
    card = card.rotate(-12, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(card, ((W * K - card.width) // 2, 8 * K))
    # banner
    d.polygon(P([(24, 196), (176, 196), (186, 216), (176, 236), (24, 236), (14, 216)]), fill=RED, outline=BLACK)
    f = font('impact.ttf', 30)
    tw = d.textlength('ACE', font=f) / K
    outlined_text(d, ((W - tw) / 2 * K, 197 * K), 'ACE', f, WHITE, BLACK, 2 * K)
    return done(im, 'ace_spades', 13)


def bomb_tally():
    W, H = 300, 120
    im, d = canvas(W, H)

    def bomb(x, y, s=1.0):
        # nose at the right: a rounded ogive, a straight body, a cone to the tail, a box fin across the tail
        prof = [(16, 0.0), (15, 3.5), (12, 6.0), (6, 7.0), (-6, 7.0), (-12, 5.0), (-17, 2.2)]
        body = [(x + px * s, y - py * s) for px, py in prof] + [(x + px * s, y + py * s) for px, py in reversed(prof)]
        d.polygon(P(body), fill=YEL, outline=BLACK)
        d.rectangle(P([(x - 26 * s, y - 7.5 * s), (x - 17 * s, y + 7.5 * s)]), fill=YEL, outline=BLACK)          # box fin
        d.line(P([(x - 17 * s, y), (x - 26 * s, y)]), fill=BLACK, width=K)
        d.line(P([(x + 9 * s, y - 6.4 * s), (x + 9 * s, y + 6.4 * s)]), fill=RED, width=2 * K)                       # nose band
    for r, n in ((0, 3), (1, 3)):
        for k in range(n):
            bomb(62 + k * 92 + r * 18, 30 + r * 56, 1.5)
    return done(im, 'bomb_tally', 14)


ALL = [shark_mouth, lucky_lady, ace_spades, bomb_tally]

if __name__ == '__main__':
    ims = [f() for f in ALL]
    W = sum(i.width + 16 for i in ims) + 16
    H = max(i.height for i in ims) + 32
    sh = Image.new('RGB', (W, H), (96, 104, 92))          # olive-drab metal behind, the way it would sit on a gun
    x = 16
    for i in ims:
        sh.paste(i, (x, 16), i)
        x += i.width + 16
    sh.save(os.path.join(HERE, '..', 'media', 'noseart_sheet.png'))
    print('wrote', len(ims))
