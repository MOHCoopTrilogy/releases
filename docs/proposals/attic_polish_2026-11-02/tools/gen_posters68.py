"""gen_posters68.py <out add dir> <out json> - v1.10.68: real WWII Allied posters on the MP room's walls.

User (2026-11-09): the multiplayer / join-game room "feels barren" - hang real liberation-era WWII posters. Public domain only
(US federal works, PD-USGov, verified on each Commons file page), no Axis imagery. Sources and credits: docs/SKIN_CREDITS.md,
hzm_credits.txt; the downloads (one folder each, SOURCE_URL.txt beside the scan) are under H:\\hzm_work\\posters68.

Each poster hangs like the real thing: US OWI sizes (20 x 28 in, 51 x 71 cm; the Shahn 28 x 20), its centre at 1.55 m, a
degree or so off level, the paper 3 mm off the wall with the corners curling away (the lower ones more), four pins, the print
a little faded and yellowed with worn edges, and a soft baked shadow on the wall behind. The room is baked (rgbGen identity),
so the paper carries its light: the hub's plaster level there (LIGHT) with a gentle top-down falloff.
"""
import json, math, os, sys
sys.path.append(os.path.join(os.environ.get("APPDATA", ""), "Python", "Python%d%d" % sys.version_info[:2], "site-packages"))   # (run with python -I: it reads downloaded scans)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skx as X  # noqa: E402

out, js = sys.argv[1:3]
mdir, tdir, sdir = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts"))
for d_ in (mdir, tdir, sdir):
    os.makedirs(d_, exist_ok=True)
SRC = r"H:\hzm_work\posters68"
U = 52.5
IN = 0.0254 * U
LIGHT = float(os.environ.get("POSTER_LIGHT", "0.70"))      # (0.80 read a little bright against the plaster)
# name, scan folder, wall (plane point, inward normal), centre along the wall, size (w, h in inches), tilt deg, curl
POSTERS = [
    ("un_fight", "p3_un_fight_freedom", ("x", 279.09, -1), 146.0, (20, 28), -0.8, 1.0),
    ("united", "p2_united_strong", ("y", -136.5, 1), 254.0, (20, 28), 0.6, 0.8),
    ("liberty", "p1_americans_liberty", ("y", 178.5, -1), 142.0, (20, 28), 1.1, 1.2),
    ("frworkers", "p5_french_workers", ("y", 178.5, -1), 2.0, (28, 20), -0.5, 0.9),
]
ZC = 1.55 * U
rng = np.random.default_rng(1944)


def frame(wall, along):
    ax, val, sgn = wall
    n = np.array([sgn, 0, 0] if ax == "x" else [0, sgn, 0], float)
    p0 = np.array([val, along, ZC] if ax == "x" else [along, val, ZC], float)
    right = np.cross(-n, [0, 0, 1.0])
    return p0, n, right / np.linalg.norm(right)


def tri(p, uv):
    p = [np.asarray(q, float) for q in p]
    nn = np.cross(p[1] - p[0], p[2] - p[0])
    ln = np.linalg.norm(nn)
    if ln < 1e-9:
        return None
    nn /= ln
    return [(0, tuple(p[k]), tuple(-nn), (float(uv[k][0]), float(1 - uv[k][1]))) for k in range(3)]


def grid(P, UV, nu, nv):
    out = []
    K = lambda i, j: i * (nv + 1) + j
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = K(i, j), K(i + 1, j), K(i + 1, j + 1), K(i, j + 1)
            for t in ((a, b, c), (a, c, d)):
                q = tri([P[k] for k in t], [UV[k] for k in t])
                if q:
                    out.append(q)
    return out


