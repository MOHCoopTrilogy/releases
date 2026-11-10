"""atticview.py - CPU-only textured view of the 3D attic main menu (no game client, no GPU, no Blender).    [advtrain 2026-11-10]

    python atticview.py <menus pk3> <main.urc> <out.png> [--add DIR] [--cam "x y z pitch yaw roll fov"] [--size WxH]
                        [--npz OUT.npz] [--hide name,name] [--show name,name] [--mark "x y z"] [--hot] [--crop x0,y0,x1,y1]

Loads every static scenemodel of the atticscene block of main.urc (models/menu/*.tik - the baked room, its props and the
generated hotspot props; the animated actors and the window's weather sky are skipped and listed), each at its urc origin and
yaw, from the menus pak (an --add dir of loose files overrides it, like polish_pak.py would) with the game's paks under it, and
z-buffers them at the menu's scenecam (or --cam), textured from each surface's shader's first map stage. Baked shaders
(rgbGen identity) draw their texture as is; lightingSpherical ones get a simple lambert from the block's scenelights, so a
generated prop reads roughly as the engine lights it. blendFunc blend stages (contact shadows) are alpha-blended over the room.

--npz writes the per-pixel world position, depth and model id (the "raycast against the bake": placement tools pick a floor
spot from it). --hot draws every home hotspot's hit rect (the engine's rule: projected radius square or the scenehotbox).
A scenemodelhide'd model stays hidden unless --show names it (a lit copy shown as when hovered)."""
import io, math, os, re, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw
import numba as nb

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\attic_polish_2026-11-02\tools"
for p_ in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "attic_polish_2026-11-02", "tools"), TOOLS,
           r"C:\mohaa-coop-dev\docs\tools\weapon_hd", r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d"):
    sys.path.insert(0, os.path.normpath(p_))
import skd_read as R  # noqa: E402
import vfs  # noqa: E402
import scene_params as SP  # noqa: E402


class FS:
    """add dir (loose) > menus pak > the game's paks (vfs: main < mainta < maintt, last wins)"""

    def __init__(self, pak, add=None):
        self.z = zipfile.ZipFile(pak)
        self.zl = {n.lower(): n for n in self.z.namelist()}
        self.add = add

    def read(self, p):
        p = p.replace("\\", "/").lstrip("/")
        if self.add:
            q = os.path.join(self.add, p)
            if os.path.isfile(q):
                return open(q, "rb").read()
        n = self.zl.get(p.lower())
        if n:
            return self.z.read(n)
        return vfs.read(p)

    def names(self):
        s = set(vfs.index().keys()) | set(self.zl.keys())
        if self.add:
            for r, _, fs in os.walk(self.add):
                for f in fs:
                    s.add(os.path.relpath(os.path.join(r, f), self.add).replace("\\", "/").lower())
        return s

    def image(self, stem):
        stem = os.path.splitext(stem)[0]
        for ext in (".dds", ".jpg", ".tga", ".png"):        # the engine's probe order (TRAPS T6)
            b = self.read(stem + ext)
            if b:
                try:
                    im = Image.open(io.BytesIO(b))
                    return np.asarray(im.convert("RGBA"), np.uint8)   # PIL reads TGA origin correctly (as the engine shows it)
                except Exception:  # noqa: BLE001
                    return None
        return None


