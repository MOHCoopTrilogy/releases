"""gen_engrave_anchors.py - where the personal engraving goes on every gun (scripts/hzm_engrave_anchors.txt).

For each first-person weapon model (grouped by mesh: finish variants share the anchor of their base gun):
  1. the mesh in the gun's entity space (gunmesh.py: skd posed by the idle animation, times the tik scale);
  2. where the camera is in that space at the hip, measured in game (cg_engraveDebug 1 -> ^~^~^ ENGRAVECAM lines,
     collected by the harness into cams.json: cam, fwd, right, up, fov);
  3. flat patches of the mesh that face the camera (triangles grown while their normals stay within PLANE_DEG and
     their distance from the seed plane within PLANE_TOL);
  4. on each patch, the largest 8:1 rectangle (the text quad) that lies fully on it, along the patch's long direction,
     reading left to right and upright from the camera;
  5. kept only if every sample point on it is in front of the camera, inside the 16:9 view with a margin, and not
     hidden by any other part of the gun (ray cast against the whole mesh);
  6. the best by projected screen area (bigger text on screen = easier to read), with a bonus for wood.
Hands are not in this mesh: the in-game check (cg_engraveCheck) renders each gun and fails any anchor a hand covers.

    python docs/tools/engrave/gen_engrave_anchors.py --cams <cams.json> --mod <mod checkout> [--only <tik> ...] [--report out.json]
"""
import json, math, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunmesh  # noqa: E402
import functools
gunmesh.read_tik = functools.lru_cache(maxsize=None)(gunmesh.read_tik)
import vfs  # noqa: E402  (weapon_hd/vfs.py, via gunmesh)

PLANE_DEG = float(os.environ.get("EG_PLANE_DEG", 14.0))
PLANE_TOL = float(os.environ.get("EG_PLANE_TOL", 0.12))
CELL = 0.04          # rasterising cell on the patch (game units)
LAYOUTS = ((8.0, 1, 0.50), (4.0, 2, 0.39))   # (quad width:height, text lines, cap height / quad height for ~18 characters); a 3-line 8:3 layout was measured 2026-11-09: 0 guns gained
LETTER_PX_GOAL = 22.0                         # letters at least this tall at 1080p, on every gun (coordinator 2026-11-09)
MIN_W = 1.2          # narrower than this and the words are unreadable at the hip
SAFE = 0.92          # fraction of the screen the anchor must stay inside (both axes)
FACING_MIN = 0.12   # a side seen at a glancing angle still reads if it is big: the hip view looks along the gun
MAX_TILT = float(os.environ.get("EG_MAX_TILT", 62.0))      # the text's baseline on screen may climb or fall this much from horizontal
MAX_PATCHES = int(os.environ.get("EG_MAX_PATCHES", 40))
MIN_TEXT_H = 0.012   # the quad's height on screen, in half-widths of the screen (~11 px at 1920 wide): smaller is unreadable


