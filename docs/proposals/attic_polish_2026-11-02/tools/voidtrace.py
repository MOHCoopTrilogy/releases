r"""voidtrace.py - offline twin of voidprobe.py: cast the camera's rays at the scene's own models (the skd files the menu loads)
and report every ray that hits NOTHING - the void past the room's edges. No game client, no screen.

    python voidtrace.py <menus pak> <mod ui dir> <poses.json> <scene> [--aspect 16:9,21:9,4:3] [--grid 96] [--add DIR]
                        [--only REGEX] [--png OUTDIR]

Models: every 'scenemodel' of the scene with its origin / yaw (the engine's: origin + R(yaw) v), read from --add DIR first (a pak
overlay under test), then the pak; models under models/human (the soldier) are skipped. A ray that first hits a weather layer
(hzm_wx_*: sky, town, rain - drawn only through the window / skylight openings) is fine; one that hits nothing is VOID.
The camera is the engine's (cl_uiscene.cpp Project): fov is vertical, fovx = 2 atan(tan(fovy/2) * W/H), pitch positive = down.
"""
import json, math, os, re, sys, zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skd_read as R  # noqa: E402

F7 = r"(-?[\d.]+(?:\s+-?[\d.]+){6})"


class Src:
    def __init__(self, pak, add=None):
        self.z = zipfile.ZipFile(pak)
        self.add = add

    def read(self, n):
        if self.add:
            p = os.path.join(self.add, n)
            if os.path.exists(p):
                return open(p, "rb").read()
        return self.z.read(n)


def scene_models(ui, scene):
    for f in sorted(os.listdir(ui)):
        if not f.lower().endswith((".urc", ".inc")):
            continue
        t = open(os.path.join(ui, f), encoding="latin-1").read().replace("\r\n", "\n")
        for m in re.finditer(r"(?m)^Scene3D\s*\n\{(.*?)\n\}", t, re.S):
            b = m.group(1)
            if re.search(r'(?m)^name "%s"' % re.escape(scene), b):
                out = []
                for mm in re.finditer(r'(?m)^scenemodel "([^"]+)" (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)', b):
                    out.append((mm.group(1), [float(mm.group(k)) for k in range(2, 6)]))
                return out
    raise SystemExit("no scene %s" % scene)


def load_tris(src, models):
    T, W = [], []
    for path, (ox, oy, oz, yaw) in models:
        if "/human/" in path:
            continue
        try:
            tik = src.read(path).decode("latin-1")
        except KeyError:
            continue
        sk = re.search(r"(?m)^\s*skelmodel\s+(\S+)", tik)
        pth = re.search(r"(?m)^\s*path\s+(\S+)", tik)
        if not sk:
            continue
        skp = (pth.group(1) + "/" if pth else "") + sk.group(1)
        try:
            m = R.read_skd(src.read(skp))
        except Exception:
            continue
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        wx = os.path.basename(path).startswith("hzm_wx_")
        for sf in m["surfaces"]:
            P = np.array([v[3] for v in sf["verts"]], np.float64)
            P = np.stack([P[:, 0] * c - P[:, 1] * s + ox, P[:, 0] * s + P[:, 1] * c + oy, P[:, 2] + oz], 1)
            T.append(P[sf["tris"]])
            W.append(np.full(len(sf["tris"]), wx))
    if not T:
        return np.zeros((0, 3, 3), np.float32), np.zeros(0, bool)
    return np.concatenate(T).astype(np.float32), np.concatenate(W)


def rays(pose, aspect, nx):
    x, y, z, pitch, yaw, _r, fov = pose
    ny = max(8, int(round(nx / aspect)))
    pr, yr = math.radians(pitch), math.radians(yaw)
    f = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr)])
    r = np.array([math.sin(yr), -math.cos(yr), 0.0])
    u = np.cross(r, f)
    ty = math.tan(math.radians(fov / 2))
    tx = ty * aspect
    xs = (np.arange(nx) + 0.5) / nx * 2 - 1
    ys = 1 - (np.arange(ny) + 0.5) / ny * 2
    X, Y = np.meshgrid(xs, ys)
    D = f[None, None, :] + X[..., None] * tx * r[None, None, :] + Y[..., None] * ty * u[None, None, :]
    D /= np.linalg.norm(D, axis=2, keepdims=True)
    return np.array([x, y, z], np.float32), D.reshape(-1, 3).astype(np.float32), (ny, nx)


