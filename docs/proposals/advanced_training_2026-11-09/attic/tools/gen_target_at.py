"""gen_target_at.py <pkadd dir> <out json> [<menus pk3> <main.urc>] - the TRAINING prop in the 3D attic.   [advtrain 2026-11-10]

Basic Training (map training) had no home in the 3D attic, and Advanced Training (m4l0, coop_advTraining 1) is new; memory note
menu-homes-in-world: a feature gets a prop in the attic that lights up while highlighted, never a brown button. The prop: a rifle
range PRACTICE TARGET on a wooden easel - two splayed front legs, a back leg hinged under the top cross-piece, a ledge between the
front legs; on the ledge a plywood backing board leaning on the legs, and pinned to it (four brass tacks) a paper bullseye card:
black aiming bull with the 7 to 10 rings, white 5 / 6 rings, the ring numbers, PRACTICE TARGET / RANGE 50 FT. Seven hits, five
of them a group at the bull, two fliers, the score pencilled beside the rings. Pine for the easel (the room's stock
textures/das_boot/wood.jpg grain, lightened), the board's plywood face from the same grain, and a soft contact shadow on the floor.
Recipe: gen_byodisc70.py (v1.10.70 OWN DISCS film cans) - same model writer (skx), lit copy (x1.32/1.27/1.14 warm), shaders
(rgbGen lightingSpherical, patch_attic_at.py adds a fill light), world-space verts placed at 0 0 0 0.

PLACEMENT (world units, 52.5 per metre): the open floor between the officer's map table and the radio bench, in front of the
two filing cabinets, left of the officer (TGT_X / TGT_Y override). With <menus pk3> <main.urc> the script RAYCASTS against
the baked room (atticview.load_scene): each foot is dropped onto the highest surface under it (floor), and every part's box is
tested against a dense point sampling of the room's triangles - any room point inside a part = intersection = abort.
The easel faces the home camera, turned TURN degrees off it so its depth reads (a three-quarter view).

Output: models/menu/hzm_at_target(.tik/.skd/.skc) + _lit, textures/menu/hzm_at_*, scripts/hzm_at_target.shader; the json
carries the prop's world bounds, centre, the camera azimuth and the urc lines for patch_attic_at.py.
"""
import json, math, os, re, sys, io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import skx as X  # noqa: E402
import vfs  # noqa: E402

_paks0 = vfs.paks                                  # the game's own assets only (pak0..pak7), never an HD / mod pak
vfs.paks = lambda: [p for p in _paks0() if re.match(r"(?i)^pak\d", os.path.basename(p))]
vfs._idx = None

pkadd, out_json = sys.argv[1:3]
RAY = sys.argv[3:5] if len(sys.argv) >= 5 else None
mdir, tdir, sdir = (os.path.join(pkadd, d) for d in ("models/menu", "textures/menu", "scripts"))
for d_ in (mdir, tdir, sdir):
    os.makedirs(d_, exist_ok=True)
FD = r"C:\Windows\Fonts"
rng = np.random.default_rng(1943)
PFX = "hzm_at"

C = np.array([float(os.environ.get("TGT_X", "266.0")), float(os.environ.get("TGT_Y", "258.0"))])
HOME_CAM = np.array([-36.7, 21.0])
CAM_AZ = math.degrees(math.atan2(HOME_CAM[1] - C[1], HOME_CAM[0] - C[0]))     # the home camera, seen from the easel
TURN = float(os.environ.get("TGT_TURN", "-14.0"))         # the easel's front turned this far off the camera (three-quarter)
FRONT_AZ = CAM_AZ + TURN
YAW = FRONT_AZ - 90.0                                     # local +y (the easel's front) -> FRONT_AZ

# ------------------------------------------------------------------ dimensions (local: x = viewer's right, y = front, z up)
LEG_W, LEG_D = 2.0, 1.3                 # front legs 38 x 25 mm
FOOT_X, FOOT_Y = 15.5, 4.0              # front feet
TOP_X, TOP_Y, TOP_Z = 8.5, -3.0, 80.0   # front leg tops (under the cross-piece)
BACK_FOOT = (0.0, -30.0)                # back leg foot (hinged at the cross-piece)
LEDGE_Z = 27.0                          # the ledge's top
BOARD_W, BOARD_H, BOARD_T = 36.0, 44.0, 0.8
CARD_W, CARD_H = 30.0, 36.0


