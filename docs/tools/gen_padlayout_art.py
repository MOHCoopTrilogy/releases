"""gen_padlayout_art.py - art for the CONTROLLER LAYOUT page (ui/coop_padlayout.urc, v1.10.46).

Sources (CC0, "8th gen console vector gamepad collection" by the OpenGameArt user who made it for Past Future,
https://opengameart.org/content/8th-gen-console-vector-gamepad-collection - "I applied CC0 license to those assets"):
    H:/hzm_work/dl_gamepad_cc0/x/Xbox One.png, Dualshock 4.png   (2048x2048 RGBA, no console logos)
Writes into <mod>/textures/hud/:
    coop_pad_xbox.tga / coop_pad_ps.tga / coop_pad_generic.tga   1024x512, the pad cropped to its outline and centred
      (generic = the Xbox render with the four lettered face buttons painted neutral grey)
    coop_pg_x_NN.tga / coop_pg_p_NN.tga                           64x64, one cell each of coop_padglyphs(_ps).tga (16 cells)
    python docs/tools/gen_padlayout_art.py <mod dir> <xbox glyph atlas tga>
"""
import os, sys
from PIL import Image, ImageDraw

SRC = r"H:/hzm_work/dl_gamepad_cc0/x"
mod, xatlas = sys.argv[1], sys.argv[2]
out = os.path.join(mod, "textures", "hud")
os.makedirs(out, exist_ok=True)


def fit(im):
    bb = im.getchannel("A").getbbox()
    im = im.crop(bb)
    W, H = 1024, 512
    s = min((W - 40) / im.width, (H - 40) / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.paste(im, ((W - im.width) // 2, (H - im.height) // 2), im)
    return c


xb = Image.open(os.path.join(SRC, "Xbox One.png")).convert("RGBA")
ps = Image.open(os.path.join(SRC, "Dualshock 4.png")).convert("RGBA")
fit(xb).save(os.path.join(out, "coop_pad_xbox.tga"))
fit(ps).save(os.path.join(out, "coop_pad_ps.tga"))
# generic: the Xbox body, the coloured lettered face buttons covered by plain grey caps (positions in the 2048 render)
g = xb.copy()
d = ImageDraw.Draw(g)
for cx, cy in ((1408, 738), (1304, 840), (1512, 840), (1408, 944)):
    r = 50
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(36, 36, 36, 255))
    d.ellipse((cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6), fill=(120, 120, 120, 255))
fit(g).save(os.path.join(out, "coop_pad_generic.tga"))
for tag, path in (("x", xatlas), ("p", os.path.join(out, "coop_padglyphs_ps.tga"))):
    a = Image.open(path).convert("RGBA")
    for i in range(16):
        a.crop(((i % 4) * 64, (i // 4) * 64, (i % 4) * 64 + 64, (i // 4) * 64 + 64)).save(os.path.join(out, "coop_pg_%s_%02d.tga" % (tag, i)))
print("wrote pad art to", out)
