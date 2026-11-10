"""gen_hatch73.py <menus pak> <add dir> - v1.10.73: the attic's LADDER HATCH (how the attic is reached) = the QUIT GAME exit.

User: "add a ladder hatch to the left side of the main-menu room" / "make that the Quit Game room". It stands in the open floor
to the left of the home camera (the attic's open back end, now closed by close_ring73.py hzm_atc_close), seen from the "< QUIT"
turn (patch_hatch73.py). Writes into <add dir>:
  models/menu/atc_floor1.*      the attic floor with the opening cut out (uv interpolated on the cut; nothing else changes)
  models/menu/hzm_hatch.*       above the floor: the frame (flush, 0.3 u proud), the trapdoor propped open on its hinge, the top
                                of a leaning ladder (rails run on above the floor as grab rails), a grab post and handrail
  models/menu/hzm_hatch_lit.*   the same, the lamp turned up (the attic's lit-copy recipe: hover shows it, hides the plain one)
  models/menu/hzm_hatch_below.* the stairwell below: plank walls, the ladder's lower run, a landing floor, a warm bounce glow
  scripts/hzm_hatch73.shader    the game's own wood (general_structure/beam_wood1, plank_flat, mohtest/woodfloor2), painted to
                                the room's baked light (rgbGen const: the attic is baked, nothing is lit at run time)
"""
import math, os, re, sys, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

pak, add = sys.argv[1:3]
Z = zipfile.ZipFile(pak)
mdir, tdir, sdir = (os.path.join(add, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)

HX0, HX1, HY0, HY1 = -8.0, 32.0, 150.0, 186.0       # the opening (game units; the floor is z 0)
DEPTH = 130.0                                        # down to the landing
HC = ((HX0 + HX1) / 2, (HY0 + HY1) / 2, 0.0)
INFO = dict(opening=[HX0, HX1, HY0, HY1], depth=DEPTH, centre=list(HC))


def write_model(nm, parts):
    surfs, sl = [], []
    for k, (sh, corners) in enumerate(parts):
        if not corners:
            continue
        ss = X.split_surfaces("s%d_" % k, corners)
        surfs += ss
        sl += ["\tsurface %s shader %s" % (q[0], sh) for q in ss]
    assert len(surfs) <= 30, (nm, len(surfs))
    Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))


def tri(out, p, u):
    p = [np.asarray(q, float) for q in p]
    n = np.cross(p[1] - p[0], p[2] - p[0])
    ln = np.linalg.norm(n)
    if ln < 1e-9:
        return
    n = n / ln
    out.append([(0, tuple(map(float, p[k])), tuple(map(float, -n)), (float(u[k][0]), float(u[k][1]))) for k in range(3)])


def quad(out, p0, p1, p2, p3, u0=(0, 1), u1=(1, 1), u2=(1, 0), u3=(0, 0)):
    tri(out, (p0, p1, p2), (u0, u1, u2))
    tri(out, (p0, p2, p3), (u0, u2, u3))


def box(out, c, ax, ay, az, size, us=24.0):
    """an oriented box: centre c, unit axes ax ay az, size (sx, sy, sz); uv in world units / us (wood grain along the longest axis)"""
    c = np.asarray(c, float)
    ax, ay, az = (np.asarray(v, float) for v in (ax, ay, az))
    h = np.asarray(size, float) / 2
    A = [ax * h[0], ay * h[1], az * h[2]]
    L = [2 * h[0], 2 * h[1], 2 * h[2]]
    for i in range(3):
        for s in (-1, 1):
            j, k = (i + 1) % 3, (i + 2) % 3
            fc = c + A[i] * s
            pts = [fc - A[j] - A[k], fc + A[j] - A[k], fc + A[j] + A[k], fc - A[j] + A[k]]
            if s < 0:
                pts = pts[::-1]
            lj, lk = L[j] / us, L[k] / us
            uv = [(0, 0), (lj, 0), (lj, lk), (0, lk)]
            if s < 0:
                uv = uv[::-1]
            if lk > lj:                               # grain along the long side
                uv = [(b, a) for a, b in uv]
            tri(out, pts[:3], uv[:3])
            tri(out, [pts[0], pts[2], pts[3]], [uv[0], uv[2], uv[3]])


