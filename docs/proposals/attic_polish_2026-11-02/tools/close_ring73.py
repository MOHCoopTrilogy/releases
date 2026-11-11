"""close_ring73.py <menus pak> <add dir> <name> <xf> <ext> <seed y> <seed z> <shell model,...> [--axis -x|+x]
- v1.10.73: close a baked menu room's open end (any cross-section: vertical walls, sloped roofs, knee walls, beams).

From a seed point just inside the open plane x = xf, rays are cast round the room's cross-section (180 directions in the y-z
plane) at the room's own triangles; each hit carries its surface's uv and shader. That ring is extruded `ext` units out through
the open plane (each texel carried unchanged along x: walls, slopes, trims and lamp falloff continue as they are at the edge)
and capped at the far end in rows of z, each row spanning the ring with the texel of the ring's left side at that height.
The extension overlaps 1.5 u back into the room (coplanar with the faces it continues, same texels: no crack, no z-fight).
--axis -x (default): the room lies at x > xf and the extension goes to smaller x; +x the other way.
"""
import math, os, re, sys, zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

a = sys.argv[1:]
pak, add, NAME = a[0], a[1], a[2]
XF, EXT, SY, SZ = (float(v) for v in a[3:7])
SHELL = a[7].split(",")
SGN = 1.0 if "--axis" in a and a[a.index("--axis") + 1] == "+x" else -1.0
Z = zipfile.ZipFile(pak)
mdir = os.path.join(add, "models", "menu")
os.makedirs(mdir, exist_ok=True)

TRI, UV, SH = [], [], []
for nm in SHELL:
    tik = Z.read("models/menu/%s.tik" % nm).decode("latin-1")
    shmap = dict(re.findall(r"(?m)^\s*surface (\S+) shader (\S+)", tik))
    m = R.read_skd(Z.read("models/menu/%s.skd" % nm))
    for s in m["surfaces"]:
        P = np.array([v[3] for v in s["verts"]], np.float64)
        U = np.array([v[1] for v in s["verts"]], np.float64)
        TRI.append(P[s["tris"]])
        UV.append(U[s["tris"]])
        SH += [shmap.get(s["name"], "")] * len(s["tris"])
TRI, UV, SH = np.concatenate(TRI), np.concatenate(UV), np.array(SH)
v0, e1, e2 = TRI[:, 0], TRI[:, 1] - TRI[:, 0], TRI[:, 2] - TRI[:, 0]


def cast(o, d):
    o, d = np.asarray(o, float), np.asarray(d, float)
    p = np.cross(d, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = o - v0
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    v = (q * d).sum(1) * inv
    t = (e2 * q).sum(1) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.01)
    if not hit.any():
        return None
    t = np.where(hit, t, np.inf)
    j = int(t.argmin())
    w = np.array([1 - u[j] - v[j], u[j], v[j]])
    return o + d * t[j], (UV[j] * w[:, None]).sum(0), SH[j]


XS = XF - SGN * 3.0
ring = []
for k in range(180):
    ang = 2 * math.pi * k / 180
    h = cast((XS, SY, SZ), (0.0, math.cos(ang), math.sin(ang)))
    if h is None:
        raise SystemExit("ring ray %d (%.0f deg) escapes: the cross-section is open there" % (k, math.degrees(ang)))
    ring.append(h)
P = np.array([h[0] for h in ring])
print("%s: ring y %.1f..%.1f z %.1f..%.1f" % (NAME, P[:, 1].min(), P[:, 1].max(), P[:, 2].min(), P[:, 2].max()))
parts = {}


def tri(sh, p, u):
    n = np.cross(np.subtract(p[1], p[0]), np.subtract(p[2], p[0]))
    ln = np.linalg.norm(n)
    if ln < 1e-9:
        return
    n = n / ln
    parts.setdefault(sh, []).append([(0, tuple(map(float, p[k])), tuple(map(float, -n)), tuple(map(float, u[k]))) for k in range(3)])


