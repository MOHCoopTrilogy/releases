"""stock_preview.py <out.jpg> <tik> [<tik> ...] - CPU-only textured previews of stock MOHAA / SH / BT models (no game client, no GPU):
each model is loaded the way gen_gram_model.py writes it for the attic (bone pose + tik scale baked in), its shaders resolved to their
first texture stage through the game's scripts/*.shader, and rasterised with a z-buffer at a 3/4 view under a simple key + fill
light.  One labelled cell per model with its posed size in game units, so stock candidates can be judged for detail, texture and
scale before anything is baked."""
import io, math, os, re, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

H_ = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(H_, "gen_gram_model.py"), encoding="utf-8").read().split("# ---- the phonograph")[0]
_ns = {"__file__": os.path.join(H_, "gen_gram_model.py")}
_argv, sys.argv = sys.argv, [sys.argv[0], os.path.join(os.environ.get("TEMP", "."), "stock_preview_tmp")]
exec(compile(_src, "gen_gram_model.py", "exec"), _ns)
sys.argv = _argv
load, rd, LOWER = _ns["load"], _ns["rd"], _ns["LOWER"]
# Spearhead / Breakthrough paks too (lower priority than main for the same name, so main's copy wins as in the game's base layer)
_G = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
for _d in ("mainta", "maintt"):
    for _f in sorted(os.listdir(os.path.join(_G, _d))):
        if _f.lower().startswith("pak") and _f.lower().endswith(".pk3"):
            _z = zipfile.ZipFile(os.path.join(_G, _d, _f))
            for _n in _z.namelist():
                LOWER.setdefault(_n.lower(), (_z, _n))

SHADERS = {}


def _parse_shaders(txt):
    """name -> first map / clampmap of each shader block (brace-counted; comments stripped)"""
    txt = re.sub(r"//[^\n]*", "", txt)
    toks = re.findall(r"\{|\}|[^\s{}]+", txt)
    i, depth, name, body = 0, 0, None, []
    while i < len(toks):
        t = toks[i]
        if t == "{":
            if depth == 0:
                name, body = toks[i - 1] if i else None, []
            depth += 1
        elif t == "}":
            depth -= 1
            if depth == 0 and name:
                for k, w in enumerate(body[:-1]):
                    if w.lower() in ("map", "clampmap", "animmap") and not body[k + 1].startswith("$"):
                        SHADERS.setdefault(name.lower(), body[k + 1] if w.lower() != "animmap" else body[k + 2])
                        break
                name = None
        elif depth > 0:
            body.append(t)
        i += 1


for name, (z, real) in LOWER.items():
    if name.startswith("scripts/") and name.endswith(".shader"):
        _parse_shaders(z.read(real).decode("latin-1", "ignore"))


# v1.10.66 (user: the desk props "read as super low quality"): STOCK_HD=1 takes the LARGEST copy of a texture found in ANY pak of
# main / mainta / maintt - .tga, .jpg or .dds, the game's own and the mod's HD packs (e.g. the typewriter: 128 px stock tga, 256 px
# stock dds, 1024 px in zzzzzzzzzz_coop_hd_m3l1a.pk3). Off by default: earlier exports (the rack guns) stay as baked.
_HD = None


def _hd_index():
    global _HD
    if _HD is None:
        _HD = {}
        for _d in ("main", "mainta", "maintt"):
            for _f in sorted(os.listdir(os.path.join(_G, _d))):
                if not _f.lower().endswith(".pk3"):
                    continue
                try:
                    _z = zipfile.ZipFile(os.path.join(_G, _d, _f))
                except Exception:
                    continue
                for _n in _z.namelist():
                    b_, e_ = os.path.splitext(_n.lower())
                    if e_ in (".tga", ".jpg", ".dds"):
                        _HD.setdefault(b_, []).append((_z, _n))
    return _HD


def _hd_texture(base):
    best, bn = None, 0
    for z, real in _hd_index().get(base.lower(), []):
        try:
            im = Image.open(io.BytesIO(z.read(real)))
            n = im.size[0] * im.size[1]
        except Exception:
            continue
        if n > bn:
            best, bn = im, n
    return best


