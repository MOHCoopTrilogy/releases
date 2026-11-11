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
                                the room's baked light (baked into copies of the textures: the attic is baked, nothing is lit at run time)
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

# ---------------------------------------------------------------- 2. above the floor (v2, coordinator QA: "fuzzy, stretched wood
# reads as a CG placeholder; noisy boxes; a flat smeared panel; an undersized ladder poking up mid-floor")
# Every piece of wood is a PLANK of the attic's own floor texture (hzm_atc_floor_alb: 8 planks per tile, one plank = 7.9 u at the
# floor's own scale - tile 126 u along the boards), so the hatch is cut from the same boards it sits in. Each piece takes one plank
# row (different rows per piece, grain along its length), the room light baked into the copy (rgbGen identity).
import io  # noqa: E402
ALB = np.asarray(Image.open(io.BytesIO(Z.read("textures/menu/hzm_atc_floor_alb.jpg"))).convert("RGB"), np.float32)
TILE_U, PLANK = 126.0, 7.875
up, ex, ey = np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
_row = [0]


def plank_box(out, c, ax, ay, az, size, row=None, end_grain=0.18):
    """an oriented box (centre c, unit axes ax ay az, size along them); its long axis carries the grain: the faces along it map
    the length over u (TILE_U per tile) and ONE plank row (v) round the section; the end faces take a small patch (end grain)"""
    c = np.asarray(c, float)
    ax, ay, az = (np.asarray(v, float) for v in (ax, ay, az))
    size = np.asarray(size, float)
    L = int(np.argmax(size))
    axes = [ax, ay, az]
    if row is None:
        row = _row[0] % 8
        _row[0] += 3
    v0, v1 = row / 8.0, (row + 1) / 8.0
    u_off = (_row[0] * 0.37) % 1.0
    h = size / 2
    A = [axes[i] * h[i] for i in range(3)]
    for i in range(3):
        for s in (-1, 1):
            j, k = (i + 1) % 3, (i + 2) % 3
            fc = c + A[i] * s
            pts = [fc - A[j] - A[k], fc + A[j] - A[k], fc + A[j] + A[k], fc - A[j] + A[k]]
            if i == L:                                     # end grain: a small square of the plank
                uv = [(u_off, v0), (u_off + end_grain, v0), (u_off + end_grain, v1), (u_off, v1)]
            elif j == L:
                lu = size[L] / TILE_U
                uv = [(u_off, v0), (u_off + lu, v0), (u_off + lu, v1), (u_off, v1)]
            else:                                          # k == L
                lu = size[L] / TILE_U
                uv = [(u_off, v0), (u_off, v1), (u_off + lu, v1), (u_off + lu, v0)]
            if s < 0:
                pts, uv = pts[::-1], uv[::-1]
            tri(out, pts[:3], uv[:3])
            tri(out, [pts[0], pts[2], pts[3]], [uv[0], uv[2], uv[3]])


