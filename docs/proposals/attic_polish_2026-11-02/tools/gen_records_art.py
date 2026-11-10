"""gen_records_art.py <art dir> - v1.10.63 the RECORDS desk kit, from the vanilla records screens.

Vanilla (maintt pak1 ui/war_records.urc + the mod's HD textures/mohmenu/warrecords_a/_b): a desk with a CLOSED wooden medal box
(dark red-brown, a brass diamond escutcheon with a keyhole on its front) and two stacked green metal letter trays labelled LOAD and
SAVE.  ui/medals.urc + textures/mohmenu/medal_bg_a/_b: the same box OPEN, seen from above - red velvet, six medal recesses, two
gold stars, a white card at the top (the medal's description) and a brass plate at the bottom (its name).
Writes (art dir): medalbox_wood.png (the box's wood, 1024), medalbox_front.png (front with the escutcheon), medalbox_inside.png
(the velvet interior = the vanilla medal_bg art cropped to the case, 1024 x 848), tray_load.png / tray_save.png (stencilled
brass plates), and medalbox_layout.json (where each vanilla medal / plate sits on the interior, 0..1 of the image)."""
import io, json, os, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
MOD = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzzz_co-op_hzm_mod_assets_tex.pk3"
z = zipfile.ZipFile(MOD)
rd = lambda n: Image.open(io.BytesIO(z.read(n))).convert("RGB")      # noqa: E731
rng = np.random.default_rng(63)

# ---- the open case, composed exactly as the vanilla menu lays it out (640 x 480 virtual: _a at 0,0 512 x 512, _b at 384,0 256 x 512)
K = 3                                                    # 1920 x 1440 working canvas
cv = Image.new("RGB", (640 * K, 480 * K))
cv.paste(rd("textures/mohmenu/medal_bg_a.jpg").resize((512 * K, 512 * K), Image.LANCZOS), (0, 0))
cv.paste(rd("textures/mohmenu/medal_bg_b.jpg").resize((256 * K, 512 * K), Image.LANCZOS), (384 * K, 0))
# the case's inner rim (the gold line) in virtual coords, measured on the art: x 70 .. 570, y 6 .. 428
CASE = (70, 6, 570, 428)
inside = cv.crop(tuple(v * K for v in CASE)).resize((1024, int(1024 * (CASE[3] - CASE[1]) / (CASE[2] - CASE[0]))), Image.LANCZOS)
inside.save(os.path.join(out, "medalbox_inside.png"))
W, H = CASE[2] - CASE[0], CASE[3] - CASE[1]
rel = lambda r: [(r[0] - CASE[0]) / W, (r[1] - CASE[1]) / H, r[2] / W, r[3] / H]        # noqa: E731  (x, y, w, h) -> 0..1
# vanilla medals.urc rects (x y w h, 640 x 480): the six medals in the order g_medalbt0 .. 5, the description card and the name plate
MEDALS = [("distinguishedcross", (412, 78, 60, 120)), ("silverstar", (289, 78, 60, 120)), ("bronzestar", (164, 78, 60, 120)),
          ("africastar", (164, 236, 60, 120)), ("distinguishedflyingcross", (289, 236, 60, 120)), ("airmedal", (412, 236, 60, 120))]
layout = {"medals": [{"name": n, "cvar": "g_medalbt%d" % i, "rect": rel(r)} for i, (n, r) in enumerate(MEDALS)],
          "desc": rel((80, 8, 480, 56)), "sign": rel((108, 380, 424, 28)), "aspect": W / H}
json.dump(layout, open(os.path.join(out, "medalbox_layout.json"), "w"), indent=1)

# ---- the box's wood: the warm dark red-brown of the vanilla box (sampled from warrecords_a: ~ (96, 44, 34)), long grain
N = 1024
base = np.array([96, 46, 34], float)
g = Image.fromarray((rng.random((N // 2, N // 32)) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3))
grain = np.asarray(g, float) / 255 - 0.5
fine = Image.fromarray((rng.random((N, N // 8)) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)
fine = np.asarray(fine, float) / 255 - 0.5
wood = base * (1 + 0.22 * grain + 0.08 * fine)[..., None]
Image.fromarray(np.clip(wood, 0, 255).astype(np.uint8)).save(os.path.join(out, "medalbox_wood.png"))
# the front: the same wood with the brass diamond escutcheon and keyhole (as on the vanilla box)
fr = Image.fromarray(np.clip(wood, 0, 255).astype(np.uint8)).resize((1024, 256))
d = ImageDraw.Draw(fr)
cx, cy, rx, ry = 512, 128, 92, 46
d.polygon([(cx - rx, cy), (cx, cy - ry), (cx + rx, cy), (cx, cy + ry)], fill=(196, 160, 92), outline=(120, 92, 44))
d.polygon([(cx - rx + 10, cy), (cx, cy - ry + 6), (cx + rx - 10, cy), (cx, cy + ry - 6)], outline=(232, 204, 140))
d.ellipse([cx - 7, cy - 18, cx + 7, cy - 4], fill=(18, 12, 8))
d.polygon([(cx - 4, cy - 8), (cx + 4, cy - 8), (cx + 6, cy + 16), (cx - 6, cy + 16)], fill=(18, 12, 8))
fr.save(os.path.join(out, "medalbox_front.png"))

# ---- LOAD / SAVE: stencilled black on a brass plate, as on the vanilla trays
font = ImageFont.truetype(r"C:\Windows\Fonts\STENCIL.TTF", 150)
for word in ("LOAD", "SAVE"):
    im = Image.new("RGB", (512, 200), (176, 150, 96))
    a = np.asarray(im, float) * (1 + 0.06 * (rng.random((200, 512)) - 0.5))[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle([6, 6, 505, 193], outline=(90, 72, 40), width=6)
    bb = d.textbbox((0, 0), word, font=font)
    d.text(((512 - (bb[0] + bb[2])) / 2, (200 - (bb[1] + bb[3])) / 2), word, font=font, fill=(28, 24, 18))
    im.save(os.path.join(out, "tray_%s.png" % word.lower()))
print("records art ->", out, layout["aspect"])
