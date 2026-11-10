"""gen_gram_art.py <out dir> - the gramophone corner's paper and sound (menus3d pak).

  textures/menu/hzm_gram_sleeve<n>.tga   the record sleeve of theme n, leaning on the gramophone facing the room: a worn kraft
                                         12-inch sleeve with a pasted, type-set shop label (title + game) and the die-cut centre
                                         hole showing the record's own label colour.  The words are the theme's, nothing else.
  textures/menu/hzm_gram_label<n>.tga    that record's paper label, drawn as the ellipse the home camera sees on the turntable
                                         (22.6 deg above the record: height = 0.385 x width), so a change of record shows ON the disc
  textures/menu/hzm_gram_shuffle.tga     a manila tag, "Shuffle ?" in pencil, tucked in the sleeve while the pick is shuffle
  sound/menu/hzm_gram_drop.wav           the needle going down: a soft thump and a second of surface crackle (synthesised, 22 kHz)
  scripts/hzm_gram.shader                blend shaders for the tga
Titles / games come from gen_menumusic.THEMES (one table)."""
import math, os, struct, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_menumusic as GM  # noqa: E402

out = sys.argv[1]
tdir, sdir, adir = (os.path.join(out, *p) for p in (("textures", "menu"), ("scripts",), ("sound", "menu")))
for d in (tdir, sdir, adir):
    os.makedirs(d, exist_ok=True)
FD = r"C:\Windows\Fonts"
rng = np.random.default_rng(1943)
# the records' own label colours (pre-war shellac labels: oxblood, navy, maroon, bottle green, black-and-gold, plum)
LABEL_COL = [(122, 28, 24), (28, 40, 82), (92, 22, 40), (30, 62, 40), (24, 22, 20), (70, 34, 70), (22, 70, 86), (118, 84, 22)]   # + teal, mustard (v1.10.63)
INK = (34, 26, 20)


