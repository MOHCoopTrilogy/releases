"""gen_projector_fx.py <bake dir> <stage dir> <out dir> <projector_reels.json> - v1.10.63: the Film Room projector comes alive on hover.

User: "when you mouse over the old projector in the menu can we animate it and make it make film reel sound ... Also when you
mouse over the old projector it doesnt light up the projector itself."  While the FILM ROOM hotspot is hovered / focused
(engine scenehotfx, menu-attic63):
  * hzm_proj_reel_top / _bot - the two reels, split out of the baked projector by attic62_edit section 10 and baked alone
    (rotor_visible.py), each its own model on its axle: `idle` still, `spin` one turn in 1.2 s (film speed, 50 rpm), both turning
    the same way;
  * hzm_projector_lit - the projector body (atc_projector1's own mesh) on a lamp-warmed copy of its atlas, shown in place of the
    dark baked one (the hover glow is a 2D light; on a black-enamel projector it barely showed, so the body itself lights up);
  * sound/menu/hzm_projector_loop.wav - 0.5 s of the stock BT projector run (maintt pak1 sound/mechanics/Projector.wav, the game's
    own asset), cut on a steady stretch with 12 ms fades and re-triggered every 0.48 s by the engine while the hover lasts."""
import io, json, math, os, shutil, sys, wave, zipfile
import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

bake, stage, out, rj = sys.argv[1:5]
S = 52.5
mdir, tdir, sdir, snd = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts", "sound/menu"))
for d in (mdir, tdir, sdir, snd):
    os.makedirs(d, exist_ok=True)


def conv(a, k=S):
    a = np.asarray(a, np.float64)
    return np.stack([a[..., 1], -a[..., 0], a[..., 2]], -1) * k


# ---- the reels
info = json.load(open(rj))
d = np.load(os.path.join(bake, "reels.npz"))
P, N, UV = conv(d["pos"]), conv(d["nrm"], 1.0), d["uv"].astype(np.float64).copy()
UV[..., 1] = 1.0 - UV[..., 1]
cent = P.mean(1)
reels = sorted({(round(r["c"][0], 2), round(r["c"][2], 3)) for r in info["reels"]}, key=lambda c: -c[1])     # top first (z)
axis = conv(info["axis_bu"], 1.0)
axis /= np.linalg.norm(axis)
Image.open(os.path.join(bake, "reels.png")).convert("RGB").save(os.path.join(tdir, "hzm_proj_reels.jpg"), quality=95)
placed = []
for name, (cx, cz) in zip(("top", "bot"), reels):
    # this reel's triangles: nearest axle (its centre, game units)
    yvals = [r["c"][1] for r in info["reels"] if abs(r["c"][2] - cz) < 0.01]
    c_bu = np.array([cx, float(np.mean(yvals)), cz])
    c = conv(c_bu)
    zg = c[2]
    mine = np.abs(cent[:, 2] - zg) < 0.11 * S
    Pm = P[mine] - c
    corners = []
    for t in range(len(Pm)):
        p, n, u = Pm[t], N[mine][t], UV[mine][t]
        cc = [(0, p[k], n[k], u[k]) for k in range(3)]
        if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:
            cc = [cc[0], cc[2], cc[1]]
        corners.append(cc)
    surfs = X.split_surfaces("r", corners)
    nm = "hzm_proj_reel_%s" % name
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
    allv = np.vstack([np.array([v[3] for v in s[2]]) for s in surfs])
    lo, hi, rad = (allv.min(0) - 1).tolist(), (allv.max(0) + 1).tolist(), float(np.linalg.norm(allv, axis=1).max()) + 1
    still = [[(0, 0, 0, 0), (0, 0, 0, 1)]]
    open(os.path.join(mdir, nm + "_idle.skc"), "wb").write(X.build_skc(["root pos", "root rot"], still, 0.1, lo, hi, rad))
    spin = []
    for k in range(25):                                 # 24 steps of 15 deg at 20 fps = one turn in 1.2 s
        a = math.radians(15.0 * k) / 2
        spin.append([(0, 0, 0, 0), (axis[0] * math.sin(a), axis[1] * math.sin(a), axis[2] * math.sin(a), math.cos(a))])
    open(os.path.join(mdir, nm + "_spin.skc"), "wb").write(X.build_skc(["root pos", "root rot"], spin, 0.05, lo, hi, rad))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n" % nm +
        "".join("\tsurface %s shader hzm_proj_reels\n" % s[0] for s in surfs) +
        "}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s_idle.skc\n\tspin %s_spin.skc\n}\n" % (nm, nm))
    placed.append({"model": nm, "origin": c.tolist(), "tris": int(mine.sum())})
    print(nm, "tris", int(mine.sum()), "at", np.round(c, 2))

# ---- the lit body: atc_projector1's mesh on a lamp-warmed copy of its atlas
for ext in ("skd", "skc"):
    shutil.copy(os.path.join(stage, "models", "menu", "atc_projector1." + ext), os.path.join(mdir, "hzm_projector_lit." + ext))
tk = open(os.path.join(stage, "models", "menu", "atc_projector1.tik")).read()
tk = tk.replace("atc_projector1.skd", "hzm_projector_lit.skd").replace("atc_projector1.skc", "hzm_projector_lit.skc").replace("shader hzm_atc_projector", "shader hzm_projector_lit")
open(os.path.join(mdir, "hzm_projector_lit.tik"), "w", newline="\n").write(tk)
a = np.asarray(Image.open(os.path.join(bake, "projector.png")).convert("RGB")).astype(np.float32) / 255
lit = 1 - (1 - np.clip(a * 1.9, 0, 1)) * (1 - np.array([0.10, 0.07, 0.03]))      # x1.9 and a warm lift (a screen blend with lamp light)
Image.fromarray((np.clip(lit, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(tdir, "hzm_projector_lit.jpg"), quality=95)
open(os.path.join(sdir, "hzm_projector_fx.shader"), "w", newline="\n").write(
    "// v1.10.63 the Film Room projector on hover (gen_projector_fx.py)\n"
    "hzm_proj_reels\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_proj_reels.jpg\n\t\trgbGen identity\n\t}\n}\n\n"
    "hzm_projector_lit\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_projector_lit.jpg\n\t\trgbGen identity\n\t}\n}\n")

# ---- the clatter: 0.50 s of the stock projector run
z = zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\pak1.pk3")
w = wave.open(io.BytesIO(z.read("sound/mechanics/Projector.wav")))
sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
if ch == 2:
    x = x.reshape(-1, 2).mean(1)
s0 = int(0.60 * sr)
seg = x[s0:s0 + int(0.50 * sr)].copy()
f = int(0.012 * sr)
seg[:f] *= np.linspace(0, 1, f)
seg[-f:] *= np.linspace(1, 0, f)
o = wave.open(os.path.join(snd, "hzm_projector_loop.wav"), "wb")
o.setnchannels(1)
o.setsampwidth(2)
o.setframerate(sr)
o.writeframes(np.clip(seg, -32768, 32767).astype(np.int16).tobytes())
o.close()
json.dump({"reels": placed}, open(os.path.join(out, "projector_fx.json"), "w"), indent=1)
print("projector fx ->", out)
