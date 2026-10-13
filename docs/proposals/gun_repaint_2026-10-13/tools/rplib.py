"""Shared helpers of the gun repaint generators (silencer.py, greasegun.py, shotgun_top.py).

Mesh side: read a .skd (winning pak copy, or a file on disk), UV islands per surface, per-texel bake of position /
normal / island id, hard-edge masks (convex = worn, concave = dirt) - the MP18 skin's method, here for any sheet
size (W x H) and with every skd of a shared sheet baked together.
Paint side: seeded noise, gutter padding, DXT1 + full mips writer (weapon_hd's encoder), old | new sheet previews.
Nothing here writes outside this proposal folder.
"""
import os, sys, io
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PROP = os.path.abspath(os.path.join(HERE, ".."))
ASSETS = os.path.join(PROP, "assets")
EVI = os.path.join(PROP, "evidence")
WORK = os.path.join(PROP, "work")
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import skd      # noqa: E402
import vfs      # noqa: E402


def read_image(stem):
    """winning image of a texture stem as RGB float array + (vpath, pak)."""
    vp, w = vfs.resolve_image(stem)
    im = Image.open(io.BytesIO(vfs.read(vp))).convert("RGB")
    return np.asarray(im, np.float32), vp, os.path.basename(w[0])


def load_skd(src, surfaces=None):
    """src: vpath in the pak set, or a path on disk. -> {surface: dict(uv,pos,nrm,tris,isl,n)}"""
    data = open(src, "rb").read() if os.path.isfile(src) else vfs.read(src)
    m = skd.read(data)
    out = {}
    for s in m["surfaces"]:
        if surfaces and s["name"] not in surfaces:
            continue
        uv = np.array([v["uv"] for v in s["verts"]], float)
        pos = np.array([v["pos"] for v in s["verts"]], float)
        nrm = np.array([v["n"] for v in s["verts"]], float)
        tris = np.array(s["tris"], int)
        key = {}
        par = list(range(len(uv)))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for i, (u, v) in enumerate(uv):
            k = (round(u, 4), round(v, 4))
            if k in key:
                par[find(i)] = find(key[k])
            else:
                key[k] = i
        for t in tris:
            a, b, c = (find(int(x)) for x in t)
            par[b] = a; par[find(c)] = a
        roots = {}
        isl = np.zeros(len(tris), int)
        for ti, t in enumerate(tris):
            isl[ti] = roots.setdefault(find(int(t[0])), len(roots))
        bone = np.array([v["bone"] for v in s["verts"]], int)
        out[s["name"]] = dict(uv=uv, pos=pos, nrm=nrm, tris=tris, isl=isl, n=len(roots), bone=bone)
    return out


def island_rows(s):
    rows = []
    for k in range(s["n"]):
        tt = s["tris"][s["isl"] == k]
        vi = np.unique(tt)
        uv = s["uv"][vi]; p = s["pos"][vi]
        fn = np.cross(s["pos"][tt[:, 1]] - s["pos"][tt[:, 0]], s["pos"][tt[:, 2]] - s["pos"][tt[:, 0]])
        area = np.linalg.norm(fn, axis=1).sum() / 2
        mn = fn.sum(0); mn = mn / (np.linalg.norm(mn) + 1e-9)
        rows.append(dict(id=k, tris=len(tt), uv0=uv.min(0).round(3).tolist(), uv1=uv.max(0).round(3).tolist(),
                         p0=p.min(0).round(2).tolist(), p1=p.max(0).round(2).tolist(), area=round(float(area), 2),
                         n=mn.round(2).tolist()))
    return rows


