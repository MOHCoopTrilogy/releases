"""gen_rain73.py <base menus pak> <add dir> - v1.10.73 rain fixes for the attic window / skylight (gen_window_view.py's rain).

1. RAIN INSIDE THE ROOM (user: "it's raining inside the building, by the briefing door"). hzm_wx_rain_near is a streak sheet
   84 u beyond the gable wall (x 442), y -105 .. 525. The gable wall only spans y -20.9 .. 472.5: right of it the attic's WING runs
   on to x 514 (gen_window_view WING_Y / ROOM_X1) - so the sheet's y -105 .. -20.9 part stood INSIDE the wing, by the briefing
   door. Clipped to y >= WING_Y + 1 (uv interpolated: the streaks do not move or rescale); the far sheet (x 1093) is outside the house.
2. THE SKYLIGHT'S "GLITCHY STRAIGHT LINES". hzm_wx_skydrops tiled the window's drop texture (map, tcMod scale 1.2 / 0.7 + scroll),
   which was never made tileable: beads cut at the image border and a bottom-heavy density (drawn for the gable pane, clampmap) make
   hard seams - straight lines the full height of the pane when wrapped. Now its own TILEABLE texture (every bead and rivulet drawn
   with wrap-around, uniform density) for a sloped roof window: small beads, and rivulets that wander DOWN the fall line (the
   texture's +t, the roof's -v), scrolling slowly with gravity; two layers at different scales / speeds so no repeat lines up.
   Subtle: alpha <= 0.55, a lens (dark top, light bottom), no white dots.
"""
import math, os, re, sys, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

base, add = sys.argv[1:3]
ZB = zipfile.ZipFile(base)
mdir, tdir, sdir = (os.path.join(add, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)
WING_Y = -20.9


def write_model(nm, corners):
    ss = X.split_surfaces("s", corners)
    Pv = np.array([v[3] for s_ in ss for v in s_[2]])
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], ss))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    tik = ZB.read("models/menu/%s.tik" % nm).decode()
    names = [q[0] for q in ss]
    old = re.findall(r"(?m)^\tsurface (\S+) shader (\S+)$", tik)
    assert len(set(s for _, s in old)) == 1
    sl = "\n".join("\tsurface %s shader %s" % (n, old[0][1]) for n in names)
    tik = re.sub(r"(?m)(^\tsurface \S+ shader \S+\n?)+", sl + "\n", tik)
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(tik)


# ---------------------------------------------------------------- 1. the near rain sheet, clipped out of the wing
m = R.read_skd(ZB.read("models/menu/hzm_wx_rain_near.skd"))
assert len(m["surfaces"]) == 1
s = m["surfaces"][0]
V = [(np.array(v[3]), np.array(v[1]), np.array(v[0])) for v in s["verts"]]        # pos, uv (file), normal
tris = [tuple(t) for t in s["tris"]]
Y0 = WING_Y + 1.0
out = []
for t in tris:
    poly = [V[i] for i in t]
    res = []
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        ia, ib = a[0][1] >= Y0, b[0][1] >= Y0
        if ia:
            res.append(a)
        if ia != ib:
            f = (Y0 - a[0][1]) / (b[0][1] - a[0][1])
            res.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2]))
    for k in range(1, len(res) - 1):
        out.append([(0, tuple(q[0]), tuple(q[2]), (float(q[1][0]), float(q[1][1]))) for q in (res[0], res[k], res[k + 1])])
P = np.array([c[1] for tr in out for c in tr])
assert P[:, 1].min() >= Y0 - 1e-3, P[:, 1].min()
write_model("hzm_wx_rain_near", out)
print("rain_near: y %.1f .. %.1f (was -105 .. 525), %d tris" % (P[:, 1].min(), P[:, 1].max(), len(out)))

# ---------------------------------------------------------------- 2. the skylight's drops: tileable beads + rivulets
N, SS = 512, 3
W2 = N * SS
rng = np.random.default_rng(73)


