"""actor_build.py - mod-owned menu actors (General Weathers, Manon): new tiki + 2048 px textures under OUR paths; the stock files are only READ.

    python actor_build.py <stage dir>        writes models/human/hzm_menu/*.tik, textures/mohmenu/hzm_actor/*.jpg, scripts/hzm_menu_actor.shader

Sources are 256 px sheets (face/hands/tunic/pants/cap).  Upscale = bicubic x8, light unsharp, cloth weave + grain (no AI smear, no invented facial features);
Weathers' tunic: the painted suspenders are cleaned out (the belt, pockets, collar and folds stay), two silver stars on each collar point and shoulder loop
(Major General unless Breakthrough text says otherwise: it does not - a CHOICE, flagged), and a peaked service cap (the stock officer-cap mesh,
repainted olive drab with gold piping, the German eagle replaced by a gold badge with two silver stars) instead of the helmet.
"""
import io, os, sys, zipfile, glob, re
import numpy as np
import cv2
from PIL import Image, ImageDraw

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
OUTS = 2048
TEXDIR = "textures/mohmenu/hzm_actor"
rng = np.random.default_rng(7)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import actor_anims as AA  # noqa: E402
_al = {"idle": "idle/generic_idle_a01(loop).skc", "maproomA": AA.CAND["mapA"], "maproomB": AA.CAND["mapB"], "maproomC": AA.CAND["mapC"],
       "radioidle": AA.CAND["commRadio"], "radiotalk": AA.CAND["radioIdle"]}
_al.update({k: v for k, v in AA.CAND.items() if k not in AA.SEATED})
ANIMS = "".join(chr(9) + "%s %s" % kv + chr(10) for kv in _al.items())

PAKS = {}


def pak(rel):
    if rel not in PAKS:
        PAKS[rel] = zipfile.ZipFile(os.path.join(GOG, rel))
    return PAKS[rel]


def tex(pk, name):
    z = pak(pk)
    for n in z.namelist():
        if n.lower() == name.lower():
            return Image.open(io.BytesIO(z.read(n))).convert("RGB")
    raise KeyError(name)


def up(img, size=OUTS, sharp=0.55, grain=2.2, weave=0.0):
    a = np.asarray(img).astype(np.float32)
    a = cv2.resize(a, (size, size), interpolation=cv2.INTER_CUBIC)
    bl = cv2.GaussianBlur(a, (0, 0), size / 256.0 * 0.9)
    a = a + (a - bl) * sharp
    if weave:
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        p = size / 256.0
        tw = np.sin((xx + yy) * (1.7 / p * 0.55)) * 0.5 + np.sin((xx - yy) * (1.3 / p * 0.55)) * 0.5
        a = a * (1.0 + weave * tw[..., None])
    if grain:
        n = rng.normal(0, grain, (size, size)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 0.7)
        a = a + n[..., None] * 2.0
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def star(draw, cx, cy, r, fill, outline=None):
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    draw.polygon(pts, fill=fill, outline=outline)


