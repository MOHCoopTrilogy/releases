"""urc_preview.py <urc> <background png|-> <out.png> [hover widget] - rough offline mock of a 640x480 virtualres sheet at 1080p
(rects, colours, borders, titles in stand-in fonts, Label shaders from the game's paks). A layout QA aid - text overflow,
overlaps, art placement - not a pixel match of the engine's UI. [advtrain 2026-11-10]"""
import io, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import vfs  # noqa: E402

urc, bg, out = sys.argv[1:4]
hover = sys.argv[4] if len(sys.argv) > 4 else None
W, H = 1920, 1080
k = H / 480.0
ox = (W - 640 * k) / 2
img = Image.open(bg).convert("RGB").resize((W, H)) if bg != "-" else Image.new("RGB", (W, H), (30, 30, 34))
d = ImageDraw.Draw(img, "RGBA")
FONTS = {"facfont-20": ("georgiab.ttf", 17), "verdana-12": ("verdana.ttf", 11), "handle-23": ("georgiab.ttf", 20)}
t = open(urc, encoding="latin-1").read().replace("\r\n", "\n")
over = []
for m in re.finditer(r'resource\n(\w+)\n\{\n(.*?)\n\}', t, re.S):
    kind, body = m.group(1), m.group(2)
    f = {}
    for ln in body.split("\n"):
        p = ln.split(None, 1)
        f[p[0]] = p[1].strip('"') if len(p) > 1 else ""
    if "rect" not in f:
        continue
    x, y, w, h = (float(v) for v in f["rect"].split())
    r = (ox + x * k, y * k, ox + (x + w) * k, (y + h) * k)
    bgc = [float(v) for v in f.get("bgcolor", "0 0 0 0").split()]
    if bgc[3] > 0:
        d.rectangle(r, fill=tuple(int(c * 255) for c in bgc[:3]) + (int(bgc[3] * 255),))
    if f.get("shader", "").startswith("textures/"):
        b = None
        for ext in (".jpg", ".tga", ".png"):
            b = vfs.read(os.path.splitext(f["shader"])[0] + ext)
            if b:
                break
        if b:
            im = Image.open(io.BytesIO(b)).convert("RGB").resize((int(r[2] - r[0]), int(r[3] - r[1])), Image.LANCZOS)
            img.paste(im, (int(r[0]), int(r[1])))
        else:
            d.rectangle(r, outline=(255, 0, 255), width=2)
            d.text((r[0] + 4, r[1] + 4), "missing:\n" + f["shader"].split("/")[-1], fill=(255, 0, 255))
    if kind == "Button" and hover and f.get("name") == hover and f.get("hovershader"):
        d.rectangle(r, fill=(255, 236, 170, 70))
    if f.get("borderstyle") == "3D_BORDER":
        d.line((r[0], r[3], r[0], r[1], r[2], r[1]), fill=(255, 255, 255, 90), width=2)
        d.line((r[2], r[1], r[2], r[3], r[0], r[3]), fill=(0, 0, 0, 120), width=2)
    if f.get("title"):
        fn, px = FONTS.get(f.get("font", "verdana-12"), ("verdana.ttf", 11))
        ft = ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", fn), int(px * k))
        fg = tuple(int(float(c) * 255) for c in f.get("fgcolor", "1 1 1 1").split()[:3])
        tw = d.textlength(f["title"], font=ft)
        al = f.get("textalign", "center" if kind == "Button" else "left")
        tx = r[0] + 2 if al == "left" else (r[0] + r[2] - tw) / 2
        d.text((tx, (r[1] + r[3]) / 2 - px * k * 0.62), f["title"], font=ft, fill=fg)
        if tw > r[2] - r[0] - 2:
            over.append((f.get("name"), round(tw / k, 1), w))
img.save(out)
print(out, "overflow:", over or "none")