def paper(w, h, base, grain=6.0, blot=10.0, seed=0):
    r = np.random.default_rng(seed)
    g = r.normal(0, 1, (h, w)).astype(np.float32) * grain
    b = np.asarray(Image.fromarray((r.random((7, 7)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 - 0.5
    img = np.array(base, np.float32)[None, None, :] + (g + b * blot)[..., None]
    return img


def fit(d, text, font_path, max_w, size):
    while size > 8:
        f = ImageFont.truetype(font_path, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(font_path, size)


def sleeve(i, title, game):
    W = 512
    img = paper(W, W, (178, 138, 96), 5.0, 14.0, seed=10 + i)
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    edge = np.minimum.reduce([xx, yy, W - 1 - xx, W - 1 - yy])
    img -= (np.clip(1 - edge / 26.0, 0, 1) ** 2 * 38)[..., None]           # handled, darker edges
    # the die-cut hole: the black record behind it and its paper label
    cx, cy, rh = W / 2, W * 0.73, W * 0.17
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    hole = d2 < rh * rh
    img[hole] = (16, 15, 14)
    lab = d2 < (rh * 0.78) ** 2
    img[lab] = np.array(LABEL_COL[i], np.float32) + rng.normal(0, 3, (int(lab.sum()), 1))
    img[d2 < 7 ** 2] = (12, 11, 10)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    dr = ImageDraw.Draw(im)
    dr.ellipse((cx - rh * 0.70, cy - rh * 0.70, cx + rh * 0.70, cy + rh * 0.70), outline=(196, 160, 82, 255), width=2)
    # the pasted shop label: cream, type-set, slightly askew
    lab_im = Image.new("RGBA", (440, 210), (0, 0, 0, 0))
    li = np.clip(paper(440, 210, (232, 222, 196), 4.0, 8.0, seed=30 + i), 0, 255).astype(np.uint8)
    lab_im = Image.fromarray(li, "RGB").convert("RGBA")
    ld = ImageDraw.Draw(lab_im)
    ld.rectangle((6, 6, 433, 203), outline=INK + (255,), width=3)
    ld.rectangle((13, 13, 426, 196), outline=INK + (200,), width=1)
    no = "No. %d" % (i + 1)
    f0 = ImageFont.truetype(os.path.join(FD, "BOD_R.TTF"), 26)
    ld.text(((440 - ld.textlength(no, font=f0)) / 2, 20), no, font=f0, fill=INK + (255,))
    f1 = fit(ld, title.upper(), os.path.join(FD, "BOD_B.TTF"), 392, 64)
    ld.text(((440 - ld.textlength(title.upper(), font=f1)) / 2, 56), title.upper(), font=f1, fill=INK + (255,))
    f2 = fit(ld, game, os.path.join(FD, "BOD_I.TTF"), 380, 44)
    ld.text(((440 - ld.textlength(game, font=f2)) / 2, 140), game, font=f2, fill=(70, 30, 24, 255))
    lab_im = lab_im.rotate(-1.2, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(lab_im, (int((W - lab_im.width) / 2), 34))
    # the sleeve's own outline: square with softened, slightly worn corners
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).rounded_rectangle((3, 3, W - 4, W - 4), radius=9, fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(1.0))).copy()
    m[hole] = 255
    im.putalpha(Image.fromarray(m))
    im.save(os.path.join(tdir, "hzm_gram_sleeve%d.tga" % i))


def label(i):
    W, Hh = 256, 256
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    k = 0.385
    big = Image.new("RGBA", (W * 4, W * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    R = W * 2
    c = W * 2
    d.ellipse((c - R + 8, c - R * k + 8, c + R - 8, c + R * k - 8), fill=LABEL_COL[i] + (255,))
    d.ellipse((c - R * 0.80, c - R * 0.80 * k, c + R * 0.80, c + R * 0.80 * k), outline=(196, 160, 82, 255), width=10)
    d.ellipse((c - 22, c - 22 * k, c + 22, c + 22 * k), fill=(14, 13, 12, 255))
    big.resize((W, Hh), Image.LANCZOS).save(os.path.join(tdir, "hzm_gram_label%d.tga" % i))


def rlabel(i, title, game):
    """v1.10.66 the record's paper label as it really is - round, flat, for the 3D label disc (hzm_gram_disc<n>): the label colour,
    a gilt ring, the record number and title set in gilt Bodoni, the game below, the spindle hole"""
    W = 512
    big = Image.new("RGBA", (W * 2, W * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c, R = W, W - 4
    d.ellipse((c - R, c - R, c + R, c + R), fill=LABEL_COL[i] + (255,))
    d.ellipse((c - R * 0.90, c - R * 0.90, c + R * 0.90, c + R * 0.90), outline=(204, 170, 92, 255), width=10)
    gilt = (214, 182, 108, 255)
    f0 = ImageFont.truetype(os.path.join(FD, "BOD_R.TTF"), 64)
    no = "No. %d" % (i + 1)
    d.text((c, c - R * 0.55), no, font=f0, fill=gilt, anchor="mm")
    f1 = fit(d, title.upper(), os.path.join(FD, "BOD_B.TTF"), R * 1.40, 120)
    d.text((c, c - R * 0.24), title.upper(), font=f1, fill=gilt, anchor="mm")
    f2 = fit(d, game, os.path.join(FD, "BOD_I.TTF"), R * 1.20, 84)
    d.text((c, c + R * 0.36), game, font=f2, fill=gilt, anchor="mm")
    d.ellipse((c - 26, c - 26, c + 26, c + 26), fill=(10, 9, 8, 255))
    big.resize((W, W), Image.LANCZOS).convert("RGB").save(os.path.join(tdir, "hzm_gram_rlabel%d.jpg" % i), quality=95)


for i, th in enumerate(GM.THEMES):
    t, g = th[3].split("|")
    sleeve(i, t, g)
    label(i)
    rlabel(i, t, g)

# the shuffle tag: manila, a reinforced string hole, pencilled
TW, TH = 384, 170
img = paper(TW, TH, (214, 192, 140), 4.0, 10.0, seed=77)
tag = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
d = ImageDraw.Draw(tag)
d.ellipse((18, TH / 2 - 16, 50, TH / 2 + 16), fill=(196, 172, 120, 255), outline=(150, 128, 86, 255), width=3)
d.ellipse((28, TH / 2 - 6, 40, TH / 2 + 6), fill=(0, 0, 0, 0))
fh = ImageFont.truetype(os.path.join(FD, "BRADHITC.TTF"), 76)
txt = "Shuffle ?"
d.text((64 + (TW - 84 - d.textlength(txt, font=fh)) / 2, 28), txt, font=fh, fill=(58, 56, 60, 235))
m = Image.new("L", (TW, TH), 0)
ImageDraw.Draw(m).polygon([(0, 26), (26, 0), (TW - 2, 0), (TW - 2, TH - 2), (26, TH - 2), (0, TH - 28)], fill=255)
a = np.asarray(tag).copy()
a[..., 3] = np.minimum(a[..., 3], np.asarray(m.filter(ImageFilter.GaussianBlur(0.8))))
a[(np.arange(TH)[:, None] - TH / 2) ** 2 + (np.arange(TW)[None, :] - 34) ** 2 < 36, 3] = 0
Image.fromarray(a, "RGBA").rotate(6, resample=Image.BICUBIC, expand=True).save(os.path.join(tdir, "hzm_gram_shuffle.tga"))

sh = ["// [attic polish 2026-11-02] the gramophone corner's paper (generated by gen_gram_art.py)"]
names = ["hzm_gram_sleeve%d" % i for i in range(len(GM.THEMES))] + ["hzm_gram_label%d" % i for i in range(len(GM.THEMES))] + ["hzm_gram_shuffle"]
for n in names:
    sh.append("textures/menu/%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tclampmap textures/menu/%s.tga\n\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}" % (n, n))
# v1.10.66 the 3D pieces: opaque (the sleeve's rounded-corner alpha would cut the box's front - the box is square), lit like the room
for i in range(len(GM.THEMES)):
    sh.append("hzm_gram_rlabel%d\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_gram_rlabel%d.jpg\n\t\trgbGen identity\n\t}\n}" % (i, i))
    sh.append("hzm_gram_sleeve3d%d\n{\n\tcull none\n\t{\n\t\tclampmap textures/menu/hzm_gram_sleeve%d.tga\n\t\trgbGen identity\n\t}\n}" % (i, i))
sh.append("hzm_gram_tag3d\n{\n\tcull none\n\t{\n\t\tclampmap textures/menu/hzm_gram_shuffle.tga\n\t\talphaFunc GE128\n\t\trgbGen identity\n\t}\n}")
open(os.path.join(sdir, "hzm_gram.shader"), "w", newline="\n").write("\n".join(sh) + "\n")

# needle drop: a muffled thump (the arm settling) then surface noise: sparse clicks over a low, band-limited hiss, fading out
SR = 22050
n = int(SR * 1.25)
t = np.arange(n) / SR
thump = np.sin(2 * math.pi * 70 * t) * np.exp(-t / 0.035) * 0.55
hiss = np.convolve(rng.normal(0, 1, n), np.ones(6) / 6, "same") * 0.035
clicks = np.zeros(n)
for k in rng.choice(np.arange(int(0.05 * SR), n), 26, replace=False):
    L = int(rng.integers(8, 40))
    clicks[k:k + L] += rng.normal(0, 1, min(L, n - k)) * rng.uniform(0.08, 0.30) * np.exp(-np.arange(min(L, n - k)) / 6)
sig = thump + (hiss + clicks) * np.clip(t / 0.06, 0, 1) * np.exp(-np.maximum(t - 0.55, 0) / 0.35)
sig = np.convolve(sig, [0.25, 0.5, 0.25], "same")          # take the digital edge off (an old horn has no top end)
pcm = (np.clip(sig / max(1e-6, np.abs(sig).max()) * 0.6, -1, 1) * 32767).astype("<i2")
with wave.open(os.path.join(adir, "hzm_gram_drop.wav"), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
# v1.10.63 the radio swing record: the stock WAV (main/sound/mechanics/Mec_RadioMusic_01.wav, 22.05 kHz mono) -> the mp3 the menu
# player needs (it takes only sound/music/*.mp3); 44.1 kHz stereo 128k like the other themes
import subprocess  # noqa: E402
_src = r"G:\GOG\Medal of Honor - Allied Assault War Chest\main\sound\mechanics\Mec_RadioMusic_01.wav"
_dst = os.path.join(out, "sound", "music", "coop_menu", "mohaa_radio_music.mp3")
os.makedirs(os.path.dirname(_dst), exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", _src, "-ar", "44100", "-ac", "2", "-b:a", "128k", "-map_metadata", "-1",
                "-fflags", "+bitexact", "-flags:a", "+bitexact", _dst], check=True)
print("gramophone art + sound ->", out)
