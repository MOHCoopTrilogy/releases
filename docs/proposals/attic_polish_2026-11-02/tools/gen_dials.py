"""gen_dials.py <bake dir> <dials.json> <out dir> - v1.10.66 crisp rotary dials on the attic's telephones.

Coordinator QA: the dials repainted INTO the baked desk atlas (retouch.py "dials") read well at desk distance, but at a close-up
the atlas cannot hold a drawn dial - stair-stepped digits, a ragged rim. So each dial gets its own flat face model a hair in front
of the baked one, all sharing ONE dedicated texture:
  textures/menu/hzm_dial.jpg  512 px, drawn at 2048 and reduced (Lanczos): black finger wheel, ten finger holes with the digits
                              1-0 counter-clockwise from the top right in Franklin Gothic Demi on a cream number card, a cream
                              centre label with a red ring, the steel finger stop, a clean steel rim. Mipmapped, nopicmip.
  models/menu/hzm_dial_<phone>.*  a 48-segment disc on the dial plane (fitted to the baked dial triangles), radius = the dial plate,
                              0.6 mm in front of the proudest dial part; vertices in absolute scene units (scenemodel ... 0 0 0 0).
                              The scene's light level (x0.80, warm) is in the texture: rgbGen const drew teal under GL2.
  scripts/hzm_dial.shader
Writes dials_models.json (the model names) for make_attic_polish.py."""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

bake, dj, out = sys.argv[1:4]
mdir, tdir, sdir = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)
S = 52.5
FD = r"C:\Windows\Fonts"


def conv(a, k=S):
    a = np.asarray(a, np.float64)
    return np.stack([a[..., 1], -a[..., 0], a[..., 2]], -1) * k


# ---- the dial art (2048 -> 512)
N, SS = 512, 4
W = N * SS
im = Image.new("RGB", (W, W), (128, 130, 134))
d = ImageDraw.Draw(im)
c, R = W / 2, W / 2 - SS
d.ellipse([c - R, c - R, c + R, c + R], fill=(142, 144, 148))                   # the steel rim
d.ellipse([c - R * 0.965, c - R * 0.965, c + R * 0.965, c + R * 0.965], fill=(112, 114, 118))
rw = R * 0.92
d.ellipse([c - rw, c - rw, c + rw, c + rw], fill=(16, 16, 18))                  # the finger wheel (black bakelite)
d.ellipse([c - rw * 0.985, c - rw * 0.985, c + rw * 0.985, c + rw * 0.985], outline=(40, 40, 44), width=3 * SS)
fnt = ImageFont.truetype(os.path.join(FD, "FRADM.TTF"), int(R * 0.19))
for k, dg in enumerate("1234567890"):
    ang = math.radians(60 + 30 * k)                                              # 1 at the top right, counter-clockwise to 0
    hx, hy = c + R * 0.635 * math.cos(ang), c - R * 0.635 * math.sin(ang)
    hr = R * 0.158
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(214, 204, 176))       # the number card through the hole
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], outline=(6, 6, 6), width=3 * SS)
    d.text((hx, hy + R * 0.005), dg, font=fnt, fill=(26, 24, 22), anchor="mm")
rc = R * 0.31                                                                    # the centre label
d.ellipse([c - rc, c - rc, c + rc, c + rc], fill=(222, 214, 188), outline=(90, 82, 66), width=3 * SS)
d.ellipse([c - rc * 0.80, c - rc * 0.80, c + rc * 0.80, c + rc * 0.80], outline=(150, 40, 30), width=3 * SS)
fl = ImageFont.truetype(os.path.join(FD, "FRADM.TTF"), int(R * 0.085))
d.text((c, c - rc * 0.28), "EXCHANGE", font=fl, fill=(60, 52, 44), anchor="mm")
d.text((c, c + rc * 0.22), "4 - 1 7 3", font=fl, fill=(60, 52, 44), anchor="mm")
a0, a1 = math.radians(-18), math.radians(-10)                                   # the finger stop, lower right, over the wheel's edge
pts = [(c + R * 0.70 * math.cos(a0), c - R * 0.70 * math.sin(a0)), (c + R * 0.97 * math.cos(a0), c - R * 0.97 * math.sin(a0)),
       (c + R * 0.97 * math.cos(a1), c - R * 0.97 * math.sin(a1)), (c + R * 0.70 * math.cos(a1), c - R * 0.70 * math.sin(a1))]
