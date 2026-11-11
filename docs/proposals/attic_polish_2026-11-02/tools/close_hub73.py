"""close_hub73.py <menus pak> <add dir> - v1.10.73: close the MP room so no camera stop, turn or aspect sees the void.

User (v1.10.72 live): "when you look left to the weapons rack you can see where the wall simply ends and you see out of bounds".
The hub (make_mphub3d.py) was baked as a corner room with NO FRONT: walls, ceiling and floor stop at x = -78.8, 8 u behind the
home camera (x -70.9). The 21:9 rack turn (yaw 42.35 + a 53 deg half-fov) and the 21:9 NOTICES view (yaw -90, its right edge at
-143 deg) look back past that plane (voidtrace.py: the whole left column of the 21:9 rack view is void).

hzm_hub_close: the room continued 120 u back from the front plane and capped there.
  * left wall / right wall / ceiling: each surface's own baked texels sampled on a line just inside the front edge (rays cast at
    the room's triangles, uv interpolated on the hit) and carried back unchanged along x - the dado, rail, plaster, beams and the
    lamp falloff continue as they are at the edge (texels smeared along the depth axis only)
  * floor: its planar uvs extrapolated linearly (the boards run on; the lightmap stage clamps to its edge)
  * front wall at x -198.8: the left wall's vertical profile (dado, rail, plaster) across the room's width
Same shaders as the room (hzm_hub_bg / hzm_hub_floor). The seam overlaps 1.5 u into the room (no crack, no z-fight: coplanar with
the walls it continues, same texels).
"""
import os, re, sys, zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402

pak, add = sys.argv[1:3]
Z = zipfile.ZipFile(pak)
mdir = os.path.join(add, "models", "menu")
os.makedirs(mdir, exist_ok=True)
XF, EXT, OVER = -78.8, 120.0, 1.5
XB = XF - EXT
HOME = np.array([-70.9, 15.8, 86.6])

TRI, UV, SH = [], [], []
for nm in ("hub_bg1", "hub_bg2", "hub_floor1"):
    tik = Z.read("models/menu/%s.tik" % nm).decode()
    shmap = dict(re.findall(r"(?m)^\s*surface (\S+) shader (\S+)", tik))
    m = R.read_skd(Z.read("models/menu/%s.skd" % nm))
    for s in m["surfaces"]:
        P = np.array([v[3] for v in s["verts"]], np.float64)
        U = np.array([v[1] for v in s["verts"]], np.float64)
        TRI.append(P[s["tris"]])
        UV.append(U[s["tris"]])
        SH += [shmap.get(s["name"], shmap.get("*", "hzm_hub_bg"))] * len(s["tris"])
TRI, UV, SH = np.concatenate(TRI), np.concatenate(UV), np.array(SH)


def cast(o, d):
    """nearest hit: (point, uv, shader) or None"""
    o, d = np.asarray(o, float), np.asarray(d, float)
    v0, e1, e2 = TRI[:, 0], TRI[:, 1] - TRI[:, 0], TRI[:, 2] - TRI[:, 0]
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


XS = XF + 3.0
NZ, NY = 28, 32
# the inner faces and the height at the front
L = [cast((XS, HOME[1], z), (0, 1, 0)) for z in np.linspace(0.6, 160.0, NZ)]
Rr = [cast((XS, HOME[1], z), (0, -1, 0)) for z in np.linspace(0.6, 160.0, NZ)]
assert all(L) and all(Rr), "a side-wall sample missed"
YL = float(np.median([h[0][1] for h in L]))
YR = float(np.median([h[0][1] for h in Rr]))
C = [cast((XS, y, 80.0), (0, 0, 1)) for y in np.linspace(YR + 0.5, YL - 0.5, NY)]
assert all(C), "a ceiling sample missed"
ZC = max(h[0][2] for h in C)
L = [cast((XS, HOME[1], z), (0, 1, 0)) for z in np.linspace(0.3, ZC - 0.3, NZ)]
Rr = [cast((XS, HOME[1], z), (0, -1, 0)) for z in np.linspace(0.3, ZC - 0.3, NZ)]
print("front: inner walls y %.1f / %.1f, ceiling up to z %.1f" % (YR, YL, ZC))