def age(img, w, h):
    """faded, yellowed print with worn edges, a little dust; the room's light baked in (top a touch brighter)"""
    im = img.convert("RGB").resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    g = a.mean(2, keepdims=True)
    a = a * 0.82 + g * 0.18                                   # fade: a little desaturated
    a = a * np.array([1.0, 0.96, 0.86]) + np.array([0.05, 0.04, 0.0])   # yellowed paper
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]).astype(np.float32)
    wear = np.clip(e / (0.02 * w), 0, 1) ** 0.6
    a = a * (0.80 + 0.20 * wear[..., None]) + (1 - wear[..., None]) * np.array([0.06, 0.05, 0.03])
    dust = np.asarray(Image.fromarray((rng.random((h // 8, w // 8)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    a = a * (0.96 + 0.06 * dust[..., None])
    light = LIGHT * (1.06 - 0.14 * (yy / h))[..., None]
    return Image.fromarray((np.clip(a * light, 0, 1) * 255 + 0.5).astype(np.uint8))


parts, SH, info = [], [], []
pins = []
shadows = []
for name, folder, wall, along, (wi, hi_), tilt, curl in POSTERS:
    scan = Image.open(os.path.join(SRC, folder, "poster.jpg"))
    W_, H_ = wi * IN, hi_ * IN
    # the art: the scan keeps its own proportions inside the sheet (a narrow paper margin where the aspect differs - no stretch)
    sa, pa = scan.size[0] / scan.size[1], W_ / H_
    tw, th = (768, int(768 / pa)) if pa >= 1 else (int(1024 * pa), 1024)
    tw, th = tw - tw % 4, th - th % 4
    sheet = Image.new("RGB", (tw, th), (226, 218, 196))
    if sa > pa:
        fw, fh = tw - 8, int((tw - 8) / sa)
    else:
        fh, fw = th - 8, int((th - 8) * sa)
    sheet.paste(scan.convert("RGB").resize((fw, fh), Image.LANCZOS), ((tw - fw) // 2, (th - fh) // 2))
    age(sheet, tw, th).save(os.path.join(tdir, "hzm_poster_%s.jpg" % name), quality=92)
    p0, n, right = frame(wall, along)
    up = np.array([0, 0, 1.0])
    c, s_ = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    r2, u2 = right * c + up * s_, up * c - right * s_
    nu, nv = 8, 10
    P, UV = [], []
    for i in range(nu + 1):
        for j in range(nv + 1):
            x, y = i / nu - 0.5, j / nv - 0.5
            # off the wall: 0.15 u everywhere, the corners curling out (lower corners more), the middle of the edges a little
            cw = (abs(2 * x) ** 4) * (abs(2 * y) ** 4) * (1.0 if y < 0 else 0.55) + 0.12 * (abs(2 * x) ** 6 + abs(2 * y) ** 6)
            off = 0.15 + curl * 0.9 * cw
            P.append(p0 + n * off + r2 * x * W_ + u2 * y * H_)
            UV.append((i / nu, j / nv))
    parts.append(("hzm_poster_%s" % name, grid(P, UV, nu, nv)))
    SH.append("hzm_poster_%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_poster_%s.jpg\n\t\trgbGen identity\n\t}\n}" % (name, name))
    # pins: a small domed steel head at each corner, inset 1.2 u, on the paper (pressing it to the wall there)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        q = p0 + n * 0.2 + r2 * sx * (W_ / 2 - 1.2) + u2 * sy * (H_ / 2 - 1.2)
        rr = 0.28
        ring = [q + (r2 * math.cos(a) + u2 * math.sin(a)) * rr for a in np.linspace(0, 2 * math.pi, 9)]
        top = q + n * 0.25
        for k in range(8):
            t = tri([ring[k], ring[k + 1], top], [(0.2, 0.2), (0.8, 0.2), (0.5, 0.8)])
            if t:
                pins.append(t)
    # the shadow on the wall: a soft dark sheet, offset down and a little to the room's light side
    so = p0 + n * 0.05 - u2 * 0.6 + r2 * 0.3
    E = [so + r2 * sx * (W_ / 2 + 2.2) + u2 * sy * (H_ / 2 + 2.2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for t in ((0, 1, 2), (0, 2, 3)):
        q = tri([E[k] for k in t], [[(0, 0), (1, 0), (1, 1), (0, 1)][k] for k in t])
        if q:
            shadows.append(q)
    info.append(dict(name=name, centre=[round(v, 1) for v in p0], size=[round(W_, 1), round(H_, 1)]))
# pin texture (steel) and shadow texture (soft rectangle, multiply)
Image.new("RGB", (16, 16), (92, 90, 86)).save(os.path.join(tdir, "hzm_poster_pin.jpg"), quality=95)
sh = Image.new("L", (128, 128), 255)
ImageDraw.Draw(sh).rectangle((22, 22, 106, 106), fill=170)
sh = sh.filter(ImageFilter.GaussianBlur(7))
Image.merge("RGB", (sh, sh, sh)).save(os.path.join(tdir, "hzm_poster_shadow.jpg"), quality=92)
parts += [("hzm_poster_pin", pins), ("hzm_poster_shadow", shadows)]
SH.append("hzm_poster_pin\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_poster_pin.jpg\n\t\trgbGen identity\n\t}\n}")
SH.append("hzm_poster_shadow\n{\n\tnopicmip\n\tcull none\n\tsort decal\n\tpolygonOffset\n\t{\n\t\tmap textures/menu/hzm_poster_shadow.jpg\n"
          "\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}\n}")
surfs, sl = [], []
for k, (sh_, cr) in enumerate(parts):
    ss = X.split_surfaces("s%d_" % k, cr)
    surfs += ss
    sl += ["\tsurface %s shader %s" % (q[0], sh_) for q in ss]
assert len(surfs) <= 30
nm = "hzm_hub_posters"
Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                              (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(), float(np.linalg.norm(Pv, axis=1).max()) + 1))
open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\n"
    "animations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))
open(os.path.join(sdir, "hzm_posters68.shader"), "w", newline="\n").write("\n\n".join(SH) + "\n")
json.dump(dict(posters=info, line='scenemodel "models/menu/hzm_hub_posters.tik" 0 0 0 0'), open(js, "w"), indent=1)
print("posters:", ", ".join("%s at %s" % (p["name"], p["centre"]) for p in info), "-", len(surfs), "surfaces")