def bead(img, cx, cy, rx, ry, strength):
    """a lens bead (dark top, light bottom, thin rim), drawn with wrap-around (tileable)"""
    R_ = max(rx, ry) * 1.3 + 2
    for ox in (-W2, 0, W2):
        for oy in (-W2, 0, W2):
            x, y = cx + ox, cy + oy
            x0, x1 = int(max(0, x - R_)), int(min(W2, x + R_ + 1))
            y0, y1 = int(max(0, y - R_)), int(min(W2, y + R_ + 1))
            if x1 <= x0 or y1 <= y0:
                continue
            sy, sx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dx, dy = (sx - x) / rx, (sy - y) / ry
            rr = np.sqrt(dx * dx + dy * dy)
            inside = np.clip((1.0 - rr) * min(rx, ry) / 1.5, 0, 1)
            lens = np.clip(0.5 + 0.5 * dy, 0, 1)
            rim = np.clip(1 - np.abs(rr - 0.85) / 0.15, 0, 1)
            col = 0.30 + 0.45 * lens - 0.18 * rim
            a = inside * (0.38 + 0.17 * rim) * strength
            reg = img[y0:y1, x0:x1]
            mk = a > reg[..., 3]
            for c, kc in ((0, 0.97), (1, 0.99), (2, 1.03)):
                reg[..., c] = np.where(mk, np.clip(col * kc, 0, 1), reg[..., c])
            reg[..., 3] = np.maximum(reg[..., 3], a)


beads = np.zeros((W2, W2, 4), np.float32)
for _ in range(1400):
    r = float(rng.choice([rng.uniform(1.0, 2.0), rng.uniform(2.0, 3.2), rng.uniform(3.2, 4.6)], p=[0.6, 0.32, 0.08])) * SS
    e = 1.0 + rng.uniform(0.0, 0.25)
    bead(beads, rng.uniform(0, W2), rng.uniform(0, W2), r / math.sqrt(e), r * math.sqrt(e), 1.0)
riv = np.zeros((W2, W2, 4), np.float32)
for _ in range(34):                     # rivulets: a drop running down the fall line (+t), wandering, thinning, a bead at its head
    x, y = rng.uniform(0, W2), rng.uniform(0, W2)
    L = rng.uniform(0.25, 0.7) * W2
    wob, amp = rng.uniform(0, 6.28), rng.uniform(1.5, 5.0) * SS
    n = int(L / (1.4 * SS))
    for i in range(n):
        t = i / n
        bead(riv, x + amp * math.sin(t * 9 + wob) + 0.3 * amp * math.sin(t * 23 + 2 * wob), y + L * t, 1.5 * SS, 1.8 * SS,
             0.45 + 0.30 * t)
    bead(riv, x + amp * math.sin(9 + wob), y + L, 2.4 * SS, 3.0 * SS, 1.0)
for nm, img in (("hzm_wx_skybeads", beads), ("hzm_wx_skyriv", riv)):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").resize((N, N), Image.LANCZOS)
    a = np.asarray(im)
    # tileability check: the wrapped seam must not differ from the interior (mean |edge column - next| like any other column pair)
    d_seam = np.abs(a[:, 0, 3].astype(int) - a[:, -1, 3].astype(int)).mean()
    d_in = np.abs(np.diff(a[:, :, 3].astype(int), axis=1)).mean()
    assert d_seam < 3 * d_in + 1, (nm, d_seam, d_in)
    im.save(os.path.join(tdir, nm + ".tga"))
SHP = [n for n in ZB.namelist() if n.startswith("scripts/") and n.endswith(".shader") and b"\nhzm_wx_skydrops\n" in ZB.read(n)]
assert len(SHP) == 1, SHP
txt = ZB.read(SHP[0]).decode("latin1")
new = ("hzm_wx_skydrops\n{\n\tnopicmip\n\tcull none\n\tsort 8.5\n"
       "\t{\n\t\tmap textures/menu/hzm_wx_skybeads.tga\n\t\tblendFunc blend\n\t\trgbGen entity\n\t\talphaGen entity\n"
       "\t\ttcMod scale 1.6 1.6\n\t\ttcMod scroll 0.0 -0.006\n\t}\n}")
# (in-game QA v1.10.73: the rivulet layer still read as thin vertical lines at LOOK UP - dropped; rain73's drop simulation runs
# real trickles down the slope)
pat = re.compile(r"(?m)^hzm_wx_skydrops\n\{\n.*?\n\}(?=\n|$)", re.S)
assert len(pat.findall(txt)) == 1
txt = pat.sub(lambda _: new, txt)
open(os.path.join(sdir, os.path.basename(SHP[0])), "w", newline="\n", encoding="latin1").write(txt)
print("skydrops: tileable beads + rivulets ->", SHP[0])

