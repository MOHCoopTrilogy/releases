"""gen_fog73.py <add dir> - rain73 stage 4: fog banks round the town outside the attic window (PLAN.md section 4).

Four soft banks (vertical cards facing the window, -x) at increasing depth in the squashed town (gen_window_view / wx_town: near
roofs from x 544, the town to ~1700, the ridges ~1760, the sky backdrop at 1928):
    hzm_wx_fog0  x  640  weight  18 %   the nearest roofs only soften
    hzm_wx_fog1  x 1000  weight  40 %
    hzm_wx_fog2  x 1450  weight  70 %
    hzm_wx_fog3  x 1880  weight 100 %   the far ridges and the church spire go first
Each card's alpha = seamless spectral clouds (periodic in u, so the slow drift never shows a seam) x a vertical profile that is
densest on the low ground and the valley floor and thins upward (zero at the card's top edge: no wrap line in v). The engine's
`scenewx ... fog <weight>` role (cl_uiscene.cpp, rain73) gives alpha = F x weight and the colour: daylight / outside tint, a lightning
strike lights the banks, a faint warm glow under the lit windows at night. Sorts 8.22 (far) .. 8.28 (near): drawn far to near,
after the cloud deck (8.2), before the rain (8.3+). All of it lies beyond the gable wall (x 358): depth-tested behind the window
frame and the room - never indoors, never over the frame.
"""
import math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

add = sys.argv[1]
mdir, tdir, sdir = (os.path.join(add, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)
CARDS = [("hzm_wx_fog0", 640.0, 18, -700.0, 120.0, 0.0010, 1300.0),
         ("hzm_wx_fog1", 1000.0, 40, -520.0, 220.0, 0.0016, 2000.0),
         ("hzm_wx_fog2", 1450.0, 70, -260.0, 330.0, 0.0022, 2600.0),
         ("hzm_wx_fog3", 1880.0, 100, -200.0, 520.0, 0.0030, 3200.0)]     # name, x, weight, z0, z1, drift, half-width (y)
YC = 150.0


def fft_clouds(w, h, beta, seed):
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.sqrt(fx * fx + (fy * w / h) ** 2)
    f[0, 0] = 1.0
    amp = f ** (-beta)
    amp[0, 0] = 0.0
    z = np.real(np.fft.ifft2(amp * np.exp(2j * math.pi * r.random((h, w)))))
    return (z - z.min()) / (z.max() - z.min())


SH = ["// rain73 the fog banks (gen_fog73.py): alpha and colour from the engine's scenewx 'fog' role (rain73 exe)"]
LINES, WX = [], []
for k, (nm, x, wgt, z0, z1, drift, hw) in enumerate(CARDS):
    W, H = 512, 128
    c = fft_clouds(W, H, 1.7, 400 + k)
    v = np.linspace(0, 1, H)[:, None]                 # 0 = the card's top (image row 0), 1 = its bottom
    prof = np.clip(v, 0, 1) ** 1.3 * (1.0 - np.clip((v - 0.92) / 0.08, 0, 1) * 0.0)
    prof[: int(H * 0.06)] = 0.0                       # no alpha in the top rows: the v wrap can never show
    a = np.clip(prof * (0.45 + 0.75 * c), 0, 1)
    rgb = np.clip(0.88 + 0.12 * c, 0, 1)
    Image.fromarray((np.dstack([rgb, rgb, rgb, a]) * 255).astype(np.uint8), "RGBA").save(os.path.join(tdir, nm + ".tga"))
    # the card: facing -x (towards the window), u along y (2.5 repeats), v down
    P = [(x, YC + hw, z1), (x, YC - hw, z1), (x, YC - hw, z0), (x, YC + hw, z0)]
    U = [(0.0, 0.0), (2.5, 0.0), (2.5, 1.0), (0.0, 1.0)]
    corners = [[(0, P[i], (-1.0, 0.0, 0.0), U[i]) for i in tri] for tri in ((0, 1, 2), (0, 2, 3))]
    ss = X.split_surfaces("s", corners)
    Pv = np.array([q[3] for s_ in ss for q in s_[2]])
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], ss))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n"
        % (nm, "\n".join("\tsurface %s shader %s" % (q[0], nm) for q in ss), nm))
    SH.append("%s\n{\n\tnopicmip\n\tcull none\n\tsort %.2f\n\t{\n\t\tmap textures/menu/%s.tga\n\t\tblendFunc blend\n\t\trgbGen entity\n"
              "\t\talphaGen entity\n\t\ttcMod scroll %.4f 0\n\t}\n}" % (nm, 8.28 - 0.02 * k, nm, drift * (1 if k % 2 else -1)))
    LINES.append('scenemodel "models/menu/%s.tik" 0 0 0 0' % nm)
    WX.append('scenewx "%s" fog %d' % (nm, wgt))
open(os.path.join(sdir, "hzm_wxfog73.shader"), "w", newline="\n").write("\n\n".join(SH) + "\n")
open(os.path.join(add, "fog73_lines.txt"), "w", newline="\n").write("\n".join(LINES + WX) + "\n")
print("fog: %d banks -> %s" % (len(CARDS), add))