def opt(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def tri_normals(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    n = np.cross(b - a, c - a)
    area = np.linalg.norm(n, axis=1) * 0.5
    n = n / (np.linalg.norm(n, axis=1)[:, None] + 1e-12)
    return n, area, (a + b + c) / 3.0


def weld(P):
    key = np.round(P / 0.01).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    return inv.reshape(-1)


def patches(P, T, N, facing_ok):
    """grow coplanar patches over shared (welded) vertices; -> list of index arrays"""
    vid = weld(P)
    tv = vid[T]
    v2t = {}
    for ti, vs in enumerate(tv):
        for v in vs:
            v2t.setdefault(v, []).append(ti)
    seen = np.zeros(len(T), bool)
    out = []
    cosmax = math.cos(math.radians(PLANE_DEG))
    order = np.argsort(-tri_normals(P, T)[1])
    cen = P[T].mean(axis=1)
    for s in order:
        if seen[s] or not facing_ok[s]:
            continue
        n0, c0 = N[s], cen[s]
        stack, grp = [s], []
        seen[s] = True
        while stack:
            t = stack.pop()
            grp.append(t)
            for v in tv[t]:
                for u in v2t[v]:
                    if not seen[u] and facing_ok[u] and N[u] @ n0 > cosmax and abs((cen[u] - c0) @ n0) < PLANE_TOL:
                        seen[u] = True
                        stack.append(u)
        out.append(np.array(grp))
    return out


def ray_hits(orig, dirs, P, T, tmax):
    """for each ray (orig + t*dir, t in (1e-3, tmax_i)), whether any triangle is hit"""
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    e1, e2 = b - a, c - a
    hit = np.zeros(len(dirs), bool)
    for i, d in enumerate(dirs):
        pv = np.cross(d, e2)
        det = (e1 * pv).sum(1)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
        tv = orig - a
        u = (tv * pv).sum(1) * inv
        qv = np.cross(tv, e1)
        v = (d * qv).sum(1) * inv
        t = (e2 * qv).sum(1) * inv
        m = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-3) & (t < tmax[i])
        hit[i] = m.any()
    return hit


def project(cam, X):
    """-> screen coords in [-1,1] (x right, y up) and depth"""
    d = X - cam["pos"]
    z = d @ cam["fwd"]
    tx = math.tan(math.radians(cam["fov_x"]) * 0.5)
    ty = math.tan(math.radians(cam["fov_y"]) * 0.5)
    return (d @ cam["right"]) / (z * tx), (d @ cam["up"]) / (z * ty), z


def screen_dir(cam, o, d):
    x0, y0, _ = project(cam, o)
    x1, y1, _ = project(cam, o + d * 0.5)
    return np.array([x1 - x0, (y1 - y0) * cam["fov_y_ratio"]])


def best_rect(P, T, grp, n, cam, allP, allT, cenTri):
    """the best 8:1 rectangle on this patch over the readable text directions; None if none fits or it is hidden.
    At the hip a gun points AWAY from the camera, so text along the barrel is seen end-on: the text direction is
    chosen in SCREEN space (its baseline within MAX_TILT of horizontal, reading left to right), from the patch's two
    principal directions, and the rectangle is scored by the letters' height on screen."""
    pts = P[T[grp]].reshape(-1, 3)
    c0 = pts.mean(0)
    Q = pts - c0
    Q = Q - np.outer(Q @ n, n)
    w_, V = np.linalg.eigh(Q.T @ Q)
    best = None
    for base in (V[:, 2], V[:, 1]):
        u = base - n * (base @ n)
        if np.linalg.norm(u) < 1e-6:
            continue
        u /= np.linalg.norm(u)
        sd = screen_dir(cam, c0, u)
        if np.linalg.norm(sd) < 1e-6:
            continue
        if sd[0] < 0:
            u = -u
            sd = -sd
        tilt = math.degrees(math.atan2(abs(sd[1]), sd[0]))
        if tilt > MAX_TILT:
            continue
        v = np.cross(n, u)             # u x v = n: the text is not mirrored when seen from outside
        for aspect, lines, frac in LAYOUTS:
            r = fit_rect(P, T, grp, n, u, v, c0, cam, allP, allT, aspect)
            if r is None:
                continue
            r["lines"] = lines
            r["letter_px"] = r["text_h"] * 960.0 * frac      # half-width units -> px at 1920 x 1080
            r["tilt"] = tilt
            # legibility on screen: letter height x how squarely the surface faces the camera, less for a tilted baseline
            r["score"] = r["letter_px"] * (0.6 + 0.4 * max(0.0, r["facing"])) * (0.75 + 0.25 * math.cos(math.radians(tilt)))
            if best is None or r["score"] > best["score"]:
                best = r
    return best


def fit_rect(P, T, grp, n, u, v, c0, cam, allP, allT, aspect):
    # rasterise the patch into (u, v) cells
    U = (P[T[grp]] - c0) @ u
    W = (P[T[grp]] - c0) @ v
    umin, umax, wmin, wmax = U.min(), U.max(), W.min(), W.max()
    nu, nw = int((umax - umin) / CELL) + 1, int((wmax - wmin) / CELL) + 1
    if nu < 4 or nw < 2 or nu * nw > 400000:
        return None
    gu = umin + (np.arange(nu) + 0.5) * CELL
    gw = wmin + (np.arange(nw) + 0.5) * CELL
    GU, GW = np.meshgrid(gu, gw)
    inside = np.zeros(GU.shape, bool)
    for k in range(len(grp)):
        (x0, x1, x2), (y0, y1, y2) = U[k], W[k]
        d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(d) < 1e-12:
            continue
        l1 = ((y1 - y2) * (GU - x2) + (x2 - x1) * (GW - y2)) / d
        l2 = ((y2 - y0) * (GU - x2) + (x0 - x2) * (GW - y2)) / d
        inside |= (l1 >= -1e-6) & (l2 >= -1e-6) & (l1 + l2 <= 1 + 1e-6)
    S = np.zeros((nw + 1, nu + 1), int)
    S[1:, 1:] = inside.cumsum(0).cumsum(1)
    # every width (coarse steps) x every placement that fits: keep those fully on screen, ray-check the best few by
    # the letters' size on screen. A large patch is often only partly in view at the hip (the stock runs under the
    # camera), so the middle of the patch is not the answer - the part that IS in view is.
    best = None
    tested = 0
    widths = sorted(set(int(w) for w in np.linspace(nu, max(4, int(MIN_W / CELL)), 24)), reverse=True)
    cands = []
    for wc in widths:
        hc = max(2, int(round(wc / aspect)))
        if hc > nw or wc * CELL < MIN_W:
            continue
        tot = S[hc:, wc:] - S[:-hc, wc:] - S[hc:, :-wc] + S[:-hc, :-wc]
        ys, xs = np.nonzero(tot == wc * hc)
        if len(ys) == 0:
            continue
        step = max(1, len(ys) // 60)
        for k in range(0, len(ys), step):
            cy, cx = ys[k] + hc / 2.0, xs[k] + wc / 2.0
            o = c0 + u * (umin + cx * CELL) + v * (wmin + cy * CELL)
            width = wc * CELL * 0.92
            pr = quick_screen(o, u, v, width, cam, aspect)
            if pr is not None:
                cands.append((pr, o, width, xs[k], ys[k], wc, hc))
    cands.sort(key=lambda c: -c[0])
    for pr, o, width, x0, y0, wc, hc in cands[:16]:
        r = check_rect(o, u, v, n, width, cam, allP, allT, aspect)
        tested += 1
        if r and (best is None or r["text_h"] * r["screen_w"] > best["text_h"] * best["screen_w"]):
            best = r
            best.update(free_range(S, int(x0), int(y0), wc, hc, nu, nw))
            break
    return best


def free_range(S, x0, y0, wc, hc, nu, nw):
    """how far the rectangle (cells x0.., y0.., wc x hc) can slide along u and v and stay on the patch, and the largest
    square around its centre that does (the emblem size cap) - in units"""
    def full(x, y, w, h):
        if x < 0 or y < 0 or x + w > nu or y + h > nw:
            return False
        return S[y + h, x + w] - S[y, x + w] - S[y + h, x] + S[y, x] == w * h
    lo = 0
    while full(x0 - lo - 1, y0, wc, hc):
        lo += 1
    hi = 0
    while full(x0 + hi + 1, y0, wc, hc):
        hi += 1
    dn = 0
    while full(x0, y0 - dn - 1, wc, hc):
        dn += 1
    up = 0
    while full(x0, y0 + up + 1, wc, hc):
        up += 1
    cx, cy = x0 + wc // 2, y0 + hc // 2
    k = 1
    while full(cx - (k + 1) // 2, cy - (k + 1) // 2, k + 1, k + 1):
        k += 1
    # the raster's v (W) runs along +v; dv > 0 moves the quad up the text
    return dict(du0=-lo * CELL, du1=hi * CELL, dv0=-dn * CELL, dv1=up * CELL, sq=k * CELL)


def quick_screen(o, u, v, width, cam, aspect):
    """text_h * screen_w if all four corners are in the safe screen area, else None (no ray casts)"""
    h = width / aspect
    pts = [project(cam, o + u * (a * width / 2) + v * (b * h / 2)) for a in (-1, 1) for b in (-1, 1)]
    for x, y, z in pts:
        if z <= 1.0 or abs(x) > SAFE or abs(y) > SAFE:
            return None
    r = cam["fov_y_ratio"]
    th = min(np.hypot(pts[1][0] - pts[0][0], (pts[1][1] - pts[0][1]) * r), np.hypot(pts[3][0] - pts[2][0], (pts[3][1] - pts[2][1]) * r))
    sw = np.hypot((pts[2][0] + pts[3][0] - pts[0][0] - pts[1][0]) / 2, (pts[2][1] + pts[3][1] - pts[0][1] - pts[1][1]) / 2 * r)
    if th < MIN_TEXT_H:
        return None
    return th * sw


AVOID = {}   # tik -> [(centre, half extent)] of anchors the in-game hand check failed (check_visible.py reports)


def check_rect(o, u, v, n, width, cam, allP, allT, aspect):
    h = width / aspect
    for c, r in AVOID.get(cam.get("tik", ""), []):
        if np.linalg.norm(o - c) < r + width * 0.5:
            return None   # a hand covered an anchor here in game
    samp = np.array([o + u * (a * width / 2) + v * (b * h / 2) for a in (-1, -0.5, 0, 0.5, 1) for b in (-1, 0, 1)])
    sx, sy = [], []
    for X in samp:
        x, y, z = project(cam, X)
        if z <= 1.0 or abs(x) > SAFE or abs(y) > SAFE:
            return None
        sx.append(x)
        sy.append(y)
    lift = samp + n * 0.02
    dirs = lift - cam["pos"]
    dist = np.linalg.norm(dirs, axis=1)
    dirs = dirs / dist[:, None]
    if ray_hits(cam["pos"], dirs, allP, allT, dist - 1e-3).any():
        return None
    sx, sy = np.array(sx).reshape(5, 3), np.array(sy).reshape(5, 3) * cam["fov_y_ratio"]
    text_h = float(np.min(np.hypot(sx[:, 2] - sx[:, 0], sy[:, 2] - sy[:, 0])))     # letter-box height on screen, worst column
    screen_w = float(np.hypot(sx[4, 1] - sx[0, 1], sy[4, 1] - sy[0, 1]))
    if text_h < MIN_TEXT_H:
        return None
    return dict(o=o, u=u, v=v, n=n, width=width, screen=text_h * screen_w, text_h=text_h, screen_w=screen_w,
                facing=float(n @ (-(o - cam["pos"]) / np.linalg.norm(o - cam["pos"]))))


SHADERS = None


def shader_image(name):
    """the first 'map' image of a shader (scripts/*.shader), or the name itself as an image path"""
    global SHADERS
    if SHADERS is None:
        SHADERS = {}
        for k in gunmesh.vfs.index():
            if k.startswith("scripts/") and k.endswith(".shader"):
                t = gunmesh.vfs.read(k).decode("latin-1", "replace")
                t = re.sub(r"//[^\n]*", "", t)
                for m in re.finditer(r"(?s)([^\s{}]+)\s*\{(.*?)\n\}", t):
                    mm = re.search(r"(?im)^\s*(?:map|clampmap|animmap\s+\S+)\s+(\S+)", m.group(2))
                    if mm and not mm.group(1).startswith("$"):
                        SHADERS[m.group(1).lower()] = mm.group(1)
    return SHADERS.get(name.lower(), name)


def sample_color(tikdir, shader, uv):
    from PIL import Image
    import io
    img = shader_image(shader)
    stem = re.sub(r"\.(tga|jpg|dds|png)$", "", img, flags=re.I)
    for cand in (stem, tikdir + "/" + stem):
        for ext in (".tga", ".jpg", ".png", ".dds"):
            b = gunmesh.vfs.read(cand + ext)
            if b:
                try:
                    im = Image.open(io.BytesIO(b)).convert("RGB")
                except Exception:
                    continue
                w, h = im.size
                x, y = int((uv[0] % 1.0) * (w - 1)), int((uv[1] % 1.0) * (h - 1))
                box = im.crop((max(0, x - 6), max(0, y - 6), min(w, x + 7), min(h, y + 7)))
                return np.asarray(box, float).reshape(-1, 3).mean(0)
    return None


def material(rgb):
    if rgb is None:
        return "metal"
    r, g, b = rgb / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    sat = (mx - mn) / (mx + 1e-6)
    return "wood" if (r > g > b and sat > 0.28 and mx > 0.18) else "metal"


def solve(tik, cam):
    m = gunmesh.load(tik, engine_bones=cam.get("bones"))
    if not m:
        return None, "no mesh"
    allP = np.vstack([s["pos"] for s in m["surfaces"]])
    offs = np.cumsum([0] + [len(s["pos"]) for s in m["surfaces"]])
    allT = np.vstack([s["tris"] + offs[i] for i, s in enumerate(m["surfaces"]) if len(s["tris"])])
    surf_of_tri = np.concatenate([np.full(len(s["tris"]), i) for i, s in enumerate(m["surfaces"])])
    N, area, cen = tri_normals(allP, allT)
    # the stored vertex normals say which way is out
    vn = np.vstack([s["nrm"] for s in m["surfaces"]])
    flip = (vn[allT].mean(1) * N).sum(1) < 0
    N[flip] *= -1
    tocam = cam["pos"] - cen
    tocam /= np.linalg.norm(tocam, axis=1)[:, None] + 1e-12
    facing = (N * tocam).sum(1) > FACING_MIN
    cands = []
    # the biggest patches only: a small one cannot carry readable letters, and a high-poly gun (scopes, HD meshes) has
    # hundreds of slivers whose ray casts took ten minutes a gun (2026-11-09)
    groups = [g for g in patches(allP, allT, N, facing) if area[g].sum() >= 0.5]
    groups.sort(key=lambda g: -area[g].sum())
    for grp in groups[:MAX_PATCHES]:
        n = (N[grp] * area[grp][:, None]).sum(0)
        n /= np.linalg.norm(n)
        r = best_rect(allP, allT, grp, n, cam, allP, allT, cen)
        if not r:
            continue
        # material from the texture under the middle of the rectangle
        k = grp[np.argmin(np.linalg.norm(cen[grp] - r["o"], axis=1))]
        si = surf_of_tri[k]
        s = m["surfaces"][si]
        lt = allT[k] - offs[si]
        uv = s["uv"][lt].mean(0)
        r["material"] = material(sample_color(os.path.dirname(tik), s["shader"] or s["name"], uv))
        r["surface"] = s["name"]
        r["score"] *= (1.1 if r["material"] == "wood" else 1.0)
        cands.append(r)
    if not cands:
        return None, "no visible flat patch"
    best = max(cands, key=lambda r: r["score"])
    best["spots"] = name_spots(cands, cam, allP)
    return best, "ok"


def name_spots(cands, cam, allP):
    """stock_l / stock_r / receiver_l / receiver_r / grip / butt / top for the hip-visible candidates (best score per name).
    Gun-left is the camera's left (the hip view looks along the gun); 'along' runs from the butt to the muzzle."""
    f, r, up = cam["fwd"], cam["right"], cam["up"]
    a = allP @ f
    amin, amax = a.min(), a.max()
    hmed = np.median(allP @ up)
    short = (amax - amin) < 14.0       # pistols: no stock, the side of the frame is the "grip" or the "receiver"
    out = {}
    for c in cands:
        n, o = c["n"], c["o"]
        t = (o @ f - amin) / max(1e-6, amax - amin)
        if n @ f < -0.7:
            name = "butt"
        elif n @ up > 0.75:
            name = "top"
        else:
            side = "l" if n @ r < 0 else "r"
            if short:
                name = "grip" if o @ up < hmed and t < 0.6 else "receiver_" + side
            elif c["material"] == "wood" and t < 0.42:
                name = "stock_" + side
            elif o @ up < hmed - 0.8 and t < 0.6 and c["material"] == "wood":
                name = "grip"
            else:
                name = "receiver_" + side
        if name not in out or c["score"] > out[name]["score"]:
            out[name] = c
    return out


def load_cams(path):
    J = json.load(open(path))
    out = {}
    for k, c in J.items():
        # the gun is drawn with the weapon fov (r_weaponfovx); the screen test uses it
        out[k.lower()] = dict(pos=np.array(c["cam"]), fwd=np.array(c["fwd"]), right=np.array(c["right"]), up=np.array(c["up"]),
                              fov_x=c.get("wfov_x", c["fov_x"]), fov_y=c.get("fov_y_w", c.get("fov_y")),
                              bones={n: (np.array(o), np.array(a)) for n, (o, a) in c.get("bones", {}).items()})
        cc = out[k.lower()]
        cc["fov_y_ratio"] = math.tan(math.radians(cc["fov_y"]) / 2) / math.tan(math.radians(cc["fov_x"]) / 2)
    return out


def load_avoid(paths, prev_report):
    """failed guns in a check report -> AVOID entries at the anchor that was tested (from the previous anchors report)"""
    for path in paths:
        chk = json.load(open(path))
        for gun, r in chk.items():
            if r.get("ok") or "tik" not in r:
                continue
            a = prev_report.get(r["tik"])
            if isinstance(a, dict):
                AVOID.setdefault(r["tik"], []).append((np.array(a["o"]), a["width"] * 0.5))


def main():
    cams = load_cams(opt("--cams"))
    for k in cams:
        cams[k]["tik"] = k
    if opt("--avoid"):
        prev = json.load(open(opt("--report"))) if opt("--report") and os.path.exists(opt("--report")) else {}
        load_avoid(opt("--avoid").split(","), prev)
        # keep the earlier results for guns not re-solved
        if prev:
            globals()["_PREV_REPORT"] = prev
    only = [a.lower() for a in sys.argv[sys.argv.index("--only") + 1:]] if "--only" in sys.argv else None
    report = dict(globals().get("_PREV_REPORT", {}))
    for tik, cam in sorted(cams.items()):
        if only and tik not in only:
            continue
        try:
            r, why = solve(tik, cam)
        except Exception as e:
            r, why = None, "error: %s" % e
        report[tik] = why if not r else dict(o=r["o"].round(3).tolist(), u=r["u"].round(4).tolist(), v=r["v"].round(4).tolist(),
                                             width=round(r["width"], 3), material=r["material"], surface=r["surface"],
                                             screen=round(r["screen"], 5), facing=round(r["facing"], 3), text_h=round(r["text_h"], 4),
                                             tilt=round(r["tilt"], 1), lines=r["lines"], letter_px=round(r["letter_px"], 1),
                                             **spot_fields(r),
                                             spots={k: dict(o=c["o"].round(3).tolist(), u=c["u"].round(4).tolist(), v=c["v"].round(4).tolist(),
                                                            width=round(c["width"], 3), material=c["material"], lines=c["lines"],
                                                            letter_px=round(c["letter_px"], 1), **spot_fields(c))
                                                    for k, c in r.get("spots", {}).items()})
        print(tik, report[tik] if not r else (r["surface"], r["material"], "w %.2f" % r["width"], "lines %d" % r["lines"], "letters %.0f px" % r["letter_px"],
                                                              "facing %.2f" % r["facing"], "tilt %.0f" % r["tilt"], "" if r["letter_px"] >= LETTER_PX_GOAL else "BELOW GOAL"))
    if opt("--report"):
        json.dump(report, open(opt("--report"), "w"), indent=1)
    if opt("--mod"):
        write_table(report, opt("--mod"))


_MESHKEY = None


def variants_of(tik):
    """every weapon tik that draws the same mesh (finish variants: _gold, _camo_*, named skins)"""
    global _MESHKEY
    if _MESHKEY is None:
        _MESHKEY = {}
        for k in gunmesh.vfs.index():
            if k.startswith("models/weapons/") and k.endswith(".tik"):
                t = gunmesh.read_tik(k)
                if t:
                    _MESHKEY.setdefault((t["path"].lower(), (t["skelmodel"] or "").lower()), []).append(k)
    base = gunmesh.read_tik(tik)
    key = (base["path"].lower(), (base["skelmodel"] or "").lower())
    return sorted(set(_MESHKEY.get(key, [])) | {tik.lower()})


def spot_fields(c):
    return dict(sq=round(float(c.get("sq", 0)), 3), du0=round(float(c.get("du0", 0)), 3), du1=round(float(c.get("du1", 0)), 3),
                dv0=round(float(c.get("dv0", 0)), 3), dv1=round(float(c.get("dv1", 0)), 3))


def spot_line(key, name, r):
    return "spot %s %s %s %s %s %.3f %s %d %.3f %.3f %.3f %.3f %.3f" % (
        key, name, " ".join("%.3f" % x for x in r["o"]), " ".join("%.4f" % x for x in r["u"]), " ".join("%.4f" % x for x in r["v"]),
        r["width"], r["material"], r["lines"], r.get("sq", 0), r.get("du0", 0), r.get("du1", 0), r.get("dv0", 0), r.get("dv1", 0))


def write_table(report, mod):
    L = ["// GENERATED by docs/tools/engrave/gen_engrave_anchors.py - do not hand-edit. Where the personal engraving sits",
         "// on each gun (cgame/cg_engrave.c): anchor <key> o(3) u(3) v(3) width wood|metal lines ; use <tiki> <key>",
         "// spot <key> <name> o(3) u(3) v(3) width wood|metal lines sq du0 du1 dv0 dv1 (Customize bench, qcommon/hzm_engrave_table.h)"]
    uses = []
    for tik, r in sorted(report.items()):
        if not isinstance(r, dict):
            continue
        key = os.path.splitext(os.path.basename(tik))[0]
        L.append("anchor %s %s %s %s %.3f %s %d" % (key, " ".join("%.3f" % x for x in r["o"]), " ".join("%.4f" % x for x in r["u"]),
                                                   " ".join("%.4f" % x for x in r["v"]), r["width"], r["material"], r["lines"]))
        if "sq" in r:
            L.append(spot_line(key, "engrave", r))
        for nm, c in sorted(r.get("spots", {}).items()):
            L.append(spot_line(key, nm, c))
        for t in variants_of(tik):
            uses.append("use %s %s" % (t, key))
    out = os.path.join(mod, "scripts", "hzm_engrave_anchors.txt")
    open(out, "w", newline="\n").write("\n".join(L + uses) + "\n")
    print("wrote", out, len(uses), "guns")


if __name__ == "__main__":
    main()
