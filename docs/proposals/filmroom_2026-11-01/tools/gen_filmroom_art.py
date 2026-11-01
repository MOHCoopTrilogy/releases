"""gen_filmroom_art.py [out dir] - the Film Room menu art (ui/filmroom.urc), drawn procedurally so it can be re-tuned.

A projection booth: near-black warm walls, one soft beam from the projector at the top left falling on the
screen, a film strip down the list, amber edges on dark plates for the controls.
Palette: wall #0c0a08, plate #1a1510, edge #5e4b30, projector amber #e8b862, cream text #efe4cb.
TGAs are written bottom-up (the engine's loader ignores the top-down bit - TRAPS).
"""
import math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

OUT = sys.argv[1] if len(sys.argv) > 1 else r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\mohmenu\filmroom"
os.makedirs(OUT, exist_ok=True)
FONTS = r"C:\Windows\Fonts"
AMBER = (232, 184, 98)
CREAM = (239, 228, 203)
random.seed(1944)


def save_tga(im, name):
    im.save(os.path.join(OUT, name), format="TGA", compression=None)


def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var:
        try:
            f.set_variation_by_name(var)
        except Exception:
            pass
    return f


def grain(im, amount):
    n = Image.effect_noise(im.size, amount).convert("L")
    n = n.point(lambda v: v - 128 + 128)
    return ImageChops.add(im, Image.merge("RGB", (n, n, n)), scale=1.0, offset=-128)


# ---------------------------------------------------------------- background 1024x768 (shown as 640x480)
def background():
    W, H = 1024, 768
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / H
        c = (int(11 + 5 * t), int(10 + 4 * t), int(8 + 3 * t))
        for x in range(W):
            px[x, y] = c
    # the beam: from the lens at the top left, widening onto the screen (right half, upper middle)
    beam = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(beam)
    lens = (40, 40)
    d.polygon([lens, (590, 150), (1000, 140), (1000, 470), (590, 455)], fill=34)
    beam = beam.filter(ImageFilter.GaussianBlur(38))
    # brighter toward the lens core
    core = Image.new("L", (W, H), 0)
    ImageDraw.Draw(core).polygon([lens, (600, 230), (600, 380)], fill=26)
    core = core.filter(ImageFilter.GaussianBlur(30))
    beam = ImageChops.add(beam, core)
    warm = Image.new("RGB", (W, H), (255, 214, 150))
    im = Image.composite(warm, im, beam.point(lambda v: min(255, v)))
    # dust motes in the beam: a few, tiny, faint
    dust = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(dust)
    bpx = beam.load()
    n = 0
    while n < 140:
        x, y = random.randint(60, 990), random.randint(40, 470)
        if bpx[x, y] < 14:
            continue
        r = random.choice((0.6, 0.8, 1.0, 1.3))
        a = random.randint(25, 70)
        dd.ellipse((x - r, y - r, x + r, y + r), fill=a)
        n += 1
    dust = dust.filter(ImageFilter.GaussianBlur(0.6))
    im = Image.composite(Image.new("RGB", (W, H), (255, 236, 200)), im, dust)
    # wall glow around where the screen hangs
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).rectangle((560, 120, 1000, 480), fill=22)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    im = Image.composite(Image.new("RGB", (W, H), (255, 220, 170)), im, glow)
    # vignette
    vig = Image.new("L", (W, H), 0)
    vp = vig.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            dx, dy = (x - W * 0.55) / (W * 0.62), (y - H * 0.45) / (H * 0.62)
            v = int(max(0, min(255, (dx * dx + dy * dy - 0.35) * 260)))
            vp[x, y] = v
            if x + 1 < W:
                vp[x + 1, y] = v
            if y + 1 < H:
                vp[x, y + 1] = v
                if x + 1 < W:
                    vp[x + 1, y + 1] = v
    vig = vig.filter(ImageFilter.GaussianBlur(20))
    im = Image.composite(Image.new("RGB", (W, H), (4, 3, 2)), im, vig)
    im = grain(im, 4)
    im.save(os.path.join(OUT, "fr_bg.jpg"), quality=92)
    return im


