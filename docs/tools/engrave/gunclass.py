"""gunclass.py - what every triangle of a gun IS: metal, wood, optic (a scope, its glass, its rings and mount) or hand.

The anchor solver (gen_engrave_anchors.py) never puts a spot on an optic triangle, and the Customize bench's free
placement (client/cl_engrave.cpp) refuses a click on one and takes wood / metal from the triangle it hit. Both read the
same answer: the solver calls classify() here, the bench reads the `tris` lines this writes into the anchor table.

An optic is found three ways, in this order:
  1. by name: the surface or its shader says scope / lens / glass / optic / eyering (a shader's "coop_<variant>_" prefix
     is not part of its name: coop_g98scope_g98_body is the rifle's body);
  2. by shader: a shader that only ever dresses optic-named surfaces on the guns that name their optics (weas, m1d2,
     carcano_scope) marks an unnamed surface on another gun (the silenced Nagant's scope is the surface "Weas");
  3. by geometry: a connected piece of mesh that holds a lens (it rings the glass), then every connected piece that lies
     inside the scope's own capsule (rings, turrets, the mount's feet) - the rifle's body never does, it is far bigger.

Triangles are numbered in skd order (surface by surface, as the engine loads them), so a (surface, triangle) the bench's
ray hits is the same index here.

    python docs/tools/engrave/gunclass.py --cams <cams.json> [--only <tik> ...] [--png <dir>]
"""
import io, json, math, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunmesh  # noqa: E402

OPTIC_WORDS = re.compile(r"scope|lens|glass|optic|eyering", re.I)
GLASS_WORDS = re.compile(r"lens|glass", re.I)
HAND_WORDS = re.compile(r"^(hands?|arms?|gloves?|sleeves?)\d*$", re.I)
METAL, WOOD, OPTIC, HAND = 0, 1, 2, 3
CODES = "mwoh"


def shader_word(sh):
    """the part of a shader's name that describes the part (a coop_<variant>_ prefix names the gun, not the part)"""
    sh = sh or ""
    m = re.match(r"(?i)coop_[^_]+_(.*)$", sh)
    return m.group(1) if m else sh


def named_optic(surf_name, shader):
    return bool(OPTIC_WORDS.search(surf_name) or OPTIC_WORDS.search(shader_word(shader)))


def named_glass(surf_name, shader):
    return bool(GLASS_WORDS.search(surf_name) or GLASS_WORDS.search(shader_word(shader)))


_SURFS = {}


def surf_names(tik):
    """[(surface name, shader)] of a tik's mesh without posing it"""
    if tik not in _SURFS:
        tk = gunmesh.read_tik(tik)
        out = []
        if tk and tk["skelmodel"]:
            b = gunmesh.vfs.read(gunmesh._join(tk["path"], tk["skelmodel"]))
            if b is not None:
                _bones, surfs = _skd_names(b)
                out = [(n, tk["surfaces"].get(n.lower(), "")) for n in surfs]
        _SURFS[tik] = out
    return _SURFS[tik]


def _skd_names(b):
    import struct
    nsurf, nbones, ofsb, ofss, ofse = struct.unpack_from("<5i", b, 72)
    names = []
    off = ofss
    for _ in range(nsurf):
        names.append(b[off + 4:off + 68].split(b"\0")[0].decode("latin-1"))
        off += struct.unpack_from("<8i", b, off + 68)[6]
    return None, names


_OPTIC_SHADERS = None


def optic_shaders(tiks):
    """shaders that dress only optic-named surfaces on the guns that name their optics"""
    global _OPTIC_SHADERS
    if _OPTIC_SHADERS is None:
        on, off = set(), set()
        for t in tiks:
            S = surf_names(t)
            if not any(OPTIC_WORDS.search(n) for n, _ in S):
                continue
            for n, sh in S:
                if not sh:
                    continue
                (on if OPTIC_WORDS.search(n) else off).add(sh.lower())
        _OPTIC_SHADERS = on - off
    return _OPTIC_SHADERS