d.polygon(pts, fill=(196, 198, 202), outline=(90, 92, 96))
im = im.resize((N, N), Image.LANCZOS)
# the scene's light level is IN the texture (x0.80, a warm lamp tint): `rgbGen const` on this stage drew TEAL under GL2 (the same
# renderer trap as the attic chrome env stages) - so one pre-lit texture, rgbGen identity, for every dial
im = Image.fromarray(np.clip(np.asarray(im, np.float32) * np.array([0.80, 0.776, 0.736]), 0, 255).astype(np.uint8))
im.save(os.path.join(tdir, "hzm_dial.jpg"), quality=95)

# ---- one disc per dial, on its fitted plane
DJ = json.load(open(dj))
D = np.load(os.path.join(bake, "desk.npz"))
P = D["pos"].astype(np.float64)
cen = P.mean(1)
lit = np.asarray(Image.open(os.path.join(bake, "desk.png")).convert("RGB"), np.float32) / 255
UV = D["uv"].astype(np.float64)
Hh, Ww = lit.shape[:2]
HOME = np.array([-0.40, -0.70, 1.95])
shaders, names = ["// v1.10.66 the telephones' rotary dials (gen_dials.py): one texture, a per-phone light level"], []
for name, dd in sorted(DJ.items()):
    c0 = np.array(dd["c"])
    rp = dd["r_plate"]
    sel = (np.linalg.norm(P - c0, axis=2) < rp * 1.03).all(1)
    if not sel.any():
        continue
    pts = P[sel].reshape(-1, 3)
    n = np.linalg.svd(pts - pts.mean(0), full_matrices=False)[2][2]
    if n @ (HOME - c0) < 0:
        n = -n
    up = np.array([0, 0, 1.0]) - n * n[2]
    if np.linalg.norm(up) < 1e-3:
        up = np.array([0, 1.0, 0]) - n * n[1]
    up /= np.linalg.norm(up)
    right = np.cross(up, n)
    front = float(((pts - c0) @ n).max()) + 0.0006
    ctr = c0 + n * front
    # the light level: the raw bake of the dial's own (white card) triangles, median luminance
    uvs = UV[sel].reshape(-1, 2)
    px = np.clip((uvs[:, 0] * Ww).astype(int), 0, Ww - 1)
    py = np.clip(((1 - uvs[:, 1]) * Hh).astype(int), 0, Hh - 1)
    Lm = float(np.median((lit[py, px] * np.array([0.30, 0.59, 0.11])).sum(1)))
    # (the dial triangles' own raw bake reads ~0 - the stock dial card material bakes dark under the black bakelite retouch's
    # lighting set - so the level is the shelf's: the long-desk phones sit in the lamp-lit riser (0.80), the wall phone in shade)
    k = 0.66 if name.startswith("wallphone") else 0.80
    seg = 48
    verts = [(tuple(conv(ctr)), (0.5, 0.5))]
    for j in range(seg):
        t = 2 * math.pi * j / seg
        p = ctr + rp * (math.cos(t) * right + math.sin(t) * up)
        verts.append((tuple(conv(p)), (0.5 + 0.5 * math.cos(t), 0.5 - 0.5 * math.sin(t))))
    tris = [[0, 1 + j, 1 + (j + 1) % seg] for j in range(seg)]
    nrm = tuple(conv(n, 1.0))
    if np.cross(np.array(verts[1][0]) - np.array(verts[0][0]), np.array(verts[2][0]) - np.array(verts[0][0])) @ np.array(nrm) < 0:
        tris = [[t[0], t[2], t[1]] for t in tris]
    nm = "hzm_dial_%s" % name
    sh = "hzm_dial_%s" % name
    vv = [(nrm, uv, 0, p) for p, uv in verts]
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], [("s", np.array(tris), vv)]))
    Pv = np.array([p for p, _ in verts])
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(), float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n\tsurface s shader %s\n}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, sh, nm))
    shaders.append("%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_dial.jpg\n\t\trgbGen identity\n\t}\n}" % sh)
    names.append(nm)
    print("%-22s light %.2f (bake L %.2f) r %.3f m" % (nm, k, Lm, rp))
open(os.path.join(sdir, "hzm_dial.shader"), "w", newline="\n").write("\n\n".join(shaders) + "\n")
json.dump(names, open(os.path.join(out, "dials_models.json"), "w"))