def shader_table(fs):
    """shader name -> (first map stage, lit?, blend?, alphatest?) over every scripts/*.shader (later pak wins: menus pak, add dir)"""
    tab = {}
    srcs = sorted(n for n in vfs.index() if n.startswith("scripts/") and n.endswith(".shader"))
    texts = [(vfs.read(n) or b"").decode("latin-1") for n in srcs]
    texts += [fs.z.read(fs.zl[n]).decode("latin-1") for n in sorted(fs.zl) if n.startswith("scripts/") and n.endswith(".shader")]
    if fs.add and os.path.isdir(os.path.join(fs.add, "scripts")):
        for f in sorted(os.listdir(os.path.join(fs.add, "scripts"))):
            texts.append(open(os.path.join(fs.add, "scripts", f), "rb").read().decode("latin-1"))
    for t in texts:
        t = re.sub(r"//[^\n]*", "", t)
        i, n = 0, len(t)
        while i < n:
            m = re.compile(r"\s*([^\s{}]+)\s*\{").match(t, i)
            if not m:
                break
            name, j, d = m.group(1).lower(), m.end(), 1
            k = j
            while k < n and d:
                d += {"{": 1, "}": -1}.get(t[k], 0)
                k += 1
            body = t[j:k - 1]
            mp = None
            for sm in re.finditer(r"(?im)^\s*(?:map|clampmap|animmap\s+\S+)\s+(\S+)", body):
                if not sm.group(1).startswith("$"):
                    mp = sm.group(1)
                    break
            tab[name] = (mp, "lightingspherical" in body.lower() or "lightingdiffuse" in body.lower(),
                         bool(re.search(r"(?i)blendfunc\s+(blend|gl_src_alpha)", body)), bool(re.search(r"(?i)alphafunc", body)))
            i = k
    return tab


def parse_tik(txt):
    path, skd, scale, surf = "", None, 1.0, {}
    for ln in txt.splitlines():
        w = ln.split()
        if not w:
            continue
        if w[0] == "path":
            path = w[1]
        elif w[0] == "skelmodel":
            skd = w[1]
        elif w[0] == "scale":
            scale = float(w[1])
        elif w[0] == "surface" and len(w) >= 4 and w[2] == "shader":
            surf[w[1]] = w[3]
        elif w[0] == "surface" and len(w) >= 3 and w[2].lower() == "+nodraw":
            surf[w[1]] = None
    return (path.rstrip("/") + "/" + skd if skd and "/" not in skd else skd), scale, surf


def scene_block(urc, name="atticscene"):
    t = open(urc, encoding="latin-1").read().replace("\r\n", "\n")
    s0 = t.index('name "%s"' % name)
    return t[s0:t.index("\n}\n", s0)]


SKIP = ("hzm_wx_",)


def load_scene(fs, blk, show=(), hide=(), log=print):
    hidden = {m.group(1) for m in re.finditer(r'(?m)^scenemodelhide "([^"]+)" 1', blk)}
    hidden = (hidden - set(show)) | set(hide)
    shd = shader_table(fs)
    tris, uvs, nrm, tex_of, lit_of, blend_of, mid = [], [], [], [], [], [], []
    texs, tex_idx, models = [], {}, []
    skipped = []
    for m in re.finditer(r'(?m)^scenemodel "([^"]+)" (\S+) (\S+) (\S+) (\S+)', blk):
        p, o, yaw = m.group(1), np.array([float(m.group(i)) for i in (2, 3, 4)]), float(m.group(5))
        base = os.path.splitext(os.path.basename(p))[0]
        if not p.startswith("models/menu/") or base.startswith(SKIP) or base in hidden:
            skipped.append(base)
            continue
        tb = fs.read(p)
        if not tb:
            skipped.append(base + "(missing)")
            continue
        skd, scale, smap = parse_tik(tb.decode("latin-1"))
        mdl = R.read_skd(fs.read(skd))
        c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        Rz = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
        models.append(base)
        for sf in mdl["surfaces"]:
            sh = smap.get(sf["name"], smap.get("*"))
            if sh is None:
                continue
            ent = shd.get(sh.lower(), (sh, False, False, False))
            tp = ent[0] or sh
            if tp not in tex_idx:
                im = fs.image(tp)
                if im is None:
                    im = np.full((4, 4, 4), (255, 0, 255, 255), np.uint8)
                    log("  no image for shader %s (%s)" % (sh, tp))
                tex_idx[tp] = len(texs)
                texs.append(im)
            V = sf["verts"]
            P = np.array([v[3] for v in V], float) * scale @ Rz.T + o
            N = np.array([v[0] for v in V], float) @ Rz.T
            U = np.array([v[1] for v in V], float)
            T = sf["tris"]
            tris.append(P[T]); uvs.append(U[T]); nrm.append(N[T])
            k = len(T)
            tex_of.append(np.full(k, tex_idx[tp])); lit_of.append(np.full(k, int(ent[1])))
            blend_of.append(np.full(k, int(ent[2]) + 2 * int(ent[3]))); mid.append(np.full(k, len(models) - 1))
    log("models: %d drawn; skipped %s" % (len(models), ", ".join(sorted(set(skipped)))))
    off, ws, hs, flat = [], [], [], []
    o_ = 0
    for im in texs:
        off.append(o_); hs.append(im.shape[0]); ws.append(im.shape[1]); flat.append(im.reshape(-1))
        o_ += im.size
    lights = [[float(v) for v in m.group(1).split()] for m in re.finditer(r"(?m)^scenelight (.*)$", blk)]
    return dict(P=np.concatenate(tris), UV=np.concatenate(uvs), N=np.concatenate(nrm), tex=np.concatenate(tex_of),
                lit=np.concatenate(lit_of), blend=np.concatenate(blend_of), mid=np.concatenate(mid), models=models,
                texflat=np.concatenate(flat), texoff=np.array(off, np.int64), texw=np.array(ws, np.int64),
                texh=np.array(hs, np.int64), lights=np.array(lights or [[0, 0, 0, 1, 0, 0, 0]], float))