def first_hit(o, D, T, chunk=4096):
    """Moller-Trumbore, all rays x all triangles in chunks: (t, tri index) of the nearest hit, t = inf for none"""
    best = np.full(len(D), np.inf, np.float32)
    idx = np.full(len(D), -1, np.int64)
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    s = o[None, :] - v0                                      # (T,3)
    q = np.cross(s, e1)                                       # (T,3)
    for a in range(0, len(T), chunk):
        b = slice(a, a + chunk)
        p = np.cross(D[:, None, :], e2[None, b, :])           # (R,C,3)
        det = (p * e1[None, b, :]).sum(2)
        inv = np.where(np.abs(det) > 1e-9, 1.0 / np.where(det == 0, 1, det), 0)
        uu = (p * s[None, b, :]).sum(2) * inv
        vv = (D[:, None, :] * q[None, b, :]).sum(2) * inv
        t = (e2[None, b, :] * q[None, b, :]).sum(2) * inv
        ok = (np.abs(det) > 1e-9) & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (t > 0.5) & (t < 2048)
        t = np.where(ok, t, np.inf)
        j = t.argmin(1)
        tj = t[np.arange(len(D)), j]
        better = tj < best
        best[better] = tj[better]
        idx[better] = j[better] + a
    return best, idx


# the attic's two openings onto the weather layers (gen_window_view.py: the gable pane at x 358.05, window67.json; the skylight
# corners, game units): a ray that first hits a weather layer WITHOUT crossing one of them is a leak, not a view out
OPENINGS = [np.array([(358.05, 170.6, 60.4), (358.05, 249.4, 60.4), (358.05, 249.4, 107.6), (358.05, 170.6, 107.6)]),
            np.array([(173.25, 175.9, 146.2), (173.25, 128.6, 168.2), (232.05, 128.6, 168.2), (232.05, 175.9, 146.2)])]


def through_opening(o, D, t, pad=4.0):
    ok = np.zeros(len(D), bool)
    for Q in OPENINGS:
        c = Q.mean(0)
        n = np.cross(Q[1] - Q[0], Q[3] - Q[0])
        n /= np.linalg.norm(n)
        e1, e2 = Q[1] - Q[0], Q[3] - Q[0]
        den = D @ n
        s = ((c - o) @ n) / np.where(np.abs(den) < 1e-9, 1e-9, den)
        P = o[None, :] + D * s[:, None] - Q[0][None, :]
        a = (P @ e1) / (e1 @ e1)
        b = (P @ e2) / (e2 @ e2)
        pa, pb = pad / np.linalg.norm(e1), pad / np.linalg.norm(e2)
        ok |= (s > 0) & (s < t) & (a > -pa) & (a < 1 + pa) & (b > -pb) & (b < 1 + pb)
    return ok


def main():
    a = sys.argv[1:]
    pak, ui, poses_f, scene = a[:4]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    aspects = {"16:9": 16 / 9, "21:9": 2.39, "4:3": 4 / 3}
    asp = [(k, aspects[k]) for k in opt("--aspect", "16:9,21:9").split(",")]
    grid = int(opt("--grid", "96"))
    only = opt("--only", None)
    png = opt("--png", None)
    src = Src(pak, opt("--add", None))
    T, W = load_tris(src, scene_models(ui, scene))
    print("%s: %d triangles (%d weather)" % (scene, len(T), int(W.sum())))
    P = json.load(open(poses_f))[scene]["poses"]
    rep = []
    for pn, pose in P:
        if only and not re.search(only, pn):
            continue
        for an, av in asp:
            o, D, shp = rays(pose, av, grid)
            t, j = first_hit(o, D, T)
            void = ~np.isfinite(t)
            if W.any():
                wxh = np.isfinite(t) & W[np.maximum(j, 0)]
                void |= wxh & ~through_opening(o, D, t)
            n = int(void.sum())
            rep.append(dict(pose_name=pn, aspect=an, pose=pose, void=n, frac=round(n / len(D), 4)))
            if n:
                m = void.reshape(shp)
                ys, xs = np.nonzero(m)
                rep[-1]["bbox_frac"] = [round(xs.min() / shp[1], 2), round(ys.min() / shp[0], 2), round((xs.max() + 1) / shp[1], 2),
                                        round((ys.max() + 1) / shp[0], 2)]
                if png:
                    from PIL import Image
                    os.makedirs(png, exist_ok=True)
                    im = np.where(m[..., None], np.array([255, 0, 255]), np.array([60, 60, 60])).astype(np.uint8)
                    Image.fromarray(im).resize((shp[1] * 4, shp[0] * 4), Image.NEAREST).save(os.path.join(png, "%s_%s_%s.png" % (scene, pn, an.replace(":", ""))))
            print("  %-14s %-5s void %5d (%5.1f %%) %s" % (pn, an, n, 100.0 * n / len(D), rep[-1].get("bbox_frac", "")), flush=True)
    out = opt("--out", None)
    if out:
        json.dump(rep, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