def texture(shader):
    cands = [SHADERS.get(shader.lower(), ""), shader]
    if os.environ.get("STOCK_HD"):
        for c in cands:
            if c:
                im = _hd_texture(os.path.splitext(c)[0])
                if im is not None:
                    return np.asarray(im.convert("RGB")).astype(np.float32)
    for c in cands:
        if not c:
            continue
        base = os.path.splitext(c)[0]
        for ext in (".tga", ".jpg", os.path.splitext(c)[1]):
            k = (base + ext).lower()
            if k in LOWER:
                z, real = LOWER[k]
                return np.asarray(Image.open(io.BytesIO(z.read(real))).convert("RGB")).astype(np.float32)
    return None


def render(tik, W=420, Hh=360, yaw=35.0, pitch=22.0):
    surfs = load(tik)
    P = np.vstack([s["P"] for s in surfs])
    lo, hi = P.min(0), P.max(0)
    ctr = (lo + hi) / 2
    rad = np.linalg.norm(hi - lo) / 2 + 1e-3
    a, b = math.radians(yaw), math.radians(pitch)
    fwd = np.array([math.cos(b) * math.cos(a), math.cos(b) * math.sin(a), -math.sin(b)])
    eye = ctr - fwd * rad * 3.2
    right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    F = Hh * 0.5 / math.tan(math.radians(20))
    img = np.full((Hh, W, 3), 42.0, np.float32)
    zb = np.full((Hh, W), 1e9, np.float32)
    L1 = np.array([-0.4, -0.6, 0.7]); L1 /= np.linalg.norm(L1)
    yy, xx = np.mgrid[0:Hh, 0:W] + 0.5
    for s in surfs:
        tex = texture(s["shader"])
        Q = s["P"] - eye
        x, y, zz = Q @ right, Q @ up, Q @ fwd
        sx, sy = W / 2 + x / zz * F, Hh / 2 - y / zz * F
        for t in s["tris"]:
            ax, ay, bx, by, cx, cy = sx[t[0]], sy[t[0]], sx[t[1]], sy[t[1]], sx[t[2]], sy[t[2]]
            x0, x1 = int(max(0, min(ax, bx, cx))), int(min(W, max(ax, bx, cx) + 1))
            y0, y1 = int(max(0, min(ay, by, cy))), int(min(Hh, max(ay, by, cy) + 1))
            if x0 >= x1 or y0 >= y1:
                continue
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-9:
                continue
            X, Y = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
            l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
            l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
            l3 = 1 - l1 - l2
            ins = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
            z = l1 * zz[t[0]] + l2 * zz[t[1]] + l3 * zz[t[2]]
            sub = zb[y0:y1, x0:x1]
            m = ins & (z < sub)
            if not m.any():
                continue
            sub[m] = z[m]
            n = s["N"][t].mean(0)
            n /= np.linalg.norm(n) + 1e-9
            shade = 0.35 + 0.65 * max(0.0, float(abs(n @ L1)))
            if tex is not None:
                u = l1 * s["U"][t[0], 0] + l2 * s["U"][t[1], 0] + l3 * s["U"][t[2], 0]
                v = l1 * s["U"][t[0], 1] + l2 * s["U"][t[1], 1] + l3 * s["U"][t[2], 1]
                th, tw = tex.shape[:2]
                c = tex[(np.mod(v[m], 1) * th).astype(int) % th, (np.mod(u[m], 1) * tw).astype(int) % tw]
            else:
                c = np.array([200, 0, 200], np.float32)
            img[y0:y1, x0:x1][m] = c * shade
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), hi - lo


if __name__ == "__main__":
    out, tiks = sys.argv[1], sys.argv[2:]
    F1 = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 16)
    cols = 4
    rows = (len(tiks) + cols - 1) // cols
    S = Image.new("RGB", (cols * 430 + 10, rows * 400 + 10), (20, 20, 20))
    d = ImageDraw.Draw(S)
    for i, t in enumerate(tiks):
        x, y = 10 + (i % cols) * 430, 10 + (i // cols) * 400
        try:
            im, size = render(t)
            S.paste(im, (x, y))
            lab = "%d. %s  %dx%dx%d u" % (i + 1, t.split("/")[-1].replace(".tik", ""), size[0], size[1], size[2])
        except Exception as e:
            lab = "%d. %s  FAILED %s" % (i + 1, t.split("/")[-1], str(e)[:30])
        d.text((x, y + 364), lab, font=F1, fill=(235, 220, 190))
    S.save(out, quality=88)
    print(out, S.size)
