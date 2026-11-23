#!/usr/bin/env python3
"""perchcheck - is an actor perch on a converted disc map real? (LOCAL ONLY, reads the player's pak, writes nothing in it)

Born of bug-11460 (Sealed Orders bridge snipers "floating/stuck in trees"): the old picker (flpolish walls/ridgefind.py)
judged a perch by COLLISION only, and treated every drawn triangle as an opaque wall. On a converted Frontline map the
collision mesh and the drawn mesh are separate, and the trees/bushes/wire are alpha cut-out cards with no collision at
all, so a perch could sit on a clip-only ledge with no drawn roof under it, or inside a tree canopy that collision
cannot see. This tool splits the drawn triangles into SOLID (opaque) and CUTOUT (alphaFunc shaders: foliage, tree
cards, wire, fences - read from the pak's own scripts/*.shader) and checks a perch against both.

  python perchcheck.py <pk3> <map> check  "x y z" ...           # report each perch
  python perchcheck.py <pk3> <map> pick   <cx> <cy> <cz> <x0> <y0> <x1> <y1> [--targets "x y z;x y z;..."]
                                                                   # candidate perches in a box, every check applied

A perch passes when, crouched (hull 54u) at the feet height collision gives:
  floor    - an OPAQUE drawn triangle lies within 8u of the feet at the centre and at least 3 of the 4 footprint
             corners (+-12u): the roof the player sees is really under him, not a clip shelf
  body     - no drawn triangle (opaque or cutout) passes through the actor's model box (+-12u, feet+18 .. feet+64;
             the bottom 18u is left to the roof slope under him): the
             model does not clip into a wall, a prop or a branch
  foliage  - no CUTOUT triangle within 40u of the body column up to feet+160 (not inside or under a canopy / bush)
  sight    - from the crouched eye (feet+44) at least N of the target points are reached through OPAQUE and CUTOUT
             triangles alike (a tree card hides the deck from a sniper as well as from the player)
  cover    - something drawn and opaque within 64u toward the target centre between knee and chest (feet+12..+36)
"""
import math
import re
import sys

import numpy as np

import os  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapgeo  # noqa: E402

CROUCH_EYE = 44.0
FOLIAGE_R, FOLIAGE_H = 40.0, 160.0      # the no-foliage column round a perch (half width, height over the feet)
BODY_TOP = 64.0


def cutout_shaders(M):
    """indices of shaders whose script carries alphaFunc (cut-out cards) in the pak's own scripts/*.shader"""
    cut = set()
    for n in M.files.values():
        if n.lower().startswith("scripts/") and n.lower().endswith(".shader"):
            t = M._z.read(n).decode("latin-1")
            for name, body in re.findall(r"^\s*(\S+)\s*\{(.*?)^\}", t, re.S | re.M):
                if re.search(r"alphaFunc", body, re.I):
                    cut.add(name.lower())
    return {i for i, s in enumerate(M.shaders) if s[0].lower() in cut}


class Split:
    """the drawn mesh split into opaque and cut-out triangle sets, each with its own grid"""

    def __init__(self, M):
        self.M = M
        cut = cutout_shaders(M)
        mask = np.array([int(s) in cut for s in M.rshader], bool)
        self.n_cut = int(mask.sum())
        self.sets = {}
        for k, m in (("solid", ~mask), ("cut", mask)):
            tri = np.ascontiguousarray(M.rtri[m]) if m.any() else np.zeros((1, 3, 3)) + 1e9
            g = mapgeo._grid(M.lo, M.hi, list(zip(tri.min(1), tri.max(1))))
            self.sets[k] = [tri, g, np.zeros(len(tri), np.int64)]
        self._stamp = 0

    def ray(self, k, a, b):
        tri, g, mark = self.sets[k]
        self._stamp += 1
        return mapgeo._ray_tris(tri, *g, np.asarray(a, np.float64), np.asarray(b, np.float64), mark, self._stamp)

    def box_hit(self, k, lo, hi):
        """does any triangle of set k cross the box? (segments through the box on a 4u lattice, 3 axes)"""
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        for ax in range(3):
            o = [i for i in range(3) if i != ax]
            for u in np.arange(lo[o[0]], hi[o[0]] + 0.1, 4.0):
                for v in np.arange(lo[o[1]], hi[o[1]] + 0.1, 4.0):
                    a = [0.0, 0.0, 0.0]
                    a[o[0]], a[o[1]], a[ax] = u, v, lo[ax]
                    b = list(a)
                    b[ax] = hi[ax]
                    if self.ray(k, a, b) < 1.0:
                        return True
        return False


def feet(M, x, y, z):
    """the collision floor the actor's origin rests on: a point trace from just above the given origin (a box trace
    starts solid on any sloped roof, the actor's own drop is a point-ish settle onto the surface under its origin)"""
    f, e, b, n, ss = M.trace((x, y, z + 16), (x, y, z - 64), (0, 0, 0), (0, 0, 0))
    if f >= 1.0 or b < 0:
        return None
    return float(e[2])