def build(stage):
    tdir = os.path.join(stage, *TEXDIR.split("/"))
    mdir = os.path.join(stage, "models", "human", "hzm_menu")
    for d in (tdir, mdir, os.path.join(stage, "scripts")):
        os.makedirs(d, exist_ok=True)
    sh = []

    def save(img, name):
        img.save(os.path.join(tdir, name + ".jpg"), quality=94)
        return "%s/%s.jpg" % (TEXDIR, name)

    def shader(name, path, spherical=True, extra=""):
        sh.append("%s\n{\n\tqer_editorimage %s\n\t{\n\t\tmap %s\n\t\trgbGen %s\n\t}\n%s}\n" % (name, path, path, "lightingSpherical" if spherical else "identity", extra))

    # ---------------- General Weathers
    tun = tex("maintt/pak1.pk3", "textures/models/human/USmaintt/Sc_AL_US_Gen_Tunic.tga")
    a = np.array(tun)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32)
    bl = cv2.GaussianBlur(g, (0, 0), 6)
    m = ((g > bl + 12) & (g > 118)).astype(np.uint8) * 255
    # only the two vertical suspender straps per panel (rows above the belt band at ~y 93..112); the belt band, pockets and collar are kept
    m[93:, :] = 0
    colmask = np.zeros(256, np.uint8)
    for x0, x1 in ((72, 92), (126, 146), (172, 186), (222, 238)):      # strap columns of the 256 px sheet (front pair, back pair)
        colmask[x0:x1] = 1
    m = m * colmask[None, :]
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=1)
    clean = cv2.inpaint(a, m, 4, cv2.INPAINT_TELEA)
    # even olive drab: keep fold shading (frequencies above ~10 px at 256) and a soft large-scale gradient, drop the painted grime blotches
    cf = clean.astype(np.float32)
    lum = cf.mean(axis=2)
    low = cv2.GaussianBlur(lum, (0, 0), 11)
    detail = np.clip(lum / np.maximum(low, 1.0), 0.55, 1.6)
    # the two dark smudges on the upper chest (where the suspenders were shaded): lift anything darker than 0.88 of its surroundings in the chest area
    ch = np.zeros_like(detail)
    ch[6:96, 56:166] = 1.0
    ch = cv2.GaussianBlur(ch, (0, 0), 5)
    mid = cv2.GaussianBlur(detail, (0, 0), 9)
    detail = np.where(detail < 0.9, detail * (1 - ch) + np.maximum(detail, 0.9 * np.minimum(mid + 0.08, 1.0)) * ch, detail)
    grad = (cv2.GaussianBlur(lum, (0, 0), 28) / max(float(lum.mean()), 1.0)) ** 0.25
    od = np.array([88, 78, 50], np.float32)                      # olive drab shade 33 wool: dark brownish olive
    cf = od[None, None, :] * (detail ** 1.15 * grad)[..., None]
    clean = np.clip(cf, 0, 255).astype(np.uint8)
    bandy0, bandy1, bandx0, bandx1 = 94, 106, 60, 254
    nz = rng.normal(0, 5, (bandy1 - bandy0, bandx1 - bandx0, 1)).astype(np.float32)
    leather = np.array([78, 54, 32], np.float32)[None, None, :] + nz
    leather[:2] *= 1.25                       # top edge highlight
    leather[-2:] *= 0.7                       # bottom edge shade
    cl = clean.astype(np.float32)
    cl[106:117, 60:254] = cv2.GaussianBlur(cl[119:130, 60:254], (0, 0), 1.2)      # the old painted pouch strip -> plain tunic cloth
    cl[bandy0:bandy1, bandx0:bandx1] = leather
    bx = 103                                  # front centre (the original buckle slot)
    cl[bandy0 + 1:bandy1 - 1, bx - 4:bx + 5] = np.array([196, 160, 70], np.float32)
    cl[bandy0 + 3:bandy1 - 3, bx - 2:bx + 3] = np.array([60, 44, 24], np.float32)
    clean = np.clip(cl, 0, 255).astype(np.uint8)
    big = up(Image.fromarray(clean), weave=0.05)
    d = ImageDraw.Draw(big)
    S = OUTS / 256.0
    silver = (214, 218, 224)
    # collar points + shoulder loops (positions in the 256 px sheet, front panel left, back panel right); iterated against renders
    # exactly two SMALL silver stars touching side by side: one pair centred on each shoulder loop, one smaller pair on each shirt-collar point
    # (the sheet is symmetric about x = 107; each pair is drawn once, on the front sheet, not across seam islands)
    def pair_at(cx, cy, r):
        for k in (-1, 1):
            sx = (cx + k * r * 0.95) * S
            sy = cy * S
            star(d, sx, sy, r * S, (150, 154, 162), (88, 90, 98))                 # metallic grey body
            star(d, sx - 0.12 * r * S, sy - 0.12 * r * S, r * 0.55 * S, (214, 218, 226), None)   # highlight
    pair_at(73, 18, 1.35)                    # left shoulder loop
    pair_at(214 - 73, 18, 1.35)              # right shoulder loop
    pair_at(92, 17, 1.0)                     # left shirt-collar point
    pair_at(214 - 92, 17, 1.0)               # right shirt-collar point
    if os.environ.get("TUNIC_GRID"):
        from PIL import ImageFont
        gd = ImageDraw.Draw(big)
        fnt = ImageFont.truetype("arial.ttf", 34)
        for gx in range(0, 256, 16):
            for gy in range(0, 256, 16):
                gd.rectangle([gx * S, gy * S, gx * S + 6, gy * S + 6], fill=(255, 0, 0))
                gd.text((gx * S + 8, gy * S + 8), "%d,%d" % (gx, gy), fill=(255, 255, 40), font=fnt, stroke_width=2, stroke_fill=(0, 0, 0))
    wt = save(big, "weathers_tunic")
    shader("hzm_menu_wea_tunic", wt)

    face = tex("main/Pak2.pk3", "textures/models/human/faces/Wheathers.jpg") if False else Image.open(r"G:\mohaa-hudfeed3\menus3d\actor_src\wheathers.png")
    shader("hzm_menu_wea_head", save(up(face, sharp=0.5, grain=1.4), "weathers_head"))
    hands = Image.open(r"G:\mohaa-hudfeed3\menus3d\actor_src\handsnew.png")
    shader("hzm_menu_wea_hands", save(up(hands, sharp=0.45, grain=1.2), "weathers_hands"))
    pants = Image.open(r"G:\mohaa-hudfeed3\menus3d\actor_src\sc_al_us_inf_pants.png")
    pa = np.array(pants).astype(np.float32)
    pl = pa.mean(axis=2)
    pdet = np.clip(pl / np.maximum(cv2.GaussianBlur(pl, (0, 0), 6), 1.0), 0.7, 1.35)
    pa = np.clip(np.array([80, 70, 46], np.float32)[None, None, :] * (pdet ** 0.8)[..., None], 0, 255).astype(np.uint8)    # boots/leggings parts keep dark: masked below
    boot = (pl < 55)
    pa[boot] = np.array(pants).astype(np.float32)[boot] * 0.9
    shader("hzm_menu_wea_pants", save(up(Image.fromarray(pa), weave=0.04), "weathers_pants"))

    # no cap (user decision): bare head, grey hair, glasses

    # ---------------- Manon: no texture copies - the tiki points at the STOCK shader names, so the installed texture stack (buckle included) is what shows

    open(os.path.join(stage, "scripts", "hzm_menu_actor.shader"), "w", newline="\n").write("// menu actors: mod-owned upscaled copies (never the stock shader names)\n" + "\n".join(sh))

    open(os.path.join(mdir, "weathers_menu.tik"), "w", newline="\n").write("""TIKI
setup
{
	scale 0.52
	path models/human/SC_AL_US_INF
	skelmodel sc_al_us_inf.skd
	surface Sc_Al_US_Inf_Pants shader hzm_menu_wea_pants
	surface Sc_Al_US_Inf_Tunic shader hzm_menu_wea_tunic
	path models/human/heads
	skelmodel head5.skd
	surface head shader hzm_menu_wea_head
	path models/human/hands
	skelmodel hand.skd
	surface hand shader hzm_menu_wea_hands
	path models/equipment/USGear
	skelmodel Af_P_Glasses.skd
	surface Af_P_Glasses shader Af_P_Glasses
	surface Af_P_Lens shader Af_P_Glasses_reflection
	scale 0.52
	path models/human/protoanimations
	radius 20
}

init
{
	server
	{
		classname Actor
	}
}

animations
{
	$path models/human/animation
""" + ANIMS + """}
""")
    open(os.path.join(mdir, "manon_menu.tik"), "w", newline="\n").write("""TIKI
setup
{
	scale 0.52
	path models/human/manon
	skelmodel manon.skd
	surface coat shader manon_shirt
	surface cull_coat shader c_manon_shirt
	surface pants shader manon_pants
	surface inside shader manon_shirt
	surface hand shader manon_hands
	path models/human/heads
	skelmodel manon_head.skd
	surface manon shader manon_head
	scale 0.52
	path models/human/protoanimations
	radius 20
}

init
{
	server
	{
		classname Actor
	}
}

animations
{
	$path models/human/animation
""" + ANIMS + """}
""")
    t = open(os.path.join(mdir, "manon_menu.tik"), encoding="utf-8").read()
    open(os.path.join(mdir, "manon_up_menu.tik"), "w", newline="\n").write(t.replace("hzm_menu_man_", "hzm_menu_man_up_"))
    print("actors built in", stage)


if __name__ == "__main__":
    build(sys.argv[1])
