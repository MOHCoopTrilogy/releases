"""gen_clock.py <out dir> - v1.10.62: the attic wall clock tells the player's real time.

User: "Can we make the clock actually animate, higher quality and be accurate based on the players PC time".
  * a new dial (1024 px, drawn here - no blur at 1080p+): cream enamel, Bodoni Arabic numerals 1-12 upright, a minute track with
    bold five-minute marks, a thin inner ring, a soft bezel shadow and a little age at the rim.  It is its own fullbright model a
    fraction in front of the baked face (whose missing texture had baked hands into the room), inside the chrome bezel;
  * three hands (blued-black spade hour and leaf minute hands, a red seconds hand with a round counterweight) and a centre cap,
    each its own model with its origin on the arbor, modelled pointing at 12 and stacked hour < minute < second < cap towards the
    glass.  Their urc anim field is clock_h / clock_m / clock_s: the v1.10.62 engine (menu-clock, cl_uiscene.cpp) draws them in
    bind pose and rolls them about their own +X to the player's local time (seconds sweep smoothly);
  * an older engine plays the tik's own clock_* anim instead - one frame at 10:10:30 - so the hands rest at a display time.
Clock (BU, attic_room.blend clock_face): centre (1.137, 5.414, 2.2336), dial radius 0.11 m, facing -Y (the room).
Writes models/menu/hzm_clock_{face,hour,minute,second,cap}.*, textures/menu/hzm_clock_{dial,hands}.*, scripts/hzm_clock.shader."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

out = sys.argv[1]
S = 52.5
# v1.10.66 the MP room's wall clock too (user: "the clock in the join game menu needs to be live like the one in the main menu"):
# CLOCK_PREFIX / CLOCK_CBU "x y z" / CLOCK_R (m) build the same dial and hands, scaled, for another clock (hub_mp.blend clk_face:
# centre (0.95, 5.327, 2.55), radius 0.14 m, facing -Y) - CLOCK_PREFIX=hzm_hubclock CLOCK_CBU="0.95 5.325 2.55" CLOCK_R=0.14
PFX = os.environ.get("CLOCK_PREFIX", "hzm_clock")
CBU = tuple(float(v) for v in os.environ.get("CLOCK_CBU", "1.137 5.412 2.2336").split())   # attic: 2 mm in front of the baked face (5.413 .. 5.415)
K = float(os.environ.get("CLOCK_R", "0.110")) / 0.110      # every model is built at the attic's size, then scaled by K
ORIGIN = (CBU[1] * S, -CBU[0] * S, CBU[2] * S)           # game units; the models sit here with yaw 180 (local +X = out of the dial)
R = 0.110 * S                                              # dial radius, game units
mdir, tdir, sdir = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)

# ---- the dial, 1024 px across the 0.22 m dial (super-sampled 2x, then reduced)
N = 2048
c = N / 2
img = Image.new("RGB", (N, N), (236, 228, 206))
d = ImageDraw.Draw(img)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
rr = np.hypot(xx - c, yy - c) / c
base = np.asarray(img).astype(np.float32)
light = 1.0 + 0.05 * ((c - xx) + (c - yy)) / N          # a touch brighter to the upper left (the room's key)
age = 1.0 - 0.07 * np.clip((rr - 0.80) / 0.20, 0, 1) ** 2 # dulled towards the rim
shade = 1.0 - 0.22 * np.exp(-np.clip(1.0 - rr, 0, None) / 0.018)   # the bezel's shadow on the enamel
img = Image.fromarray(np.clip(base * (light * age * shade)[..., None], 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
ink = (24, 22, 20)
r_out, r_in = 0.925 * c, 0.865 * c                         # the minute track
for k in range(60):
    a = math.radians(k * 6)
    s_, co = math.sin(a), -math.cos(a)
    if k % 5 == 0:
        w, r0 = 14, 0.835 * c
    else:
        w, r0 = 5, r_in
    d.line([(c + s_ * r0, c + co * r0), (c + s_ * r_out, c + co * r_out)], fill=ink, width=w)
for rad, w in ((r_out + 4, 5), (r_in - 2, 3), (0.60 * c, 2)):
    d.ellipse([c - rad, c - rad, c + rad, c + rad], outline=ink, width=w)
font = ImageFont.truetype(r"C:\Windows\Fonts\BOD_B.TTF", int(0.205 * c))
for h in range(1, 13):
    a = math.radians(h * 30)
    rn = 0.70 * c
    x, y = c + math.sin(a) * rn, c - math.cos(a) * rn
    t = str(h)
    bb = d.textbbox((0, 0), t, font=font)
    d.text((x - (bb[0] + bb[2]) / 2, y - (bb[1] + bb[3]) / 2), t, font=font, fill=ink)
img = img.filter(ImageFilter.GaussianBlur(0.6)).resize((1024, 1024), Image.LANCZOS)
# outside the dial circle: the enamel colour (the bezel covers it; mip-mapping must not bleed dark into the rim)
a = np.asarray(img).copy()
m = np.hypot(*(np.mgrid[0:1024, 0:1024] - 511.5)) > 511
a[m] = (180, 172, 154)
Image.fromarray(a).save(os.path.join(tdir, PFX + "_dial.jpg"), quality=95)
# hands' paint: 4 swatches (blued black, its edge highlight, signal red, brass cap)
sw = Image.new("RGB", (64, 16))
for i, col in enumerate(((20, 22, 28), (58, 62, 72), (176, 30, 24), (150, 120, 60))):
    sw.paste(col, (i * 16, 0, i * 16 + 16, 16))
sw.save(os.path.join(tdir, PFX + "_hands.tga"))
SW = {"black": (0.125, 0.5), "edge": (0.375, 0.5), "red": (0.625, 0.5), "brass": (0.875, 0.5)}
open(os.path.join(sdir, PFX + ".shader"), "w", newline="\n").write((
    "// v1.10.62 the attic wall clock (gen_clock.py): dial + hands, fullbright\n"
    "hzm_clock_dial\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_clock_dial.jpg\n\t\trgbGen identity\n\t}\n}\n\n"
    "hzm_clock_hands\n{\n\tcull none\n\tnopicmip\n\tnomipmaps\n\t{\n\t\tmap textures/menu/hzm_clock_hands.tga\n\t\trgbGen identity\n\t}\n}\n").replace("hzm_clock", PFX))


def write(name, shader, tris, verts, anim=None, pose_deg=None):
    """verts: (pos local, uv); local frame: +X out of the dial, +Y the viewer's right, +Z up (12 o'clock)"""
    n = (1.0, 0.0, 0.0)
    verts = [(tuple(c * K for c in p), uv) for p, uv in verts]
    name, shader = name.replace("hzm_clock", PFX), shader.replace("hzm_clock", PFX)
    vv = [(n, uv, 0, p) for p, uv in verts]
    open(os.path.join(mdir, name + ".skd"), "wb").write(X.build_skd(name, [("root", "worldbone")], [("s", np.array(tris), vv)]))
    P = np.array([p for p, _ in verts])
    lo, hi, rad = (P.min(0) - 1).tolist(), (P.max(0) + 1).tolist(), float(np.linalg.norm(P, axis=1).max()) + 1
    frames = [[(0, 0, 0, 0), (0, 0, 0, 1)]]
    if pose_deg is not None:
        t = math.radians(pose_deg) / 2            # clockwise seen from the front: measured in an old engine (the negative turned them anticlockwise)
        frames = [[(0, 0, 0, 0), (math.sin(t), 0, 0, math.cos(t))]]
    open(os.path.join(mdir, name + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], frames, 0.1, lo, hi, rad))
    an = "\tidle %s.skc\n" % name + ("\t%s %s.skc\n" % (anim, name) if anim else "")
    open(os.path.join(mdir, name + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n\tsurface s shader %s\n}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n%s}\n" % (name, shader, an))


# ---- the dial disc (96 segments), 0.02 u proud of the baked face
seg = 96
verts = [((0.02, 0.0, 0.0), (0.5, 0.5))]
for k in range(seg):
    a = 2 * math.pi * k / seg
    y, z = R * math.cos(a), R * math.sin(a)
    verts.append(((0.02, y, z), (0.5 + y / (2 * R), 0.5 - z / (2 * R))))
tris = [[0, 1 + k, 1 + (k + 1) % seg] for k in range(seg)]
write("hzm_clock_face", "hzm_clock_dial", tris, verts)
# CLOCK_BEZEL (m, outer radius): a blued-steel bezel ring round the dial, for a clock whose baked face is a SQUARE quad bigger than its
# round case (the MP room's: its face's corners stuck out past the case at any distance) - the ring covers them (outer 0.205 m)
if os.environ.get("CLOCK_BEZEL"):
    rb = float(os.environ["CLOCK_BEZEL"]) / float(os.environ.get("CLOCK_R", "0.110")) * R
    bv, bt = [], []
    for k in range(seg):
        a_ = 2 * math.pi * k / seg
        for rr, xx, sw in ((R * 0.995, 0.06, "edge"), (R * 1.012, 0.10, "black"), (rb, 0.03, "black")):
            bv.append(((xx, rr * math.cos(a_), rr * math.sin(a_)), SW[sw]))
    for k in range(seg):
        i0, i1 = 3 * k, 3 * ((k + 1) % seg)
        for r0 in (0, 1):
            bt += [[i0 + r0, i1 + r0, i1 + r0 + 1], [i0 + r0, i1 + r0 + 1, i0 + r0 + 1]]
    write("hzm_clock_bezel", "hzm_clock_hands", bt, bv)


def hand(name, outline, x, swatch, anim, pose):
    """outline: (y, z) points around the hand (convex fan from the arbor), pointing at 12"""
    uv = SW[swatch]
    vs = [((x, 0.0, 0.0), uv)] + [((x, y, z), uv) for y, z in outline]
    n = len(outline)
    tr = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]
    write(name, "hzm_clock_hands", tr, vs, anim, pose)


def leaf(length, width, tail, tip_frac=0.82):
    """a symmetric hand outline: tail -> widest -> tip, as a closed polygon (fan-able from the arbor: star-shaped about it)"""
    pts = [(0, -tail), (width * 0.5, -tail * 0.6), (width * 0.5, 0), (width * 0.62, length * tip_frac * 0.55),
           (width * 0.40, length * tip_frac), (0, length), (-width * 0.40, length * tip_frac),
           (-width * 0.62, length * tip_frac * 0.55), (-width * 0.5, 0), (-width * 0.5, -tail * 0.6)]
    return [(y, z) for y, z in pts]


def spade(length, width, tail):
    """the hour hand: a narrow stem opening into a spade near the tip"""
    pts = [(0, -tail), (width * 0.45, -tail * 0.6), (width * 0.40, 0), (width * 0.30, length * 0.55), (width * 1.10, length * 0.70),
           (width * 0.55, length * 0.86), (0, length), (-width * 0.55, length * 0.86), (-width * 1.10, length * 0.70),
           (-width * 0.30, length * 0.55), (-width * 0.40, 0), (-width * 0.45, -tail * 0.6)]
    return pts


# old engines: the tik's clock_* anim holds 10:10:30
hand("hzm_clock_hour", spade(0.56 * R, 0.30, 0.55), 0.15, "black", "clock_h", (10 + 10.5 / 60) * 30)
hand("hzm_clock_minute", leaf(0.84 * R, 0.30, 0.75), 0.25, "black", "clock_m", 10.5 * 6)
# the seconds hand: a needle with a round counterweight on its tail (two fans: needle + disc)
sec = [(0, 0.90 * R), (0.06, 0.2), (0.07, -0.9), (-0.07, -0.9), (-0.06, 0.2)]
cw = [(0.42 * math.cos(2 * math.pi * k / 24), -1.25 + 0.42 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
uvr = SW["red"]
vs = [((0.35, 0.0, 0.0), uvr)] + [((0.35, y, z), uvr) for y, z in sec]
tr = [[0, 1 + k, 1 + (k + 1) % len(sec)] for k in range(len(sec))]
b = len(vs)
vs += [((0.35, 0.0, -1.25), uvr)] + [((0.35, y, z), uvr) for y, z in cw]
tr += [[b, b + 1 + k, b + 1 + (k + 1) % 24] for k in range(24)]
write("hzm_clock_second", "hzm_clock_hands", tr, vs, "clock_s", 30 * 6)
cap = [((0.45, 0.0, 0.0), SW["brass"])] + [((0.45, 0.30 * math.cos(2 * math.pi * k / 20), 0.30 * math.sin(2 * math.pi * k / 20)), SW["brass"]) for k in range(20)]
write("hzm_clock_cap", "hzm_clock_hands", [[0, 1 + k, 1 + (k + 1) % 20] for k in range(20)], cap)
print("%s at %.2f %.2f %.2f (yaw 180), dial radius %.2f u" % ((PFX,) + ORIGIN + (R * K,)))
