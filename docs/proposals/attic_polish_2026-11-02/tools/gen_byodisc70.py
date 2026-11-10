"""gen_byodisc70.py <pkadd dir> <out json> - v1.10.70: the OWN DISCS prop in the attic.

The own-disc missions (Medal of Honor: Frontline / European Assault, converted on the player's PC from their own disc - see
docs/proposals/byo68_2026-11-09) had no home in the 3D attic: the OWN DISCS sheet (ui/coop_byodisc.urc) was reached only through
FIELD SETTINGS and the co-op map select. Memory note menu-homes-in-world: a feature gets a prop in the attic that lights up while
highlighted, never a brown button.

The prop: Signal Corps style film cans on the projector's desk, beside the projector (the FILM ROOM) - the period's way to keep a
picture is a can of film, and these are the two "pictures" the player brings from his own discs. Two piles: by the projector a plain
can under a FRONTLINE can, in front of them EUROPEAN ASSAULT on its own; each lid carries a typed label (the game, its mission
SEALED ORDERS / THEIR DYING BREATH, REEL 1) turned towards the room. Olive drab paint (the game's own: the OD of
textures/models/items/messkit.tga, its aluminium bands for the worn rims), each lid closed over its base with a skirt and the seam
sealed with a strip of buff paper tape, as film cans were shipped. A soft contact shadow under each pile (the room's bake never saw
them). (QA round 1: a single stack of three 0.31 m cans with wide cream tapes read as a striped cake next to the small projector.)

Shaders: rgbGen lightingSpherical (the scene's lights shade the cans like the attic's actors and the gramophone; the room itself
is baked and ignores them) - patch_attic70.py adds one warm scenelight over the desk for them. The lit copy (hzm_byo70_cans_lit,
the scenehotfx lit-copy recipe of the projector / the MP room's notices) has every texture turned up and warmed (x1.45).

Output: models/menu/hzm_byo70_cans(.tik/.skd/.skc) + _lit, textures/menu/hzm_byo70_*, scripts/hzm_byo70.shader; the json carries
the stack's world bounds, centre and the urc lines for patch_attic70.py. World coordinates: the models are placed at 0 0 0 0.
"""
import json, math, os, sys, io, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\engrave")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import skx as X  # noqa: E402
import vfs  # noqa: E402

_paks0 = vfs.paks                                  # the game's own assets only (pak0..pak7), never an HD / mod pak
vfs.paks = lambda: [p for p in _paks0() if re.match(r"(?i)^pak\d", os.path.basename(p))]
vfs._idx = None

pkadd, out_json = sys.argv[1:3]
mdir, tdir, sdir = (os.path.join(pkadd, d) for d in ("models/menu", "textures/menu", "scripts"))
for d_ in (mdir, tdir, sdir):
    os.makedirs(d_, exist_ok=True)
FD = r"C:\Windows\Fonts"
rng = np.random.default_rng(1944)

# ------------------------------------------------------------------ placement (attic world units; raycast against the bake)
# The projector's desk (the narrow one along the right-hand side, phones on it): top z 52.6, front edge y -48.8, back y -67;
# the projector's base starts at x 100.1. The stack stands just in front of it (towards the camera), clear of its base.
DESK_Z = 52.62
# two piles (QA round 1: one stack of three big cans read as a striped cake beside the small attic projector): by the projector a
# plain can under FRONTLINE, in front of it (towards the room) EUROPEAN ASSAULT on its own - both lid labels face the room.
# (dx, dy from C, level, yaw, tape, lid label)
STACK = [(3.4, -0.9, 0, 0.0, "hzm_byo70_tape", None), (3.0, -0.6, 1, 17.0, "hzm_byo70_tape", "hzm_byo70_label_fl"),
         (-8.6, 0.9, 0, -9.0, "hzm_byo70_tape", "hzm_byo70_label_ea")]
C = np.array([float(os.environ.get("BYO70_X", "88.6")), float(os.environ.get("BYO70_Y", "-57.6"))])
R_BODY, R_LID, H_CAN, H_SKIRT = 5.7, 5.9, 1.55, 0.7
TAPE_Z0, TAPE_Z1 = 0.22, 0.18          # the tape: from the skirt's lower edge + TAPE_Z0 to the lid's top - TAPE_Z1
TAPE_H = H_SKIRT - TAPE_Z0 - TAPE_Z1
SEG = 40
HOME_CAM = np.array([-36.7, 21.0])
CAM_AZ = math.degrees(math.atan2(HOME_CAM[1] - C[1], HOME_CAM[0] - C[0]))      # the home camera, seen from the stack (~148 deg)