@nb.njit(cache=True)
def _sample(texflat, off, w, h, u, v):
    x = int(math.floor((u - math.floor(u)) * w)) % w
    y = int(math.floor((v - math.floor(v)) * h)) % h
    b = off + (y * w + x) * 4
    return texflat[b] / 255.0, texflat[b + 1] / 255.0, texflat[b + 2] / 255.0, texflat[b + 3] / 255.0


@nb.njit(cache=True)
def _raster(C, P, UV, Nn, tex, lit, blend, mid, texflat, toff, tw, th, lights, W, H, F, near, passno,
            img, zbuf, wpos, idbuf):
    """C: camera-space (x fwd, y left, z up) per corner; pass 0 = opaque (+alpha test), pass 1 = blended (no z write)"""
    for t in range(C.shape[0]):
        isblend = (blend[t] & 1) == 1
        if (passno == 0 and isblend) or (passno == 1 and not isblend):
            continue
        # clip against x >= near (Sutherland-Hodgman, up to 4 verts)
        px = np.zeros((4, 3)); pu = np.zeros((4, 2)); pw = np.zeros((4, 3)); nv = 0
        for k in range(3):
            a, b = k, (k + 1) % 3
            ina, inb = C[t, a, 0] >= near, C[t, b, 0] >= near
            if ina:
                px[nv] = C[t, a]; pu[nv] = UV[t, a]; pw[nv] = P[t, a]; nv += 1
            if ina != inb:
                s = (near - C[t, a, 0]) / (C[t, b, 0] - C[t, a, 0])
                px[nv] = C[t, a] + s * (C[t, b] - C[t, a]); pu[nv] = UV[t, a] + s * (UV[t, b] - UV[t, a])
                pw[nv] = P[t, a] + s * (P[t, b] - P[t, a]); nv += 1
        if nv < 3:
            continue
        # shading for lightingSpherical surfaces: ambient + lambert from the scene lights (+ the normal's facing)
        sh = 1.0
        if lit[t] == 1:
            n0 = Nn[t, 0] + Nn[t, 1] + Nn[t, 2]
            ln = math.sqrt(n0[0] ** 2 + n0[1] ** 2 + n0[2] ** 2) + 1e-9
            n0 = n0 / ln
            cx = (P[t, 0] + P[t, 1] + P[t, 2]) / 3.0
            acc = 0.42
            for L in range(lights.shape[0]):
                d = lights[L, :3] - cx
                dl = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) + 1e-9
                nd = (n0[0] * d[0] + n0[1] * d[1] + n0[2] * d[2]) / dl
                if nd > 0:
                    acc += nd * 0.55 * max(0.0, 1.0 - dl / (lights[L, 3] * 1.6)) * (lights[L, 4] + lights[L, 5] + lights[L, 6]) / 2.4
            sh = min(acc, 1.25)
        for f in range(1, nv - 1):
            ids = (0, f, f + 1)
            sx = np.zeros(3); sy = np.zeros(3); iz = np.zeros(3)
            for q in range(3):
                v = px[ids[q]]
                sx[q] = W / 2.0 - v[1] / v[0] * F
                sy[q] = H / 2.0 - v[2] / v[0] * F
                iz[q] = 1.0 / v[0]
            area = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
            if abs(area) < 1e-9:
                continue
            x0 = max(int(math.floor(min(sx[0], sx[1], sx[2]))), 0)
            x1 = min(int(math.ceil(max(sx[0], sx[1], sx[2]))), W - 1)
            y0 = max(int(math.floor(min(sy[0], sy[1], sy[2]))), 0)
            y1 = min(int(math.ceil(max(sy[0], sy[1], sy[2]))), H - 1)
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    cxp, cyp = xx + 0.5, yy + 0.5
                    w0 = ((sx[1] - cxp) * (sy[2] - cyp) - (sx[2] - cxp) * (sy[1] - cyp)) / area
                    w1 = ((sx[2] - cxp) * (sy[0] - cyp) - (sx[0] - cxp) * (sy[2] - cyp)) / area
                    w2 = 1.0 - w0 - w1
                    if w0 < 0 or w1 < 0 or w2 < 0:
                        continue
                    izp = w0 * iz[0] + w1 * iz[1] + w2 * iz[2]
                    z = 1.0 / izp
                    if z >= zbuf[yy, xx] - (0.02 if passno == 1 else 0.0):
                        continue
                    a0, a1, a2 = w0 * iz[0] * z, w1 * iz[1] * z, w2 * iz[2] * z
                    u = a0 * pu[ids[0], 0] + a1 * pu[ids[1], 0] + a2 * pu[ids[2], 0]
                    v = a0 * pu[ids[0], 1] + a1 * pu[ids[1], 1] + a2 * pu[ids[2], 1]
                    r, g, b, al = _sample(texflat, toff[tex[t]], tw[tex[t]], th[tex[t]], u, v)
                    if passno == 0:
                        if (blend[t] & 2) == 2 and al < 0.5:
                            continue
                        img[yy, xx, 0] = r * sh; img[yy, xx, 1] = g * sh; img[yy, xx, 2] = b * sh
                        zbuf[yy, xx] = z
                        for q in range(3):
                            wpos[yy, xx, q] = a0 * pw[ids[0], q] + a1 * pw[ids[1], q] + a2 * pw[ids[2], q]
                        idbuf[yy, xx] = mid[t]
                    else:
                        img[yy, xx, 0] = img[yy, xx, 0] * (1 - al) + r * sh * al
                        img[yy, xx, 1] = img[yy, xx, 1] * (1 - al) + g * sh * al
                        img[yy, xx, 2] = img[yy, xx, 2] * (1 - al) + b * sh * al


