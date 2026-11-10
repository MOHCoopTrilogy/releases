"""gen_wx_sky.py <out dir> - v1.10.67 the attic window's skies, cut from the game's own skybox art (no generated clouds).

Each time-of-day key is ONE side face of a stock MOHAA skybox (a 90 deg view, horizon on its middle row), cropped to its top 55 %
(the sky plus a strip of horizon haze the hills sit in) and resampled to 1024 x 512:
    night   mohnight1 ft (HD, starfield + moonlit cloud) with the afnight moon moved down to where the window can see it
    dawn    nordawn ft (pink and violet streaks)
    day     mohday1 rt (blue with fair-weather cloud)
    golden  cassino lf (low sun under gold cloud)
    dusk    bocdusk bk (afterglow under a deep blue)
    cloud   ddaystormy ft as a grey deck (the overcast / rain layer: alpha = cover, colour = daylight in the engine)
    flash   the same deck lit from inside (lightning: additive x the flash envelope)
Writes textures/menu/hzm_wx_sky_<key>.jpg and wx_sky.json (the plane: distance + extents in metres) into <out dir>.
"""
import io, json, os, sys, zipfile
import numpy as np
from PIL import Image, ImageFilter

out = sys.argv[1]
tdir = os.path.join(out, "textures", "menu")
os.makedirs(tdir, exist_ok=True)
G = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
HDS = G + r"\maintt\zzzzzzzzzz_coop_hd_skies.pk3"
AAH = G + r"\maintt\zzzzz-AA_HD_Project_Pak1.pk3"
EP2 = G + r"\maintt\pak1.pk3"
_z = {}


def face(pk, name):
    z = _z.setdefault(pk, zipfile.ZipFile(pk))
    return Image.open(io.BytesIO(z.read(name))).convert("RGB")


CROP = 0.55
W, H = 1024, 512


def cut(im):
    w, h = im.size
    return im.crop((0, 0, w, int(round(h * CROP)))).resize((W, H), Image.LANCZOS)


def grade(im, mul=(1, 1, 1), gamma=1.0, sat=1.0):
    a = np.asarray(im, np.float32) / 255
    a = np.power(np.clip(a, 0, 1), gamma) * np.array(mul, np.float32)
    if sat != 1.0:
        l = (a * [0.3, 0.59, 0.11]).sum(2, keepdims=True)
        a = l + (a - l) * sat
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