# ---------------------------------------------------------------- title 512x64
def title():
    W, H = 512, 64
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("STENCIL.TTF", 46)
    x = 4
    for ch in "FILM ROOM":
        d.text((x, 4), ch, font=f, fill=CREAM + (255,))
        x += d.textlength(ch, font=f) + (10 if ch != " " else 6)
    # a short amber rule under it
    d.rectangle((6, 56, 120, 58), fill=AMBER + (230,))
    save_tga(im, "fr_title.tga")


# ---------------------------------------------------------------- screen frame 512x320: the picture sits inside a 448x256 hole at (32,32)
def screen_frame():
    W, H = 512, 320
    hx0, hy0, hx1, hy1 = 32, 32, 480, 288
    a = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(a)
    d.rectangle((hx0 - 10, hy0 - 10, hx1 + 10, hy1 + 10), fill=120)
    a = a.filter(ImageFilter.GaussianBlur(12))
    d = ImageDraw.Draw(a)
    d.rectangle((hx0 - 3, hy0 - 3, hx1 + 3, hy1 + 3), fill=255)
    d.rectangle((hx0, hy0, hx1, hy1), fill=0)
    rgb = Image.new("RGB", (W, H), (255, 226, 176))
    rd = ImageDraw.Draw(rgb)
    rd.rectangle((hx0 - 3, hy0 - 3, hx1 + 3, hy1 + 3), outline=(214, 204, 182), width=3)
    im = Image.merge("RGBA", rgb.split() + (a,))
    save_tga(im, "fr_screen.tga")


# ---------------------------------------------------------------- film strip edge 32x512 (8 holes)
def strip():
    W, H = 32, 512
    im = Image.new("RGBA", (W, H), (22, 18, 13, 235))
    d = ImageDraw.Draw(im)
    for i in range(8):
        y = 16 + i * 64
        d.rounded_rectangle((9, y, 23, y + 30), radius=4, fill=(58, 49, 38, 255))
        d.rounded_rectangle((10, y + 1, 22, y + 3), radius=2, fill=(78, 66, 50, 255))
    d.line((0, 0, 0, H), fill=(70, 57, 36, 255))
    d.line((W - 1, 0, W - 1, H), fill=(70, 57, 36, 255))
    save_tga(im, "fr_strip.tga")