# ---------------------------------------------------------------- 3. LOOK UP: a sky with depth through the skylight
# (user, LOOK UP: "the sky behind is flat grey") - the one cloud deck (hzm_wx_top_cloud, z 1296) under rain light reads flat through
# the small pane. A second, lower layer of scud (soft wisps cut from the same deck's texture, offset and rescaled, alpha = the
# cloud cover like the deck - scenewx role 'cloud') drifts ~3x faster at z 1250: two speeds = depth. It sits ABOVE every plane
# pass (the engine flies them 620-1150 u out along the skylight normal: z <= ~1200), so the planes still cross in front of it.
import io  # noqa: E402
def fft_clouds(n, beta, seed):
    """fractal clouds by spectral synthesis (1/f^beta amplitude, random phase): periodic by construction - tiles with no seam and
    no half-tile repeat (the v1.10.67 deck was a photo cut: its seam drifted through the skylight with the scroll)"""
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    amp = f ** (-beta)
    amp[0, 0] = 0.0
    amp[f > 0.25] *= np.exp(-((f[f > 0.25] - 0.25) / 0.08) ** 2)
    z = np.real(np.fft.ifft2(amp * np.exp(2j * math.pi * r.random((n, n)))))
    return (z - z.mean()) / z.std()


src = np.asarray(Image.open(io.BytesIO(ZB.read("textures/menu/hzm_wx_top_cloud.jpg"))).convert("RGB"), np.float32) / 255
mu, sd = src.mean((0, 1)), src.std((0, 1))
z = fft_clouds(1024, 1.35, 1296)
deck = np.clip(mu[None, None, :] + z[..., None] * sd[None, None, :] * 1.15, 0, 1)
# the deck (tcMod scroll 0.004 0.0025) - the same tones as the v1.10.67 cut (mean / spread per channel), now seamless; replaced in place
Image.fromarray((deck * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_top_cloud.jpg"), quality=92)
cl = fft_clouds(512, 1.6, 1250)
cl = (cl - cl.min()) / (cl.max() - cl.min())
lo, hi = np.percentile(cl, 35), np.percentile(cl, 92)
a = np.clip((cl - lo) / (hi - lo), 0, 1) ** 1.6 * 0.62
rgb = np.clip(0.62 + 0.38 * cl, 0, 1)
im = Image.fromarray((np.dstack([rgb, rgb, rgb * 1.02, a]).clip(0, 1) * 255).astype(np.uint8), "RGBA").resize((512, 512), Image.LANCZOS)
im.save(os.path.join(tdir, "hzm_wx_top_scud.tga"))
Z = 1250.0
X0, X1, Y0_, Y1_ = -1400.0, 1800.0, -700.0, 2600.0
P4 = [(X0, Y0_, Z), (X1, Y0_, Z), (X1, Y1_, Z), (X0, Y1_, Z)]
U4 = [(0, 3.0), (3.0, 3.0), (3.0, 0), (0, 0)]                  # file uvs; 3 repeats across the deck
corners = [[(0, P4[k], (0.0, 0.0, -1.0), U4[k]) for k in tri] for tri in ((0, 1, 2), (0, 2, 3))]
ss = X.split_surfaces("s", corners)
Pv = np.array([v[3] for s_ in ss for v in s_[2]])
open(os.path.join(mdir, "hzm_wx_top_scud.skd"), "wb").write(X.build_skd("hzm_wx_top_scud", [("root", "worldbone")], ss))
open(os.path.join(mdir, "hzm_wx_top_scud.skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                         (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                         float(np.linalg.norm(Pv, axis=1).max()) + 1))
open(os.path.join(mdir, "hzm_wx_top_scud.tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel hzm_wx_top_scud.skd\n%s\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle hzm_wx_top_scud.skc\n}\n"
    % "\n".join("\tsurface %s shader hzm_wx_top_scud" % q[0] for q in ss))
txt = open(os.path.join(sdir, os.path.basename(SHP[0])), encoding="latin1").read()
assert "hzm_wx_top_scud" not in txt
txt += ("\nhzm_wx_top_scud\n{\n\tnopicmip\n\tcull none\n\tsort 8.21\n\t{\n\t\tmap textures/menu/hzm_wx_top_scud.tga\n\t\tblendFunc blend\n"
        "\t\trgbGen entity\n\t\talphaGen entity\n\t\ttcMod scroll 0.012 0.0075\n\t}\n}\n")
open(os.path.join(sdir, os.path.basename(SHP[0])), "w", newline="\n", encoding="latin1").write(txt)
print("top_scud: z %.0f, + its shader" % Z)