def island_map(s, W, H, path, label=True, under=None):
    im = Image.new("RGB", (W, H), (20, 20, 20)) if under is None else under.resize((W, H), Image.LANCZOS).convert("RGB")
    d = ImageDraw.Draw(im)
    sz = np.array([W, H], float)
    for k in range(s["n"]):
        tt = s["tris"][s["isl"] == k]
        col = tuple(int(c) for c in np.random.RandomState(k * 7 + 3).randint(70, 255, 3))
        for t in tt:
            pts = [tuple(s["uv"][i] * sz) for i in t]
            if under is None:
                d.polygon(pts, fill=col, outline=(0, 0, 0))
            else:
                d.line(pts + [pts[0]], fill=col, width=1)
        if label:
            c = s["uv"][np.unique(tt)].mean(0) * sz
            d.text((c[0] - 6, c[1] - 6), str(k), fill=(0, 0, 0) if under is None else (255, 255, 0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return im


def noise(shape, sigma, seed):
    r = np.random.RandomState(seed).rand(*shape).astype(np.float32)
    g = ndi.gaussian_filter(r, sigma, mode="wrap")
    g -= g.mean(); g /= (g.std() + 1e-9)
    return g


def bake(s, W, H, wrap=False, want_tid=False):
    """texel -> (pos, normal, island id); island -1 where no triangle. wrap: UVs outside 0..1 are folded back.
    want_tid: also the index (into s["tris"]) of the triangle that wrote each texel."""
    pos = np.zeros((H, W, 3), np.float32); nrm = np.zeros((H, W, 3), np.float32)
    isl = -np.ones((H, W), np.int32)
    tid = -np.ones((H, W), np.int32) if want_tid else None
    uvp = s["uv"] * np.array([W, H], float)
    for ti, t in enumerate(s["tris"]):
        a, b, c = uvp[t]
        if wrap:
            sh = np.floor(np.array([min(a[0], b[0], c[0]) / W, min(a[1], b[1], c[1]) / H])) * np.array([W, H])
            a, b, c = a - sh, b - sh, c - sh
        x0 = max(0, int(np.floor(min(a[0], b[0], c[0])) - 1)); x1 = min(W, int(np.ceil(max(a[0], b[0], c[0])) + 2))
        y0 = max(0, int(np.floor(min(a[1], b[1], c[1])) - 1)); y1 = min(H, int(np.ceil(max(a[1], b[1], c[1])) + 2))
        if x1 <= x0 or y1 <= y0:
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -0.03) & (w1 >= -0.03) & (w2 >= -0.03)
        if not m.any():
            continue
        Wt = np.stack([w0, w1, w2], -1)[m]
        sub_p = pos[y0:y1, x0:x1]; sub_n = nrm[y0:y1, x0:x1]; sub_i = isl[y0:y1, x0:x1]
        sub_p[m] = Wt @ s["pos"][t]; sub_n[m] = Wt @ s["nrm"][t]; sub_i[m] = s["isl"][ti]
        if want_tid:
            tid[y0:y1, x0:x1][m] = ti
    l = np.linalg.norm(nrm, axis=2, keepdims=True)
    nrm = nrm / np.maximum(l, 1e-6)
    if want_tid:
        return pos, nrm, isl, tid
    return pos, nrm, isl


def hard_edge_points(s, deg=28, step=0.06):
    """sample points (3D) along the mesh's sharp edges: (convex, concave). Same edge test as edge_masks."""
    P = s["pos"]; T = s["tris"]
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    fn /= (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-9)
    vn = s["nrm"][T].mean(1)
    fn *= np.sign((fn * vn).sum(1, keepdims=True) + 1e-9)
    cen = P[T].mean(1)
    key = {}
    wid = np.zeros(len(P), int)
    for i, p in enumerate(P):
        wid[i] = key.setdefault(tuple(np.round(p, 2)), len(key))
    edges = {}
    for ti, t in enumerate(T):
        for k in range(3):
            i, j = int(t[k]), int(t[(k + 1) % 3])
            edges.setdefault(tuple(sorted((wid[i], wid[j]))), []).append((ti, i, j))
    out = ([], [])
    for e, lst in edges.items():
        if len(lst) != 2:
            continue
        (ta, ia, ja), (tb, ib, jb) = lst
        if float((fn[ta] * fn[tb]).sum()) > np.cos(np.radians(deg)):
            continue
        na = s["nrm"][ia] + s["nrm"][ja]; nb = s["nrm"][ib] + s["nrm"][jb]
        na /= (np.linalg.norm(na) + 1e-9); nb /= (np.linalg.norm(nb) + 1e-9)
        if float((na * nb).sum()) > np.cos(np.radians(20)):
            continue
        convex = float(((cen[tb] - cen[ta]) * fn[ta]).sum()) < 0
        a, b = P[ia], P[ja]
        n = max(2, int(np.linalg.norm(b - a) / step) + 1)
        w = np.linspace(0, 1, n)[:, None]
        out[0 if convex else 1].append(a[None] * (1 - w) + b[None] * w)
    cv = np.concatenate(out[0]) if out[0] else np.zeros((0, 3))
    cc = np.concatenate(out[1]) if out[1] else np.zeros((0, 3))
    return cv, cc


def vnoise3(P, seed):
    """value noise on the integer lattice of P (n,3) -> (n,) in 0..1. Solid: no UV stretch can smear it."""
    i = np.floor(P).astype(np.int64); f = (P - i).astype(np.float32)
    f = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        n = ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 1442695041
        n = (n ^ (n >> 13)) * 1274126177
        n = n ^ (n >> 16)
        return (n & 0xffff).astype(np.float32) / 65535.0
    x0, y0, z0 = i[:, 0], i[:, 1], i[:, 2]
    c = [[[h(x0 + a, y0 + b, z0 + c_) for c_ in (0, 1)] for b in (0, 1)] for a in (0, 1)]
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    x00 = c[0][0][0] * (1 - fx) + c[1][0][0] * fx; x01 = c[0][0][1] * (1 - fx) + c[1][0][1] * fx
    x10 = c[0][1][0] * (1 - fx) + c[1][1][0] * fx; x11 = c[0][1][1] * (1 - fx) + c[1][1][1] * fx
    y0_ = x00 * (1 - fy) + x10 * fy; y1_ = x01 * (1 - fy) + x11 * fy
    return y0_ * (1 - fz) + y1_ * fz


def fbm3(P, freq, octaves, seed, dmin=None, lac=2.0, gain=0.55, floor=0.0):
    """sum of octaves, zero mean, about unit range. dmin (px per unit on the texel's coarse axis): an octave whose
    wavelength falls under ~3 texels there is faded out (to `floor`) instead of being smeared."""
    out = np.zeros(len(P), np.float32); amp = 1.0; tot = 0.0; f = float(freq)
    for o in range(octaves):
        n = vnoise3(P * f + 17.3 * o, seed + o) - 0.5
        if dmin is not None:
            w = np.clip(dmin / (3.0 * f), floor, 1.0)
            n = n * w
        out += amp * n; tot += amp
        amp *= gain; f *= lac
    return out / tot * 2.0


def edge_masks(s, W, H, deg=28, width=None):
    """(convex, concave) masks in UV space from the mesh's sharp edges (dihedral > deg), welded by position."""
    P = s["pos"]; T = s["tris"]
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    fn /= (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-9)
    vn = s["nrm"][T].mean(1)
    fn *= np.sign((fn * vn).sum(1, keepdims=True) + 1e-9)
    cen = P[T].mean(1)
    key = {}
    wid = np.zeros(len(P), int)
    for i, p in enumerate(P):
        wid[i] = key.setdefault(tuple(np.round(p, 2)), len(key))
    edges = {}
    for ti, t in enumerate(T):
        for k in range(3):
            i, j = int(t[k]), int(t[(k + 1) % 3])
            edges.setdefault(tuple(sorted((wid[i], wid[j]))), []).append((ti, i, j))
    cv = Image.new("L", (W, H), 0); cc = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(cv); dc = ImageDraw.Draw(cc)
    uvp = s["uv"] * np.array([W, H], float)
    wd = width or max(2, max(W, H) // 512)
    for e, lst in edges.items():
        if len(lst) != 2:
            continue
        (ta, ia, ja), (tb, ib, jb) = lst
        d = float((fn[ta] * fn[tb]).sum())
        if d > np.cos(np.radians(deg)):
            continue
        na = s["nrm"][ia] + s["nrm"][ja]; nb = s["nrm"][ib] + s["nrm"][jb]
        na /= (np.linalg.norm(na) + 1e-9); nb /= (np.linalg.norm(nb) + 1e-9)
        if float((na * nb).sum()) > np.cos(np.radians(20)):
            continue
        convex = float(((cen[tb] - cen[ta]) * fn[ta]).sum()) < 0
        for (i, j) in ((ia, ja), (ib, jb)):
            (dv if convex else dc).line([tuple(uvp[i]), tuple(uvp[j])], fill=255, width=wd)
    return np.asarray(cv, np.float32) / 255, np.asarray(cc, np.float32) / 255


def pad(img, mask, px, fill=(30.0, 30.0, 31.0)):
    """bleed island colours into the gutters (mips): nearest covered texel; beyond px the flat fill."""
    dist, idx = ndi.distance_transform_edt(~mask, return_distances=True, return_indices=True)
    out = img[idx[0], idx[1]]
    if px is not None:
        far = dist > px
        out[far] = np.array(fill, np.float32)
    return out


def write_dds(arr, vpath):
    """DXT1 + full mips under assets/<vpath> (the .dds name wins over any .jpg / .tga of the same stem)."""
    import build_sheets as B
    a = np.clip(arr, 0, 255).astype(np.float64)
    assert a.shape[0] % 4 == 0 and a.shape[1] % 4 == 0
    data = B.encode_mipped(a)
    p = os.path.join(ASSETS, *vpath.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data)
    return p, len(data)


def dds_decode_top(path):
    """level 0 of a DXT1 dds back to RGB (to QA what the engine will actually sample)."""
    return np.asarray(Image.open(path).convert("RGB"), np.float32)


def side_by_side(old, new, path, h=768, labels=("today", "repaint")):
    o = Image.fromarray(np.clip(old, 0, 255).astype(np.uint8)); n = Image.fromarray(np.clip(new, 0, 255).astype(np.uint8))
    w = int(round(h * n.size[0] / n.size[1]))
    o = o.resize((w, h), Image.LANCZOS); n = n.resize((w, h), Image.LANCZOS)
    sh = Image.new("RGB", (2 * w + 8, h + 22), (255, 255, 255))
    sh.paste(o, (0, 22)); sh.paste(n, (w + 8, 22))
    d = ImageDraw.Draw(sh)
    d.text((4, 5), labels[0], fill=(0, 0, 0)); d.text((w + 12, 5), labels[1], fill=(0, 0, 0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sh.save(path, quality=90)
    return path