# ---------------------------------------------------------------- buttons 256x64
def button(name, hot):
    W, H = 256, 64
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fill = (40, 31, 20, 240) if hot else (26, 21, 16, 232)
    edge = AMBER + (255,) if hot else (94, 75, 48, 255)
    d.rounded_rectangle((1, 1, W - 2, H - 2), radius=7, fill=fill, outline=edge, width=3 if hot else 2)
    if hot:
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).rounded_rectangle((6, 6, W - 7, H // 2), radius=6, fill=40)
        glow = glow.filter(ImageFilter.GaussianBlur(6))
        top = Image.new("RGBA", (W, H), (255, 214, 150, 0))
        top.putalpha(glow)
        im = Image.alpha_composite(im, top)
    save_tga(im, name)


# ---------------------------------------------------------------- tab underline 128x32 (hover / selected)
def tab(name, on):
    W, H = 128, 32
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if on:
        d = ImageDraw.Draw(im)
        g = Image.new("L", (W, H), 0)
        ImageDraw.Draw(g).rectangle((14, 22, W - 15, 30), fill=90)
        g = g.filter(ImageFilter.GaussianBlur(4))
        im = Image.merge("RGBA", (Image.new("L", (W, H), AMBER[0]), Image.new("L", (W, H), AMBER[1]), Image.new("L", (W, H), AMBER[2]), g))
        d = ImageDraw.Draw(im)
        d.rectangle((14, 27, W - 15, 29), fill=AMBER + (255,))
    save_tga(im, name)


# ---------------------------------------------------------------- film leader 512x288 (no picture)
def nofilm():
    W, H = 512, 288
    im = Image.new("RGB", (W, H), (40, 37, 33))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    d.line((0, cy, W, cy), fill=(86, 80, 70), width=2)
    d.line((cx, 0, cx, H), fill=(86, 80, 70), width=2)
    for r, w in ((118, 3), (98, 2)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(150, 140, 120), width=w)
    # a wedge of the countdown sweep, lighter
    d.pieslice((cx - 96, cy - 96, cx + 96, cy + 96), -90, 30, fill=(62, 57, 50))
    d.ellipse((cx - 96, cy - 96, cx + 96, cy + 96), outline=(150, 140, 120), width=2)
    f = font("bahnschrift.ttf", 120, "Bold")
    tw = d.textlength("3", font=f)
    d.text((cx - tw / 2, cy - 76), "3", font=f, fill=(226, 218, 200))
    small = font("bahnschrift.ttf", 18, "SemiBold")
    t = "NO PICTURE"
    d.text((cx - d.textlength(t, font=small) / 2, H - 34), t, font=small, fill=(170, 160, 140))
    im = grain(im, 6).filter(ImageFilter.GaussianBlur(0.4))
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).rectangle((0, 0, W, H), outline=255, width=40)
    vig = vig.filter(ImageFilter.GaussianBlur(30))
    im = Image.composite(Image.new("RGB", (W, H), (14, 12, 10)), im, vig.point(lambda v: v * 0.7))
    save_tga(im.convert("RGBA"), "fr_nofilm.tga")


if __name__ == "__main__":
    background()
    title()
    screen_frame()
    strip()
    button("fr_btn.tga", False)
    button("fr_btn_h.tga", True)
    tab("fr_tab.tga", False)
    tab("fr_tab_h.tga", True)
    nofilm()
    print("wrote", sorted(os.listdir(OUT)))


# ---------------------------------------------------------------- the projector switched on (attic hover): beam 512x256 + lamp 128x128
# additive art on black: the apex (the lens) is the RIGHT edge's middle, the cone opens to the left
def beam():
    W, H = 512, 256
    a = Image.new("L", (W, H), 0)
    px = a.load()
    for x in range(W):
        t = (W - 1 - x) / (W - 1)                       # 0 at the lens, 1 at the far end
        half = (0.05 + 0.92 * t) * (H / 2)
        core = (1.0 - t) ** 1.4 * 0.85 + 0.12 * (1.0 - t)
        for y in range(H):
            d = abs(y - H / 2) / max(half, 1.0)
            if d >= 1.0:
                continue
            edge = (1.0 - d) ** 1.6
            px[x, y] = int(255 * min(1.0, core * edge))
    a = a.filter(ImageFilter.GaussianBlur(3))
    # faint dust in the light
    d = ImageDraw.Draw(a)
    rnd = random.Random(7)
    for _ in range(90):
        x, y = rnd.randint(40, W - 60), rnd.randint(20, H - 20)
        if a.getpixel((x, y)) < 20:
            continue
        r = rnd.choice((0.7, 1.0, 1.3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=min(255, a.getpixel((x, y)) + rnd.randint(30, 70)))
    rgb = Image.merge("RGB", [a.point(lambda v, k=k: int(v * k)) for k in (1.0, 0.92, 0.76)])
    rgb.save(os.path.join(OUT, "fr_beam.jpg"), quality=95)


def lamp():
    W = 128
    a = Image.new("L", (W, W), 0)
    ImageDraw.Draw(a).ellipse((40, 40, 88, 88), fill=255)
    a = a.filter(ImageFilter.GaussianBlur(14))
    rgb = Image.merge("RGB", [a.point(lambda v, k=k: int(v * k)) for k in (1.0, 0.86, 0.62)])
    rgb.save(os.path.join(OUT, "fr_lamp.jpg"), quality=95)


if __name__ == "__main__":
    beam()
    lamp()
    print("beam + lamp")