parts = {}


def quad(sh, p0, p1, p2, p3, u0, u1, u2, u3):
    for a, b, c in ((0, 1, 2), (0, 2, 3)):
        P_ = (p0, p1, p2, p3)
        U_ = (u0, u1, u2, u3)
        n = np.cross(np.subtract(P_[b], P_[a]), np.subtract(P_[c], P_[a]))
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        n = n / ln
        parts.setdefault(sh, []).append([(0, tuple(map(float, P_[k])), tuple(map(float, -n)), tuple(map(float, U_[k]))) for k in (a, b, c)])


X0, X1 = XB, XF + OVER
# side walls: rows of the sampled profile, carried along x
for hits, yw in ((L, YL), (Rr, YR)):
    for i in range(len(hits) - 1):
        (pa, ua, sa), (pb, ub, sb) = hits[i], hits[i + 1]
        za, zb = pa[2] if i else 0.0, pb[2] if i + 1 < len(hits) - 1 else ZC
        quad(sa, (X0, yw, za), (X1, yw, za), (X1, yw, zb), (X0, yw, zb), ua, ua, ub, ub)
# ceiling: the sampled line across y, carried along x, at each sample's own height (beams stay beams)
for i in range(len(C) - 1):
    (pa, ua, sa), (pb, ub, sb) = C[i], C[i + 1]
    ya, yb = (YR if i == 0 else pa[1]), (YL if i + 1 == len(C) - 1 else pb[1])
    quad(sa, (X0, ya, pa[2]), (X1, ya, pa[2]), (X1, yb, pb[2]), (X0, yb, pb[2]), ua, ua, ub, ub)
    if abs(pb[2] - pa[2]) > 0.5:          # a beam's side: close the step between two heights
        quad(sa, (X0, yb, pa[2]), (X1, yb, pa[2]), (X1, yb, pb[2]), (X0, yb, pb[2]), ub, ub, ub, ub)
# floor: planar uvs extrapolated (fit uv = A [x y 1] on the floor triangles near the front)
fl = (SH == "hzm_hub_floor") & (np.abs(TRI[:, :, 2]).max(1) < 0.05)
Pf, Uf = TRI[fl].reshape(-1, 3), UV[fl].reshape(-1, 2)
A = np.c_[Pf[:, 0], Pf[:, 1], np.ones(len(Pf))]
coef, *_ = np.linalg.lstsq(A, Uf, rcond=None)
res = np.abs(A @ coef - Uf).max()
assert res < 1e-3, "floor uvs are not planar (%.4f)" % res
fsh = SH[fl][0]
uvf = lambda x, y: tuple(np.array([x, y, 1.0]) @ coef)  # noqa: E731
YF0, YF1 = Pf[:, 1].min(), Pf[:, 1].max()
quad(fsh, (X0, YF0, 0.0), (X1, YF0, 0.0), (X1, YF1, 0.0), (X0, YF1, 0.0), uvf(X0, YF0), uvf(X1, YF0), uvf(X1, YF1), uvf(X0, YF1))
# the front wall: the left wall's vertical profile across the room
for i in range(len(L) - 1):
    (pa, ua, sa), (pb, ub, sb) = L[i], L[i + 1]
    za, zb = pa[2] if i else 0.0, pb[2] if i + 1 < len(L) - 1 else ZC
    quad(sa, (XB, YR - 1, za), (XB, YL + 1, za), (XB, YL + 1, zb), (XB, YR - 1, zb), ua, ua, ub, ub)

surfs, sl = [], []
for k, (sh, corners) in enumerate(sorted(parts.items())):
    ss = X.split_surfaces("c%d_" % k, corners)
    surfs += ss
    sl += ["\tsurface %s shader %s" % (q[0], sh) for q in ss]
assert len(surfs) <= 30
Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
nm = "hzm_hub_close"
open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                               (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                               float(np.linalg.norm(Pv, axis=1).max()) + 1))
open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))
print("%s: %d surfaces, %d tris, shaders %s" % (nm, len(surfs), sum(len(v) for v in parts.values()), sorted(parts)))
