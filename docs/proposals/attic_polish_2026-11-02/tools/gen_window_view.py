"""gen_window_view.py <town bake dir> <sky dir> <base pak> <out dir> - v1.10.67 the attic window shows the outside.

User (2026-11-09): "Can you make the window in the main menu actually show outside? Maybe a tree and the sky? With the time of day
mirroring the time of day in real life. Also, occasionally rain and thunderstorms other times sunny out there? Needs to look lovely."

The gable window was a frame on a solid wall (its glass plane is a bake 'skip' material). This generator:
  1. cuts the pane out of the baked wall: the wall triangles of atc_bg2 / atc_bgng1 lose the pane rectangle (re-triangulated around
     it, uv interpolated - no re-bake), and every room triangle beyond the wall (the roof's overhang) is clipped away, so the opening
     looks out onto whatever is behind it.  The cut pieces go to one new surface per model (the old surfaces are full at 900 verts).
  2. puts the outside behind it, each layer a scene model driven by the engine's `scenewx` director (cl_uiscene.cpp, menu-attic67):
       sky        five skies (night / dawn / day / golden / dusk; gen_wx_sky.py, cut from the game's skybox art), additive, each
                  weighted by the local clock; the cloud deck (alpha = cloud cover) and the lightning-lit deck (x flash) over them
       tint       the town (wx_town.py: near roofs, the town, the church, two ridges - baked once, neutral light) and the oak (the
                  stock 3D tree, swaying) multiplied by the outside light: blue at night, warm at golden hour, dim under rain
       lights     the town's lit windows (additive, night-ness)
       rain       two streak sheets at different depths (scrolling) and the drops on the glass
       flash      (the engine also flashes the whole room on a strike and plays a distant thunder clap 1-4 s later)
  3. writes wx_scene.json: the scene lines make_attic_polish.py adds to the attic (and the new-game attic, whose camera sees the pane).
Coordinates: the town bake is in metres on the game axes; game units = metres * 52.5.
"""
import io, json, math, os, struct, sys, wave, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402
import skd_read as R  # noqa: E402

town, skyd, basepak, out = sys.argv[1:5]
mdir, tdir, sdir, snd = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts", "sound/menu"))
for d in (mdir, tdir, sdir, snd):
    os.makedirs(d, exist_ok=True)
U = 52.5
WALL_X = 358.05
# the gable pane and the skylight (attic67_edit.py -> window67.json, BU): the pane in game units y0 y1 z0 z1
W67 = json.load(open(os.environ.get("WX_WINJSON", r"H:\hzm_work\attic62\window67.json")))
_g = W67["gable"]
WIN = (-_g["x1"] * 52.5, -_g["x0"] * 52.5, _g["z0"] * 52.5, _g["z1"] * 52.5)
SKY_CORNERS = np.array([(c[1] * 52.5, -c[0] * 52.5, c[2] * 52.5) for c in W67["skylight"]["corners"]])     # game units
WC = np.array([WALL_X, (WIN[0] + WIN[1]) / 2, (WIN[2] + WIN[3]) / 2])
BEYOND = WALL_X + 2.2                        # room triangles past this AND left of the right wing are outside the house
ROOM_X1 = 516.0                              # the attic floor quad ran on to x 712: a floorboard wedge in the window's right pane
WING_Y = -20.9                               # the gable wall spans y -20.9..472.5; right of it (y < -20.9) the room runs on to x 514
G = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
rng = np.random.default_rng(1944)
SH = ["// v1.10.67 the attic window's outside (gen_window_view.py). Sort 8.x: after the room's opaque, before its own glows."]
LINES = []          # scene lines
WX = []             # scenewx lines


# ------------------------------------------------------------------ 1. the hole
def clip_poly(poly, axis, val, keep_less):
    """Sutherland-Hodgman on one half-space; poly = list of (pos3, nrm3, uv2) as numpy arrays"""
    outp = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia = (a[0][axis] <= val) if keep_less else (a[0][axis] >= val)
        ib = (b[0][axis] <= val) if keep_less else (b[0][axis] >= val)
        if ia:
            outp.append(a)
        if ia != ib:
            t = (val - a[0][axis]) / (b[0][axis] - a[0][axis])
            outp.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return outp


def fan(poly):
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def minus_rect(poly):
    """poly minus the pane rectangle (in y/z, on the wall plane) -> list of polygons"""
    y0, y1, z0, z1 = WIN
    res, rest = [], poly
    for axis, val in ((1, y0), (1, y1), (2, z0), (2, z1)):
        if len(rest) < 3:
            break
        if (axis, val) in ((1, y0), (2, z0)):
            outside = clip_poly(rest, axis, val, True)
            rest = clip_poly(rest, axis, val, False)
        else:
            outside = clip_poly(rest, axis, val, False)
            rest = clip_poly(rest, axis, val, True)
        if len(outside) >= 3:
            res.append(outside)
    return res          # `rest` (inside the pane) is dropped


def patch_model(z, name):
    b = z.read("models/menu/%s.skd" % name)
    d = R.read_skd(b)
    tik = z.read("models/menu/%s.tik" % name).decode("latin-1")
    newtris = []        # corners (bone, pos, nrm, uv) in file winding
    shader_of = {}
    for ln in tik.splitlines():
        p = ln.split()
        if len(p) >= 4 and p[0] == "surface" and p[2] == "shader":
            shader_of[p[1]] = p[3]
    cut_shader = None
    ncut = nclip = 0
    for s in d["surfaces"]:
        V = s["verts"]
        P = np.array([v[3] for v in V])
        keep = []
        for t in s["tris"]:
            tp = P[t]
            on_wall = np.all(np.abs(tp[:, 0] - WALL_X) < 0.02)
            out_pt = ((tp[:, 0] > BEYOND) & (tp[:, 1] > WING_Y)) | (tp[:, 0] > ROOM_X1)      # ROOM_X1: nothing of the room lies past its back wall
            past = bool(out_pt.any())
            hits = on_wall and tp[:, 1].max() > WIN[0] and tp[:, 1].min() < WIN[1] and tp[:, 2].max() > WIN[2] and tp[:, 2].min() < WIN[3]
            if not (hits or past):
                keep.append(t)
                continue
            if out_pt.all():
                nclip += 1
                continue                     # wholly outside: gone
            poly = [(np.array(V[i][3]), np.array(V[i][0]), np.array(V[i][1])) for i in t]
            polys = [poly]
            if past:
                # the triangle minus the quadrant {x > BEYOND, y > WING_Y}: (x <= BEYOND) + (x >= BEYOND and y <= WING_Y)
                polys = [clip_poly(poly, 0, BEYOND, True), clip_poly(clip_poly(clip_poly(poly, 0, BEYOND, False), 1, WING_Y, True), 0, ROOM_X1, True)]
                polys = [q for q in polys if len(q) >= 3]
                nclip += 1
            if hits:
                polys = [q for pp in polys if len(pp) >= 3 for q in minus_rect(pp)]
                ncut += 1
            fn = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
            for pp in polys:
                for tri in fan(pp):
                    c = [(0, tuple(x[0]), tuple(x[1]), tuple(x[2])) for x in tri]
                    if np.dot(np.cross(np.array(c[1][1]) - c[0][1], np.array(c[2][1]) - c[0][1]), fn) < 0:
                        c = [c[0], c[2], c[1]]
                    newtris.append(c)
            cut_shader = shader_of.get(s["name"], cut_shader)
        s["tris"] = np.array(keep, int).reshape(-1, 3)
    surfs = [(s["name"], s["tris"], s["verts"]) for s in d["surfaces"]]
    extra = X.split_surfaces("wx", newtris) if newtris else []
    surfs = [s for s in surfs if len(s[1])] + extra
    open(os.path.join(mdir, name + ".skd"), "wb").write(X.build_skd(d["name"], d["bones"], surfs))
    lines = []
    for ln in tik.splitlines():
        p = ln.split()
        if len(p) >= 4 and p[0] == "surface" and p[2] == "shader" and p[1] not in [s[0] for s in surfs]:
            continue
        lines.append(ln)
        if ln.strip().startswith("skelmodel"):
            pass
    j = max(i for i, ln in enumerate(lines) if ln.strip().startswith(("surface", "skelmodel")))     # (all surfaces may have been re-cut)
    for s in extra:
        lines.insert(j + 1, "\tsurface %s shader %s" % (s[0], cut_shader))
        j += 1
    open(os.path.join(mdir, name + ".tik"), "w", newline="\n").write("\n".join(lines) + "\n")
    print("hole %-10s cut %d wall tris, clipped %d outside, +%d tris in %d surfaces" % (name, ncut, nclip, len(newtris), len(extra)))