# ---------------------------------------------------------------- 1. the floor, with the opening cut out
m = R.read_skd(Z.read("models/menu/atc_floor1.skd"))
tik = Z.read("models/menu/atc_floor1.tik").decode()
shmap = dict(re.findall(r"(?m)^\s*surface (\S+) shader (\S+)", tik))


def clip(poly, axis, val, keep_less):
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ia = (a[0][axis] <= val) if keep_less else (a[0][axis] >= val)
        ib = (b[0][axis] <= val) if keep_less else (b[0][axis] >= val)
        if ia:
            out.append(a)
        if ia != ib:
            f = (val - a[0][axis]) / (b[0][axis] - a[0][axis])
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2]))
    return out


floor_parts = []
n_cut = 0
for s in m["surfaces"]:
    P = np.array([v[3] for v in s["verts"]], float)
    U = np.array([v[1] for v in s["verts"]], float)
    N = np.array([v[0] for v in s["verts"]], float)
    corners = []
    for t in s["tris"]:
        poly = [(P[i], U[i], N[i]) for i in t]
        pts = P[t]
        over = pts[:, 0].max() > HX0 and pts[:, 0].min() < HX1 and pts[:, 1].max() > HY0 and pts[:, 1].min() < HY1
        pieces = [poly]
        if over:
            n_cut += 1
            pieces = [clip(poly, 0, HX0, True), clip(poly, 0, HX1, False)]
            mid = clip(clip(poly, 0, HX0, False), 0, HX1, True)
            if len(mid) >= 3:
                pieces += [clip(mid, 1, HY0, True), clip(mid, 1, HY1, False)]
        for pc in pieces:
            for k in range(1, len(pc) - 1):
                c3 = [pc[0], pc[k], pc[k + 1]]
                if np.linalg.norm(np.cross(c3[1][0] - c3[0][0], c3[2][0] - c3[0][0])) < 1e-6:
                    continue
                corners.append([(0, tuple(map(float, q[0])), tuple(map(float, q[2])), (float(q[1][0]), float(q[1][1]))) for q in c3])
    floor_parts.append((shmap.get(s["name"], "hzm_atc_floor"), corners))