def rung(out, a, b, rad=1.05, n=8):
    """a round rung (octagonal prism) from a to b; grain along it"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    d /= L
    s1 = np.cross(d, up)
    s1 = s1 / np.linalg.norm(s1) if np.linalg.norm(s1) > 1e-6 else ey
    s2 = np.cross(d, s1)
    row = _row[0] % 8
    _row[0] += 3
    v0, v1 = row / 8.0, (row + 1) / 8.0
    for k in range(n):
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        o0 = (s1 * math.cos(t0) + s2 * math.sin(t0)) * rad
        o1 = (s1 * math.cos(t1) + s2 * math.sin(t1)) * rad
        q = [a + o0, b + o0, b + o1, a + o1]
        vv0, vv1 = v0 + (v1 - v0) * k / n, v0 + (v1 - v0) * (k + 1) / n
        uv = [(0, vv0), (L / TILE_U, vv0), (L / TILE_U, vv1), (0, vv1)]
        tri(out, q[:3], uv[:3])
        tri(out, [q[0], q[2], q[3]], [uv[0], uv[2], uv[3]])


frame, lid, ladder_up, rail, iron = [], [], [], [], []
brace, rim = [], []        # rain73 v2: the leaf's battens + Z-brace in the lighter frame wood, a thin lit trim on its edges
# the frame: four boards round the opening, flush with the floor (0.1 u proud), mitred lengths
FW, FT = 5.5, 0.6
for (c, a1, sz) in (((HC[0], HY0 - FW / 2, FT / 2 - 0.5), ex, (HX1 - HX0 + 2 * FW, FW, FT)),
                    ((HC[0], HY1 + FW / 2, FT / 2 - 0.5), ex, (HX1 - HX0 + 2 * FW, FW, FT)),
                    ((HX0 - FW / 2, HC[1], FT / 2 - 0.5), ey, (HY1 - HY0, FW, FT)),
                    ((HX1 + FW / 2, HC[1], FT / 2 - 0.5), ey, (HY1 - HY0, FW, FT))):
    plank_box(frame, c, a1, np.cross(up, a1), up, sz)
# the lining: the opening's edges, the joists' faces (6 u deep) - lit wood, no void under the rim
for (p, q, nrm) in (((HX0, HY0), (HX1, HY0), ey), ((HX1, HY0), (HX1, HY1), -ex), ((HX1, HY1), (HX0, HY1), -ey), ((HX0, HY1), (HX0, HY0), ex)):
    c = np.array([(p[0] + q[0]) / 2, (p[1] + q[1]) / 2, -3.2]) - np.asarray(nrm) * 0.6
    ln = math.hypot(q[0] - p[0], q[1] - p[1])
    a1 = np.array([q[0] - p[0], q[1] - p[1], 0.0]) / ln
    plank_box(frame, c, a1, np.cross(up, a1), up, (ln, 1.2, 6.4))
# the trapdoor: hinged on the far edge (y = HY1), swung up to 100 deg, leaning back - five planks with gaps, two battens and a
# Z-brace on its underside (now facing the opening), two iron strap hinges over the hinge edge
# v3 (coordinator: "the trapdoor and ladder top stand oddly tall and close together, like a crate frame"): open to a clear 115 deg,
# leaning back on a stop post; the hinge line ON the frame's inner edge, at the frame's top face
th = math.radians(115.0)
lw, ld, lt = HY1 - HY0 - 0.5, HX1 - HX0 - 0.5, 1.8
d_ = np.array([0.0, -math.cos(th), math.sin(th)])
n_ = np.array([0.0, math.sin(th), math.cos(th)])
hinge = np.array([HC[0], HY1, FT - 0.5])
NP = 5
pw = ld / NP
for k in range(NP):
    xk = HX0 + 0.25 + pw * (k + 0.5) - HC[0]
    plank_box(lid, hinge + d_ * lw / 2 + n_ * lt / 2 + ex * xk, d_, ex, n_, (lw, pw - 0.35, lt))
for f_ in (0.15, 0.85):
    plank_box(brace, hinge + d_ * lw * f_ - n_ * 1.0, ex, d_, -n_, (ld - 3.0, 4.2, 2.0))
zb = (ex * (ld / 2 - 4.0) + d_ * lw * 0.15) - (-ex * (ld / 2 - 4.0) + d_ * lw * 0.85)
zl = np.linalg.norm(zb)
plank_box(brace, hinge + d_ * lw * 0.5 - n_ * 1.0, zb / zl, np.cross(-n_, zb / zl), -n_, (zl, 3.6, 2.0))
# the rim light: the leaf's free edge and its two sides catch the room's light - a 0.8 u trim, proud of both faces by 0.2 u
plank_box(rim, hinge + d_ * (lw + 0.3) + n_ * lt / 2, ex, d_, n_, (ld + 0.6, 0.8, lt + 0.4))
for sx in (-1, 1):
    plank_box(rim, hinge + d_ * lw / 2 + n_ * lt / 2 + ex * sx * (ld / 2 + 0.3), d_, ex, n_, (lw, 0.8, lt + 0.4))
for sx in (-1, 1):                                   # strap hinges: across the hinge line, half on the leaf, half on the frame
    hc = hinge + ex * sx * (ld / 2 - 7.0) + d_ * 5.0 + n_ * (lt + 0.25)
    plank_box(iron, hc, d_, ex, n_, (11.0, 2.0, 0.5))
    plank_box(iron, hinge + ex * sx * (ld / 2 - 7.0) + ey * (FW * 0.5) + up * 0.35, ey, ex, up, (FW - 0.6, 2.0, 0.5))
    rung(iron, hinge + ex * (sx * (ld / 2 - 7.0) - 1.6), hinge + ex * (sx * (ld / 2 - 7.0) + 1.6), rad=0.55, n=6)   # the knuckle
# the stop: a short post on the floor behind the frame, its top under the leaf's back face (where the leaf rests)
s_rest = 24.0
rest = hinge + d_ * s_rest + n_ * lt
plank_box(brace, (HC[0], rest[1] + 2.2, rest[2] / 2), up, ex, ey, (rest[2], 4.4, 4.4))
# the ladder: a loft ladder from the landing, leaning on the far wall at ~75 deg; two stiles (2.4 x 5.5), round rungs every
# 10.5 u, the stiles run on 48 u above the floor (grab rails, rounded tops) - full size: 0.62 m between the stiles
LX = (HC[0] - 16.5, HC[0] + 16.5)
yb, yt, zb_, zt = HY1 - 28.0, HY1 - 4.0, -DEPTH, 36.0                 # v3: the stiles rise ~0.7 m above the floor (were 48 u)
dv = np.array([0, yt - yb, zt - zb_])
dv /= np.linalg.norm(dv)
sd = np.cross(ex, dv)
lad_below = []
for x_ in LX:
    for z0, z1, out in ((zb_, -0.3, lad_below), (-0.3, zt, ladder_up)):
        s0_ = np.array([x_, yb + (yt - yb) * (z0 - zb_) / (zt - zb_), z0])
        s1_ = np.array([x_, yb + (yt - yb) * (z1 - zb_) / (zt - zb_), z1])
        plank_box(out, (s0_ + s1_) / 2, dv, ex, sd, (np.linalg.norm(s1_ - s0_), 2.4, 5.5))
    tp = np.array([x_, yt, zt])
    plank_box(ladder_up, tp + dv * 0.9, dv, ex, sd, (1.8, 2.0, 4.6))         # a rounded-off top (a shorter cap)
for zr in np.arange(zb_ + 9.0, zt - 4.0, 10.5):
    yr = yb + (yt - yb) * (zr - zb_) / (zt - zb_)
    rung(ladder_up if zr > -1.0 else lad_below, (LX[0] + 1.2, yr, zr), (LX[1] - 1.2, yr, zr))
# the guard rail along the open right side: two posts (4 x 4), a handrail and a mid rail
RX = HX1 + FW + 2.2
for py in (HY0 - FW, HY1 + FW):
    plank_box(rail, (RX, py, 23.0), up, ex, ey, (46.0, 4.0, 4.0))
plank_box(rail, (RX, HC[1], 44.0), ey, ex, up, (HY1 - HY0 + 2 * FW + 4.0, 3.6, 3.2))
plank_box(rail, (RX, HC[1], 23.0), ey, ex, up, (HY1 - HY0 + 2 * FW, 2.4, 3.0))

# ---------------------------------------------------------------- 3. below: a plastered stairwell, warm-lit from the landing
shaft, landing = [], []
ZB = -DEPTH
for (p0, p1) in (((HX0, HY0), (HX1, HY0)), ((HX1, HY0), (HX1, HY1)), ((HX1, HY1), (HX0, HY1)), ((HX0, HY1), (HX0, HY0))):
    ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    quad(shaft, (p0[0], p0[1], -6.4), (p1[0], p1[1], -6.4), (p1[0], p1[1], ZB), (p0[0], p0[1], ZB),
         (0, 0), (ln / 64.0, 0), (ln / 64.0, 1), (0, 1))
quad(landing, (HX0, HY0, ZB), (HX1, HY0, ZB), (HX1, HY1, ZB), (HX0, HY1, ZB),
     (0, 0), ((HX1 - HX0) / TILE_U, 0), ((HX1 - HX0) / TILE_U, (HY1 - HY0) / 63.0), (0, (HY1 - HY0) / 63.0))
# the lamp's light on the far wall, below the rim (what the turn view sees down the opening): an additive warm pool
glow = []
gy = HY1 - 0.3
quad(glow, (HX0 + 2, gy, -10.0), (HX1 - 2, gy, -10.0), (HX1 - 2, gy, -70.0), (HX0 + 2, gy, -70.0), (0, 0), (1, 0), (1, 1), (0, 1))
quad(glow, (HX0 + 1, HY0 + 1, ZB + 0.4), (HX1 - 1, HY0 + 1, ZB + 0.4), (HX1 - 1, HY1 - 1, ZB + 0.4), (HX0 + 1, HY1 - 1, ZB + 0.4),
     (0, 0), (1, 0), (1, 1), (0, 1))

# ---------------------------------------------------------------- 4. textures + shaders (the light baked in, rgbGen identity)
PAK2 = zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\main\Pak2.pk3")
SH = []


def bake(name, src, rgb, ramp=None):
    im = src.copy()
    if ramp is not None:                       # a vertical light ramp baked in (v 0 = top of the shaft .. 1 = the landing)
        h = im.shape[0]
        r = np.interp(np.linspace(0, 1, h), np.linspace(0, 1, len(ramp)), ramp)[:, None, None]
        im = im * r
    im = np.clip(im * np.array(rgb, np.float32)[None, None, :], 0, 255).astype(np.uint8)
    Image.fromarray(im).save(os.path.join(tdir, name + ".jpg"), quality=92)


def shader(name, clamp=False, extra=""):
    SH.append("%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\t%s textures/menu/%s.jpg\n\t\trgbGen identity\n%s\t}\n}" % (name, "clampmap" if clamp else "map", name, extra))


ROOM = (0.42, 0.38, 0.37)              # the boards' level beside the opening, measured twice in-game against the lightmapped floor there
LIT = (0.58, 0.51, 0.45)               # hover: ~1.35 x and warmer
# the trapdoor (rain73, coordinator: "still reads a little like a crate panel standing upright"): seen from the opening it shows
# its UNDERSIDE - years of the stairwell's dust and damp: darker, greyer, a grimy bloom towards its lower edge and fine streaks
_r = np.random.default_rng(1945)
_h, _w = ALB.shape[:2]
_grey = ALB.mean(2, keepdims=True)
_lid = ALB * 0.62 + _grey * 0.38                                         # weathered greyer
_n = np.asarray(Image.fromarray((_r.random((_h // 16, _w // 16)) * 255).astype(np.uint8)).resize((_w, _h), Image.BICUBIC), np.float32) / 255
_streak = np.asarray(Image.fromarray((_r.random((8, _w // 4)) * 255).astype(np.uint8)).resize((_w, _h), Image.BICUBIC), np.float32) / 255
_lid = _lid * (0.78 + 0.16 * _n[..., None]) * (0.88 + 0.12 * _streak[..., None])
for sfx, k in (("", ROOM), ("_lit", LIT)):
    bake("hzm_hatch_wood%s" % sfx, ALB, k)
    shader("hzm_hatch_wood%s" % sfx)
    bake("hzm_hatch_lid%s" % sfx, _lid[::2, ::2], (k[0] * 0.98, k[1] * 0.97, k[2] * 0.99))      # half size: small on screen (menu VRAM, menuload)
    shader("hzm_hatch_lid%s" % sfx)
    bake("hzm_hatch_iron%s" % sfx, ALB, (k[0] * 0.16, k[1] * 0.16, k[2] * 0.17))
    shader("hzm_hatch_iron%s" % sfx)
plaster = np.asarray(Image.open(io.BytesIO(PAK2.read("textures/general_structure/plaster_wall2.jpg"))).convert("RGB"), np.float32)
bake("hzm_hatch_shaft", plaster, (0.95, 0.80, 0.60), ramp=[0.34, 0.42, 0.55, 0.72, 0.86])      # dim at the rim, warmer down to the lamp
shader("hzm_hatch_shaft")
bake("hzm_hatch_ladlo", ALB, (0.62, 0.52, 0.38))
shader("hzm_hatch_ladlo")
bake("hzm_hatch_landing", ALB, (0.70, 0.58, 0.40))
shader("hzm_hatch_landing")
g = np.linspace(-1, 1, 128)
GX, GY = np.meshgrid(g, g)
pool = np.clip(1 - np.sqrt((GX / 1.0) ** 2 + ((GY - 0.25) / 0.9) ** 2), 0, 1) ** 1.8 * 0.55
Image.fromarray((np.dstack([pool * 1.0, pool * 0.70, pool * 0.38]).clip(0, 1) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_hatch_pool.jpg"), quality=92)
SH.append("hzm_hatch_pool\n{\n\tnopicmip\n\tcull none\n\tsort additive\n\tpolygonOffset\n\t{\n\t\tclampmap textures/menu/hzm_hatch_pool.jpg\n"
          "\t\tblendFunc add\n\t\trgbGen identity\n\t}\n}")
open(os.path.join(sdir, "hzm_hatch73.shader"), "w", newline="\n").write(
    "// v1.10.73 the attic's ladder hatch (gen_hatch73.py v2): the attic floor's own boards, the room light baked in; a plastered,\n"
    "// warm-lit stairwell below\n\n" + "\n\n".join(SH) + "\n")
for sfx in ("", "_lit"):
    write_model("hzm_hatch" + sfx, [("hzm_hatch_wood" + sfx, frame + ladder_up + rail + brace), ("hzm_hatch_lid" + sfx, lid), ("hzm_hatch_wood_lit", rim),
                                    ("hzm_hatch_iron" + sfx, iron)])
write_model("hzm_hatch_below", [("hzm_hatch_shaft", shaft), ("hzm_hatch_ladlo", lad_below), ("hzm_hatch_landing", landing),
                                ("hzm_hatch_pool", glow)])
import json  # noqa: E402
json.dump(INFO, open(os.path.join(add, "hatch73.json"), "w"), indent=1)
print("hatch v2: models hzm_hatch / _lit / _below, opening x %.0f..%.0f y %.0f..%.0f, depth %.0f" % (HX0, HX1, HY0, HY1, DEPTH))
