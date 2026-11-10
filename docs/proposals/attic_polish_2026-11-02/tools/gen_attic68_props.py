"""gen_attic68_props.py <stage62 dir> <pkadd dir> <out json> - v1.10.68: the rack moves to the MP room, the projector turns to the
right-hand wall and a pull-down screen hangs there.

User (2026-11-09): "Move the weapon rack to the LEFT wall inside the multiplayer / join-game room" + "the projector permanently
faces the RIGHT wall, where the weapons locker used to be. A pull-down screen hangs on that wall."

1. THE RACK leaves the attic: every triangle of the baked props atlas (atc_props1) inside the rack's box (attic62_edit section 9:
   the shelf, the pegs, the seven stock guns, the picture lamp - nothing else lies in it) is cut from stage62's atc_props1 IN PLACE
   (run after build_models2, before the pak copy, so every scene - main, New Game, records, viewer - takes the cut model).
   The same triangles, with their own baked light (the props atlas, shader hzm_atc_props), become models/menu/hzm_hub_rack: turned
   half round onto the MP room's left wall (hub plaster y 178.5 facing -y), the shelf sitting on the dado rail (its top z 59.1), the
   lamp 2 u lower than the rest so its wall plate clears the picture rail (z 145.9). A soft shadow decal (multiply) on the wall
   behind it - the hub's bake never saw a rack. hzm_hub_rackshadow.
2. THE PROJECTOR (atc_projector1, its reels and the lamp-lit copy) is not re-baked: the urc places each model at O with yaw TH, so a
   vertex v lands at O + R(TH) v = P + R(TH)(v - P) (O = P - R(TH) P): a turn about the projector's own centre P. TH aims the lens
   (+y in the bake) at the screen's picture centre.
3. THE SCREEN on the right-hand wall (attic plaster y -157.5 facing +y) where the rack hung: a roller case on two brackets, the
   fabric hanging from the roller's front, a weighted bottom slat and a pull ring. One atlas texture (painted light: the room is
   baked, nothing here is lit at run time - the level matches the wall beside it, SCR_LIGHT).
4. THE RUNNING PROJECTOR: the beam (an additive cone, lens to picture, soft edges, dust shimmer) and the picture's light on the
   fabric go INTO hzm_projector_lit (inverse-turned, since that model is placed with the same O / TH), so the one model the
   engine's scenehotfx already shows while the projector runs carries the beam too.
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

stage, pkadd, out_json = sys.argv[1:4]
smd = os.path.join(stage, "models", "menu")
mdir = os.path.join(pkadd, "models", "menu")
tdir = os.path.join(pkadd, "textures", "menu")
sdir = os.path.join(pkadd, "scripts")
for d_ in (mdir, tdir, sdir):
    os.makedirs(d_, exist_ok=True)
SH = []
INFO = {}


def write_model(dirp, nm, parts):
    """parts = [(shader, corners)]: corners = [[(bone, pos, nrm, uv_file)] * 3] in file winding"""
    surfs, sl = [], []
    for k, (sh_, corners) in enumerate(parts):
        if not corners:
            continue
        ss = X.split_surfaces("s%d_" % k, corners)
        surfs += ss
        sl += ["\tsurface %s shader %s" % (q[0], sh_) for q in ss]
    assert len(surfs) <= 30, (nm, len(surfs))
    Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
    open(os.path.join(dirp, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
    open(os.path.join(dirp, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(dirp, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))
    return len(surfs)


def tri_corners(p, uv, flip_v=True):
    """a triangle (3 x pos, game units) + uvs (v up) -> file corners (write_model's convention in gen_window_view.py)"""
    p = [np.asarray(q, float) for q in p]
    n = np.cross(p[1] - p[0], p[2] - p[0])
    ln = np.linalg.norm(n)
    if ln < 1e-9:
        return None
    n = n / ln
    return [(0, tuple(p[k]), tuple(-n), (float(uv[k][0]), float(1 - uv[k][1]) if flip_v else float(uv[k][1]))) for k in range(3)]


def quad_c(p0, p1, p2, p3, u0, u1, u2, u3):
    out = []
    for a, b, c in ((0, 1, 2), (0, 2, 3)):
        P_ = (p0, p1, p2, p3)
        U_ = (u0, u1, u2, u3)
        t = tri_corners((P_[a], P_[b], P_[c]), (U_[a], U_[b], U_[c]))
        if t:
            out.append(t)
    return out


# ------------------------------------------------------------------ 1. the rack: cut from the attic, rebuilt in the MP room
RACK_LO, RACK_HI = np.array([35.0, -160.0, 35.0]), np.array([130.0, -115.0, 140.0])
import shutil


def _rack_tris(path):
    d_ = R.read_skd(open(path, "rb").read())
    n = 0
    for s_ in d_["surfaces"]:
        P_ = np.array([v[3] for v in s_["verts"]])
        if len(s_["tris"]):
            c_ = P_[s_["tris"]].mean(1)
            n += int(np.all((c_ > RACK_LO) & (c_ < RACK_HI), axis=1).sum())
    return n


# a fresh build_models2 output still holds the rack: keep it as atc_props1_orig (a re-run then cuts from that again)
if _rack_tris(os.path.join(smd, "atc_props1.skd")) > 8000:
    for ext in (".skd", ".tik", ".skc"):
        shutil.copyfile(os.path.join(smd, "atc_props1" + ext), os.path.join(smd, "atc_props1_orig" + ext))
props = R.read_skd(open(os.path.join(smd, "atc_props1_orig.skd"), "rb").read())
tik = open(os.path.join(smd, "atc_props1_orig.tik")).read()
shmap = dict(l.split()[1:4:2] for l in tik.splitlines() if l.strip().startswith("surface "))
keep, rack = [], []
for s in props["surfaces"]:
    V = s["verts"]
    P = np.array([v[3] for v in V])
    T = s["tris"]
    if not len(T):
        continue
    c = P[T].mean(1)
    inb = np.all((c > RACK_LO) & (c < RACK_HI), axis=1)
    sh_ = shmap.get(s["name"], "hzm_atc_props")
    for t_, ib in zip(T, inb):
        cr = [(0, tuple(V[k][3]), tuple(V[k][0]), tuple(V[k][1])) for k in t_]
        (rack if ib else keep).append((sh_, cr))
assert 8000 < len(rack) < 12000, len(rack)
by = {}
for sh_, cr in keep:
    by.setdefault(sh_, []).append(cr)
if "--no-cut" not in sys.argv:
    n_ = write_model(smd, "atc_props1", list(by.items()))
    print("atc_props1: cut %d rack triangles, kept %d (%d surfaces) -> %s" % (len(rack), len(keep), n_, smd))
# the MP room: attic (x, y, z) -> hub (HX - (x - AX), HW - (y - AW), z + dz): half a turn about z, the wall plane onto the hub's
AX, AW = 80.9, -157.5
HX, HW = float(os.environ.get("HUB_RACK_X", "125.0")), 178.5          # x 98-152: clear of the exit door's casing (177)
DZ, DZ_LAMP = 12.0, 10.0


def to_hub(p):
    return (HX - (p[0] - AX), HW - (p[1] - AW), p[2] + (DZ_LAMP if p[2] > 120.0 else DZ))


hub = {}
for sh_, cr in rack:
    zc = np.mean([q[1][2] for q in cr])
    dz = DZ_LAMP if zc > 120.0 else DZ
    nc = [(0, (HX - (q[1][0] - AX), HW - (q[1][1] - AW), q[1][2] + dz), (-q[2][0], -q[2][1], q[2][2]), q[3]) for q in cr]
    hub.setdefault(sh_, []).append(nc)
write_model(mdir, "hzm_hub_rack", list(hub.items()))
RP = np.array([q[1] for crs in hub.values() for cr in crs for q in cr])
INFO["hub_rack_lo"], INFO["hub_rack_hi"] = RP.min(0).round(1).tolist(), RP.max(0).round(1).tolist()
INFO["hub_rack_centre"] = ((RP.min(0) + RP.max(0)) / 2).round(1).tolist()
print("hzm_hub_rack:", INFO["hub_rack_lo"], INFO["hub_rack_hi"])
# its shadow on the hub wall: a soft dark rectangle (multiply), offset down a little (the room's lamps hang from the ceiling)
W_, H_ = 256, 256
sh = Image.new("L", (W_, H_), 255)
dr = ImageDraw.Draw(sh)
dr.rectangle((56, 40, 200, 214), fill=150)
sh = sh.filter(ImageFilter.GaussianBlur(16))
Image.merge("RGB", (sh, sh, sh)).save(os.path.join(tdir, "hzm_hub_rackshadow.jpg"), quality=92)
lo, hi = RP.min(0), RP.max(0)
xs0, xs1 = lo[0] - 16, hi[0] + 16
zs0, zs1 = lo[2] - 14, hi[2] + 8
ys = HW - 0.25
write_model(mdir, "hzm_hub_rackshadow", [("hzm_hub_rackshadow", quad_c((xs1, ys, zs0), (xs0, ys, zs0), (xs0, ys, zs1), (xs1, ys, zs1),
                                                                         (0, 0), (1, 0), (1, 1), (0, 1)))])
SH.append("hzm_hub_rackshadow\n{\n\tnopicmip\n\tcull none\n\tsort decal\n\tpolygonOffset\n\t{\n\t\tmap textures/menu/hzm_hub_rackshadow.jpg\n"
          "\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}\n}")

# ------------------------------------------------------------------ 3. the pull-down screen (attic right wall, y -157.5, facing +y)
WALL = -157.5
SX0, SX1 = float(os.environ.get("SCR_X0", "47.0")), float(os.environ.get("SCR_X1", "115.0"))      # the fabric
SZ0, SZ1 = 50.0, 129.5          # (down to 50: the old rack shelf's baked shadow line on the wall stays covered)
# the case over the old picture lamp's wall plate (baked into the room at z 130-136: QA 2026-11-09, a dark square over the case)
CASE_R, CASE_Y, CASE_Z = 3.4, WALL + 4.6, 133.0
LIGHT = float(os.environ.get("SCR_LIGHT", "0.44"))           # the room's light on that wall (baked level beside the rack)
AT = 1024
atl = np.zeros((AT, AT, 3), np.float32)
rng = np.random.default_rng(68)
# fabric (0..768 x 0..768): matte white beaded cloth, a black masking border, faint hang ripples, lit a touch more from the top
fy, fx = np.mgrid[0:768, 0:768] / 767.0
weave = 1 + 0.025 * rng.standard_normal((768, 768))
weave = np.asarray(Image.fromarray(((weave - 0.9) * 1000).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 1000 + 0.9
ripple = 1 + 0.035 * np.sin(fx * math.pi * 7 + 1.3) * np.exp(-((1 - fy) * 4.0))       # hang ripples near the slat
alb = 0.86 * weave * ripple
bord = (fx < 0.035) | (fx > 0.965) | (fy < 0.03) | (fy > 0.95)
alb = np.where(bord, 0.07, alb)
light = LIGHT * (1.06 - 0.16 * fy) * (1.0 - 0.10 * np.abs(fx - 0.45))
atl[0:768, 0:768] = (alb * light)[..., None] * np.array([1.0, 0.98, 0.94])
# case (768..1024 x 0..256): dark olive enamel round a cylinder - light on top, shadow under (v = angle round it)
cv = np.linspace(0, 1, 256)[:, None]
shade = 0.35 + 0.65 * np.clip(np.cos((cv - 0.25) * 2 * math.pi), 0, 1) ** 0.7
atl[0:256, 768:1024] = (LIGHT * 0.55 * shade * (1 + 0.04 * rng.standard_normal((256, 256))))[..., None] * np.array([0.42, 0.44, 0.34])
# slat + brackets + ring (768..1024 x 256..512): dark varnished wood / black iron
atl[256:384, 768:1024] = (LIGHT * 0.5 * (1 + 0.08 * rng.standard_normal((128, 256))))[..., None] * np.array([0.52, 0.36, 0.22])
atl[384:512, 768:1024] = LIGHT * 0.22 * np.array([0.8, 0.8, 0.82])
# end caps (768..1024 x 512..640): flat, a little darker
atl[512:640, 768:1024] = LIGHT * 0.55 * 0.5 * np.array([0.42, 0.44, 0.34])          # the case's own enamel, in its shade
# shadow (0..256 x 768..1024): a soft dark halo for the wall under the screen (multiply - its own shader below)
Image.fromarray((np.clip(atl, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(tdir, "hzm_proj_screen.jpg"), quality=93)


def auv(px0, py0, px1, py1):
    """atlas pixel box -> (u0, v0, u1, v1) blender-style (v up)"""
    return px0 / AT, 1 - py1 / AT, px1 / AT, 1 - py0 / AT


S = []
FY = CASE_Y + CASE_R * 0.92                     # the fabric hangs from the roller's front
u0, v0, u1, v1 = auv(2, 2, 766, 766)
S += quad_c((SX1, FY, SZ0), (SX0, FY, SZ0), (SX0, FY, SZ1), (SX1, FY, SZ1), (u1, v0), (u0, v0), (u0, v1), (u1, v1))
# the roller case: a 16-sided cylinder along x, from SX0 - 3 to SX1 + 3, end caps
cu0, cv0, cu1, cv1 = auv(770, 2, 1022, 254)
NSEG = 16
CX0, CX1 = SX0 - 3.0, SX1 + 3.0
ring = [(CASE_Y + CASE_R * math.cos(2 * math.pi * k / NSEG), CASE_Z + CASE_R * math.sin(2 * math.pi * k / NSEG)) for k in range(NSEG + 1)]
for k in range(NSEG):
    (ya, za), (yb, zb) = ring[k], ring[k + 1]
    va, vb = cv0 + (cv1 - cv0) * (k / NSEG), cv0 + (cv1 - cv0) * ((k + 1) / NSEG)
    S += quad_c((CX0, ya, za), (CX1, ya, za), (CX1, yb, zb), (CX0, yb, zb), (cu0, va), (cu1, va), (cu1, vb), (cu0, vb))
eu0, ev0, eu1, ev1 = auv(770, 514, 1022, 638)
for xe in (CX0, CX1):
    for k in range(NSEG):
        (ya, za), (yb, zb) = ring[k], ring[k + 1]
        t = tri_corners(((xe, CASE_Y, CASE_Z), (xe, ya, za), (xe, yb, zb)), ((eu0, ev0), (eu1, ev0), (eu1, ev1)))
        if t:
            S.append(t)
# brackets: two iron plates from the wall to the case ends
bu0, bv0, bu1, bv1 = auv(770, 386, 1022, 510)


def box(x0, x1, y0, y1, z0, z1, uvb):
    a0, b0_, a1, b1_ = uvb
    out = []
    for p0, p1, p2, p3 in (((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)), ((x1, y0, z0), (x0, y0, z0), (x0, y0, z1), (x1, y0, z1)),
                           ((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)), ((x1, y1, z0), (x1, y0, z0), (x1, y0, z1), (x1, y1, z1)),
                           ((x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1)), ((x0, y1, z0), (x0, y0, z0), (x1, y0, z0), (x1, y1, z0))):
        out += quad_c(p0, p1, p2, p3, (a0, b0_), (a1, b0_), (a1, b1_), (a0, b1_))
    return out


for xb in (CX0 - 0.6, CX1 + 0.0):
    S += box(xb, xb + 0.6, WALL + 0.05, CASE_Y + 1.2, CASE_Z - CASE_R - 0.8, CASE_Z + CASE_R + 0.8, (bu0, bv0, bu1, bv1))
# the bottom slat (wood) and the pull ring (iron) on a short cord
wu0, wv0, wu1, wv1 = auv(770, 258, 1022, 382)
S += box(SX0 - 1.0, SX1 + 1.0, FY - 0.7, FY + 0.7, SZ0 - 2.2, SZ0 + 0.1, (wu0, wv0, wu1, wv1))
XC = (SX0 + SX1) / 2
S += box(XC - 0.12, XC + 0.12, FY - 0.12, FY + 0.12, SZ0 - 6.0, SZ0 - 2.2, (bu0, bv0, bu1, bv1))
RR, RZ = 1.5, SZ0 - 7.5
for k in range(12):
    a, b = 2 * math.pi * k / 12, 2 * math.pi * (k + 1) / 12
    pa = (XC + RR * math.cos(a), FY, RZ + RR * math.sin(a))
    pb = (XC + RR * math.cos(b), FY, RZ + RR * math.sin(b))
    for dy in (-0.2, 0.2):
        S += quad_c((pa[0], FY + dy, pa[2]), (pb[0], FY + dy, pb[2]), (pb[0] * 0.92 + XC * 0.08, FY + dy, pb[2] * 0.92 + RZ * 0.08),
                    (pa[0] * 0.92 + XC * 0.08, FY + dy, pa[2] * 0.92 + RZ * 0.08), (bu0, bv0), (bu1, bv0), (bu1, bv1), (bu0, bv1))
# a soft contact shadow on the wall round the screen (multiply decal)
shd = Image.new("L", (256, 256), 255)
ImageDraw.Draw(shd).rectangle((40, 30, 216, 236), fill=170)
shd = shd.filter(ImageFilter.GaussianBlur(14))
Image.merge("RGB", (shd, shd, shd)).save(os.path.join(tdir, "hzm_proj_screenshadow.jpg"), quality=92)
SD = quad_c((SX1 + 9, WALL + 0.2, SZ0 - 12), (SX0 - 9, WALL + 0.2, SZ0 - 12), (SX0 - 9, WALL + 0.2, CASE_Z + 6), (SX1 + 9, WALL + 0.2, CASE_Z + 6),
            (1, 0), (0, 0), (0, 1), (1, 1))
write_model(mdir, "hzm_proj_screen", [("hzm_proj_screen", S), ("hzm_proj_screenshadow", SD)])
SH.append("hzm_proj_screen\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_proj_screen.jpg\n\t\trgbGen identity\n\t}\n}")
SH.append("hzm_proj_screenshadow\n{\n\tnopicmip\n\tcull none\n\tsort decal\n\tpolygonOffset\n\t{\n\t\tmap textures/menu/hzm_proj_screenshadow.jpg\n"
          "\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}\n}")

# ------------------------------------------------------------------ 2. the projector's turn: lens (+y in the bake) at the picture
pj = R.read_skd(open(os.path.join(smd, "atc_projector1.skd"), "rb").read())
PP = np.concatenate([np.array([v[3] for v in s["verts"]]) for s in pj["surfaces"]])
PC = (PP.min(0) + PP.max(0)) / 2
LENS0 = np.array([101.6, PP[:, 1].max(), 62.2])             # the lens tube's front (bake: +y end, x 101.6, z 62)
PIC = np.array([XC, FY + 0.3, float(os.environ.get("SCR_PICZ", "84.0"))])      # the picture's centre on the fabric
PICW, PICH = float(os.environ.get("SCR_PICW", "50.0")), float(os.environ.get("SCR_PICH", "38.0"))


def turn(p, th):
    c, s_ = math.cos(th), math.sin(th)
    d = np.asarray(p, float) - PC
    return np.array([PC[0] + c * d[0] - s_ * d[1], PC[1] + s_ * d[0] + c * d[1], p[2]])


th = math.pi
for _ in range(20):                          # the lens moves as the body turns: iterate to aim it
    L = turn(LENS0, th)
    want = math.atan2(PIC[1] - L[1], PIC[0] - L[0])
    th = want - math.pi / 2
O = PC - np.array([math.cos(th) * PC[0] - math.sin(th) * PC[1], math.sin(th) * PC[0] + math.cos(th) * PC[1], PC[2]])
O[2] = 0.0
INFO["proj_pivot"] = PC.round(3).tolist()
INFO["proj_yaw"] = round(math.degrees(th), 3)
INFO["proj_origin"] = O.round(3).tolist()
LENS = turn(LENS0, th)
INFO["lens"] = LENS.round(2).tolist()
print("projector: pivot", PC.round(2), "yaw %.2f" % math.degrees(th), "origin", O.round(2), "lens", LENS.round(2), "picture", PIC)


def place_world(p):
    """a baked (unturned) model point -> where the urc puts it (O + R(th) p)"""
    c, s_ = math.cos(th), math.sin(th)
    return np.array([O[0] + c * p[0] - s_ * p[1], O[1] + s_ * p[0] + c * p[1], p[2]])


def unplace(w):
    """world -> the model space of a model placed with O / th (for geometry added to hzm_projector_lit)"""
    c, s_ = math.cos(-th), math.sin(-th)
    d = np.asarray(w, float) - np.array([O[0], O[1], 0.0])
    return np.array([c * d[0] - s_ * d[1], s_ * d[0] + c * d[1], w[2]])


INFO["turn_cs"] = [math.cos(th), math.sin(th)]

# ------------------------------------------------------------------ 4. the running projector: beam + the picture's light -> hzm_projector_lit
# the beam texture: u along the beam (0 lens .. 1 screen), v across; bright core near the lens, soft edges, dust streaks
BW, BH = 256, 128
bu = np.linspace(0, 1, BW)[None, :]
bv = np.linspace(-1, 1, BH)[:, None]
dust = np.asarray(Image.fromarray((rng.random((BH, BW)) * 255).astype(np.uint8)).resize((BW, BH)).filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
beam = np.exp(-(bv ** 2) * 5.0) * (0.16 * (1 - bu) ** 1.6 + 0.045) * (0.7 + 0.6 * dust)      # soft: a face fades out to its edges
beam *= np.clip(bu * 30, 0, 1)
Image.fromarray((np.clip(beam[..., None] * np.array([1.0, 0.92, 0.75]), 0, 1) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_proj_beam.jpg"), quality=92)
# the picture's light on the fabric: warm white, a soft vignette, the gate's rounded corners
gx, gy = np.mgrid[-1:1:256j, -1:1:192j]
gate = np.clip((1 - np.maximum(np.abs(gx) ** 6, np.abs(gy) ** 6)) * 3, 0, 1).T
vig = (1 - 0.35 * (gx ** 2 + gy ** 2)).T
pic = gate * vig * 0.55
Image.fromarray((np.clip(pic[..., None] * np.array([1.0, 0.95, 0.82]), 0, 1) * 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_proj_picture.jpg"), quality=92)
if os.path.exists(os.path.join(mdir, "hzm_projector_lit.skd")):     # (the first, early run of the build has no lit model yet)
    lit = R.read_skd(open(os.path.join(mdir, "hzm_projector_lit.skd"), "rb").read())
    _lsh = dict(l.split()[1:4:2] for l in open(os.path.join(mdir, "hzm_projector_lit.tik")).read().splitlines() if l.strip().startswith("surface "))
    lit_parts = []
    for s in lit["surfaces"]:
        if _lsh.get(s["name"]) != "hzm_projector_lit":          # (a re-run: the beam / picture added last time)
            continue
        V = s["verts"]
        lit_parts.append(("hzm_projector_lit", [[(0, tuple(V[k][3]), tuple(V[k][0]), tuple(V[k][1])) for k in t_] for t_ in s["tris"]]))
    # the cone: the lens aperture (r 1.1) to the picture rectangle, 8 sides (4 faces + their corners), each face its own quad
    L = LENS
    ax = (PIC - L) / np.linalg.norm(PIC - L)
    right = np.array([1.0, 0.0, 0.0]) if abs(ax[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    rgt = np.cross(ax, np.array([0.0, 0.0, 1.0]))
    rgt /= np.linalg.norm(rgt)
    upv = np.cross(rgt, ax)
    r0 = 1.1
    far = [PIC + rgt * sx * PICW / 2 + np.array([0, 0, 1.0]) * sz * PICH / 2 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    near = [L + rgt * sx * r0 + upv * sz * r0 * 0.75 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    BEAM = []
    # three nested pyramids (the whole picture, 0.7, 0.4): additive faces that fade out across their width, so no edge or
    # corner of the cone draws a line (QA 2026-11-09: crossed sheets and hard faces read as glass wedges)
    for sc_ in (1.0, 0.7, 0.4):
        far_ = [PIC + (q - PIC) * sc_ for q in far]
        for k in range(4):
            a, b = k, (k + 1) % 4
            BEAM += quad_c(unplace(near[a]), unplace(near[b]), unplace(far_[b]), unplace(far_[a]), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
    PICQ = quad_c(*[unplace(np.array([q[0], FY + 0.35, q[2]])) for q in (far[1], far[0], far[3], far[2])], (1, 0), (0, 0), (0, 1), (1, 1))
    lit_parts += [("hzm_proj_beam", BEAM), ("hzm_proj_picture", PICQ)]
    write_model(mdir, "hzm_projector_lit", lit_parts)
else:
    print("no hzm_projector_lit yet: beam not added")
SH.append("hzm_proj_beam\n{\n\tnopicmip\n\tcull none\n\tsort additive\n\t{\n\t\tclampmap textures/menu/hzm_proj_beam.jpg\n\t\tblendFunc add\n"
          "\t\tdepthWrite\n\t\trgbGen wave noise 0.85 0.15 0 9\n\t}\n}".replace("\t\tdepthWrite\n", ""))
SH.append("hzm_proj_picture\n{\n\tnopicmip\n\tcull none\n\tsort additive\n\tpolygonOffset\n\t{\n\t\tclampmap textures/menu/hzm_proj_picture.jpg\n"
          "\t\tblendFunc add\n\t\trgbGen wave noise 0.8 0.2 0 12\n\t}\n}")
open(os.path.join(sdir, "hzm_attic68.shader"), "w", newline="\n").write("\n\n".join(SH) + "\n")
INFO["screen"] = dict(x0=SX0, x1=SX1, z0=SZ0, z1=SZ1, fy=FY, pic=PIC.round(2).tolist())
json.dump(INFO, open(out_json, "w"), indent=1)
print("attic68 props ->", out_json)

# the projector's run, LOW (user: "the projector makes its sounds (motor and clatter, low)"): the hover / running loop to -28 dB RMS
# (gen_projector_fx.py's cut of the stock Projector.wav sat at -19.5 dB). Scaled to a target, so a re-run leaves it alone.
import wave
_wp = os.path.join(pkadd, "sound", "menu", "hzm_projector_loop.wav")
if os.path.exists(_wp):
    w_ = wave.open(_wp)
    prm = w_.getparams()
    a_ = np.frombuffer(w_.readframes(w_.getnframes()), np.int16).astype(np.float64)
    w_.close()
    rms = math.sqrt((a_ ** 2).mean()) / 32768
    g = 10 ** (-28 / 20) / max(rms, 1e-6)
    if abs(20 * math.log10(g)) > 0.3:
        o_ = wave.open(_wp, "wb")
        o_.setparams(prm)
        o_.writeframes(np.clip(a_ * g, -32768, 32767).astype(np.int16).tobytes())
        o_.close()
    print("projector loop: %.1f dB RMS -> -28 dB" % (20 * math.log10(rms)))