_IMG = {}


def _image(tikdir, shader):
    import gen_engrave_anchors as G
    from PIL import Image
    img = G.shader_image(shader)
    stem = re.sub(r"\.(tga|jpg|dds|png)$", "", img, flags=re.I)
    key = (tikdir.lower(), stem.lower())
    if key not in _IMG:
        arr = None
        for cand in (stem, tikdir + "/" + stem):
            for ext in (".tga", ".jpg", ".png", ".dds"):
                b = gunmesh.vfs.read(cand + ext)
                if b:
                    try:
                        im = Image.open(io.BytesIO(b)).convert("RGB")
                    except Exception:
                        continue
                    if max(im.size) > 512:
                        im = im.resize((512, 512 * im.size[1] // im.size[0] or 1))
                    arr = np.asarray(im, float)
                    break
            if arr is not None:
                break
        _IMG[key] = arr
    return _IMG[key]


def is_wood(rgb):
    """brown: red over green over blue with some colour in it. Looser than the solver's own rule (gen_engrave_anchors
    .material, kept as it is so hand-checked spots do not change): dark walnut stocks (the Garand, the StG44) read as
    metal there, and a hand-placed carving on them got the bright steel cut"""
    r, g, b = rgb / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    return bool(r > g > b and (mx - mn) / (mx + 1e-6) > 0.22 and mx > 0.09 and (r - b) > 0.035)


def tri_material(tikdir, shader, uv3):
    """wood / metal for each triangle of a surface from its texture (uv3: (T, 3, 2), the corners' texture coordinates):
    four samples a triangle - its middle and a point towards each corner - and wood when at least two of them are (one
    sample in the middle of a long stock triangle lands on a dark streak as often as not)"""
    import gen_engrave_anchors as G
    arr = _image(tikdir, shader)
    out = np.full(len(uv3), METAL, np.uint8)
    if arr is None:
        return out
    h, w = arr.shape[:2]
    for k, tri in enumerate(uv3):
        mid = tri.mean(0)
        n = 0
        for u, v in [mid] + [mid * 0.4 + c * 0.6 for c in tri]:
            x, y = int((u % 1.0) * (w - 1)), int((v % 1.0) * (h - 1))
            box = arr[max(0, y - 3):y + 4, max(0, x - 3):x + 4].reshape(-1, 3)
            n += is_wood(box.mean(0))
        if n >= 2:
            out[k] = WOOD
    return out


def components(P, T):
    """connected pieces over welded vertices -> component id per triangle"""
    key = np.round(P / 0.01).astype(np.int64)
    _, vid = np.unique(key, axis=0, return_inverse=True)
    vid = vid.reshape(-1)
    parent = np.arange(vid.max() + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    tv = vid[T]
    for a, b, c in tv:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[rc] = ra
    root = np.array([find(a) for a in tv[:, 0]])
    _, comp = np.unique(root, return_inverse=True)
    return comp


LEARNED_SHADERS = set()   # shaders found (pass 1, every gun) to dress only optic triangles: see classify_all


def classify_all(meshes):
    """{tik: mesh} -> {tik: classify()}: pass 1 classifies every gun, then a shader whose triangles came out >= 90 % optic
    on the guns that have an optic marks its surfaces on every gun (the silenced Nagant's unnamed scope), pass 2"""
    tiks = sorted(meshes)
    out = {t: classify(t, meshes[t], tiks) for t in tiks}
    on, tot = {}, {}
    for t in tiks:
        C = out[t]
        if not (C["cls"] == OPTIC).any():
            continue
        for i, s in enumerate(meshes[t]["surfaces"]):
            sh = (s["shader"] or "").lower()
            sel = C["sot"] == i
            if sh and sel.any():
                tot[sh] = tot.get(sh, 0) + int(sel.sum())
                on[sh] = on.get(sh, 0) + int((C["cls"][sel] == OPTIC).sum())
    new = {sh for sh in tot if on[sh] >= 0.9 * tot[sh]} - LEARNED_SHADERS
    if new:
        LEARNED_SHADERS.update(new)
        out = {t: classify(t, meshes[t], tiks) for t in tiks}
    return out


def classify(tik, m, all_tiks=None):
    """m = gunmesh.load(...) -> dict(cls (T,) uint8 in skd order, why (T,) 0 none / 1 name / 2 shader / 3 geometry)"""
    S = m["surfaces"]
    allP = np.vstack([s["pos"] for s in S])
    offs = np.cumsum([0] + [len(s["pos"]) for s in S])
    T = np.vstack([s["tris"] + offs[i] for i, s in enumerate(S) if len(s["tris"])])
    sot = np.concatenate([np.full(len(s["tris"]), i) for i, s in enumerate(S)])
    cls = np.zeros(len(T), np.uint8)
    why = np.zeros(len(T), np.uint8)
    glass = np.zeros(len(T), bool)
    osh = optic_shaders(all_tiks or [tik])
    tikdir = os.path.dirname(tik)
    for i, s in enumerate(S):
        sel = sot == i
        if not sel.any():
            continue
        lt = s["tris"]
        cls[sel] = tri_material(tikdir, s["shader"] or s["name"], s["uv"][lt])
        if HAND_WORDS.match(s["name"]):
            cls[sel] = HAND
        elif named_optic(s["name"], s["shader"]):
            cls[sel], why[sel] = OPTIC, 1
            glass[sel] = named_glass(s["name"], s["shader"])
        elif s["shader"] and (s["shader"].lower() in osh or s["shader"].lower() in LEARNED_SHADERS):
            cls[sel], why[sel] = OPTIC, 2
    if (cls == OPTIC).any():
        a, b, c = allP[T[:, 0]], allP[T[:, 1]], allP[T[:, 2]]
        area = np.linalg.norm(np.cross(b - a, c - a), axis=1) * 0.5
        cen = (a + b + c) / 3.0
        comp = components(allP, T)
        total = area.sum()
        ncomp = comp.max() + 1
        carea = np.bincount(comp, area, ncomp)
        # 3a. the piece that holds a lens: it rings the glass (a tube mouth around each lens disc)
        if glass.any():
            gcomp = comp[glass]
            for g in np.unique(gcomp):
                gs = glass & (comp == g)
                c0 = (cen[gs] * area[gs][:, None]).sum(0) / area[gs].sum()
                rad = np.linalg.norm(allP[T[gs]].reshape(-1, 3) - c0, axis=1).max()
                # by vertex, not by middle: a tube's triangles run its whole length, their middles are far from the glass
                near = (np.linalg.norm(allP[T] - c0, axis=2).min(1) < rad * 1.5) & (cls != OPTIC)
                for k in np.unique(comp[near]):
                    if near[comp == k].sum() < 4:
                        continue
                    if carea[k] < 0.35 * total:
                        s2 = (comp == k) & (cls != OPTIC)
                        cls[s2], why[s2] = OPTIC, 3
                        continue
                    # the tube is welded to the rifle (the L42A1): walk from the glass along the mesh, staying inside the
                    # tube's radius about the lens's own axis - it ends where the tube ends, and never reaches the receiver
                    gn = np.cross(b[gs] - a[gs], c[gs] - a[gs]).sum(0)
                    if np.linalg.norm(gn) < 1e-9:
                        continue
                    gn /= np.linalg.norm(gn)
                    rel = allP - c0
                    vperp = np.linalg.norm(rel - np.outer(rel @ gn, gn), axis=1)
                    okt = (vperp[T] < rad * 1.7).all(1) & (comp == k)
                    front = near & okt
                    vmark = np.zeros(len(allP), bool)
                    seen = np.zeros(len(T), bool)
                    wkey = np.round(allP / 0.01).astype(np.int64)
                    _u, wv = np.unique(wkey, axis=0, return_inverse=True)
                    wv = wv.reshape(-1)
                    vm = np.zeros(wv.max() + 1, bool)
                    while front.any():
                        seen |= front
                        vm[wv[T[front]].reshape(-1)] = True
                        front = okt & ~seen & vm[wv[T]].any(1)
                    s2 = seen & (cls != OPTIC)
                    cls[s2], why[s2] = OPTIC, 3
        # 3b. everything that lies inside the scope's own capsule (rings, turrets, mount feet)
        o = cls == OPTIC
        pts = allP[T[o]].reshape(-1, 3)
        c0 = pts.mean(0)
        _w, V = np.linalg.eigh(np.cov((pts - c0).T))
        ax = V[:, 2]
        t = (pts - c0) @ ax
        perp = np.linalg.norm((pts - c0) - np.outer(t, ax), axis=1)
        # the tube's own radius (the 70th percentile: turrets and mount legs reach further and would swallow the bolt)
        r = float(np.percentile(perp, 70))
        t0, t1 = t.min() - 0.3, t.max() + 0.3
        if (t1 - t0) > 2.5 * r:        # a tube, not a lone lens disc
            ct = (cen - c0) @ ax
            cp = np.linalg.norm((cen - c0) - np.outer(ct, ax), axis=1)
            inside = (ct > t0) & (ct < t1) & (cp < r * 1.35)
            for k in range(ncomp):
                s2 = (comp == k) & ~o
                if s2.any() and carea[k] < 0.25 * total and area[s2 & inside].sum() >= 0.6 * area[s2].sum():
                    cls[s2], why[s2] = OPTIC, 3
            # small pieces that hug the scope (ring halves, mount feet): most of their vertices touch optic mesh
            o = cls == OPTIC
            ov = np.unique(np.round(allP[T[o]].reshape(-1, 3) / 0.25).astype(np.int64), axis=0)
            oset = set(map(tuple, ov))
            for k in range(ncomp):
                s2 = (comp == k) & ~o
                if not s2.any() or carea[k] >= 0.05 * total:
                    continue
                q = np.round(allP[np.unique(T[s2])] / 0.25).astype(np.int64)
                touch = sum(1 for x in q if any((x[0] + i, x[1] + j, x[2] + l) in oset for i in (-1, 0, 1) for j in (-1, 0, 1) for l in (-1, 0, 1)))
                if touch >= 0.5 * len(q):
                    cls[s2], why[s2] = OPTIC, 3
    return dict(cls=cls, why=why, P=allP, T=T, sot=sot)


def rle(cls):
    out, i, n = [], 0, len(cls)
    while i < n:
        j = i
        while j < n and cls[j] == cls[i]:
            j += 1
        out.append("%s%d" % (CODES[cls[i]], j - i))
        i = j
    return "".join(out)


def unrle(s):
    out = []
    for c, n in re.findall(r"([mwoh])(\d+)", s):
        out += [CODES.index(c)] * int(n)
    return np.array(out, np.uint8)


def tri_under(P, T, o, n, reach=0.6):
    """the triangle the point o lies ON: of the triangles a ray from o + n * reach along -n crosses, the one nearest o
    (not the first one: a scope floating a hair above a receiver is not what a quad on the receiver sits on).
    -> (index, distance from o along -n), or (-1, None)"""
    orig = np.asarray(o, float) + np.asarray(n, float) * reach
    d = -np.asarray(n, float)
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    e1, e2 = b - a, c - a
    pv = np.cross(d, e2)
    det = (e1 * pv).sum(1)
    ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
    tv = orig - a
    u = (tv * pv).sum(1) * inv
    qv = np.cross(tv, e1)
    v = (qv @ d) * inv
    t = (e2 * qv).sum(1) * inv
    hit = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (t > 1e-4) & (t < 2 * reach)
    if not hit.any():
        return -1, None
    k = np.nonzero(hit)[0]
    j = k[np.argmin(np.abs(t[k] - reach))]
    return int(j), float(t[j] - reach)


def quad_on_optic(C, o, u, v, width, aspect):
    """does any of 5 x 3 points of a quad lie on an optic triangle (or is the quad's middle off the mesh)?"""
    o, u, v = np.asarray(o, float), np.asarray(u, float), np.asarray(v, float)
    n = np.cross(u, v)
    h = width / aspect
    for a in (-1, -0.5, 0, 0.5, 1):
        for b in (-1, 0, 1):
            k, _d = tri_under(C["P"], C["T"], o + u * (a * width / 2 * 0.96) + v * (b * h / 2 * 0.96), n)
            if k >= 0 and C["cls"][k] == OPTIC:
                return True
    return False


def render(C, path, title=""):
    """side and top view, triangles coloured by class (QA of the classifier)"""
    from PIL import Image, ImageDraw
    P, T, cls, why = C["P"], C["T"], C["cls"], C["why"]
    ext = P.max(0) - P.min(0)
    order = np.argsort(-ext)          # long axis first
    L, A, B = order[0], order[1], order[2]
    W = 1100
    sc = (W - 40) / ext[L]
    col = {METAL: (120, 128, 140), WOOD: (150, 100, 55), HAND: (220, 170, 140)}
    ocol = {1: (255, 40, 200), 2: (255, 150, 0), 3: (60, 220, 255)}
    views = []
    for up, depth in ((B, A), (A, B)):
        H = int(ext[up] * sc) + 40
        im = Image.new("RGB", (W, H), (24, 24, 28))
        d = ImageDraw.Draw(im)
        z = P[T][:, :, depth].mean(1)
        for k in np.argsort(z):
            pts = [(20 + (P[i][L] - P.min(0)[L]) * sc, H - 20 - (P[i][up] - P.min(0)[up]) * sc) for i in T[k]]
            c = ocol[int(why[k]) or 1] if cls[k] == OPTIC else col[int(cls[k])]
            d.polygon(pts, fill=c, outline=tuple(int(x * 0.7) for x in c))
        views.append(im)
    out = Image.new("RGB", (W, sum(v.size[1] for v in views) + 18), (24, 24, 28))
    y = 18
    ImageDraw.Draw(out).text((6, 3), title + "   pink=optic by name  orange=by shader  cyan=by geometry  brown=wood", fill=(230, 230, 230))
    for v in views:
        out.paste(v, (0, y))
        y += v.size[1]
    out.save(path)


def main():
    import gen_engrave_anchors as G
    cams = G.load_cams(sys.argv[sys.argv.index("--cams") + 1])
    only = [a.lower() for a in sys.argv[sys.argv.index("--only") + 1:] if not a.startswith("--")] if "--only" in sys.argv else None
    png = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
    tiks = sorted(cams)
    meshes = {}
    for tik in tiks:
        m = gunmesh.load(tik, engine_bones=cams[tik].get("bones"))
        if m:
            meshes[tik] = m
        else:
            print(tik, "no mesh")
    ALL = classify_all(meshes)
    print("optic shaders:", sorted(optic_shaders(tiks) | LEARNED_SHADERS))
    for tik in sorted(meshes):
        if only and tik not in only:
            continue
        C = ALL[tik]
        n = np.bincount(C["cls"], minlength=4)
        w = np.bincount(C["why"][C["cls"] == OPTIC], minlength=4)
        if n[OPTIC] or only:
            print("%-46s tris %5d  wood %5d  optic %5d (name %d shader %d geometry %d)  rle %d chars" % (
                tik, len(C["cls"]), n[WOOD], n[OPTIC], w[1], w[2], w[3], len(rle(C["cls"]))))
            if png:
                os.makedirs(png, exist_ok=True)
                render(C, os.path.join(png, os.path.basename(tik)[:-4] + ".png"), os.path.basename(tik))


if __name__ == "__main__":
    main()
