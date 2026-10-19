"""gamefont.py - draw text with the game's own bitmap fonts (gfx/fonts/<name>@3x.tga + fonts/<name>@3x.RitualFont).

RitualFont: 'indirections' = 256 char codes -> glyph index (-1 = none); 'locations' = one {x y w h} per glyph index
in SHEET units; the @3x tga is 4 px per sheet unit (1024 px wide for a 256-unit sheet).
"""
import os, re
from PIL import Image

MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
_cache = {}


def load(name):
    if name in _cache:
        return _cache[name]
    txt = open(os.path.join(MOD, "fonts", name + "@3x.RitualFont"), encoding="latin-1").read()
    height = float(re.search(r"height\s+([\d.]+)", txt).group(1))
    ind = re.search(r"indirections\s*\{(.*?)\}", txt, re.S).group(1).split()
    ind = [int(x) for x in ind]
    loc = re.search(r"locations\s*\{(.*)\}\s*$", txt, re.S).group(1)
    boxes = [tuple(float(v) for v in b.split()) for b in re.findall(r"\{\s*([^{}]+?)\s*\}", loc)]
    sheet = Image.open(os.path.join(MOD, "gfx", "fonts", name + "@3x.tga")).convert("RGBA")
    k = sheet.size[0] / 256.0
    f = {"h": height, "ind": ind, "box": boxes, "sheet": sheet, "k": k}
    _cache[name] = f
    return f


def glyph(f, ch):
    c = ord(ch) if ord(ch) < 256 else 63
    gi = f["ind"][c] if c < len(f["ind"]) else -1
    if gi < 0 or gi >= len(f["box"]):
        return None
    x, y, w, h = f["box"][gi]
    if w <= 0:
        return None
    return gi, x, y, w, h


def measure(name, text, px, xs=1.0):
    f = load(name)
    s = px / f["h"]
    tot = 0.0
    for ch in text:
        if ch == " ":
            tot += 3.5 * s * xs
            continue
        g = glyph(f, ch)
        tot += (g[3] + 0.5) * s * xs if g else 4 * s * xs
    return int(tot)


def draw(img, xy, text, name="verdana-12", px=24, fill=(240, 232, 214), anchor="l", spacing=0.5, xs=1.0):
    """px = line height in output pixels (the font's 12-unit cell). anchor l/m/r on x."""
    f = load(name)
    s = px / f["h"]
    w = measure(name, text, px, xs)
    x, y = xy
    if anchor == "m":
        x -= w // 2
    elif anchor == "r":
        x -= w
    sheet, k = f["sheet"], f["k"]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cx = float(x)
    for ch in text:
        if ch == " ":
            cx += 3.5 * s * xs
            continue
        g = glyph(f, ch)
        if not g:
            cx += 4 * s * xs
            continue
        _, gx, gy, gw, gh = g
        crop = sheet.crop((int(gx * k), int(gy * k), int((gx + gw) * k), int((gy + gh) * k)))
        tw, th = max(1, round(gw * s * xs)), max(1, round(gh * s))
        crop = crop.resize((tw, th), Image.LANCZOS)
        a = crop.split()[3]
        lum = crop.convert("L")
        # glyphs are white-on-transparent; fall back to luminance when the alpha channel is flat
        mask = a if a.getextrema()[0] < 250 else lum
        col = Image.new("RGBA", (tw, th), tuple(fill) + (255,))
        col.putalpha(mask)
        layer.alpha_composite(col, (int(round(cx)), int(round(y))))
        cx += (gw + spacing) * s * xs
    img.alpha_composite(layer)
    return w


if __name__ == "__main__":
    im = Image.new("RGBA", (900, 240), (19, 18, 17, 255))
    draw(im, (10, 10), "ARMORY  M1 GARAND  Rank: Staff Sergeant 0123456789", "verdana-12", 24)
    draw(im, (10, 60), "ARMORY // SELECT LOADOUT", "facfont-20", 40)
    draw(im, (10, 120), "Damage Rate of fire Accuracy Mobility Reload", "verdana-14", 28, (140, 199, 115))
    im.convert("RGB").save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonttest.png"))