def leg_y(z):
    return FOOT_Y + (TOP_Y - FOOT_Y) * z / TOP_Z


def leg_x(z):
    return FOOT_X + (TOP_X - FOOT_X) * z / TOP_Z


LEAN = math.atan2(FOOT_Y - TOP_Y, TOP_Z)      # the legs' (and the board's) lean back from vertical


def font(n, px):
    return ImageFont.truetype(os.path.join(FD, n), int(px))


# ------------------------------------------------------------------ textures
def game_tex(path):
    return np.asarray(Image.open(io.BytesIO(vfs.read(path))).convert("RGB"), np.float32)


WOOD = game_tex("textures/das_boot/wood.jpg")          # smooth dark grain (the room's furniture tone); lightened to pine


def wood_strip(w, h, seed, tone=(1.55, 1.38, 1.12), lift=(18, 12, 4)):
    """pine: the stock grain (grain runs along v in the source) resampled along u, lightened and warmed, a little mottle"""
    src = WOOD
    g = np.random.default_rng(seed)
    x0 = int(g.integers(0, src.shape[1] - 64))
    crop = src[:, x0:x0 + 64]
    a = np.asarray(Image.fromarray(np.uint8(crop)).transpose(Image.ROTATE_90).resize((w, h), Image.BICUBIC), np.float32)
    a = a * np.array(tone) + np.array(lift)
    n = np.asarray(Image.fromarray(np.uint8(g.random((h // 8 + 1, w // 8 + 1)) * 255)).resize((w, h), Image.BICUBIC), np.float32) / 255
    return np.clip(a * (0.92 + 0.12 * n[..., None]), 0, 255)


def plywood(W=512, H=512):
    a = np.asarray(Image.fromarray(np.uint8(WOOD)).resize((W, H), Image.BICUBIC), np.float32) * np.array([1.35, 1.22, 1.02]) + np.array([20, 14, 6])
    yy, xx = np.mgrid[0:H, 0:W]
    e = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy]).astype(np.float32)
    a *= (0.80 + 0.20 * np.clip(e / 18.0, 0, 1))[..., None]               # edges handled darker
    return np.clip(a, 0, 255)


def paper(w, h, seed, tone=(214, 204, 178)):
    p = np.zeros((h, w, 3), np.float32) + np.array(tone, np.float32)
    n1 = np.asarray(Image.fromarray(np.uint8(np.random.default_rng(seed).random((h // 6 + 1, w // 6 + 1)) * 255)).resize((w, h), Image.BICUBIC), np.float32) / 255
    fib = np.asarray(Image.fromarray(np.uint8(np.random.default_rng(seed + 1).random((h, w // 3 + 1)) * 255)).resize((w, h), Image.BICUBIC), np.float32) / 255
    p *= (0.93 + 0.08 * n1 + 0.03 * fib)[..., None]
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]).astype(np.float32)
    return p * (0.86 + 0.14 * np.clip(e / (0.035 * min(w, h) + 2), 0, 1) ** 0.6)[..., None]


INK = (28, 24, 22)


def card_art(W=1024, H=1229):
    """the target card, drawn at 2x and reduced (anti-aliased rings); CARD_W x CARD_H units -> W x H texels (same aspect)"""
    S = 2
    w, h = W * S, H * S
    im = Image.fromarray(np.uint8(paper(w, h, 31)))
    d = ImageDraw.Draw(im)
    cx, cy = w / 2, h * 0.53
    R10 = w * 0.050                 # the 10 ring; each ring out adds the same step (ring 5 = 0.35 of the card's width)
    step = w * 0.060
    rings = {k: R10 + (10 - k) * step for k in range(5, 11)}           # radius of ring k's outer edge
    bull = rings[7]                                                    # the black aiming bull covers 7..10
    d.ellipse((cx - rings[5], cy - rings[5], cx + rings[5], cy + rings[5]), outline=INK, width=int(3 * S))
    d.ellipse((cx - bull, cy - bull, cx + bull, cy + bull), fill=INK)
    for k in (6,):
        r = rings[k]
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=int(2.4 * S))
    for k in (8, 9, 10):
        r = rings[k]
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(214, 206, 186), width=int(2.0 * S))
    fn = font("arialbd.ttf", 38 * S)
    for k in (5, 6):                    # ring numbers on the white rings: left, right, top, bottom
        r = (rings[k] + rings[k + 1]) / 2
        t = str(k)
        tw = d.textlength(t, font=fn)
        for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
            d.text((cx + dx - tw / 2, cy + dy - 23 * S), t, font=fn, fill=INK)
    fw = font("arialbd.ttf", 30 * S)
    for k in (7, 8, 9):                 # inside the bull: light numbers, left and right only
        r = (rings[k] + rings[k + 1]) / 2
        t = str(k)
        tw = d.textlength(t, font=fw)
        for dx in (-r, r):
            d.text((cx + dx - tw / 2, cy - 18 * S), t, font=fw, fill=(214, 206, 186))
    # head and foot: printed in the card's own ink
    fh = font("STENCIL.TTF", 74 * S)
    t = "PRACTICE TARGET"
    while d.textlength(t, font=fh) > w * 0.86:
        fh = font("STENCIL.TTF", fh.size - 2)
    d.text(((w - d.textlength(t, font=fh)) / 2, h * 0.045), t, font=fh, fill=(120, 26, 20))
    d.line((w * 0.08, h * 0.125, w * 0.92, h * 0.125), fill=INK, width=int(3 * S))
    ff = font("courbd.ttf", 40 * S)
    t = "RANGE 50 FT."
    d.text(((w - d.textlength(t, font=ff)) / 2, h * 0.925), t, font=ff, fill=INK)
    d.line((w * 0.08, h * 0.915, w * 0.92, h * 0.915), fill=INK, width=int(3 * S))
    # hits: a group of five at the bull, two fliers; each a dark hole with a torn light rim (in the black) / grey bruise (on white)
    hits = [(0.18, -0.35), (-0.55, 0.30), (0.62, 0.48), (-0.20, -0.85), (0.95, -0.20), (-2.9, 1.9), (2.4, -2.7)]
    for hx, hy in hits:
        px, py = cx + hx * step * 0.95, cy + hy * step * 0.95
        rr = 8.0 * S
        inside = math.hypot(px - cx, py - cy) < bull
        d.ellipse((px - rr - 3 * S, py - rr - 3 * S, px + rr + 3 * S, py + rr + 3 * S),
                  fill=(150, 142, 128) if inside else (168, 156, 138))
        d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=(10, 8, 8))
    # the score pencilled beside the rings (five 9s and 10s + two 7s)
    pen = (96, 96, 104)
    fp = font("segoepr.ttf", 46 * S)
    d.text((cx + rings[5] * 0.78, cy - rings[5] * 1.22), "62", font=fp, fill=pen)
    a = np.asarray(im.resize((W, H), Image.LANCZOS), np.float32)
    # four brass tacks at the corners (with their shadow)
    for tx, ty in ((0.05, 0.035), (0.95, 0.035), (0.05, 0.965), (0.95, 0.965)):
        x0, y0 = tx * W, ty * H
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.hypot(xx - x0, yy - y0)
        sh = np.clip(1 - np.hypot(xx - x0 - 4, yy - y0 - 5) / 14.0, 0, 1)
        a *= (1 - 0.35 * sh)[..., None]
        m = np.clip(11.0 - r, 0, 1)[..., None]
        hl = np.clip(1 - np.hypot(xx - x0 + 3, yy - y0 + 3) / 7.0, 0, 1)[..., None]
        a = a * (1 - m) + (np.array([168, 132, 62]) + hl * np.array([70, 64, 40])) * m
    return a


def shadow_art(S=128):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot((xx - S / 2 + 0.5) / (S / 2), (yy - S / 2 + 0.5) / (S / 2))
    al = np.clip(1.0 - (r - 0.45) / 0.5, 0, 1) ** 1.8 * 0.50
    return np.dstack([np.zeros((S, S, 3)), al[..., None] * 255]).astype(np.uint8)


SH = []


def save_pair(name, a):
    """<name>.jpg and the lit copy <name>_lit.jpg (turned up and warmed: gen_byodisc70.py's x1.32/1.27/1.14)"""
    pot = lambda n: 1 << (int(n) - 1).bit_length()  # noqa: E731
    sz = (pot(a.shape[1]), pot(a.shape[0]))
    Image.fromarray(np.uint8(np.clip(a, 0, 255))).resize(sz, Image.LANCZOS).save(os.path.join(tdir, name + ".jpg"), quality=94, subsampling=0)
    lit = np.clip(a * np.array([1.32, 1.27, 1.14]) + np.array([8, 5, 0]), 0, 255)
    Image.fromarray(np.uint8(lit)).resize(sz, Image.LANCZOS).save(os.path.join(tdir, name + "_lit.jpg"), quality=94, subsampling=0)
    for sfx in ("", "_lit"):
        SH.append("textures/menu/%s%s\n{\n\tnopicmip\n\t{\n\t\tmap textures/menu/%s%s.jpg\n\t\trgbGen lightingSpherical\n\t}\n}"
                  % (name, sfx, name, sfx))


save_pair(PFX + "_pine", wood_strip(512, 64, 3))
save_pair(PFX + "_ply", plywood())
save_pair(PFX + "_card", card_art())
Image.fromarray(shadow_art()).save(os.path.join(tdir, PFX + "_shadow.tga"))
SH.append("textures/menu/%s_shadow\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/%s_shadow.tga\n"
          "\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}" % (PFX, PFX))


# ------------------------------------------------------------------ geometry (local frame; placed into the world at the end)
def face(p, uv, n):
    """one triangle: p counter-clockwise seen from OUTSIDE (n = outward normal), uv image space; written in the file's winding
    (gen_byodisc70.py's order (0, 2, 1))"""
    return [(0, tuple(map(float, p[k])), tuple(map(float, n[k])), (float(uv[k][0]), float(uv[k][1]))) for k in (0, 2, 1)]


def quad(q, uq, n):
    """q: 4 corners in order round the face; flipped if they wind clockwise seen from outside along n"""
    q = [np.asarray(v, float) for v in q]
    if np.dot(np.cross(q[1] - q[0], q[2] - q[0]), n) < 0:
        q, uq = q[::-1], uq[::-1]
    nn = [n] * 3
    return [face([q[0], q[1], q[2]], [uq[0], uq[1], uq[2]], nn), face([q[0], q[2], q[3]], [uq[0], uq[2], uq[3]], nn)]


BOXES = []           # (centre, axes 3x3 (columns), half sizes) - for the intersection test


def beam(p0, p1, w, d, up=(0, 0, 1.0), u_len=1.0, side=None):
    """a square-section beam from p0 to p1 (w across 'side', d across the third axis); uv: u along the length (u_len repeats)"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = p1 - p0
    L = np.linalg.norm(ax)
    ax /= L
    s = np.asarray(side if side is not None else np.cross(ax, up), float)
    if np.linalg.norm(s) < 1e-6:
        s = np.array([1.0, 0, 0])
    s = s - ax * np.dot(s, ax)
    s /= np.linalg.norm(s)
    t = np.cross(ax, s)
    hw, hd = w / 2, d / 2
    out = []
    for nrm, dist, a, b in ((s, hw, t, hd), (-s, hw, t, hd), (t, hd, s, hw), (-t, hd, s, hw)):
        off = nrm * dist
        q = [p0 + off - a * b, p0 + off + a * b, p1 + off + a * b, p1 + off - a * b]
        out += quad(q, [(0, 0), (0, 0.18), (u_len, 0.18), (u_len, 0)], nrm)
    for nrm, pc in ((-ax, p0), (ax, p1)):                                  # end grain
        q = [pc - s * hw - t * hd, pc + s * hw - t * hd, pc + s * hw + t * hd, pc - s * hw + t * hd]
        out += quad(q, [(0.02, 0.2), (0.06, 0.2), (0.06, 0.3), (0.02, 0.3)], nrm)
    BOXES.append(((p0 + p1) / 2, np.stack([ax, s, t], 1), np.array([L / 2, hw, hd])))
    return out


parts = {}


def add(sh, tris):
    parts.setdefault(sh, []).extend(tris)


PINE, PLY, CARD = PFX + "_pine", PFX + "_ply", PFX + "_card"
Zup = np.array([0, 0, 1.0])
# front legs (the outer face of each leg faces outwards: 'side' = local x)
for sx in (-1, 1):
    add(PINE, beam((sx * FOOT_X, FOOT_Y, 0.0), (sx * TOP_X, TOP_Y, TOP_Z), LEG_W, LEG_D, side=(1.0, 0, 0), u_len=2.0))
# the top cross-piece (joins the leg tops; the back leg hangs from its back)
add(PINE, beam((-(TOP_X + 2.2), TOP_Y, TOP_Z + 0.6), ((TOP_X + 2.2), TOP_Y, TOP_Z + 0.6), 1.6, 3.0, side=(0, 1.0, 0), u_len=0.8))
# the back leg
add(PINE, beam((0.0, TOP_Y - 1.6, TOP_Z - 0.6), (BACK_FOOT[0], BACK_FOOT[1], 0.0), 1.8, 1.2, side=(1.0, 0, 0), u_len=2.0))
# the ledge: a flat bar across both front legs, in front of them, and its lip
yl = leg_y(LEDGE_Z) + LEG_D / 2           # the legs' front face at the ledge
LEDGE_D = 3.4
xl = leg_x(LEDGE_Z) + 3.0
add(PINE, beam((-xl, yl + LEDGE_D / 2, LEDGE_Z - 0.7), (xl, yl + LEDGE_D / 2, LEDGE_Z - 0.7), LEDGE_D, 1.4, side=(0, 1.0, 0), u_len=0.9))
add(PINE, beam((-xl, yl + LEDGE_D - 0.4, LEDGE_Z), (xl, yl + LEDGE_D - 0.4, LEDGE_Z), 0.8, 1.6, side=(0, 1.0, 0), up=(0, 1.0, 0), u_len=0.9))
# a spreader bar low between the front legs (keeps the feet from splaying)
zs = 9.0
add(PINE, beam((-leg_x(zs) + 1.0, leg_y(zs) - LEG_D / 2 - 0.6, zs), (leg_x(zs) - 1.0, leg_y(zs) - LEG_D / 2 - 0.6, zs), 1.0, 2.2,
               side=(0, 1.0, 0), u_len=0.9))

# the backing board: on the ledge, leaning back on the legs' front faces (the legs' lean)
up_b = np.array([0.0, -math.sin(LEAN), math.cos(LEAN)])         # along the board, upwards
nb_ = np.array([0.0, math.cos(LEAN), math.sin(LEAN)])            # the board's front normal
b0 = np.array([0.0, yl + 0.05 + BOARD_T / 2 * math.cos(LEAN), LEDGE_Z + 0.02])     # bottom edge centre (mid thickness)
b0 = b0 + nb_ * 0.0
ex = np.array([1.0, 0, 0])
bc = b0 + up_b * BOARD_H / 2
# board faces
for nrm, sgn in ((nb_, 1), (-nb_, -1)):
    c_ = bc + nrm * BOARD_T / 2
    q = [c_ - ex * BOARD_W / 2 - up_b * BOARD_H / 2, c_ + ex * BOARD_W / 2 - up_b * BOARD_H / 2,
         c_ + ex * BOARD_W / 2 + up_b * BOARD_H / 2, c_ - ex * BOARD_W / 2 + up_b * BOARD_H / 2]
    add(PLY, quad(q, [(0, 1), (1, 1), (1, 0), (0, 0)], nrm))
for nrm, a, L_, other, Lo in ((ex, up_b, BOARD_H, nb_, BOARD_T), (-ex, up_b, BOARD_H, nb_, BOARD_T),
                              (up_b, ex, BOARD_W, nb_, BOARD_T), (-up_b, ex, BOARD_W, nb_, BOARD_T)):
    half = BOARD_W / 2 if np.allclose(abs(nrm), ex) else BOARD_H / 2
    c_ = bc + nrm * half
    q = [c_ - a * L_ / 2 - other * Lo / 2, c_ + a * L_ / 2 - other * Lo / 2, c_ + a * L_ / 2 + other * Lo / 2, c_ - a * L_ / 2 + other * Lo / 2]
    add(PINE, quad(q, [(0, 0.3), (1, 0.3), (1, 0.32), (0, 0.32)], nrm))
BOXES.append((bc, np.stack([ex, up_b, nb_], 1), np.array([BOARD_W / 2, BOARD_H / 2, BOARD_T / 2])))
# the card, a hair in front of the board, its lower edge 4 up the board
cc = bc + nb_ * (BOARD_T / 2 + 0.06) + up_b * (4.0 + CARD_H / 2 - BOARD_H / 2)
q = [cc - ex * CARD_W / 2 - up_b * CARD_H / 2, cc + ex * CARD_W / 2 - up_b * CARD_H / 2, cc + ex * CARD_W / 2 + up_b * CARD_H / 2,
     cc - ex * CARD_W / 2 + up_b * CARD_H / 2]
add(CARD, quad(q, [(1, 1), (0, 1), (0, 0), (1, 0)], nb_))     # local +x is the VIEWER'S LEFT (he looks along -y): u runs -x
assert bc[2] + BOARD_H / 2 * up_b[2] < TOP_Z - 1.0, "the board would hit the cross-piece"

# ------------------------------------------------------------------ into the world
cy_, sy_ = math.cos(math.radians(YAW)), math.sin(math.radians(YAW))
Rw = np.array([[cy_, -sy_, 0], [sy_, cy_, 0], [0, 0, 1.0]])
Z0 = 0.0
if RAY:
    import atticview as V
    fs = V.FS(RAY[0])
    S = V.load_scene(fs, V.scene_block(RAY[1]), hide=[PFX + "_target", PFX + "_target_lit"], log=lambda *a: None)  # never itself (a re-run)
    P = S["P"]
    # each foot: the highest room surface under it (z in -4..12)
    feet = [np.array([sx * FOOT_X, FOOT_Y, 0]) for sx in (-1, 1)] + [np.array([BACK_FOOT[0], BACK_FOOT[1], 0])]
    zs_ = []
    for f_ in feet:
        w_ = Rw @ f_ + np.array([C[0], C[1], 0])
        A_, B_, C2 = P[:, 0], P[:, 1], P[:, 2]
        v0, v1 = B_ - A_, C2 - A_
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        ok = np.abs(den) > 1e-9
        px, py = w_[0] - A_[:, 0], w_[1] - A_[:, 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = (px * v1[:, 1] - v1[:, 0] * py) / den
            v = (v0[:, 0] * py - px * v0[:, 1]) / den
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1)
        z = A_[hit, 2] + u[hit] * v0[hit, 2] + v[hit] * v1[hit, 2]
        z = z[(z > -4) & (z < 12)]
        assert len(z), ("nothing under the foot", w_)
        zs_.append(float(z.max()))
    print("feet land on z %s" % [round(v, 2) for v in zs_])
    assert max(zs_) - min(zs_) < 0.6, ("uneven ground under the feet", zs_)
    Z0 = max(zs_)
    # dense sampling of the room near the easel; any room point inside a part box (+0.3) = intersection
    # every room triangle whose bounding box reaches the easel's (+3), sampled on a ~0.5 unit lattice (big wall / roof
    # triangles included: a centroid test would miss a roof slab whose centre is far away)
    allp = np.array([Rw @ (cen + axs @ (hs * np.array(sg))) for cen, axs, hs in BOXES
                     for sg in [(i, j, k) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]]) + np.array([C[0], C[1], Z0])
    elo, ehi = allp.min(0) - 3, allp.max(0) + 3
    near = np.all(P.min(1) <= ehi, 1) & np.all(P.max(1) >= elo, 1)
    Pn = P[near]
    pts = [Pn.reshape(-1, 3)]
    for tri in Pn:
        e1, e2 = tri[1] - tri[0], tri[2] - tri[0]
        n_ = int(min(400, max(2, math.sqrt(np.linalg.norm(np.cross(e1, e2)) / 2) / 0.5)))
        a, b = np.meshgrid(np.linspace(0, 1, n_ + 1), np.linspace(0, 1, n_ + 1))
        k_ = (a + b) <= 1
        q_ = tri[0] + a[k_][:, None] * e1 + b[k_][:, None] * e2
        pts.append(q_[np.all((q_ >= elo) & (q_ <= ehi), 1)])
    pts = np.concatenate(pts)
    pts = pts[pts[:, 2] > Z0 + 0.4]                      # the floor itself is not a collision
    clear = 1e9
    for cen, axs, hs in BOXES:
        wc = Rw @ cen + np.array([C[0], C[1], Z0])
        wa = Rw @ axs
        loc = (pts - wc) @ wa
        inside = np.all(np.abs(loc) <= hs + 0.3, axis=1)
        assert not inside.any(), ("the easel intersects the room", wc.round(1), pts[inside][:3].round(1))
        clear = min(clear, float(np.min(np.max(np.abs(loc) - hs, axis=1))))
    print("room clearance: %.1f units (nearest room point to any part box), %d points tested" % (clear, len(pts)))


def W_(p):
    return Rw @ np.asarray(p, float) + np.array([C[0], C[1], Z0])


def to_world(tri):
    out = []
    for b, p, n, uv in tri:
        out.append((b, tuple(W_(p)), tuple(Rw @ np.asarray(n)), uv))
    return out


wparts = {k: [to_world(t) for t in v] for k, v in parts.items()}
# the contact shadow: one soft oval on the floor under the easel's footprint (between the three feet)
sc_ = W_((0.0, -9.0, 0.0)) + np.array([0, 0, 0.05])
ax_, ay_ = Rw @ np.array([1.0, 0, 0]), Rw @ np.array([0, 1.0, 0])
SX, SY = 23.0, 26.0
q = [sc_ - ax_ * SX - ay_ * SY, sc_ + ax_ * SX - ay_ * SY, sc_ + ax_ * SX + ay_ * SY, sc_ - ax_ * SX + ay_ * SY]
shadow = quad(q, [(0, 1), (1, 1), (1, 0), (0, 0)], np.array([0, 0, 1.0]))


def write_model(nm, sfx):
    surfs, sl = [], []
    for k, (sh_, crs) in enumerate(list(wparts.items()) + [(PFX + "_shadow", shadow)]):
        shn = "textures/menu/%s%s" % (sh_, "" if sh_.endswith("_shadow") else sfx)
        ss = X.split_surfaces("s%d_" % k, crs)
        surfs += ss
        sl += ["\tsurface %s shader %s" % (q_[0], shn) for q_ in ss]
    assert 0 < len(surfs) <= 30, (nm, len(surfs))       # TRAPS: a model draws 32 surfaces; chunk at 30
    Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n"
        "\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))
    return len(surfs)


n0 = write_model(PFX + "_target", "")
n1 = write_model(PFX + "_target_lit", "_lit")
open(os.path.join(sdir, PFX + "_target.shader"), "w", newline="\n").write(
    "// generated by docs/proposals/advanced_training_2026-11-09/attic/tools/gen_target_at.py (the TRAINING practice target)\n\n"
    + "\n\n".join(SH) + "\n")
body = np.array([v for crs in wparts.values() for t in crs for v in (t[0][1], t[1][1], t[2][1])])
lo, hi = body.min(0), body.max(0)
card_c = W_(cc)
hull = np.unique(body.round(1), axis=0).tolist()                 # every corner of the easel (the hit box is fitted to them)
info = dict(hull=hull, centre=[round(float(C[0]), 2), round(float(C[1]), 2), round(float((lo[2] + hi[2]) / 2), 2)], lo=lo.round(2).tolist(),
            hi=hi.round(2).tolist(), cam_az=round(CAM_AZ, 1), front_az=round(FRONT_AZ, 1), card=card_c.round(2).tolist(), z0=Z0,
            lines=['scenemodel "models/menu/%s_target.tik" 0 0 0 0' % PFX, 'scenemodel "models/menu/%s_target_lit.tik" 0 0 0 0' % PFX])
json.dump(info, open(out_json, "w"), indent=1)
print("%s_target: %d surfaces (lit %d), bounds %s .. %s, camera azimuth %.1f, front %.1f, card centre %s"
      % (PFX, n0, n1, lo.round(1).tolist(), hi.round(1).tolist(), CAM_AZ, FRONT_AZ, card_c.round(1).tolist()))