S = {}
# night: the HD moonlit sky, with the afnight moon (bk face) lifted out and set low on the left, ~1.3 deg across
night = cut(face(HDS, "env/hzmhd/mohnight1_ft.tga"))
mb = face(AAH, "env/afnight_bk.jpg")
mw, mh = mb.size
ma = np.asarray(mb, np.float32)
lum = ma.mean(2)
yy, xx = np.unravel_index(np.argmax(lum), lum.shape)
r = int(mw * 0.022)
ys, xs = np.nonzero(lum[max(0, yy - 3 * r):yy + 3 * r, max(0, xx - 3 * r):xx + 3 * r] > 170)
cy0, cx0 = ys.mean() + max(0, yy - 3 * r), xs.mean() + max(0, xx - 3 * r)
rad = max(3.0, np.sqrt(len(ys) / np.pi))
print("moon at", int(cx0), int(cy0), "radius %.1f px of %d" % (rad, mw))
R = int(rad * 3.2)
patch = Image.fromarray(ma[int(cy0) - R:int(cy0) + R, int(cx0) - R:int(cx0) + R].astype(np.uint8))
# placement: 0.8 deg wide, 2 deg above the horizon, 26 deg left of the plane axis: inside the home camera pane (25-30 deg left, -2.8..+1.4 deg)
px_per_deg = W / 90.0
scale = (0.8 * px_per_deg) / (2 * rad)
patch = patch.resize((max(8, int(patch.width * scale * 1.0)), max(8, int(patch.height * scale * 1.0))), Image.LANCZOS)
na = np.asarray(night, np.float32)
pa = np.asarray(patch, np.float32)
ph, pw = pa.shape[:2]
hz_row = H * (0.5 / CROP)                         # the horizon's row in the cut image (tan 1 .. 0 spans rows 0 .. hz_row)
import math
cx = W / 2 - math.tan(math.radians(26.0)) * (W / 2)          # image left = the viewer's left (+y)
cyy = hz_row - math.tan(math.radians(8.0)) * hz_row      # 8 deg up (QA 2026-11-09: at 2 deg it sat on the hills / roofline in LOOK OUTSIDE)
x0, y0 = int(cx - pw / 2), int(cyy - ph / 2)
# only the disc and a soft halo: the patch's own cloud surround is masked away (it stamped a square on the sky)
yy2, xx2 = np.mgrid[0:ph, 0:pw]
rr = np.hypot(yy2 - ph / 2, xx2 - pw / 2) / (rad * scale)
disc = np.clip((1.06 - rr) / 0.12, 0, 1)[..., None]
halo = (0.20 * np.exp(-((rr / 2.2) ** 2)))[..., None] * np.array([150, 170, 205], np.float32)
reg = na[y0:y0 + ph, x0:x0 + pw]
lit = pa * disc
na[y0:y0 + ph, x0:x0 + pw] = 255 - (255 - reg) * (255 - np.maximum(lit, halo)) / 255
S["night"] = grade(Image.fromarray(np.clip(na, 0, 255).astype(np.uint8)), (0.95, 1.0, 1.08), 1.0)
S["dawn"] = grade(cut(face(HDS, "env/hzmhd/nordawn_ft.tga")), (1.04, 0.98, 1.0), 0.95)
S["day"] = grade(cut(face(HDS, "env/hzmhd/mohday1_rt.tga")), (0.98, 1.0, 1.03), 1.0, 1.05)
S["golden"] = grade(cut(face(EP2, "env/ep2sky/cassino_lf.tga")), (1.02, 0.98, 0.95), 1.0)
S["dusk"] = grade(cut(face(AAH, "env/bocdusk_bk.jpg")), (0.92, 0.92, 1.0), 1.05)
_df = face(AAH, "env/ddaystormy_ft.jpg")      # the deck: the face's cloud band (rows 5-48 %), so its structure reaches the horizon
deck = _df.crop((0, int(_df.height * 0.05), _df.width, int(_df.height * 0.48))).resize((W, H), Image.LANCZOS)
dl = np.asarray(deck, np.float32).mean(2) / 255
dl = np.clip((dl - dl.min()) / (np.ptp(dl) + 1e-6), 0, 1)
S["cloud"] = Image.fromarray((np.stack([dl * 0.80 + 0.12] * 3, 2) * 255).astype(np.uint8))
fl = np.clip(dl ** 1.6 * 1.3, 0, 1)
fl = fl * (0.55 + 0.45 * np.exp(-(((np.arange(W) - W * 0.35) / (W * 0.25)) ** 2))[None, :])
S["flash"] = Image.fromarray((np.stack([fl * 0.86, fl * 0.90, fl * 1.0], 2) * 255).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
HR = int(H * 0.5 / CROP)


def fill_below(im, k):
    a = np.asarray(im, np.float32).copy()
    ref = a[HR - 10:HR - 4].mean(0)                 # the haze just above the horizon, per column
    t = np.clip((np.arange(H) - (HR - 4)) / 6.0, 0, 1)[:, None, None]
    a = a * (1 - t) + ref[None] * t
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


for k in ("night", "dawn", "day", "golden", "dusk"):
    S[k] = fill_below(S[k], k)
# the sky seen from below through the skylight: each key's skybox UP face (soft cloud shapes overhead), 1024 square
AAH4 = G + r"\maintt\zzzzz-AA_HD_Project_Pak4.pk3"
CLC = {"night": (0.20, 0.23, 0.32), "dawn": (0.96, 0.80, 0.82), "day": (0.97, 0.97, 0.99), "golden": (1.0, 0.82, 0.60), "dusk": (0.86, 0.62, 0.62)}
CLA = {"night": 0.75, "dawn": 0.95, "day": 0.95, "golden": 0.95, "dusk": 0.9}
UP = {"night": (HDS, "env/hzmhd/mohnight1_up.tga"), "dawn": (HDS, "env/hzmhd/nordawn_up.tga"), "day": (HDS, "env/hzmhd/mohday1_up.tga"),
      "golden": (EP2, "env/ep2sky/cassino_up.tga"), "dusk": (AAH, "env/bocdusk_up.jpg"), "cloud": (AAH, "env/ddaystormy_up.jpg")}
GR = {"night": ((0.95, 1.0, 1.08), 1.0), "dawn": ((1.04, 0.98, 1.0), 0.95), "day": ((0.98, 1.0, 1.03), 1.0), "golden": ((1.02, 0.98, 0.95), 1.0),
      "dusk": ((0.92, 0.92, 1.0), 1.05)}
for k, (pk, nm) in UP.items():
    im = face(pk, nm).resize((1024, 1024), Image.LANCZOS)
    if k == "cloud":
        l = np.asarray(im, np.float32).mean(2) / 255
        l = np.clip((l - l.min()) / (np.ptp(l) + 1e-6), 0, 1)
        im = Image.fromarray((np.stack([l * 0.80 + 0.12] * 3, 2) * 255).astype(np.uint8))
        fl = np.clip(l ** 1.6 * 1.3, 0, 1)
        Image.fromarray((np.stack([fl * 0.86, fl * 0.90, fl], 2) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_top_flash.jpg"), quality=92)
    else:
        im = grade(im, *GR[k])
        if k == "day":         # mohday1's UP face is mostly its sun's glare: the zenith is a plain blue, deeper overhead
            yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32) / 1023 - 0.5
            r = np.clip(np.hypot(xx, yy) / 0.7, 0, 1)[..., None]
            im = Image.fromarray((np.clip(np.array([0.38, 0.55, 0.85]) * (1 - r) + np.array([0.60, 0.72, 0.92]) * r, 0, 1) * 255).astype(np.uint8))
        # the skybox UP faces are bare gradients: a layer of the game's own fair-weather cloud (AA HD talonclouds, tiled 2x), lit
        # in the key's light - so the skylight shows soft clouds from below that drift with the texture scroll
        cl = np.asarray(face(AAH4, "textures/sky/talonclouds.jpg").resize((342, 342), Image.LANCZOS), np.float32).mean(2) / 255
        cl = np.tile(cl, (3, 3))[:1024, :1024]      # 3x: the skylight sees about a fifth of the ceiling plane
        al = np.clip((cl - 0.05) * 3.6, 0, 1) ** 0.9 * CLA[k]
        col = np.array(CLC[k], np.float32) * (0.78 + 0.35 * np.clip(cl * 2.2, 0, 1))[..., None]
        base = np.asarray(im, np.float32) / 255
        im = Image.fromarray((np.clip(base * (1 - al[..., None]) + col * al[..., None], 0, 1) * 255).astype(np.uint8))
    im.save(os.path.join(tdir, "hzm_wx_top_%s.jpg" % k), quality=92)
for k, im in S.items():
    im.save(os.path.join(tdir, "hzm_wx_sky_%s.jpg" % k), quality=92)
# the plane, in metres from the window (wx_town.py and gen_window_view.py share this): a 90 deg face seen from the home eye
D = 29.9          # the UI scene clips at 2048 units (renderer: RDF_NOWORLDMODEL zFar) - the sky stands 37.4 m from the home eye
EYE_X = -36.7 / 52.5
half = (D + 358.05 / 52.5 - EYE_X)
info = {"D": D, "yL": 21.0 / 52.5 + half, "yR": 21.0 / 52.5 - half, "zT": half, "zB": -half * (2 * CROP - 1)}
json.dump(info, open(os.path.join(out, "wx_sky.json"), "w"), indent=1)
print(info)
