"""gen_squad_icons.py - the squad state icons (user 2026-11-16: "use our icon area above the health to show soldiers and
what they are doing ... just one icon that shows what the squad is doing") and the placement marker's texture.

Our own art, in the item row's style (flat colour, dark outline, 128 px, like coop_medkit_icon / coop_cover_icon):
    textures/hud/coop_sq_follow.tga   a helmet with a cream chevron over it: the squad is with you
    textures/hud/coop_sq_hold.tga     a helmet behind a sandbag line: holding a place
    textures/hud/coop_sq_move.tga     a helmet, an arrow and the green ground ring: moving to a place
    textures/hud/coop_sq_white.tga    8 px white (the marker polys are vertex-coloured: scripts/coop_squad.shader)
No text anywhere (nothing to garble). Drawn at 4x and reduced.
    python docs/tools/gen_squad_icons.py [mod dir]
"""
import os
import sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUT = os.path.join(MOD, "textures", "hud")
S, K = 128, 4
B = S * K
INK = (24, 22, 18, 255)
OLIVE = (104, 118, 64, 255)
OLIVE_HI = (138, 152, 86, 255)
CREAM = (236, 226, 196, 255)
SAND = (196, 160, 104, 255)
SAND_HI = (222, 192, 138, 255)
GREEN = (110, 228, 96, 255)
W = 7 * K  # outline width


def helmet(d, cx, cy, r):
    """an M1-style helmet in profile-front: a dome with a brim, outlined"""
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=INK)
    ri = r - W
    d.pieslice([cx - ri, cy - ri, cx + ri, cy + ri], 180, 360, fill=OLIVE)
    d.pieslice([cx - ri * 0.62, cy - ri * 0.86, cx + ri * 0.2, cy - ri * 0.1], 200, 300, fill=OLIVE_HI)
    bw, bh = r * 1.32, r * 0.20
    d.rounded_rectangle([cx - bw, cy - bh * 0.3, cx + bw, cy + bh], radius=bh * 0.6, fill=INK)
    d.rounded_rectangle([cx - bw + W, cy - bh * 0.3 + W * 0.6, cx + bw - W, cy + bh - W * 0.6], radius=bh * 0.4,
                        fill=OLIVE)


def chevron(d, cx, cy, w, h, t, col):
    pts = [(cx - w, cy + h), (cx, cy), (cx + w, cy + h), (cx + w, cy + h + t), (cx, cy + t), (cx - w, cy + h + t)]
    d.polygon(pts, fill=INK)
    k = W * 0.8
    inner = [(cx - w + k, cy + h + k * 0.2), (cx, cy + k), (cx + w - k, cy + h + k * 0.2), (cx + w - k, cy + h + t - k),
             (cx, cy + t + k * 0.1), (cx - w + k, cy + h + t - k)]
    d.polygon(inner, fill=col)


def sandbags(d, x0, y0, x1, h):
    """two courses of flat sandbags, the top one offset half a bag (a sandbag wall, never a row of wheels)"""
    def bag(a, b, y):
        d.rounded_rectangle([a, y, b, y + h], radius=h * 0.28, fill=INK)
        d.rounded_rectangle([a + W, y + W, b - W, y + h - W], radius=h * 0.2, fill=SAND)
        d.line([(a + W * 2.5, y + h * 0.32), (b - W * 2.5, y + h * 0.32)], fill=SAND_HI, width=int(W * 0.9))
    n = 3
    bw = (x1 - x0) / n
    for i in range(n):
        bag(x0 + i * bw, x0 + (i + 1) * bw, y0 + h * 0.92)
    for i in range(2):
        a = x0 + bw * 0.5 + i * bw
        bag(a, a + bw, y0)


def arrow(d, x0, y, x1, t, col):
    hh = t * 1.25
    body = [(x0, y - t / 2), (x1 - hh, y - t / 2), (x1 - hh, y - hh), (x1, y), (x1 - hh, y + hh), (x1 - hh, y + t / 2),
            (x0, y + t / 2)]
    d.polygon(body, fill=INK)
    k = W * 0.75
    inner = [(x0 + k, y - t / 2 + k), (x1 - hh - k * 0.4, y - t / 2 + k), (x1 - hh - k * 0.4, y - hh + k * 1.6),
             (x1 - k * 1.6, y), (x1 - hh - k * 0.4, y + hh - k * 1.6), (x1 - hh - k * 0.4, y + t / 2 - k),
             (x0 + k, y + t / 2 - k)]
    d.polygon(inner, fill=col)


def ring(d, cx, cy, rx, ry, t, col):
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=INK, width=int(t + 2 * W))
    d.ellipse([cx - rx + W, cy - ry + W, cx + rx - W, cy + ry - W], outline=col, width=int(t))


def make(name, draw):
    im = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    draw(ImageDraw.Draw(im))
    im = im.resize((S, S), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, name + ".tga"))
    print("wrote", name)


def follow(d):
    chevron(d, B * 0.5, B * 0.04, B * 0.30, B * 0.17, B * 0.14, CREAM)
    helmet(d, B * 0.5, B * 0.86, B * 0.44)


def hold(d):
    helmet(d, B * 0.5, B * 0.48, B * 0.36)
    sandbags(d, B * 0.04, B * 0.52, B * 0.96, B * 0.23)


def move(d):
    ring(d, B * 0.74, B * 0.84, B * 0.22, B * 0.11, B * 0.06, GREEN)
    helmet(d, B * 0.30, B * 0.66, B * 0.30)
    arrow(d, B * 0.20, B * 0.20, B * 0.97, B * 0.17, CREAM)


make("coop_sq_follow", follow)
make("coop_sq_hold", hold)
make("coop_sq_move", move)
Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(os.path.join(OUT, "coop_sq_white.tga"))
print("wrote coop_sq_white")