X0, X1 = XF + SGN * EXT, XF - SGN * 1.5
# the floor is planar-mapped (its boards tile in world space): continue it with its own uvs instead of smearing its edge texels
# (in-game QA: the smeared floor read as a dark band of stretched wood at the left of the hatch view)
FLOOR_FIT = {}
for shf in set(SH.tolist()):
    sel = (SH == shf) & (np.abs(TRI[:, :, 2]).max(1) < 0.05)
    if sel.sum() >= 2:
        Pf, Uf = TRI[sel].reshape(-1, 3), UV[sel].reshape(-1, 2)
        Af = np.c_[Pf[:, 0], Pf[:, 1], np.ones(len(Pf))]
        cf, *_ = np.linalg.lstsq(Af, Uf, rcond=None)
        if np.abs(Af @ cf - Uf).max() < 1e-3:
            FLOOR_FIT[shf] = cf


def fuv(sh, p):
    return tuple(np.array([p[0], p[1], 1.0]) @ FLOOR_FIT[sh])


for i in range(len(ring)):
    (pa, ua, sa), (pb, ub, sb) = ring[i], ring[(i + 1) % len(ring)]
    A0, A1 = (X0, pa[1], pa[2]), (X1, pa[1], pa[2])
    B0, B1 = (X0, pb[1], pb[2]), (X1, pb[1], pb[2])
    if sa in FLOOR_FIT and sa == sb and abs(pa[2]) < 0.6 and abs(pb[2]) < 0.6:
        tri(sa, (A0, A1, B1), (fuv(sa, A0), fuv(sa, A1), fuv(sa, B1)))
        tri(sa, (A0, B1, B0), (fuv(sa, A0), fuv(sa, B1), fuv(sa, B0)))
        continue
    tri(sa, (A0, A1, B1), (ua, ua, ub))
    tri(sa, (A0, B1, B0), (ua, ub, ub))
# the cap: rows of z, from the ring's left (max y) point to its right (min y) point at that height
zs = np.linspace(P[:, 2].min(), P[:, 2].max(), 40)
for i in range(len(zs) - 1):
    za, zb = zs[i], zs[i + 1]
    zm = (za + zb) / 2
    span = []
    for k in range(len(ring)):
        p0, p1 = ring[k][0], ring[(k + 1) % len(ring)][0]
        if (p0[2] - zm) * (p1[2] - zm) <= 0 and p0[2] != p1[2]:
            f = (zm - p0[2]) / (p1[2] - p0[2])
            span.append((p0[1] + (p1[1] - p0[1]) * f, k))
    if len(span) < 2:
        continue
    yl, kl = max(span)
    yr, _ = min(span)
    pl, ul, sl = ring[kl]
    tri(sl, ((X0, yr, za), (X0, yl, za), (X0, yl, zb)), (ul, ul, ul))
    tri(sl, ((X0, yr, za), (X0, yl, zb), (X0, yr, zb)), (ul, ul, ul))

surfs, sl_ = [], []
for k, (sh, corners) in enumerate(sorted(parts.items())):
    ss = X.split_surfaces("c%d_" % k, corners)
    surfs += ss
    sl_ += ["\tsurface %s shader %s" % (q[0], sh) for q in ss]
assert len(surfs) <= 30, len(surfs)
Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
open(os.path.join(mdir, NAME + ".skd"), "wb").write(X.build_skd(NAME, [("root", "worldbone")], surfs))
open(os.path.join(mdir, NAME + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                 (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                 float(np.linalg.norm(Pv, axis=1).max()) + 1))
open(os.path.join(mdir, NAME + ".tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (NAME, "\n".join(sl_), NAME))
print("%s: %d surfaces, %d tris, shaders %s" % (NAME, len(surfs), sum(len(v) for v in parts.values()), sorted(parts)))