def render(S, cam, W, H):
    org = np.array(cam[:3])
    f, l, u = SP.axes_from_angles(*cam[3:6])
    F = (H / 2) / math.tan(math.radians(cam[6]) / 2)
    D = S["P"] - org
    C = np.stack([D @ f, D @ l, D @ u], -1)
    img = np.zeros((H, W, 3)); img[:] = (0.05, 0.05, 0.07)
    zb = np.full((H, W), 1e9); wp = np.zeros((H, W, 3)); idb = np.full((H, W), -1, np.int64)
    for ps in (0, 1):
        _raster(C, S["P"], S["UV"], S["N"], S["tex"], S["lit"], S["blend"], S["mid"], S["texflat"], S["texoff"], S["texw"],
                S["texh"], S["lights"], W, H, F, 0.5, ps, img, zb, wp, idb)
    return img, zb, wp, idb, F


def project(p, cam, W, H):
    org = np.array(cam[:3])
    f, l, u = SP.axes_from_angles(*cam[3:6])
    F = (H / 2) / math.tan(math.radians(cam[6]) / 2)
    c = np.asarray(p, float) - org
    x, y, z = c @ f, c @ l, c @ u
    return W / 2 - y / x * F, H / 2 - z / x * F, x


def hot_rects(blk, cam, W, H):
    boxes = {m.group(1): [float(v) for v in m.groups()[1:]] for m in re.finditer(r'(?m)^scenehotbox "(\w+)" (\S+) (\S+) (\S+) (\S+)', blk)}
    out = {}
    k = H / 1080.0
    for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "(?:[^"\\]|\\.)*" "[^"]*" "[^"]*"(?: (-?\d+))?', blk):
        if m.group(6) not in (None, "0", "-1"):
            continue
        sx, sy, dep = project([float(m.group(i)) for i in (2, 3, 4)], cam, W, H)
        r = float(m.group(5)) / dep * ((H / 2) / math.tan(math.radians(cam[6]) / 2))
        cx, cy, hx, hy = sx, sy, r, r
        if m.group(1) in boxes:
            b = boxes[m.group(1)]
            cx, cy, hx, hy = sx + b[0] * k, sy + b[1] * k, b[2] * k, b[3] * k
        out[m.group(1)] = (cx - hx, cy - hy, cx + hx, cy + hy)
    return out


