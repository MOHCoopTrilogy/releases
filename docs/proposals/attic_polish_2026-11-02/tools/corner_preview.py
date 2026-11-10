"""corner_preview.py <bg screenshot> <out.png> <w> <h> - quick offline composite of the gramophone corner over a home-view still
(painter's flat shading from the stock textures) to choose placements before spending a harness run.  Reads CORNER from
make_attic_polish.py so the preview and the menu use the same numbers."""
import io, math, os, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw

H_ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import scene_params as SP  # noqa: E402
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")

bg, outp, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
cam = [-36.7, 21.0, 102.4, 7.01, 0.0, 0.0, 55.11]
f, l, u = SP.axes_from_angles(*cam[3:6])
org = np.array(cam[:3])
F = (H / 2) / math.tan(math.radians(cam[6] / 2))
ns = {}
exec(compile(open(os.path.join(H_, "corner_layout.py")).read(), "corner_layout.py", "exec"), ns)
PK = r"H:\hzm_work\attic_polish\pkadd\models\menu"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest\main"
TEX = {"static_phonograph": ("Pak2.pk3", "textures/models/furniture/phonograph.tga")}


def proj(p):
    c = np.asarray(p, float) - org
    x, y, z = c @ f, c @ l, c @ u
    return np.stack([W / 2 - y / x * F, H / 2 - z / x * F], -1), x


def read_skd(path):
    import struct
    d = open(path, "rb").read()
    h = struct.unpack_from("<4si64s5i", d, 0)
    o = h[6]
    tris_all, P_all = [], []
    for s in range(h[3]):
        sh = struct.unpack_from("<4s64s8i", d, o)
        nT, nV, _, oT, oV, oC, oE, oCI = sh[2:]
        tris = np.frombuffer(d, "<i4", nT * 3, o + oT).reshape(nT, 3)
        p = o + oV
        P = []
        for v in range(nV):
            nw, nm = struct.unpack_from("<2i", d, p + 20)
            p += 28
            bi, wt, x, y, z = struct.unpack_from("<if3f", d, p)
            p += 20 * nw + 16 * nm
            P.append((x, y, z))
        tris_all.append(tris + len(P_all))
        P_all += P
        o += oE
    return np.vstack(tris_all), np.array(P_all)


im = Image.open(bg).convert("RGB").resize((W, H))
dr = ImageDraw.Draw(im, "RGBA")
items = []
for name, x, y, z, yaw, col in ns["MODELS_PREVIEW"]:
    tris, P = read_skd(os.path.join(PK, name + ".skd"))
    a = math.radians(yaw)
    R = np.array([[math.cos(a), math.sin(a), 0], [-math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Wp = P @ R + np.array([x, y, z])
    S, dep = proj(Wp)
    for t in tris:
        nrm = np.cross(Wp[t[1]] - Wp[t[0]], Wp[t[2]] - Wp[t[0]])
        sh = 0.55 + 0.45 * abs(nrm[2]) / (np.linalg.norm(nrm) + 1e-9)
        items.append((dep[t].mean(), [tuple(S[i]) for i in t], tuple(int(c * sh) for c in col)))
items.sort(key=lambda r: -r[0])
for _, pts, c in items:
    dr.polygon(pts, fill=c + (255,))
for nm, (cx, cy, cz, hw, hh) in ns["LABELS_PREVIEW"]:
    pts = [proj((cx, cy + sy * hw, cz + sz * hh))[0] for sy, sz in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    dr.rectangle((min(xs), min(ys), max(xs), max(ys)), outline=(255, 230, 120, 255), width=2)
    dr.text((min(xs) + 3, min(ys) + 2), nm, fill=(255, 230, 120, 255))
im.save(outp)
print(outp)