def font(n, px):
    return ImageFont.truetype(os.path.join(FD, n), int(px))


# ------------------------------------------------------------------ textures
def game_tex(path):
    return np.asarray(Image.open(io.BytesIO(vfs.read(path))).convert("RGB"), np.float32)


MK = game_tex("textures/models/items/messkit.tga")          # 256 x 256: OD body rows 176-255, aluminium bands rows 112-150
OD = MK[178:254, 4:220]
AL = MK[114:150, 4:220]


def od_patch(w, h, seed):
    """the messkit's OD paint: its mean colour (lifted a little - the mess tin is darker than a can's paint) with a multi-scale
    mottle; generated, not tiled, so the lid and the wrap-round side carry no tile seams"""
    base = OD.reshape(-1, 3).mean(0) * 1.12 + np.array([6, 5, 0])
    g = np.random.default_rng(seed)
    m = np.zeros((h, w), np.float32)
    for cell, amp in ((64, 0.07), (16, 0.045), (4, 0.03)):
        n = g.random((h // cell + 2, w // cell + 2)).astype(np.float32)
        m += amp * (np.asarray(Image.fromarray(np.uint8(n * 255)).resize((w + cell * 2, h + cell * 2), Image.BICUBIC), np.float32)[cell:cell + h, cell:cell + w] / 127.5 - 1)
    a = base[None, None, :] * (1 + m[..., None]) + np.array([0, 3, 0]) * m[..., None] * 10
    return a


def al_patch(w, h):
    return np.asarray(Image.fromarray(np.uint8(AL)).resize((w, h), Image.BICUBIC), np.float32)


def lid_art(S=512):
    """the lid seen from above: OD, the pressed rings of a film-can lid, its rim worn to bare metal in places"""
    a = od_patch(S, S, 1)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot(xx - S / 2 + 0.5, yy - S / 2 + 0.5) / (S / 2)
    shade = np.ones_like(r)
    for r0, w, k in ((0.955, 0.012, -0.30), (0.935, 0.010, 0.18), (0.70, 0.010, -0.20), (0.685, 0.008, 0.14),
                     (0.30, 0.010, -0.22), (0.285, 0.008, 0.12)):
        shade += k * np.exp(-((r - r0) / w) ** 2)
    a *= shade[..., None]
    wear = np.clip((r - 0.94) / 0.05, 0, 1)
    ang = np.arctan2(yy - S / 2, xx - S / 2)
    patchy = np.clip(np.sin(ang * 7 + 1.3) * 0.5 + np.sin(ang * 17) * 0.4 + 0.15, 0, 1)
    m = (wear * patchy)[..., None] * 0.75
    a = a * (1 - m) + al_patch(S, S) * m
    sc = np.zeros((S, S), np.float32)                       # a few fine scratches through the paint
    im = Image.fromarray(np.uint8(sc))
    d = ImageDraw.Draw(im)
    for _ in range(14):
        x0, y0 = rng.uniform(0.15, 0.85, 2) * S
        an, ln = rng.uniform(0, math.pi), rng.uniform(0.04, 0.14) * S
        d.line((x0, y0, x0 + math.cos(an) * ln, y0 + math.sin(an) * ln), fill=int(rng.uniform(60, 130)), width=1)
    sc = np.asarray(im.filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None] / 255
    a = a * (1 - sc * 0.5) + al_patch(S, S) * sc * 0.5
    return np.clip(a, 0, 255)


def side_art(W=1024, H=64):
    """the can's side (the base below the lid, and the lid's skirt): OD, a lighter worn line at the top and bottom edges"""
    a = od_patch(W, H, 2)
    v = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    edge = np.exp(-(v / 0.07) ** 2) + np.exp(-((1 - v) / 0.07) ** 2)
    a = a * (1 - 0.45 * edge[..., None]) + al_patch(W, H) * 0.45 * edge[..., None]
    return np.clip(a, 0, 255)


def paper(w, h, seed, tone=(214, 200, 164)):
    p = np.zeros((h, w, 3), np.float32) + np.array(tone, np.float32)
    n1 = np.asarray(Image.fromarray(np.uint8(np.random.default_rng(seed).random((h // 6 + 1, w // 6 + 1)) * 255)).resize((w, h), Image.BICUBIC), np.float32) / 255
    fib = np.asarray(Image.fromarray(np.uint8(np.random.default_rng(seed + 1).random((h, w // 3 + 1)) * 255)).resize((w, h), Image.BICUBIC), np.float32) / 255
    p *= (0.92 + 0.10 * n1 + 0.04 * fib)[..., None]
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]).astype(np.float32)
    wear = np.clip(e / (0.04 * min(w, h) + 2), 0, 1) ** 0.6
    return p * (0.84 + 0.16 * wear[..., None])


INK = (40, 34, 30)


def tape_art(text, seed, W=2048, H=64):
    """the seam tape: a strip of paper round the lid's skirt, the title typed on it once, centred where the home camera looks.
    The strip is 2 pi R_TAPE long and TAPE_H tall: the text is drawn square and squeezed to the strip's texel aspect"""
    a = paper(W, H, seed, (176, 160, 122))      # buff tape, aged darker than the lid labels
    im = Image.fromarray(np.uint8(a))
    if text:
        f = font("courbd.ttf", 46)
        tw = int(ImageDraw.Draw(im).textlength(text, font=f)) + 8
        lay = Image.new("L", (tw, H), 0)
        ImageDraw.Draw(lay).text((4, (H - 46) / 2 - 4), text, font=f, fill=255)
        k = (W / (2 * math.pi * (R_LID + 0.04))) / (H / TAPE_H)          # texels per unit: along / across
        lay = lay.resize((max(1, int(tw * k)), H), Image.LANCZOS)
        cx = (CAM_AZ % 360.0) / 360.0 * W          # u = azimuth / 360 (see cyl(): u runs with the angle)
        mask = Image.new("L", (W, H), 0)
        mask.paste(lay, (int(cx - lay.width / 2), 0))
        ink = np.asarray(mask, np.float32)[..., None] / 255
        a = a * (1 - ink * 0.85) + np.array(INK, np.float32) * ink * 0.85
    v = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    a *= (0.80 + 0.20 * np.clip(np.minimum(v, 1 - v) / 0.12, 0, 1))[..., None]          # the tape's edges lift a little
    return a


def label_art(game, mission, reel, seed, W=512, H=320):
    """a typed lid label (the War Department film labels: a printed head, the title typed in)"""
    a = paper(W, H, seed)
    im = Image.fromarray(np.uint8(a))
    d = ImageDraw.Draw(im)
    d.rectangle((14, 14, W - 15, H - 15), outline=INK, width=3)
    d.line((14, 74, W - 15, 74), fill=INK, width=2)
    f0 = font("georgiab.ttf", 30)
    t0 = "MEDAL OF HONOR"
    d.text(((W - d.textlength(t0, font=f0)) / 2, 28), t0, font=f0, fill=INK)
    px = 84
    while d.textlength(game, font=font("STENCIL.TTF", px)) > W - 70:
        px -= 2
    fs = font("STENCIL.TTF", px)
    d.text(((W - d.textlength(game, font=fs)) / 2, 92 + (84 - px) / 2), game, font=fs, fill=(70, 24, 20))
    ft = font("courbd.ttf", 30)
    for i, ln in enumerate((mission, reel)):
        d.text(((W - d.textlength(ln, font=ft)) / 2, 196 + i * 44), ln, font=ft, fill=INK)
    return np.asarray(im, np.float32)


def shadow_art(S=128):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot(xx - S / 2 + 0.5, yy - S / 2 + 0.5) / (S / 2)
    al = np.clip(1.0 - (r - 0.62) / 0.36, 0, 1) ** 1.6 * 0.55
    return np.dstack([np.zeros((S, S, 3)), al[..., None] * 255]).astype(np.uint8)


SH = []


def save_pair(name, a, alpha=None):
    """<name>.jpg and the lit copy <name>_lit.jpg (turned up and warmed: the projector's lit copy, the MP notices' x1.45)"""
    pot = lambda n: 1 << (int(n) - 1).bit_length()  # noqa: E731  (every side a power of two: the renderer resamples others at load)
    sz = (pot(a.shape[1]), pot(a.shape[0]))
    Image.fromarray(np.uint8(np.clip(a, 0, 255))).resize(sz, Image.LANCZOS).save(os.path.join(tdir, name + ".jpg"), quality=94, subsampling=0)
    lit = np.clip(a * np.array([1.32, 1.27, 1.14]) + np.array([8, 5, 0]), 0, 255)
    Image.fromarray(np.uint8(lit)).resize(sz, Image.LANCZOS).save(os.path.join(tdir, name + "_lit.jpg"), quality=94, subsampling=0)
    for sfx in ("", "_lit"):
        SH.append("textures/menu/%s%s\n{\n\tnopicmip\n\t{\n\t\tmap textures/menu/%s%s.jpg\n\t\trgbGen lightingSpherical\n\t}\n}"
                  % (name, sfx, name, sfx))


save_pair("hzm_byo70_lid", lid_art())
save_pair("hzm_byo70_side", side_art())
save_pair("hzm_byo70_tape", tape_art("", 13))                       # plain seam tape (the titles are on the lid labels)
save_pair("hzm_byo70_label_fl", label_art("FRONTLINE", "SEALED ORDERS", "REEL 1", 21))
save_pair("hzm_byo70_label_ea", label_art("EUROPEAN ASSAULT", "THEIR DYING BREATH", "REEL 1", 22))
Image.fromarray(shadow_art()).save(os.path.join(tdir, "hzm_byo70_shadow.tga"))
SH.append("textures/menu/hzm_byo70_shadow\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_byo70_shadow.tga\n"
          "\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}")


# ------------------------------------------------------------------ geometry
def face(p, uv, n):
    """one triangle: p counter-clockwise seen from OUTSIDE (n = outward normal, per corner), uv image space (u right, v down).
    Written in the file's winding (cross product inward; the stored normal outward - checked against the stock meshes)."""
    order = (0, 2, 1)
    return [(0, tuple(map(float, p[k])), tuple(map(float, n[k])), (float(uv[k][0]), float(uv[k][1]))) for k in order]


def cyl(c, z0, z1, r, yaw, u_from_az=True):
    """the side of a cylinder; u = azimuth / 360 (the world azimuth: the tape's text sits at the camera's azimuth), v 0 top"""
    out = []
    for i in range(SEG):
        a0, a1 = 2 * math.pi * i / SEG, 2 * math.pi * (i + 1) / SEG
        w0, w1 = a0 + math.radians(yaw), a1 + math.radians(yaw)
        P = lambda a, z: np.array([c[0] + r * math.cos(a), c[1] + r * math.sin(a), z])  # noqa: E731
        N = lambda a: np.array([math.cos(a), math.sin(a), 0.0])  # noqa: E731
        u0, u1 = (w0 / (2 * math.pi)) % 1.0, None
        u1 = u0 + 1.0 / SEG
        q = [P(w0, z0), P(w1, z0), P(w1, z1), P(w0, z1)]
        nq = [N(w0), N(w1), N(w1), N(w0)]
        uq = [(u0, 1), (u1, 1), (u1, 0), (u0, 0)]
        out.append(face([q[0], q[1], q[2]], [uq[0], uq[1], uq[2]], [nq[0], nq[1], nq[2]]))
        out.append(face([q[0], q[2], q[3]], [uq[0], uq[2], uq[3]], [nq[0], nq[2], nq[3]]))
    return out


def disc(c, z, r, yaw, up=True, r_in=0.0, uv_r=1.0):
    """a flat disc (or annulus) facing up / down; planar uv over the lid art (turned with the can)"""
    out = []
    n = np.array([0, 0, 1.0 if up else -1.0])
    for i in range(SEG):
        a0, a1 = 2 * math.pi * i / SEG + math.radians(yaw), 2 * math.pi * (i + 1) / SEG + math.radians(yaw)
        def pt(a, rr):
            return np.array([c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), z])

        def uvp(a, rr):
            k = rr / R_LID * uv_r
            return (0.5 + 0.5 * k * math.cos(a - math.radians(yaw)), 0.5 - 0.5 * k * math.sin(a - math.radians(yaw)))
        if r_in <= 0:
            tri_ = [pt(0, 0) * 0 + np.array([c[0], c[1], z]), pt(a0, r), pt(a1, r)]
            uvs = [(0.5, 0.5), uvp(a0, r), uvp(a1, r)]
            if not up:
                tri_, uvs = [tri_[0], tri_[2], tri_[1]], [uvs[0], uvs[2], uvs[1]]
            out.append(face(tri_, uvs, [n] * 3))
        else:
            q = [pt(a0, r_in), pt(a0, r), pt(a1, r), pt(a1, r_in)]
            uq = [uvp(a0, r_in), uvp(a0, r), uvp(a1, r), uvp(a1, r_in)]
            if not up:
                q, uq = q[::-1], uq[::-1]
            out.append(face([q[0], q[1], q[2]], [uq[0], uq[1], uq[2]], [n] * 3))
            out.append(face([q[0], q[2], q[3]], [uq[0], uq[2], uq[3]], [n] * 3))
    return out


def rect_flat(c, z, w, h, up_az):
    """a flat paper rectangle on a lid, its text's 'up' pointing to azimuth up_az"""
    U = np.array([math.cos(math.radians(up_az)), math.sin(math.radians(up_az)), 0])
    Rr = np.array([U[1], -U[0], 0])                           # reader's right (looking down, up = away from him)
    p0 = np.array([c[0], c[1], z])
    q = [p0 - Rr * w / 2 - U * h / 2, p0 + Rr * w / 2 - U * h / 2, p0 + Rr * w / 2 + U * h / 2, p0 - Rr * w / 2 + U * h / 2]
    uq = [(0, 1), (1, 1), (1, 0), (0, 0)]
    n = [np.array([0, 0, 1.0])] * 3
    return [face([q[0], q[1], q[2]], [uq[0], uq[1], uq[2]], n), face([q[0], q[2], q[3]], [uq[0], uq[2], uq[3]], n)]


parts = {}


def add(sh, tris):
    parts.setdefault(sh, []).extend(tris)


for dx, dy, lvl, yaw, tape, lab in STACK:
    c = C + np.array([dx, dy])
    z0 = DESK_Z + lvl * (H_CAN + 0.05)
    zt = z0 + H_CAN + 0.05
    add("hzm_byo70_side", cyl(c, z0, zt - H_SKIRT, R_BODY, yaw))                 # the base
    add("hzm_byo70_side", cyl(c, zt - H_SKIRT, zt, R_LID, yaw))                  # the lid's skirt
    add("hzm_byo70_side", disc(c, zt - H_SKIRT, R_LID, yaw, up=False, r_in=R_BODY))   # the skirt's lower edge
    add("hzm_byo70_lid", disc(c, zt, R_LID, yaw, up=True))
    add(tape, cyl(c, zt - H_SKIRT + TAPE_Z0, zt - TAPE_Z1, R_LID + 0.03, 0.0))  # the seam tape
    if lab:                                                                      # the lid label, its text towards the room
        add(lab, rect_flat(c + np.array([0.2, -0.1]), zt + 0.03, 6.8, 4.25, CAM_AZ + 180.0 + yaw * 0.3))
shadow = [q for dx, dy, lvl, _y, _t, _l in STACK if lvl == 0 for q in rect_flat(C + np.array([dx + 0.5, dy + 0.6]), DESK_Z + 0.02, R_LID * 2.9, R_LID * 2.9, 0.0)]


def write_model(nm, sfx):
    surfs, sl = [], []
    for k, (sh_, crs) in enumerate(list(parts.items()) + [("hzm_byo70_shadow", shadow)]):
        shn = "textures/menu/%s%s" % (sh_, "" if sh_ == "hzm_byo70_shadow" else sfx)
        ss = X.split_surfaces("s%d_" % k, crs)
        surfs += ss
        sl += ["\tsurface %s shader %s" % (q[0], shn) for q in ss]
    assert 0 < len(surfs) <= 30, (nm, len(surfs))       # TRAPS: a model draws 32 surfaces; chunk at 30
    Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n"
        "\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))
    return len(surfs), Pv


n0, Pv = write_model("hzm_byo70_cans", "")
n1, _ = write_model("hzm_byo70_cans_lit", "_lit")
open(os.path.join(sdir, "hzm_byo70.shader"), "w", newline="\n").write(
    "// generated by docs/proposals/attic_polish_2026-11-02/tools/gen_byodisc70.py (v1.10.70 OWN DISCS film cans)\n\n" + "\n\n".join(SH) + "\n")
body = np.array([v for crs in parts.values() for t in crs for v in (t[0][1], t[1][1], t[2][1])])
lo, hi = body.min(0), body.max(0)
info = dict(centre=[round(float(C[0]), 2), round(float(C[1]), 2), round(float((lo[2] + hi[2]) / 2), 2)], lo=lo.round(2).tolist(),
            hi=hi.round(2).tolist(), cam_az=round(CAM_AZ, 1),
            lines=['scenemodel "models/menu/hzm_byo70_cans.tik" 0 0 0 0', 'scenemodel "models/menu/hzm_byo70_cans_lit.tik" 0 0 0 0'])
json.dump(info, open(out_json, "w"), indent=1)
print("hzm_byo70_cans: %d surfaces (lit %d), bounds %s .. %s, camera azimuth %.1f" % (n0, n1, lo.round(1).tolist(), hi.round(1).tolist(), CAM_AZ))