def main(a):
    pak, urc, outp = a[:3]
    opt = {}
    i = 3
    while i < len(a):
        if a[i] == "--hot":
            opt["hot"] = True; i += 1
        else:
            opt[a[i][2:]] = a[i + 1]; i += 2
    W, H = (int(v) for v in opt.get("size", "1920x1080").split("x"))
    blk = scene_block(urc, opt.get("scene", "atticscene"))
    cam = [float(v) for v in (opt.get("cam") or re.search(r"(?m)^scenecam (.*)$", blk).group(1)).split()]
    fs = FS(pak, opt.get("add"))
    S = load_scene(fs, blk, show=[s for s in opt.get("show", "").split(",") if s], hide=[s for s in opt.get("hide", "").split(",") if s])
    img, zb, wp, idb, F = render(S, cam, W, H)
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    d = ImageDraw.Draw(im)
    if opt.get("hot"):
        for n, r in hot_rects(blk, cam, W, H).items():
            d.rectangle(r, outline=(255, 60, 60) if n != opt.get("hl") else (60, 255, 60), width=2)
            d.text((r[0] + 3, r[1] + 2), n, fill=(255, 255, 0))
    if opt.get("mark"):
        for pt in opt["mark"].split(";"):
            sx, sy, _ = project([float(v) for v in pt.split()], cam, W, H)
            d.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), outline=(0, 255, 255), width=2)
    if opt.get("crop"):
        im = im.crop(tuple(int(v) for v in opt["crop"].split(",")))
    im.save(outp)
    if opt.get("npz"):
        np.savez_compressed(opt["npz"], wpos=wp.astype(np.float32), depth=zb.astype(np.float32), mid=idb.astype(np.int16),
                            models=np.array(S["models"]), cam=np.array(cam))
    print("%s: %dx%d, %d triangles, cam %s" % (outp, W, H, len(S["P"]), cam))


if __name__ == "__main__":
    main(sys.argv[1:])