def check(S, p, targets, centre, need=4, fast=False):
    """every test on one perch; fast=True stops at the first failure (cheapest tests first) for the picker"""
    M = S.M
    x, y, z0 = p
    z = feet(M, x, y, z0)
    r = {"p": [x, y, z0], "feet": None if z is None else round(z, 1), "fail": []}

    def bad(msg):
        r["fail"].append(msg)
        r["ok"] = False
        return fast
    if z is None and bad("no collision floor") or z is None:
        return r
    # floor: opaque drawn triangle just under the feet
    under = []
    for dx, dy in ((0, 0), (12, 12), (12, -12), (-12, 12), (-12, -12)):
        h = 8 if (dx, dy) == (0, 0) else 20     # corners: a sloped roof drops/rises up to ~17u over 12u
        under.append(S.ray("solid", (x + dx, y + dy, z + h), (x + dx, y + dy, z - h)) < 1.0)
    r["floor"] = "".join("1" if u else "0" for u in under)
    if (not under[0] or sum(under[1:]) < 3) and bad("no drawn floor under the feet (%s)" % r["floor"]):
        return r
    # sight through opaque and cut-out alike
    eye = (x, y, z + CROUCH_EYE)
    vis = sum(1 for t in targets if S.ray("solid", eye, t) >= 1.0 and S.ray("cut", eye, t) >= 1.0)
    r["vis"] = vis
    if vis < need and bad("sees %d of %d targets" % (vis, len(targets))):
        return r
    # cover toward the centre: something opaque between knee and chest within 64u
    d = (centre[0] - x, centre[1] - y)
    L = math.hypot(*d) or 1.0
    ux, uy = d[0] / L, d[1] / L
    cov = min(S.ray("solid", (x, y, z + h), (x + ux * 64, y + uy * 64, z + h)) for h in (12, 24, 36))
    r["cover"] = None if cov >= 1.0 else round(64 * cov)
    if cov >= 1.0 and bad("no cover toward the target"):
        return r
    # body: the model box clear of anything drawn
    lo, hi = (x - 12, y - 12, z + 18), (x + 12, y + 12, z + BODY_TOP)
    if S.box_hit("solid", lo, hi) and bad("model box hits opaque geometry"):
        return r
    if S.box_hit("cut", lo, hi) and bad("model box inside foliage/cut-out"):
        return r
    # foliage column: nothing cut-out within 40u up to a canopy height
    fr, fh = FOLIAGE_R, FOLIAGE_H
    if S.box_hit("cut", (x - fr, y - fr, z + 6), (x + fr, y + fr, z + fh)) and bad("foliage within %du (canopy/bush)" % fr):
        return r
    # open sky above (roof) or a ceiling (inside)
    f2, e2, b2, n2, ss2 = M.trace((x, y, z + 80), (x, y, z + 4000), (0, 0, 0), (0, 0, 0))
    r["up"] = None if f2 >= 1.0 else round(e2[2] - z)
    r["ok"] = not r["fail"]
    return r


def _vec(s):
    return tuple(float(v) for v in s.replace(",", " ").split())


if __name__ == "__main__":
    pk3, mapname, mode = sys.argv[1:4]
    rest = sys.argv[4:]
    targets = None
    if "--targets" in rest:
        i = rest.index("--targets")
        targets = [_vec(t) for t in rest[i + 1].split(";")]
        rest = rest[:i] + rest[i + 2:]
    M = mapgeo.MapGeo.load(pk3, mapname)
    S = Split(M)
    print("cut-out triangles:", S.n_cut, "of", len(M.rtri))
    if mode == "check":
        cen = _vec(rest[0])
        targets = targets or [cen]
        for s in rest[1:]:
            print(check(S, _vec(s), targets, cen))
    elif mode == "pick":
        cx, cy, cz, x0, y0, x1, y1 = (float(v) for v in rest[:7])
        targets = targets or [(cx, cy, cz)]
        step = float(rest[7]) if len(rest) > 7 else 16.0
        out = []
        for x in np.arange(x0, x1 + 0.1, step):
            for y in np.arange(y0, y1 + 0.1, step):
                top = 1000.0
                for _l in range(4):
                    f, e, b, n, ss = M.trace((x, y, top), (x, y, -600), (0, 0, 0), (0, 0, 0))
                    if f >= 1 or b < 0:
                        break
                    zz = e[2]
                    top = zz - 8
                    if n[2] < 0.7:
                        continue
                    r = check(S, (float(x), float(y), float(zz)), targets, (cx, cy, cz), fast=True)
                    if r["ok"]:
                        out.append(r)
        out.sort(key=lambda r: (-r["vis"], r["cover"]))
        sel = []
        for r in out:   # one per 160u
            if all(math.hypot(r["p"][0] - s["p"][0], r["p"][1] - s["p"][1]) > 160 for s in sel):
                sel.append(r)
        for r in sel[:40]:
            print(r)
        print(len(out), "passing")
