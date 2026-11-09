"""finishes2 - the SHARED pattern and wear tiles (one set for every gun: a finish is a shader that lays these over the gun's own
texture, so no gun gets 13 new full textures). Every tile is seamless (drawn on a torus: each shape is also drawn shifted by
+-1 tile) and drawn at 4x then box-filtered - clean edges, no noise mush.

  camo_splitter.png    Splittertarn 31: angular splinters of green + brown on a tan field, with the fine vertical green
                       "rain" strokes (period 1931 Zeltbahn pattern)
  camo_pea.png         Erbsenmuster 44: tan field, brown + green blobs with dense small dots of both (the pea dots)
  camo_telo.png        telo mimetico 1929: ochre field, soft-edged brown + green amoebae, large, sparse
  camo_amoeba.png      Soviet MKK amoeba: khaki-olive field, dark brown amoeba cut-outs
  camo_whitewash.png   hand-brushed field whitewash: white strokes with gaps, RGBA (alpha = paint), over the gun
  wear_chips.png       RGBA chip mask for painted finishes: alpha 1 = paint, 0 = chipped to the metal / wood under it
  wear_scratch.png     L: fine scratches and rub-through for Battle-worn (multiplied in as a light mask)
  engrave_vines.png    RGBA: hand-engraved vine scroll (trench art) - dark cut lines, alpha = the cut

    python patterns.py [out dir]      default ../assets/tiles
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'assets', 'tiles')
N = 512
SS = 4


class Torus:
    """a 4x canvas on which every polygon / ellipse is drawn at its 9 wrapped copies (seamless tile)"""
    def __init__(self, mode='RGB', bg=(0, 0, 0)):
        self.n = N * SS
        self.im = Image.new(mode, (self.n, self.n), bg)
        self.d = ImageDraw.Draw(self.im)

    def poly(self, pts, fill):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.d.polygon([((x + dx) * self.n, (y + dy) * self.n) for x, y in pts], fill=fill)

    def ellipse(self, cx, cy, rx, ry, fill):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = (cx + dx) * self.n, (cy + dy) * self.n
                self.d.ellipse((x - rx * self.n, y - ry * self.n, x + rx * self.n, y + ry * self.n), fill=fill)

    def line(self, pts, fill, w):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.d.line([((x + dx) * self.n, (y + dy) * self.n) for x, y in pts], fill=fill, width=max(1, int(w * self.n)))

    def done(self):
        return self.im.resize((N, N), Image.LANCZOS)


def blob(rng, cx, cy, r, lobes=7, rough=0.35, k=24):
    """a closed organic outline (sum of a few low harmonics) - the amoeba / telo shapes"""
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(lobes)]
    am = [rng.uniform(0, rough) / (i + 1) for i in range(lobes)]
    pts = []
    for i in range(k * 3):
        t = 2 * math.pi * i / (k * 3)
        rr = r * (1 + sum(a * math.sin((j + 2) * t + p) for j, (a, p) in enumerate(zip(am, ph))))
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t) * 0.75))
    return pts


def splitter(rng):
    """Splittertarn: the field is cut by long straight lines into angular shards; about a third of the shards are printed
    brown, a third green, the rest stay tan - then the fine green rain strokes over everything"""
    T = Torus(bg=(160, 146, 106))
    cols = ((60, 74, 46), (100, 72, 46))
    for _ in range(46):
        cx, cy = rng.random(), rng.random()
        a = rng.choice((rng.uniform(-0.5, -0.2), rng.uniform(0.2, 0.5))) + math.pi * rng.randint(0, 1)
        L, W = rng.uniform(0.10, 0.26), rng.uniform(0.04, 0.09)
        ca, sa = math.cos(a), math.sin(a)
        # a sliver: a long thin quadrilateral / triangle with one blunt and one sharp end, straight sides
        q = [(-L, -W * rng.uniform(0.3, 1.0)), (L * rng.uniform(0.6, 1.0), -W * rng.uniform(0.0, 0.4)),
             (L, W * rng.uniform(0.2, 0.8)), (-L * rng.uniform(0.3, 0.8), W)]
        T.poly([(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in q], cols[rng.randint(0, 1)])
    for _ in range(1300):
        x, y = rng.random(), rng.random()
        T.line([(x, y), (x, y + rng.uniform(0.015, 0.04))], (54, 70, 42), 0.0024)
    return T.done()


def pea(rng):
    T = Torus(bg=(156, 140, 104))
    for col, n, r in (((98, 74, 50), 14, 0.07), ((70, 82, 52), 14, 0.06)):
        for _ in range(n):
            T.poly(blob(rng, rng.random(), rng.random(), r * rng.uniform(0.7, 1.3), rough=0.5), col)
    for col in ((88, 64, 42), (64, 76, 46), (178, 160, 120)):   # the dots: brown, green and light, everywhere
        for _ in range(900):
            T.ellipse(rng.random(), rng.random(), 0.0045, 0.0045, col)
    return T.done()


def telo(rng):
    T = Torus(bg=(176, 150, 96))
    for col, n in (((112, 84, 52), 7), ((86, 98, 58), 7)):
        for _ in range(n):
            T.poly(blob(rng, rng.random(), rng.random(), rng.uniform(0.10, 0.16), rough=0.45), col)
    im = T.done().filter(ImageFilter.GaussianBlur(1.6))   # printed cloth: soft edges
    return im


def amoeba(rng):
    T = Torus(bg=(120, 116, 78))
    for _ in range(11):
        T.poly(blob(rng, rng.random(), rng.random(), rng.uniform(0.07, 0.12), lobes=9, rough=0.6), (66, 52, 36))
    return T.done()


def whitewash(rng):
    T = Torus(mode='L', bg=0)
    for _ in range(260):                                   # brush strokes: long, slightly curved, mostly one direction
        x, y = rng.random(), rng.random()
        a = rng.gauss(0.15, 0.25)
        L = rng.uniform(0.12, 0.3)
        pts = [(x + L * t * math.cos(a), y + L * t * math.sin(a) + 0.01 * math.sin(6 * t)) for t in np.linspace(0, 1, 8)]
        T.line(pts, int(rng.uniform(170, 255)), rng.uniform(0.012, 0.03))
    a = np.asarray(T.done(), float) / 255.0
    rgb = np.zeros((N, N, 4), np.uint8)
    rgb[..., 0:3] = (232, 234, 236)
    rgb[..., 3] = (np.clip(a * 1.15, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(rgb, 'RGBA')


def chips(rng):
    """paint survives everywhere except small chips (alpha 0 = the metal / wood shows); a few clusters, mostly isolated"""
    T = Torus(mode='L', bg=255)
    for _ in range(260):
        cx, cy = rng.random(), rng.random()
        n = 1 if rng.random() < 0.7 else rng.randint(3, 7)
        for k in range(n):
            x, y = cx + rng.gauss(0, 0.012) * (n > 1), cy + rng.gauss(0, 0.012) * (n > 1)
            T.poly(blob(rng, x, y, rng.uniform(0.002, 0.008), lobes=5, rough=0.7, k=8), 0)
    a = T.done()
    return Image.merge('RGBA', [Image.new('L', (N, N), 255)] * 3 + [a])


def scratches(rng):
    T = Torus(mode='L', bg=255)
    for _ in range(500):
        x, y = rng.random(), rng.random()
        a = rng.uniform(0, math.pi)
        L = rng.uniform(0.01, 0.06)
        T.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], int(rng.uniform(200, 238)), 0.0018)
    return T.done()


def vines(rng):
    """hand-engraved scrollwork: rows of vine stems with curled tendrils and paired leaves, cut lines only (dense, like the
    trench-art shell cases and engraved presentation pieces)"""
    T = Torus(mode='L', bg=0)
    rows = 5
    for row in range(rows):
        y0 = (row + 0.5) / rows
        f = lambda t: y0 + 0.045 * math.sin(2 * math.pi * 3 * t + row)
        T.line([(t, f(t)) for t in np.linspace(0, 1, 160)], 255, 0.0032)
        for k in range(24):
            t = k / 24.0
            y = f(t)
            s_ = 1 if k % 2 else -1
            for side in (1, -1):                           # paired leaves: two arcs meeting at a point
                lx = [(t + 0.022 * u, y + side * s_ * 0.016 * math.sin(math.pi * u)) for u in np.linspace(0, 1, 9)]
                T.line(lx, 255, 0.0022)
            if k % 3 == 0:                                 # a curled tendril
                cx, cy = t + 0.01, y + s_ * 0.03
                spiral = [(cx + 0.012 * (1 - u) * math.cos(6 * u), cy + 0.012 * (1 - u) * math.sin(6 * u) * s_) for u in np.linspace(0, 1, 18)]
                T.line([(t, y)] + spiral, 255, 0.002)
    a = T.done()
    return Image.merge('RGBA', [Image.new('L', (N, N), 26)] * 3 + [a])


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(1944)
    tiles = {'camo_splitter': splitter, 'camo_pea': pea, 'camo_telo': telo, 'camo_amoeba': amoeba,
             'camo_whitewash': whitewash, 'wear_chips': chips, 'wear_scratch': scratches, 'engrave_vines': vines}
    for name, fn in tiles.items():
        im = fn(random.Random(hash(name) & 0xffff ^ 1944))
        p = os.path.join(OUT, name + '.png')
        im.save(p, optimize=True)
        print('%-16s %s %d KB' % (name, im.mode, os.path.getsize(p) // 1024))


if __name__ == '__main__':
    main()
