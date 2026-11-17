"""[flguns] the disc gun's own sight points F / R, solved on the PLAYER's PC from the disc mesh and the ship-safe spec
table discguns_sights.json (boxes in fractions of the gun's own length - no disc coordinates).

Solve-only port of the private authoring tool discsights.py (H:\\hzm_work\\discguns; authoring views, check sheets and
OBJ reading stay private). The Gun is built straight from the flguns cut (parts: V metres bind pose, UV, T, tex) with
the same rounding the private OBJ export applied (%.5f), so F / R equal the private discsights_FR.json exactly
(proven 0.000000 m for the five batch-1 guns, p2\\fr_from_parts.py check).

Canonical gun frame: X lateral, Y forward (muzzle at +Y), Z up. Fractions (units of the gun length L along Y):
    a = (Ymuzzle - y) / L    0 at the muzzle, 1 at the butt
    s = (x - Xbore) / L      lateral, from the bore centre line at the muzzle
    h = (z - Zbore) / L      up, from the bore centre line at the muzzle
A box is [a0, a1, s0, s1, h0, h1]; "part" restricts it to surfaces whose texture name contains that text.
Feature types: tip, ring, lens, top, ears, overf, over, centroid, notch, point, level (see discsights.py)."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(getattr(sys, "_MEIPASS", None) or __file__))
SPECS = os.path.join(HERE, "discguns_sights.json")


def load_specs(path=None):
    return json.load(open(path or SPECS))


def _rot(axis, deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def _from_parts(disc):
    """-> (V, VT, surfs) exactly as the private OBJ round trip gave them (V, UV at 5 decimals; UV v kept as written
    by fl_gunpart: the OBJ stored 1 - v and the reader flipped it back)"""
    V, VT, surfs = [], [], {}
    for p in disc["parts"]:
        base = len(V)
        V += np.round(np.asarray(p["V"], float), 5).tolist()
        VT += [[float(u), float(v)] for u, v in np.round(np.asarray(p["UV"], float), 5)]
        surfs.setdefault(p["tex"], []).extend((np.asarray(p["T"]) + base).tolist())
    return np.array(V), np.array(VT), surfs


class Gun:
    def __init__(self, key, disc, spec=None):
        spec = spec or {}
        self.key = key
        V, VT, surfs = _from_parts(disc)
        M = np.eye(3)
        for ax, deg in spec.get("rot", []):
            M = _rot(ax, deg) @ M
        V = V @ M.T
        if spec.get("align") == "yaw":     # the disc mesh is yawed in its own frame (FL Springfield): bore -> the y axis
            c = V.mean(0)
            w, v = np.linalg.eigh(np.cov((V - c).T))
            ax = v[:, -1]
            Rz = _rot("z", np.degrees(np.arctan2(ax[0], ax[1])))
            V = V @ Rz.T
            M = Rz @ M
        lo, hi = V.min(0), V.max(0)
        L = hi[1] - lo[1]
        if "muzzle" in spec:
            muz_hi = spec["muzzle"] == "+y"
        else:
            a = V[V[:, 1] > hi[1] - 0.05 * L]
            b = V[V[:, 1] < lo[1] + 0.05 * L]
            spread = lambda P: np.ptp(P[:, 0]) + np.ptp(P[:, 2])
            muz_hi = spread(a) < spread(b)
        if spec.get("flip"):
            muz_hi = not muz_hi
        if not muz_hi:
            F = np.diag([-1.0, -1.0, 1.0])
            V = V @ F.T
            M = F @ M
        self.M = M                      # raw -> canonical
        self.V, self.VT, self.surfs = V, VT, surfs
        self.tex = disc.get("tex", {})
        lo, hi = V.min(0), V.max(0)
        self.L = hi[1] - lo[1]
        tip = V[V[:, 1] > hi[1] - 0.01 * self.L]
        self.O = np.array([np.median(tip[:, 0]), hi[1], (tip[:, 2].min() + tip[:, 2].max()) / 2])
        if "bore" in spec:              # explicit bore height/lateral at the muzzle (fractions) when the tip is odd
            self.O = self.O + np.array([spec["bore"][0], 0, spec["bore"][1]]) * self.L
        self.punched = {}

    def to_m(self, f):
        a, s, h = f
        return self.O + np.array([s, -a, h]) * self.L

    def to_f(self, p):
        d = (np.asarray(p) - self.O) / self.L
        return np.array([-d[1], d[0], d[2]])

    def box_verts(self, box, part=None):
        a0, a1, s0, s1, h0, h1 = box
        out = []
        for k, t in self.surfs.items():
            if part and part.lower() not in k.lower():
                continue
            idx = np.unique(np.array(t).ravel())
            F = np.array([self.to_f(p) for p in self.V[idx]]) if len(idx) else np.zeros((0, 3))
            m = (F[:, 0] >= a0) & (F[:, 0] <= a1) & (F[:, 1] >= s0) & (F[:, 1] <= s1) & (F[:, 2] >= h0) & (F[:, 2] <= h1)
            out.append(self.V[idx][m])
        return np.vstack(out) if out else np.zeros((0, 3))

    def feature(self, fs):
        typ = fs["type"]
        if typ == "point":
            return self.to_m(fs["p"])
        if typ == "level":
            return self.O.copy()      # placeholder: solve() places it from F
        P = self.box_verts(fs["box"], fs.get("part"))
        if len(P) == 0:
            raise RuntimeError("%s: empty box %s" % (self.key, fs))
        z = P[:, 2]
        if typ in ("tip", "apex"):
            tol = fs.get("tol", 0.001) * self.L if typ == "tip" else 1e-6
            p = P[z >= z.max() - tol].mean(0)
        elif typ == "ring":
            lo, hi = P.min(0), P.max(0)
            p = (lo + hi) / 2
            p[1] = P[:, 1].mean()
        elif typ == "lens":
            P = P[P[:, 1] <= P[:, 1].min() + fs.get("slice", 0.003) * self.L]
            lo, hi = P.min(0), P.max(0)
            p = (lo + hi) / 2
            p[1] = P[:, 1].min()
            self.lens_r = float((hi[0] - lo[0] + hi[2] - lo[2]) / 4)    # the ocular's mean half-size (lens disc)
        elif typ == "top":
            lo, hi = P.min(0), P.max(0)
            p = P[z >= z.max() - fs.get("tol", 0.0003) * self.L].mean(0)
            p[0] = (lo[0] + hi[0]) / 2
        elif typ == "ears":
            lo, hi = P.min(0), P.max(0)
            p = (lo + hi) / 2
            p[1] = P[:, 1].mean()
        elif typ == "overf":
            p = P[np.argmax(P[:, 2])].copy()
            p[1] = P[:, 1].max()
            p[0] = self.O[0]
            p[2] = P[:, 2].max() + fs.get("dh", 0.001) * self.L
        elif typ == "over":
            p = P[np.argmax(P[:, 2])].copy()
            p[1] = P[:, 1].min()
            p[0] = self.O[0]
            p[2] = P[:, 2].max() + fs.get("dh", 0.001) * self.L
        elif typ == "centroid":
            p = P.mean(0)
        elif typ == "notch":
            xs = np.sort(P[:, 0])
            gap = np.argmax(np.diff(xs))
            xc = (xs[gap] + xs[gap + 1]) / 2
            tops = []
            for E in (P[P[:, 0] < xc], P[P[:, 0] >= xc]):
                if len(E):
                    tops.append(E[E[:, 2] >= E[:, 2].max() - 0.002 * self.L].mean(0))
            p = np.mean(tops, axis=0)
            p[0] = xc
            if fs.get("sym"):
                p[0] = (P[:, 0].min() + P[:, 0].max()) / 2
        else:
            raise ValueError(typ)
        if "offset" in fs:
            p = p + np.array([fs["offset"][1], -fs["offset"][0], fs["offset"][2]]) * self.L
        return p

    def punch(self, R, ps):
        """A peep aperture the disc only PAINTED: {tex name: UV-space bool mask} of the texels of the triangles inside
        ps["box"] whose 3D point lies within ps["r"] * L of the bore-parallel line through R. The fit stage clears
        their alpha (and the upscale applies the same mask)."""
        r = ps["r"] * self.L
        masks = {}
        for k, t in self.surfs.items():
            if k not in self.tex:
                continue
            Ww, Hh = self.tex[k][0], self.tex[k][1]
            T = np.array(t)
            F = np.array([[self.to_f(self.V[i]) for i in tri] for tri in T])
            a0, a1, s0, s1, h0, h1 = ps["box"]
            inb = ((F[..., 0] >= a0) & (F[..., 0] <= a1) & (F[..., 1] >= s0) & (F[..., 1] <= s1) & (F[..., 2] >= h0)
                   & (F[..., 2] <= h1)).all(1)
            hit = np.zeros((Hh, Ww), bool)
            for tri in T[inb]:
                uv = self.VT[tri] * [Ww, Hh]
                P = self.V[tri]
                x0, x1 = int(np.floor(uv[:, 0].min())), int(np.ceil(uv[:, 0].max()))
                y0, y1 = int(np.floor(uv[:, 1].min())), int(np.ceil(uv[:, 1].max()))
                gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
                Tm = np.array([[uv[1, 0] - uv[0, 0], uv[2, 0] - uv[0, 0]], [uv[1, 1] - uv[0, 1], uv[2, 1] - uv[0, 1]]])
                if abs(np.linalg.det(Tm)) < 1e-9:
                    continue
                lam = np.linalg.solve(Tm, np.stack([gx.ravel() - uv[0, 0], gy.ravel() - uv[0, 1]]))
                ok = (lam[0] >= -0.02) & (lam[1] >= -0.02) & (lam[0] + lam[1] <= 1.02)
                Q = P[0] + np.outer(lam[0], P[1] - P[0]) + np.outer(lam[1], P[2] - P[0])
                d = np.hypot(Q[:, 0] - R[0], Q[:, 2] - R[2])
                sel = ok & (d < r)
                xs = np.mod(gx.ravel()[sel].astype(int), Ww)
                ys = np.mod(gy.ravel()[sel].astype(int), Hh)
                hit[ys, xs] = True
            if hit.any():
                masks[k] = hit
        self.punched = masks
        return masks


def solve(gun, spec):
    """-> F, R (canonical metres)"""
    R = gun.feature(spec["rear"])
    if spec.get("kind") == "scope":
        F = R + np.array([0, 1.0, 0]) * 0.3       # gen_scope_rows rule: the scope axis = the bore, not the tube PCA
        if "tube" in spec:                          # tube axis = the objective's front-face centre - the ocular's
            T = gun.box_verts(spec["tube"]["box"], spec["tube"].get("part"))
            T = T[T[:, 1] >= T[:, 1].max() - spec["tube"].get("slice", 0.003) * gun.L]
            O = (T.min(0) + T.max(0)) / 2
            u = (O - R) / np.linalg.norm(O - R)
            gun.tube_off = (np.degrees(np.arctan2(u[2], u[1])), np.degrees(np.arctan2(u[0], u[1])))
            gun.objective = O
            if spec.get("axis", "tube") == "tube":
                F = R + u * 0.3
    else:
        F = gun.feature(spec["front"])
    if "punch" in spec:
        gun.punch(R, spec["punch"])
    if spec["rear"].get("s_from_front"):
        R = R.copy()
        R[0] = F[0]
    if spec["rear"]["type"] == "level":
        R = F + np.array([0, -(spec["rear"]["a"] - gun.to_f(F)[0]) * gun.L, 0])
    if spec["rear"]["type"] == "ears":
        R = R.copy()
        R[2] = F[2] + spec["rear"].get("dh", 0.0) * gun.L
    return F, R


def solve_key(key, disc, spec):
    """-> the per-gun record the fit reads (same shape as the private discsights_FR.json[key])"""
    g = Gun(key, disc, spec)
    if spec.get("kind") == "none":       # a grenade: no sight - only the canonical frame for the fit
        return {"F": None, "R": None, "kind": "none", "L": round(float(g.L), 4), "O": g.O.round(5).tolist(),
                "M": g.M.round(6).tolist(), "punch": {}, "lens_r": 0.0}
    F, R = solve(g, spec)
    return {"F": F.round(5).tolist(), "R": R.round(5).tolist(), "kind": spec.get("kind", "iron"), "L": round(float(g.L), 4),
            "O": g.O.round(5).tolist(), "M": g.M.round(6).tolist(), "punch": g.punched,
            "lens_r": round(float(getattr(g, "lens_r", 0.0)), 5)}