zb = zipfile.ZipFile(basepak)
for nm in ("atc_bg1", "atc_bg2", "atc_bgng1"):
    patch_model(zb, nm)


class _DirPak:
    """the stage dir's models read like the pak (the floor is a group of its own: build_models2 -> stage62, not in the base pak)"""
    def __init__(self, root):
        self.root = root

    def read(self, name):
        return open(os.path.join(self.root, name), "rb").read()


# the attic floor ran on under the gable wall: through the bigger pane it was a wooden deck outside (QA, 2026-11-09)
STAGE = os.environ.get("WX_STAGE", r"H:\hzm_work\attic62\stage62")
for f in sorted(os.listdir(os.path.join(STAGE, "models", "menu"))):
    if f.startswith(("atc_floor", "atc_chrome", "atc_props", "atc_projector", "atc_fan")) and f.endswith(".skd"):
        patch_model(_DirPak(STAGE), f[:-4])


# ------------------------------------------------------------------ helpers: a model from triangles in game units
def write_model(nm, tris, uvs, shader, flip_v=True, parts=None, path="models/menu", line=True):
    """tris (T,3,3) game units, uvs (T,3,2) blender-style (v up) -> models/menu/<nm>.tik/skd/skc, one shader; or parts =
    [(shader, tris, uvs)]: a surface set per shader"""
    if parts is None:
        parts = [(shader, tris, uvs)]
    surfs, sl = [], []
    for k, (sh_, tr_, uv_) in enumerate(parts):
        corners = []
        for p, u in zip(tr_, uv_):
            n = np.cross(p[1] - p[0], p[2] - p[0])
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                continue
            n = n / ln
            c = [(0, tuple(p[k2]), tuple(-n), (float(u[k2][0]), float(1 - u[k2][1]) if flip_v else float(u[k2][1]))) for k2 in range(3)]
            corners.append(c)
        if not corners:
            continue
        ss = X.split_surfaces("s%d_" % k if len(parts) > 1 else "s", corners)
        surfs += ss
        sl += ["\tsurface %s shader %s" % (q[0], sh_) for q in ss]
    # the engine keeps at most 32 surfaces per model (MAX_MODEL_SURFACES; QA 2026-11-09: the town's 126 lost walls past the 32nd) -
    # a big set is written as several models: <nm>, <nm>_c1, <nm>_c2 ... (returned as a list)
    names = []
    for ci in range(0, len(surfs), 30):
        cn = nm if ci == 0 else "%s_c%d" % (nm, ci // 30)
        cs, cl = surfs[ci:ci + 30], sl[ci:ci + 30]
        Pv = np.array([v[3] for s_ in cs for v in s_[2]])
        open(os.path.join(mdir, cn + ".skd"), "wb").write(X.build_skd(cn, [("root", "worldbone")], cs))
        open(os.path.join(mdir, cn + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                       (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                       float(np.linalg.norm(Pv, axis=1).max()) + 1))
        open(os.path.join(mdir, cn + ".tik"), "w", newline="\n").write(
            "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
            "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (cn, "\n".join(cl), cn))
        if line:
            LINES.append('scenemodel "models/menu/%s.tik" 0 0 0 0' % cn)
        names.append(cn)
    return names[0] if len(names) == 1 else names


def quad(p0, p1, p2, p3, u0=(0, 0), u1=(1, 0), u2=(1, 1), u3=(0, 1)):
    """two triangles + uvs for a quad (v up)"""
    P = np.array([[p0, p1, p2], [p0, p2, p3]], float)
    Uv = np.array([[u0, u1, u2], [u0, u2, u3]], float)
    return P, Uv


def wall_quad(x, ya, yb, za, zb, ru=1.0, rv=1.0):
    """a quad on the plane x (game), facing the room; u runs with the viewer's left->right (+y -> -y), v up"""
    return quad((x, ya, za), (x, yb, za), (x, yb, zb), (x, ya, zb), (0, 0), (ru, 0), (ru, rv), (0, rv))


# ------------------------------------------------------------------ 2a. skies
SJ = json.load(open(os.path.join(skyd, "wx_sky.json")))
EYE = np.array([-36.7, 21.0, 102.4])


def horizon_z(xg):
    return EYE[2] - math.tan(math.radians(1.3)) * (xg - EYE[0])


SX = WALL_X + SJ["D"] * U
hz = horizon_z(SX)
for k in ("night", "dawn", "day", "golden", "dusk", "cloud", "flash"):
    im = os.path.join(skyd, "textures", "menu", "hzm_wx_sky_%s.jpg" % k)
    Image.open(im).save(os.path.join(tdir, "hzm_wx_sky_%s.jpg" % k), quality=92)
    off = {"cloud": -0.15, "flash": -0.3}.get(k, 0.0)      # the decks a hair in front of the skies, still behind the far ridge (<= x 1906)
    P, Uv = wall_quad(SX + off * U, SJ["yL"] * U, SJ["yR"] * U, hz + SJ["zB"] * U, hz + SJ["zT"] * U)
    nm = write_model("hzm_wx_sky_%s" % k, P, Uv, "hzm_wx_sky_%s" % k)
    if k == "cloud":
        SH.append("hzm_wx_sky_cloud\n{\n\tnopicmip\n\tcull none\n\tsort 8.2\n\t{\n\t\tclampmap textures/menu/hzm_wx_sky_cloud.jpg\n"
                  "\t\tblendFunc blend\n\t\trgbGen entity\n\t\talphaGen entity\n\t}\n}")
        WX.append('scenewx "%s" cloud' % nm)
    elif k == "flash":
        SH.append("hzm_wx_sky_flash\n{\n\tnopicmip\n\tcull none\n\tsort 8.25\n\t{\n\t\tclampmap textures/menu/hzm_wx_sky_flash.jpg\n"
                  "\t\tblendFunc add\n\t\trgbGen entity\n\t}\n}")
        WX.append('scenewx "%s" flash' % nm)
    else:
        SH.append("hzm_wx_sky_%s\n{\n\tnopicmip\n\tcull none\n\tsort 8.1\n\t{\n\t\tclampmap textures/menu/hzm_wx_sky_%s.jpg\n"
                  "\t\tblendFunc add\n\t\trgbGen entity\n\t}\n}" % (k, k))
        WX.append('scenewx "%s" sky %s' % (nm, k))
# the black backing behind everything (the scene's clear is not ours to rely on)
P, Uv = wall_quad(SX + 0.4 * U, SJ["yL"] * U * 1.2, SJ["yR"] * U * 1.2, hz - 200 * U, hz + SJ["zT"] * U * 1.2)
write_model("hzm_wx_back", P, Uv, "hzm_wx_back")
Image.new("RGB", (8, 8), (0, 0, 0)).save(os.path.join(tdir, "hzm_wx_black.jpg"), quality=95)     # (rgbGen const draws teal under GL2)
SH.append("hzm_wx_back\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_wx_black.jpg\n\t\trgbGen identity\n\t}\n}")

# ------------------------------------------------------------------ 2b. the town (baked) + its lit windows
TJ = json.load(open(os.path.join(town, "town.json")))
# the roofs' breakup: smooth value noise round 0.5 (two octaves), 256 px
_rg = np.random.default_rng(68)
_bk = np.zeros((256, 256), np.float32)
for _n, _w in ((4, 0.65), (11, 0.35)):
    _g = _rg.random((_n, _n)).astype(np.float32)
    _g = np.asarray(Image.fromarray((_g * 255).astype(np.uint8)).resize((256, 256), Image.BICUBIC), np.float32) / 255
    _bk += _g * _w
_bk = 0.5 + (_bk - _bk.mean()) * (0.16 / max(1e-6, float(_bk.std())))
Image.fromarray((np.clip(np.stack([_bk] * 3, 2), 0, 1) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_breakup.jpg"), quality=92)
TOWNMATS = TJ.get("townmats", {})
GAIN = float(os.environ.get("WX_LGAIN", "1.0"))
_done_mat = set()


def _fill_holes(a, ok):
    """fill texels where ok is False from their valid neighbourhood (normalized box blur, growing radius) - float HxWx3"""
    w_ = ok.astype(np.float32)
    for r_ in (2, 6, 18, 54):
        if w_.min() > 0.5:
            break
        k_ = 2 * r_ + 1
        num = np.zeros_like(a)
        den = np.zeros(a.shape[:2], np.float32)
        # separable box blur via cumulative sums
        def box(x):
            c = np.cumsum(np.pad(x, [(r_ + 1, r_)] + [(0, 0)] * (x.ndim - 1), mode="edge"), 0)
            x = (c[k_:] - c[:-k_]) / k_
            c = np.cumsum(np.pad(x, [(0, 0), (r_ + 1, r_)] + [(0, 0)] * (x.ndim - 2), mode="edge"), 1)
            return (c[:, k_:] - c[:, :-k_]) / k_
        num = box(a * w_[..., None])
        den = box(w_)
        need = (w_ < 0.5) & (den > 0.02)
        a[need] = num[need] / den[need][..., None]
        w_ = np.where(need, 1.0, w_)
    return a


for g in ("hills", "ground", "far", "town", "near"):
    npz = os.path.join(town, g + ".npz")
    if not os.path.exists(npz):
        print("no", npz)
        continue
    D = np.load(npz)
    if g == "hills":
        im = Image.open(os.path.join(town, g + ".png")).convert("RGB")
        _a = np.asarray(im, np.float32)
        _a = _fill_holes(_a, _a.max(2) > 10)
        Image.fromarray(np.clip(_a, 0, 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_%s.jpg" % g), quality=93)
        nm = write_model("hzm_wx_%s" % g, D["pos"].astype(np.float64) * U, D["uv"].astype(np.float64), "hzm_wx_%s" % g)
        SH.append("hzm_wx_%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_wx_%s.jpg\n\t\trgbGen entity\n\t}\n}" % (g, g))
        WX.append('scenewx "%s" tint' % nm)
        continue
    # LIGHT (lighting x wash x (1 - haze); stored halved, drawn as a 2x modulate) and HAZE (added, tinted)
    Lf = np.load(os.path.join(town, g + "_L.npz"))["img"].astype(np.float32) * GAIN
    Hf = np.load(os.path.join(town, g + "_H.npz"))["img"].astype(np.float32)
    Lf = _fill_holes(Lf, Lf.max(2) > 0.025)                           # (0.004 left near-black occluded texels under dormers: dark halos once mipped)                          # bake holes (a face seen from inside) take their wall's light
    print("light %s: p50 %.2f p99 %.2f clipped %.2f%%" % (g, np.percentile(Lf, 50), np.percentile(Lf, 99), 100 * (Lf > 2).mean()))
    Image.fromarray((np.clip(Lf / 2, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_%s_L.jpg" % g), quality=94)
    Image.fromarray((np.clip(Hf, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_%s_H.jpg" % g), quality=94)
    P_ = D["pos"].astype(np.float64) * U
    mats = [str(m) for m in D["mats"]]
    mi = D["mi"].astype(int)
    parts = []
    for k, m in enumerate(mats):
        sel = mi == k
        if not sel.any():
            continue
        if m not in TOWNMATS:
            print("no texture for", m)
            continue
        sh_ = "hzm_wx_t_%s" % m
        if m not in _done_mat:
            _done_mat.add(m)
            # a .tga with alpha (the shop awning's scalloped edge): alpha-tested, so the light pass's depthFunc equal skips the holes
            at_ = "\n\t\talphaFunc GE128\n\t\tdepthWrite" if TOWNMATS[m][0].lower().endswith(".tga") else ""
            # roofs: a low-frequency breakup (our own noise, mean 0.5, a 2x modulate = neutral) over the slate / tile, so its own
            # repeat stops reading as a diagonal pattern up close (QA 2026-11-09, the banner close-up)
            bk_ = ("\n\t{\n\t\tmap textures/menu/hzm_wx_breakup.jpg\n\t\tblendFunc GL_DST_COLOR GL_SRC_COLOR\n\t\ttcMod scale 0.137 0.091\n\t}"
                   if m in ("slate", "tile", "tile2", "tile3") else "")
            SH.append("%s\n{\n\tcull none\n\t{\n\t\tmap %s%s\n\t\trgbGen entity\n\t}%s\n}" % (sh_, TOWNMATS[m][0], at_, bk_))
        parts.append((sh_, P_[sel], D["tuv"][sel].astype(np.float64)))
    nm = write_model("hzm_wx_%s" % g, None, None, None, parts=parts)
    for n_ in (nm if isinstance(nm, list) else [nm]):
        WX.append('scenewx "%s" tint' % n_)
    nm2 = write_model("hzm_wx_%s_lh" % g, P_, D["uv"].astype(np.float64), "hzm_wx_%s_lh" % g)
    SH.append("hzm_wx_%s_lh\n{\n\tnopicmip\n\tcull none\n\tsort 8.01\n\t{\n\t\tclampmap textures/menu/hzm_wx_%s_L.jpg\n"
              "\t\tblendFunc GL_DST_COLOR GL_SRC_COLOR\n\t\tdepthFunc equal\n\t\trgbGen identity\n\t}\n\t{\n"
              "\t\tclampmap textures/menu/hzm_wx_%s_H.jpg\n\t\tblendFunc add\n\t\tdepthFunc equal\n\t\trgbGen entity\n\t}\n}" % (g, g, g))
    for n_ in (nm2 if isinstance(nm2, list) else [nm2]):
        WX.append('scenewx "%s" tint' % n_)
LQ = np.load(os.path.join(town, "lights.npz"))["quads"].astype(np.float64) * U
if len(LQ):
    try:
        lw = Image.open(io.BytesIO(zipfile.ZipFile(G + r"\maintt\zzzzzz_hd_world.pk3").read("textures/TAHolland/hollwindow_f1.blend.tga"))).convert("RGB")
    except KeyError:
        lw = Image.open(io.BytesIO(zipfile.ZipFile(G + r"\main\pak1.pk3").read("textures/TAHolland/hollwindow_f1.blend.tga"))).convert("RGB")
    lw = lw.resize((128, 256), Image.LANCZOS)
    a = np.asarray(lw, np.float32) / 255
    # three variants side by side (an atlas): full, warm behind the curtain (softer, redder), and dim
    full = np.clip(a * 1.25, 0, 1)
    curt = np.clip(a.mean(2, keepdims=True) * 1.1, 0, 1) * np.array([1.0, 0.66, 0.36])
    dim = full * 0.45
    Image.fromarray((np.concatenate([full, curt, dim], 1) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_lit.jpg"), quality=92)
    P, Uv = [], []
    vr = np.random.default_rng(23)
    for q in LQ:
        _c = q.mean(0)
        _to = EYEg - _c if "EYEg" in globals() else np.array([-36.7, 21.0, 102.4]) - _c
        q = q + _to / np.linalg.norm(_to) * 3.5      # 3.5 u towards the eye: in front of its window (pushed 4 cm = 2.1 u), never behind the wall
        p, u = quad(*q)
        k = int(vr.choice(3, p=[0.45, 0.35, 0.20]))
        u = u.copy(); u[..., 0] = (u[..., 0] + k) / 3.0
        P.append(p); Uv.append(u)
    write_model("hzm_wx_lights", np.concatenate(P), np.concatenate(Uv), "hzm_wx_lights")
    SH.append("hzm_wx_lights\n{\n\tnopicmip\n\tcull none\n\tsort 8.05\n\t{\n\t\tmap textures/menu/hzm_wx_lit.jpg\n\t\tblendFunc add\n\t\trgbGen entity\n\t}\n}")
    WX.append('scenewx "hzm_wx_lights" lights')

# ------------------------------------------------------------------ 2b'. chimney smoke and treetops on the town's line (wx_town.py marks)
MK = json.load(open(os.path.join(town, "marks.json"))) if os.path.exists(os.path.join(town, "marks.json")) else []
EYEg = np.array([-36.7, 21.0, 102.4])


def card(base, wid, hgt, lean=0.0):
    """a vertical quad standing on `base` (game units), facing the home eye; u left->right, v up"""
    to = EYEg[:2] - base[:2]
    to = to / np.linalg.norm(to)
    right = np.array([to[1], -to[0], 0.0])                 # the viewer's right
    b0 = base - right * wid / 2
    b1 = base + right * wid / 2
    up = np.array([lean, 0.0, hgt])
    return quad(tuple(b0), tuple(b1), tuple(b1 + up), tuple(b0 + up))


# smoke: a plume built from the game's own smoke puff (zzzzzz_hd_fx smokeswirl), rising, widening, leaning with the wind
pz = zipfile.ZipFile(G + r"\maintt\zzzzzz_hd_fx.pk3")
puff = Image.open(io.BytesIO(pz.read("textures/sprites/smokeswirl.tga"))).convert("RGBA")
PW, PH = 128, 512
plume = np.zeros((PH, PW, 4), np.float32)
pr = np.random.default_rng(7)
for k in range(26):
    t = k / 25.0
    sz = int(26 + 96 * t)
    pp = np.asarray(puff.resize((sz, sz), Image.LANCZOS).rotate(pr.uniform(0, 360)), np.float32) / 255
    cx = int(PW * 0.5 + (t ** 1.4) * PW * 0.22 + pr.uniform(-3, 3))
    cy = int(PH * (0.97 - 0.86 * t))
    a = pp[..., 3] * (0.55 * (1 - t) ** 1.3 + 0.04)
    x0, y0 = cx - sz // 2, cy - sz // 2
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(PW, x0 + sz), min(PH, y0 + sz)
    if xs1 <= xs0 or ys1 <= ys0:
        continue
    sub = a[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    reg = plume[ys0:ys1, xs0:xs1]
    reg[..., 3] = reg[..., 3] + sub * (1 - reg[..., 3])
pl = np.dstack([np.full((PH, PW), 0.78), np.full((PH, PW), 0.78), np.full((PH, PW), 0.80), np.clip(plume[..., 3] * 0.55, 0, 0.5)])
Image.fromarray((pl * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, "hzm_wx_smoke.tga"))
P, Uv = [], []
for m in MK:
    if m["kind"] != "smoke":
        continue
    base = np.array(m["p"]) * U
    s_ = m["size"]
    p_, u_ = card(base, 2.6 * U * s_, 7.0 * U * s_)
    P.append(p_); Uv.append(u_)
if P:
    write_model("hzm_wx_smoke", np.concatenate(P), np.concatenate(Uv), "hzm_wx_smoke")
    SH.append("hzm_wx_smoke\n{\n\tnopicmip\n\tcull none\n\tsort 8.07\n\tdeformVertexes wave 40 sin 0 0.8 0 0.12\n\t{\n"
              "\t\tclampmap textures/menu/hzm_wx_smoke.tga\n\t\tblendFunc blend\n\t\trgbGen entity\n"
              "\t\ttcMod stretch sin 1 0.03 0 0.1\n\t}\n}")
    WX.append('scenewx "hzm_wx_smoke" tint')
# treetops: the stock HD tree sprite, hazed by distance (two bands), alpha-tested
ts = Image.open(io.BytesIO(zipfile.ZipFile(G + r"\maintt\zzzzz_hd_foliage.pk3").read("textures/models/natural/tree1sprite.tga"))).convert("RGBA")
ts = ts.resize((256, 512), Image.LANCZOS)
ta = np.asarray(ts, np.float32) / 255
HZ = np.array([0.64, 0.68, 0.75])
for band, hz in (() if not os.environ.get("WX_TREECARDS") else (("n", 0.22), ("f", 0.42))):
    c = ta[..., :3] * (1 - hz) + HZ * hz
    Image.fromarray((np.dstack([c, ta[..., 3]]) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, "hzm_wx_tree_%s.tga" % band))
    P, Uv = [], []
    for m in MK:
        if m["kind"] != "tree":
            continue
        dist = np.linalg.norm(np.array(m["p"]) * U - EYEg) / U
        if (band == "n") != (dist < 36.75):
            continue
        base = np.array(m["p"]) * U
        h_ = m["size"] * U
        p_, u_ = card(base, h_ * 0.62, h_)
        P.append(p_); Uv.append(u_)
    if P:
        nm = write_model("hzm_wx_trees_%s" % band, np.concatenate(P), np.concatenate(Uv), "hzm_wx_trees_%s" % band)
        SH.append("hzm_wx_trees_%s\n{\n\tcull none\n\t{\n\t\tclampmap textures/menu/hzm_wx_tree_%s.tga\n\t\talphaFunc GE128\n"
                  "\t\tdepthWrite\n\t\trgbGen entity\n\t}\n}" % (band, band))
        WX.append('scenewx "%s" tint' % nm)

# ------------------------------------------------------------------ 2b''. banners (user: "there are Nazi flags and banners in the game, we
# should have those hanging from some buildings to give the vibe of being behind enemy lines"): the game's own models and textures,
# referenced from the installed paks (models/static/flags/nazibanner1|2.skd + skc, textures/models/flags/*) - nothing re-shipped but
# our tik / shader wrappers. Hung under the eaves of the hero roofs that face the attic (wx_town.py marks), scaled to the building
# (the stage set's squash factor rides in the mark's size), turned to face the main menu's eye, tinted by the outside light like the
# town. Two copies each: a gentle flap, and a storm flap (scenemodelcvar on ui_wxWindy, set by the engine's weather).
BANNER_TEX = {"nazibanner1": "textures/models/flags/nazibanner.tga", "nazibanner2": "textures/models/flags/nazibanner2.tga"}
for _wind, _flap in (("calm", "deformvertexes flap t 1 sin 0 1 0 .10 0 2"), ("windy", "deformvertexes flap t 1 sin 0 2.6 0 .32 0 5")):
    for _bm, _tx in BANNER_TEX.items():
        SH.append("hzm_wx_%s_%s\n{\n\tcull none\n\t%s\n\t{\n\t\tmap %s\n\t\trgbGen entity\n\t}\n}" % (_bm, _wind, _flap, _tx))
SH.append("hzm_wx_flagtop\n{\n\tcull none\n\t{\n\t\tmap textures/models/flags/flagtop.tga\n\t\tblendFunc blend\n\t\tdepthWrite\n"
          "\t\trgbGen entity\n\t}\n}")
# (v1.10.68, user QA "banners janky / asymmetric"): a rigid model stood vertical while the squashed wall leans (the squash compresses
# along the sight line), so one edge clipped and the other floated. Now the stock mesh (models/static/flags/nazibanner1.skd, posed by
# its skc: a -90 deg turn about z) is placed on the REAL wall - its rod's back on the wall plane, hanging plumb from the eaves - and
# every vertex is squashed exactly like the town's, so it lies on the squashed wall wherever the wall goes. Our own mesh, the game's
# textures (referenced by path), the flap deform in the shader.
KNEE, SPAN, EPS_SQ = 12.0, 25.0, 5e-4
EYE_M = np.array([-36.7, 21.0, 102.4]) / U


def squash_m(p):
    """wx_town.py's squash, metres, per point (N,3)"""
    v = p - EYE_M
    d = np.linalg.norm(v, axis=1)
    dd = np.where(d <= KNEE, d, KNEE + SPAN * (1 - np.exp(-(d - KNEE) / SPAN)) + EPS_SQ * (d - KNEE))
    return EYE_M + v * (dd / np.maximum(d, 1e-9))[:, None]


_bz = zipfile.ZipFile(G + r"\main\Pak0.pk3")
BAN = R.read_skd(_bz.read("models/static/flags/nazibanner1.skd"))
_BS = []
for _s in BAN["surfaces"]:
    off = np.array([v[3] for v in _s["verts"]], np.float64)
    off = np.stack([off[:, 1], -off[:, 0], off[:, 2]], 1)          # the skc's pose: -90 deg about z (cloth in the model's y-z plane)
    uvs = np.array([v[1] for v in _s["verts"]], np.float64)
    _BS.append((_s["name"], off, uvs, _s["tris"]))
ROD_BACK = min(o[:, 0].min() for _, o, _, _ in _BS)                # the rod's back (model x): it touches the wall
BAN_LEN = 506.0                                                     # model units, cloth bottom (14) to the brass top (506)
BAN_TOPZ = max(o[:, 2].max() for _, o, _, _ in _BS)
_nb = 0
for m in MK:
    if not m["kind"].startswith("banner:"):
        continue
    _, bmod, blen = m["kind"].split(":")
    Lr = float(blen)                                                # metres, real
    sc = Lr / BAN_LEN
    top = np.array(m["preal"], np.float64)
    n = np.array(m["facereal"], np.float64)
    n[2] = 0.0
    n /= np.linalg.norm(n)
    rgt = np.array([-n[1], n[0], 0.0])                              # model +y -> the viewer's right (x = n, y = rgt, z = up: right-handed)
    parts = {}
    for sname, off, uvs, tris in _BS:
        mp = off * sc
        wpos = (top[None, :] + n[None, :] * (mp[:, 0:1] - ROD_BACK * sc + 0.006)
                + rgt[None, :] * mp[:, 1:2] + np.array([0, 0, 1.0])[None, :] * (mp[:, 2:3] - BAN_TOPZ * sc))
        gp = squash_m(wpos)
        gp = (gp + (EYE_M - gp) / np.linalg.norm(EYE_M - gp, axis=1)[:, None] * 0.02) * U    # 2 cm toward the eye (the squash crushes the
        # rod's few cm of real depth to under a millimetre; the wall's tessellated chord can sit a few mm proud of the true surface)
        T = gp[tris]
        Uv_ = uvs[tris].copy()
        Uv_[..., 1] = 1 - Uv_[..., 1]                                   # write_model flips v back
        parts[sname] = (T, Uv_)
    for _wind in ("calm", "windy"):
        nm = "hzm_wx_ban%d_%s" % (_nb, _wind)
        write_model(nm, None, None, None, parts=[("hzm_wx_flagtop", *parts["material1"]),
                                                 ("hzm_wx_%s_%s" % (bmod, _wind), *parts["material2"])])
        WX.append('scenewx "%s" tint' % nm)
        WX.append('scenemodelcvar "%s" "ui_wxWindy" "%d"' % (nm, 1 if _wind == "windy" else 0))
    _nb += 1
print("banners", _nb)

# ------------------------------------------------------------------ 2b-iii. the sky over the skylight: the same keys on a ceiling plane
# (the gable's sky planes stand upright beyond the town; looking up through the roof light they were out of view)
TOPZ = 1300.0          # within the UI far plane (2048) along the steepest views out of the skylight
for k in ("night", "dawn", "day", "golden", "dusk", "cloud", "flash"):
    off = {"cloud": -4.0, "flash": -8.0}.get(k, 0.0)
    z_ = TOPZ + off
    P, Uv = quad((-1400.0, 2600.0, z_), (1800.0, 2600.0, z_), (1800.0, -700.0, z_), (-1400.0, -700.0, z_),
                 (0, 1.0), (1, 1.0), (1, 0.0), (0, 0.0))          # the key's skybox UP face (gen_wx_sky.py), drifting slowly
    Image.open(os.path.join(skyd, "textures", "menu", "hzm_wx_top_%s.jpg" % k)).save(os.path.join(tdir, "hzm_wx_top_%s.jpg" % k), quality=92)
    blend = {"cloud": "blendFunc blend\n\t\trgbGen entity\n\t\talphaGen entity", "flash": "blendFunc add\n\t\trgbGen entity"}.get(
        k, "blendFunc add\n\t\trgbGen entity")
    SH.append("hzm_wx_top_%s\n{\n\tnopicmip\n\tcull none\n\tsort %s\n\t{\n\t\tmap textures/menu/hzm_wx_top_%s.jpg\n\t\t%s\n"
              "\t\ttcMod scroll 0.004 0.0025\n\t}\n}" % (k, {"cloud": "8.2", "flash": "8.25"}.get(k, "8.1"), k, blend))
    nm = write_model("hzm_wx_top_%s" % k, P, Uv, "hzm_wx_top_%s" % k)
    if k == "cloud":
        WX.append('scenewx "%s" cloud' % nm)
    elif k == "flash":
        WX.append('scenewx "%s" flash' % nm)
    else:
        WX.append('scenewx "%s" sky %s' % (nm, k))
P, Uv = quad((-1400.0, 2600.0, TOPZ + 6), (1800.0, 2600.0, TOPZ + 6), (1800.0, -700.0, TOPZ + 6), (-1400.0, -700.0, TOPZ + 6))
write_model("hzm_wx_top_back", P, Uv, "hzm_wx_back")

# ------------------------------------------------------------------ 2b-iv. aircraft (the game's own flying models, referenced from the
# installed paks): one tik per slot (scenewx keys them kind*8+slot; the engine's WxPlanes moves them), our shaders (rgbGen entity:
# lit like the town; the stock ones use lightingSpherical, black in the menu scene), the props and canopies draw nothing
PLANES = [  # kind, stock skd dir / name, skc, surfaces -> texture or None, tik scale, slots
    (0, "models/vehicles/c47", "c47fly", {"c471": "c47/c47fly", "c472": "c47/c47fly", "c473": "c47/c47fly", "c47prop": None}, 0.011, 6),
    (1, "models/vehicles/fockwulf", "fockwulffly", {"fockwulf1": "fockwulf/fockwulffly", "fockwulf3": "fockwulf/fockwulffly",
                                                   "fockwindow": None, "prop": None}, 0.06, 2),
    (2, "models/vehicles/stuka", "stuka_fly", {"stuka1": "stuka/stuka", "stuka2": "stuka/stuka", "stuka3": "stuka/stuka",
                                              "stuka4": "stuka/stuka", "stukawindow": None, "prop": None}, 0.03, 1),
    (3, "models/vehicles/p47", "p47fly", {"p472": "p47/p47fly", "p473": "p47/p47fly", "p47window": None, "prop": None}, 0.025, 2),
]
_pt = set()
for kind, path, skd, surfs, scl, slots in PLANES:
    for tx in set(v for v in surfs.values() if v):
        if tx not in _pt:
            _pt.add(tx)
            SH.append("hzm_wx_pl_%s\n{\n\t{\n\t\tmap textures/models/vehicles/%s.tga\n\t\trgbGen entity\n\t}\n}" % (tx.split("/")[1], tx))
    sl = "\n".join("\tsurface %s shader %s" % (sn, ("hzm_wx_pl_%s" % tx.split("/")[1]) if tx else "hzm_wx_none") for sn, tx in surfs.items())
    for k in range(slots):
        nm = "hzm_wx_pl%d_%d" % (kind, k)
        open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
            "TIKI\nsetup\n{\n\tscale %.4f\n\tlod_scale 100\n\tpath %s\n\tskelmodel %s.skd\n%s\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n"
            "\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (scl, path, skd, sl, skd))
        LINES.append('scenemodel "models/menu/%s.tik" 0 0 -4000 0 "idle"' % nm)
        WX.append('scenewx "%s" plane %d' % (nm, kind * 8 + k))

# ------------------------------------------------------------------ 2c. the oak (stock 3D tree, its own shaders: rgbGen entity)
# right of the close camera's view and clear of the home camera's (which looks out 27 deg to the left): the crown reaches in from the right.
# The crown (radius ~320 at scale 0.95) must stay OUT of the room: x > 360 everywhere and x > 514 right of y -21 (the room's right wing
# runs back to x 514) - at (700, -140) it stood in the middle of the attic in the home view.
OAK = json.loads(os.environ.get("WX_OAK", '{"x": 870, "y": -156, "z": -575, "yaw": 30, "scale": 0.95}'))
# the HD foliage pack's oak (zzzzz_hd_foliage), cleaned for a close view: its branches are drawn pure black (half the opaque
# texels of tree4_2) - fine at 50 m in a map, black blots through a window 6 m away - so near-black opaque texels become bark
# brown, and the colour is bled into the transparent texels (the alpha-test edge never samples black)
fz = zipfile.ZipFile(G + r"\maintt\zzzzz_hd_foliage.pk3")


def oak_tex(src, dst, alpha):
    im = np.asarray(Image.open(io.BytesIO(fz.read("textures/models/natural/%s.tga" % src))).convert("RGBA"), np.float32) / 255
    rgb, a_ = im[..., :3], im[..., 3]
    lum = (rgb * [0.3, 0.59, 0.11]).sum(2, keepdims=True)
    bark = np.array([0.22, 0.17, 0.12], np.float32) * (0.55 + 2.5 * lum)
    k = np.clip((0.16 - lum) / 0.16, 0, 1)
    rgb = rgb * (1 - k) + bark * k
    if alpha:
        op = a_ >= 0.5
        filled = rgb * op[..., None]
        wsum = op.astype(np.float32)
        for _ in range(6):                 # bleed the leaf colour outwards
            pad = np.pad(filled, ((1, 1), (1, 1), (0, 0)), mode="edge")
            pw = np.pad(wsum, 1, mode="edge")
            acc = sum(pad[1 + dy:pad.shape[0] - 1 + dy, 1 + dx:pad.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            wac = sum(pw[1 + dy:pw.shape[0] - 1 + dy, 1 + dx:pw.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            grow = (wsum == 0) & (wac > 0)
            filled[grow] = acc[grow] / wac[grow][:, None]
            wsum = np.where(grow, 1.0, wsum)
        rgb = np.where(op[..., None], rgb, filled)
    out = np.dstack([np.clip(rgb, 0, 1), a_]) if alpha else np.clip(rgb, 0, 1)
    Image.fromarray((out * 255).astype(np.uint8), "RGBA" if alpha else "RGB").save(os.path.join(tdir, dst))
    return "textures/menu/" + dst


tsh = {"tree4_1": (oak_tex("tree4_1", "hzm_wx_oak1.tga", False), False, None),
       "tree4_2": (oak_tex("tree4_2", "hzm_wx_oak2.tga", True), True, "flap"),
       "tree4_3": (oak_tex("tree4_3", "hzm_wx_oak3.tga", True), True, "flap"),
       "tree4_6": ("textures/menu/hzm_wx_oak3.tga", True, "flap"),
       }
surf = []
for sn, (tex, alpha, dfm) in tsh.items():
    shn = "hzm_wx_oak_%s" % sn.split("_")[1]
    st = "\t\tclampmap %s\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen entity\n" % tex if alpha else "\t\tmap %s\n\t\trgbGen entity\n" % tex
    df = ""
    if dfm == "flap":                                    # the stock oak's own wind, a touch livelier (the window is close)
        df = "\tdeformVertexes flap t 24 sin 0 3.2 0 0.22 1 0\n\tdeformVertexes flap t 24 sin 0 3.2 0.25 0.33 1 0\n"
    elif dfm == "wave":
        df = "\tdeformVertexes wave 24 sin 0 0.6 0 0.22\n"
    SH.append("%s\n{\n\tcull none\n%s\t{\n%s\t}\n}" % (shn, df, st))
    surf.append("\tsurface %s shader %s" % (sn, shn))
surf.append("\tsurface tree4sprite shader static_tree4sprite")      # the stock sprite: invisible this close (oneMinusDistFade)
for sn in ("tree4_4", "tree4_7"):         # the radial planes draw nothing (black blobs where their HD dds alpha passes)
    surf.append("\tsurface %s shader hzm_wx_none" % sn)
SH.append("hzm_wx_none\n{\n\t{\n\t\tmap textures/menu/hzm_wx_black.jpg\n\t\tblendFunc GL_ZERO GL_ONE\n\t}\n}")
open(os.path.join(mdir, "hzm_wx_oak.tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale %.3f\n\tpath models/static/natural\n\tskelmodel tree_oak.skd\n%s\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle tree_oak.skc\n}\n" % (OAK["scale"], "\n".join(surf)))
# "idle": the stock oak's skeleton is Y-up and only its idle frame stands it upright (without an anim it lay on its side, under the roofs)
LINES.append('scenemodel "models/menu/hzm_wx_oak.tik" %.1f %.1f %.1f %.1f "idle"' % (OAK["x"], OAK["y"], OAK["z"], OAK["yaw"]))
WX.append('scenewx "hzm_wx_oak" tint')

# ------------------------------------------------------------------ 2d. rain: two streak sheets + drops on the glass
N = 512
SS = 3
im = Image.new("L", (N * SS, N * SS), 0)
d = ImageDraw.Draw(im)
for _ in range(900):                       # fine, faint streaks (the first cut read as a white wall)
    x, y = rng.uniform(0, N * SS), rng.uniform(0, N * SS)
    L = rng.uniform(12, 38) * SS
    a = int(rng.uniform(22, 70))
    w = SS if rng.random() < 0.85 else 2 * SS
    for dx in (-N * SS, 0, N * SS):
        for dy in (-N * SS, 0, N * SS):
            d.line([(x + dx, y + dy), (x + dx + L * 0.10, y + dy + L)], fill=a, width=w)
al = np.asarray(im.resize((N, N), Image.LANCZOS), np.float32) / 255
rgb = np.ones((N, N, 3), np.float32) * np.array([0.82, 0.86, 0.92])
Image.fromarray((np.dstack([rgb, al]) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, "hzm_wx_rain.tga"))
for nm, dist, half, hgt, rep, spd, srt in (("hzm_wx_rain_far", 14.0, 40.0, 26.0, 9.0, 0.55, 8.3), ("hzm_wx_rain_near", 1.6, 6.0, 5.0, 7.0, 2.2, 8.4)):
    x = WALL_X + dist * U
    P, Uv = wall_quad(x, WC[1] + half * U, WC[1] - half * U, WC[2] - hgt * U * 0.55, WC[2] + hgt * U * 0.45, rep * half / hgt * 2 / 2, rep)
    write_model(nm, P, Uv, nm)
    SH.append("%s\n{\n\tnopicmip\n\tcull none\n\tsort %.2f\n\t{\n\t\tmap textures/menu/hzm_wx_rain.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE\n"
              "\t\trgbGen entity\n\t\talphaGen entity\n\t\ttcMod scroll %.3f %.2f\n\t}\n}" % (nm, srt, -0.1 * spd, -spd))
    # NEGATIVE scroll: the image must fall (a positive t sampled further down every frame - the rain flew upwards, user QA);
    # s drifts with the streaks' slant (+x as they fall, 1 : 10)
    WX.append('scenewx "%s" rain' % nm)

# drops on the glass (coordinator: "read as round soap bubbles"): small irregular beads, 1-4 mm on a 0.62 m pane, denser towards the
# bottom; each a lens - it shows the world above it upside down, so it is DARK in its upper part and BRIGHT in its lower part, with a
# thin dark rim and a tiny specular glint high on the light side; some elongated with a short wet trail running down from them
G2 = 1024
SS = 3
W2 = G2 * SS
base = np.zeros((W2, W2, 4), np.float32)
rr_ = np.random.default_rng(67)


def bead(cx, cy, rx, ry, rot=0.0, strength=1.0, wob=None):
    R = max(rx, ry) * 1.3 + 3
    x0, x1 = int(max(0, cx - R)), int(min(W2, cx + R + 1))
    y0, y1 = int(max(0, cy - R)), int(min(W2, cy + R + 1))
    if x1 <= x0 or y1 <= y0:
        return
    sy, sx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ca, sa = math.cos(rot), math.sin(rot)
    ux, uy = (sx - cx) * ca + (sy - cy) * sa, -(sx - cx) * sa + (sy - cy) * ca
    ang = np.arctan2(uy, ux)
    edge = 1.0 + (0.10 * np.sin(3 * ang + wob[0]) + 0.06 * np.sin(5 * ang + wob[1]) if wob is not None else 0.0)
    dx, dy = ux / rx, uy / ry
    rr = np.sqrt(dx * dx + dy * dy) / edge
    inside = np.clip((1.0 - rr) * min(rx, ry) / 1.2, 0, 1)
    v = (sy - cy) / ry                                  # -1 top .. +1 bottom (screen space)
    lens = np.clip(0.5 + 0.55 * v, 0, 1)                # inverted world: dark top, light bottom
    rim = np.clip(1 - np.abs(rr - 0.84) / 0.16, 0, 1)
    glint = np.exp(-(((sx - cx) / rx + 0.35) ** 2 + ((sy - cy) / ry + 0.42) ** 2) / 0.02)
    col = 0.18 + 0.62 * lens - 0.22 * rim + 0.75 * glint
    a = inside * (0.55 + 0.25 * rim + 0.2 * glint) * strength
    reg = base[y0:y1, x0:x1]
    m = a > reg[..., 3]
    for c, k in ((0, 0.97), (1, 0.99), (2, 1.03)):
        reg[..., c] = np.where(m, np.clip(col * k, 0, 1), reg[..., c])
    reg[..., 3] = np.maximum(reg[..., 3], a)


n_drops = 0
for _ in range(2600):
    yv = rr_.uniform(0, 1) ** 0.62                      # denser towards the bottom of the pane
    cy = yv * W2
    cx = rr_.uniform(0, W2)
    r = float(rr_.choice([rr_.uniform(1.0, 2.0), rr_.uniform(2.0, 3.6), rr_.uniform(3.6, 5.5)], p=[0.62, 0.30, 0.08])) * SS
    elong = 1.0 + (rr_.uniform(0.2, 0.8) if r > 2.6 * SS and rr_.random() < 0.35 else rr_.uniform(0.0, 0.18))
    bead(cx, cy, r / math.sqrt(elong), r * math.sqrt(elong), rr_.uniform(-0.25, 0.25), 1.0, rr_.uniform(0, 6.28, 2))
    n_drops += 1
    if r > 3.0 * SS and rr_.random() < 0.30:            # a short wet trail running down from it: a chain of tiny beads
        L = rr_.uniform(8, 30) * SS
        wob = rr_.uniform(0, 6.28)
        for t in np.linspace(0.15, 1, 24):
            bead(cx + 1.2 * SS * math.sin(t * 6 + wob), cy - L * t, 0.55 * SS, 0.9 * SS, 0.0, 0.45 * (1 - 0.6 * t))   # trail ABOVE: it ran down
drop = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGBA").resize((G2, G2), Image.LANCZOS)
drop.save(os.path.join(tdir, "hzm_wx_drops.tga"))
gx = WALL_X + 1.0                         # just outside the mullions' back faces (the frame is 358.4-360.2 deep)
P, Uv = wall_quad(gx + 1.6, WIN[0] - 2, WIN[1] + 2, WIN[2] - 2, WIN[3] + 2)
write_model("hzm_wx_drops", P, Uv, "hzm_wx_drops")
SH.append("hzm_wx_drops\n{\n\tnopicmip\n\tcull none\n\tsort 8.5\n\t{\n\t\tclampmap textures/menu/hzm_wx_drops.tga\n\t\tblendFunc blend\n"
          "\t\trgbGen entity\n\t\talphaGen entity\n\t}\n}")
WX.append('scenewx "hzm_wx_drops" rain')
# the skylight's glass: the same beads, running slowly down the slope (the roof's fall line is the texture's -v), a hair outside
_n = np.cross(SKY_CORNERS[1] - SKY_CORNERS[0], SKY_CORNERS[3] - SKY_CORNERS[0])
_n = _n / np.linalg.norm(_n)
if _n[2] < 0:
    _n = -_n
_sc = SKY_CORNERS + _n * 1.0
# corners: 0 = low/front, 1 = high/front, 2 = high/back, 3 = low/back (attic67_edit order): v runs up the slope
P, Uv = quad(tuple(_sc[0]), tuple(_sc[3]), tuple(_sc[2]), tuple(_sc[1]), (0, 0), (1.2, 0), (1.2, 1), (0, 1))
write_model("hzm_wx_skydrops", P, Uv, "hzm_wx_skydrops")
SH.append("hzm_wx_skydrops\n{\n\tnopicmip\n\tcull none\n\tsort 8.5\n\t{\n\t\tmap textures/menu/hzm_wx_drops.tga\n\t\tblendFunc blend\n"
          "\t\trgbGen entity\n\t\talphaGen entity\n\t\ttcMod scroll 0.0 -0.035\n\t}\n\t{\n\t\tmap textures/menu/hzm_wx_drops.tga\n"
          "\t\tblendFunc blend\n\t\trgbGen entity\n\t\talphaGen entity\n\t\ttcMod scale 0.7 0.7\n\t\ttcMod scroll 0.013 -0.09\n\t}\n}")
WX.append('scenewx "hzm_wx_skydrops" rain')

# ------------------------------------------------------------------ 2d'. the strike lights the room: a box round the whole attic, faces
# inward, drawn additively with NO depth test after everything else (sort nearest), role flash - from any camera pose exactly one face
# covers each pixel, so it is an even wash; its texture is brighter above and towards the window (+x / +y), so the light seems to
# come in from the window and down through the skylight. (A 2D full-widget overlay in the engine came out solid white.)
GW = 256
gy, gx = np.mgrid[0:GW, 0:GW].astype(np.float32) / (GW - 1)
grad = (0.05 + 0.11 * (1 - gy) ** 1.5 + 0.03 * gx)      # (halved: the strike still blew the frame to ~114 grey)        # v up = brighter
Image.fromarray((np.clip(np.dstack([grad * 0.93, grad * 0.97, grad * 1.0]), 0, 1) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_wx_flashwash.jpg"), quality=92)
bx0, bx1, by0, by1, bz0, bz1 = -300.0, 760.0, -560.0, 640.0, -150.0, 460.0
P, Uv = [], []
for f in (((bx1, by0, bz0), (bx1, by1, bz0), (bx1, by1, bz1), (bx1, by0, bz1)),      # +x (the window wall's side)
          ((bx0, by1, bz0), (bx0, by0, bz0), (bx0, by0, bz1), (bx0, by1, bz1)),
          ((bx0, by1, bz0), (bx1, by1, bz0), (bx1, by1, bz1), (bx0, by1, bz1)),
          ((bx1, by0, bz0), (bx0, by0, bz0), (bx0, by0, bz1), (bx1, by0, bz1)),
          ((bx0, by0, bz1), (bx1, by0, bz1), (bx1, by1, bz1), (bx0, by1, bz1)),      # the ceiling: the top of the gradient
          ((bx0, by0, bz0), (bx1, by0, bz0), (bx1, by1, bz0), (bx0, by1, bz0))):
    p_, u_ = quad(*f, (0, 0), (1, 0), (1, 1), (0, 1))
    P.append(p_); Uv.append(u_)
write_model("hzm_wx_roomflash3d", np.concatenate(P), np.concatenate(Uv), "hzm_wx_roomflash3d")
SH.append("hzm_wx_roomflash3d\n{\n\tnopicmip\n\tcull none\n\tsort nearest\n\t{\n\t\tclampmap textures/menu/hzm_wx_flashwash.jpg\n"
          "\t\tblendFunc add\n\t\tnoDepthTest\n\t\trgbGen entity\n\t}\n}")
WX.append('scenewx "hzm_wx_roomflash3d" flash')

# ------------------------------------------------------------------ 2e. the room flash (engine 2D overlay) + thunder
Image.new("RGB", (8, 8), (255, 255, 255)).save(os.path.join(tdir, "hzm_wx_white.jpg"), quality=95)
SH.append("hzm_wx_roomflash\n{\n\tnopicmip\n\tnomipmaps\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_wx_white.jpg\n\t\tblendFunc add\n\t\trgbGen vertex\n\t}\n}")
zs = zipfile.ZipFile(G + r"\maintt\zzzzzz_co-op_hzm_mod_assets_snd.pk3")
for i in (1, 2, 3):
    w = wave.open(io.BytesIO(zs.read("sound/amb/Amb_Thunder_%02d.wav" % i)))
    ch, sw, fr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    a = np.frombuffer(w.readframes(n), "<i2").astype(np.float32).reshape(-1, ch).mean(1)
    if fr == 44100:
        a = a[: len(a) // 2 * 2].reshape(-1, 2).mean(1)
        fr = 22050
    g = 10 ** (-14 / 20)                  # distant: -14 dB under the stock clap
    fade = np.clip((len(a) - np.arange(len(a))) / (fr * 0.6), 0, 1)
    a = np.clip(a * g * fade, -32767, 32767).astype("<i2")
    ow = wave.open(os.path.join(snd, "hzm_wx_thunder%d.wav" % i), "wb")
    ow.setnchannels(1); ow.setsampwidth(2); ow.setframerate(fr); ow.writeframes(a.tobytes()); ow.close()
    print("thunder%d %.1f s %d Hz (from %d ch %d Hz)" % (i, len(a) / fr, fr, ch, w.getframerate()))

# the ambience (H:\hzm_work\wx\amb, tools/build.py there: game / mod sounds made loopable and distant, a synthesized bell and owl)
import glob, shutil  # noqa: E402
AMB = os.environ.get("WX_AMB", r"H:\hzm_work\wx\amb\sound\menu\amb")
os.makedirs(os.path.join(snd, "amb"), exist_ok=True)
for f in sorted(glob.glob(os.path.join(AMB, "wx_*.wav"))):
    shutil.copyfile(f, os.path.join(snd, "amb", os.path.basename(f)))
print("ambience", len(glob.glob(os.path.join(snd, "amb", "*.wav"))), "files")
open(os.path.join(sdir, "hzm_wx.shader"), "w", newline="\n").write("\n\n".join(SH) + "\n")
json.dump({"lines": LINES + WX}, open(os.path.join(out, "wx_scene.json"), "w"), indent=1)
print("models", len(LINES), "wx", len(WX))