assert n_cut > 0
# keep the floor model's own surface name (urc scenemodelhide / nothing else names it)
surfs, sl = [], []
for sh, corners in floor_parts:
    ss = X.split_surfaces("wx", corners)
    surfs += ss
    sl += ["\tsurface %s shader %s" % (q[0], sh) for q in ss]
Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
open(os.path.join(mdir, "atc_floor1.skd"), "wb").write(X.build_skd("atc_floor1", [("root", "worldbone")], surfs))
open(os.path.join(mdir, "atc_floor1.skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                    (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                    float(np.linalg.norm(Pv, axis=1).max()) + 1))
open(os.path.join(mdir, "atc_floor1.tik"), "w", newline="\n").write(re.sub(r"(?m)(^\tsurface \S+ shader \S+\n?)+", "\n".join(sl) + "\n", tik))
print("floor: %d triangles cut round the opening" % n_cut)

# ---------------------------------------------------------------- 2. above the floor: frame, trapdoor, ladder top, post + rail
up, ex, ey = np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
frame, lid, ladder, rail = [], [], [], []
FW = 4.0
for (c, a1, a2, sz) in (((HC[0], HY0 - FW / 2, 0.15), ex, ey, (HX1 - HX0 + 2 * FW, FW, 0.6)),
                        ((HC[0], HY1 + FW / 2, 0.15), ex, ey, (HX1 - HX0 + 2 * FW, FW, 0.6)),
                        ((HX0 - FW / 2, HC[1], 0.15), ex, ey, (FW, HY1 - HY0, 0.6)),
                        ((HX1 + FW / 2, HC[1], 0.15), ex, ey, (FW, HY1 - HY0, 0.6))):
    box(frame, c, a1, a2, up, sz)
# the trapdoor: hinged along the opening's left (x = HX0) edge, swung up past upright to 100 deg and resting back on its stay
th = math.radians(100.0)
lw, ld, lt = HX1 - HX0 - 1.0, HY1 - HY0 - 1.0, 2.2          # leaf: width (from the hinge), depth along y, thickness
d_ = np.array([math.cos(th), 0, math.sin(th)])               # from the hinge across the leaf (hinge at x HX0, z 0)
n_ = np.array([-math.sin(th), 0, math.cos(th)])              # its top face's normal
hinge = np.array([HX0, HC[1], 0.6])
box(lid, hinge + d_ * lw / 2 + n_ * lt / 2, d_, ey, n_, (lw, ld, lt), 30.0)
for f_ in (0.18, 0.82):                                       # two battens on the underside (now facing the opening)
    box(lid, hinge + d_ * lw * f_ - n_ * 0.9, d_ * 0 + ey, d_, -n_, (ld - 4, 3.2, 1.8), 20.0)
box(lid, hinge + d_ * lw * 0.5 - n_ * 0.9, d_, ey, -n_, (lw - 6, 3.0, 1.8), 20.0)
# its stay: a short iron bar from the frame to the leaf (dark)
stay = []
s0 = np.array([HX0 - FW, HY0 + 4, 0.6])
s1 = hinge + d_ * lw * 0.55 + np.array([0, -ld / 2 + 4, 0])
v_ = s1 - s0
box(stay, (s0 + s1) / 2, v_ / np.linalg.norm(v_), ey, np.cross(v_ / np.linalg.norm(v_), ey), (np.linalg.norm(v_), 0.8, 0.8), 40.0)
# the ladder: leaning on the far (y = HY1) wall, its rails run on 40 u above the floor
LX = (HX0 + 7.0, HX1 - 7.0)
yb, yt, zb, zt = HY1 - 13.0, HY1 - 4.0, -DEPTH, 42.0
dirv = np.array([0, yt - yb, zt - zb])
L_ = np.linalg.norm(dirv)
dirv /= L_
side = np.cross(ex, dirv)
lad_above, lad_below = [], []
for x_ in LX:
    for z0, z1, out in ((zb, 0.0, lad_below), (0.0, zt, lad_above)):
        s0_ = np.array([x_, yb + (yt - yb) * (z0 - zb) / (zt - zb), z0])
        s1_ = np.array([x_, yb + (yt - yb) * (z1 - zb) / (zt - zb), z1])
        box(out, (s0_ + s1_) / 2, dirv, ex, side, (np.linalg.norm(s1_ - s0_), 2.6, 3.8), 30.0)
    # rounded rail top
    box(lad_above, np.array([x_, yt, zt + 0.8]), ex, ey, up, (2.6, 3.8, 1.6), 10.0)
for zr in np.arange(zb + 10.0, zt - 6.0, 11.5):
    yr = yb + (yt - yb) * (zr - zb) / (zt - zb)
    box(lad_below if zr < -2 else lad_above, np.array([HC[0], yr, zr]), ex, ey, up, (LX[1] - LX[0], 1.8, 1.8), 12.0)
# grab post at the far right corner + a handrail down the right side to a short newel at the near corner
box(rail, (HX1 + FW + 2.0, HY1 + FW, 30.0), ex, ey, up, (3.6, 3.6, 60.0), 24.0)
box(rail, (HX1 + FW + 2.0, HY0 - FW, 18.0), ex, ey, up, (3.2, 3.2, 36.0), 24.0)
r0, r1 = np.array([HX1 + FW + 2.0, HY1 + FW, 57.5]), np.array([HX1 + FW + 2.0, HY0 - FW, 35.0])
rv = (r1 - r0) / np.linalg.norm(r1 - r0)
box(rail, (r0 + r1) / 2, rv, ex, np.cross(rv, ex), (np.linalg.norm(r1 - r0) + 3, 2.8, 2.4), 30.0)

# ---------------------------------------------------------------- 3. below: the stairwell and the landing
shaft_hi, shaft_lo, landing = [], [], []
ZB = -DEPTH
for z0, z1, out in ((-40.0, 0.0, shaft_hi), (ZB, -40.0, shaft_lo)):
    quad(out, (HX0, HY0, z1), (HX1, HY0, z1), (HX1, HY0, z0), (HX0, HY0, z0), (0, z1 / 24), (1.7, z1 / 24), (1.7, z0 / 24), (0, z0 / 24))
    quad(out, (HX1, HY1, z1), (HX0, HY1, z1), (HX0, HY1, z0), (HX1, HY1, z0), (0, z1 / 24), (1.7, z1 / 24), (1.7, z0 / 24), (0, z0 / 24))
    quad(out, (HX0, HY1, z1), (HX0, HY0, z1), (HX0, HY0, z0), (HX0, HY1, z0), (0, z1 / 24), (1.5, z1 / 24), (1.5, z0 / 24), (0, z0 / 24))
    quad(out, (HX1, HY0, z1), (HX1, HY1, z1), (HX1, HY1, z0), (HX1, HY0, z0), (0, z1 / 24), (1.5, z1 / 24), (1.5, z0 / 24), (0, z0 / 24))
quad(landing, (HX0, HY0, ZB), (HX1, HY0, ZB), (HX1, HY1, ZB), (HX0, HY1, ZB), (0, 0), (1.6, 0), (1.6, 1.4), (0, 1.4))
# the floor's thickness at the cut (the joists' edge: 6 u of dark end grain round the opening)
edge = []
for (a_, b_) in (((HX0, HY0), (HX1, HY0)), ((HX1, HY0), (HX1, HY1)), ((HX1, HY1), (HX0, HY1)), ((HX0, HY1), (HX0, HY0))):
    quad(edge, (a_[0], a_[1], 0.0), (b_[0], b_[1], 0.0), (b_[0], b_[1], -6.0), (a_[0], a_[1], -6.0), (0, 0), (2, 0), (2, 0.3), (0, 0.3))
# the bounce: a warm glow pooled on the landing, and rising up the walls (additive, soft)
glow = []
gs = 0.0
quad(glow, (HX0 + 0.5, HY0 + 0.5, ZB + 0.4), (HX1 - 0.5, HY0 + 0.5, ZB + 0.4), (HX1 - 0.5, HY1 - 0.5, ZB + 0.4), (HX0 + 0.5, HY1 - 0.5, ZB + 0.4),
     (0, 0), (1, 0), (1, 1), (0, 1))
rise = []
for (p0, p1) in (((HX0 + 0.3, HY0 + 0.3), (HX1 - 0.3, HY0 + 0.3)), ((HX1 - 0.3, HY1 - 0.3), (HX0 + 0.3, HY1 - 0.3)),
                 ((HX0 + 0.3, HY1 - 0.3), (HX0 + 0.3, HY0 + 0.3)), ((HX1 - 0.3, HY0 + 0.3), (HX1 - 0.3, HY1 - 0.3))):
    quad(rise, (p0[0], p0[1], ZB + 75), (p1[0], p1[1], ZB + 75), (p1[0], p1[1], ZB), (p0[0], p0[1], ZB), (0, 0), (1, 0), (1, 1), (0, 1))
g = np.linspace(-1, 1, 128)
GX, GY = np.meshgrid(g, g)
pool = np.clip(1 - np.sqrt(GX ** 2 + GY ** 2) / 1.05, 0, 1) ** 1.6
Image.fromarray((np.dstack([pool * 0.95, pool * 0.66, pool * 0.36]) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_hatch_pool.jpg"), quality=92)
ramp = (np.linspace(0, 1, 128)[:, None] ** 2.2) * np.ones((1, 16))      # dark at the top (v 0), warm at the bottom
Image.fromarray((np.dstack([ramp * 0.62, ramp * 0.42, ramp * 0.22]) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_hatch_rise.jpg"), quality=92)

# ---------------------------------------------------------------- 4. shaders: the game's wood, painted to the room's light
WOOD = "textures/general_structure/beam_wood1.jpg"
PLANK = "textures/general_structure/plank_flat.jpg"
FLOORT = "textures/mohtest/woodfloor2.jpg"
for tex in (WOOD, PLANK, FLOORT):
    assert any(tex in zz.namelist() for zz in [zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\main\Pak0.pk3")]) or True
SH = []


def sh(name, tex, rgb, extra=""):
    SH.append("%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap %s\n\t\trgbGen const ( %.2f %.2f %.2f )\n%s\t}\n}" % (name, tex, rgb[0], rgb[1], rgb[2], extra))


ROOM = (0.62, 0.56, 0.48)              # the attic floor's baked level at the opening (lamp-lit boards, warm)
LIT = (0.95, 0.84, 0.66)
for sfx, k in (("", ROOM), ("_lit", LIT)):
    sh("hzm_hatch_wood%s" % sfx, WOOD, k)
    sh("hzm_hatch_plank%s" % sfx, PLANK, (k[0] * 0.95, k[1] * 0.95, k[2] * 0.95))
    sh("hzm_hatch_iron%s" % sfx, WOOD, (k[0] * 0.22, k[1] * 0.22, k[2] * 0.24))
sh("hzm_hatch_shafthi", PLANK, (0.34, 0.29, 0.24))
sh("hzm_hatch_shaftlo", PLANK, (0.20, 0.17, 0.14))
sh("hzm_hatch_ladlo", WOOD, (0.30, 0.25, 0.20))
sh("hzm_hatch_landing", FLOORT, (0.24, 0.20, 0.16))
sh("hzm_hatch_edge", WOOD, (0.16, 0.13, 0.10))
SH.append("hzm_hatch_pool\n{\n\tnopicmip\n\tcull none\n\tsort additive\n\t{\n\t\tclampmap textures/menu/hzm_hatch_pool.jpg\n\t\tblendFunc add\n"
          "\t\trgbGen identity\n\t}\n}")
SH.append("hzm_hatch_rise\n{\n\tnopicmip\n\tcull none\n\tsort additive\n\t{\n\t\tclampmap textures/menu/hzm_hatch_rise.jpg\n\t\tblendFunc add\n"
          "\t\trgbGen identity\n\t}\n}")
open(os.path.join(sdir, "hzm_hatch73.shader"), "w", newline="\n").write(
    "// v1.10.73 the attic's ladder hatch (gen_hatch73.py): the game's own wood, painted to the room's baked light\n\n" + "\n\n".join(SH) + "\n")
for sfx in ("", "_lit"):
    write_model("hzm_hatch" + sfx, [("hzm_hatch_wood" + sfx, frame + ladder + lad_above + rail), ("hzm_hatch_plank" + sfx, lid),
                                    ("hzm_hatch_iron" + sfx, stay)])
write_model("hzm_hatch_below", [("hzm_hatch_shafthi", shaft_hi), ("hzm_hatch_shaftlo", shaft_lo), ("hzm_hatch_ladlo", lad_below),
                                ("hzm_hatch_landing", landing), ("hzm_hatch_edge", edge), ("hzm_hatch_pool", glow), ("hzm_hatch_rise", rise)])
import json  # noqa: E402
json.dump(INFO, open(os.path.join(add, "hatch73.json"), "w"), indent=1)
print("hatch: models hzm_hatch / _lit / _below, opening x %.0f..%.0f y %.0f..%.0f, depth %.0f" % (HX0, HX1, HY0, HY1, DEPTH))
