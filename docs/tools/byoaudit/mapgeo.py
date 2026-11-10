#!/usr/bin/env python3
"""mapgeo - load a converted bring-your-own-disc map (our BSP v19 writer's output: Frontline and European Assault
converters, docs/tools/frontline/flbsp.py and docs/tools/ea/flbsp.py) straight out of its LOCAL pk3, and answer
geometry questions about it with the engine's own collision rules. Our code; reads the player's converted pak, writes
nothing into it.

  M = MapGeo.load(pk3, "coop_fl_1_1")
  M.trace(start, end, mins, maxs)  -> (fraction, endpos, brush, normal, startsolid)   (CM_BoxTrace rules, brushes only)
  M.render_ray(a, b)               -> fraction along a->b to the first DRAWN triangle (sky / nodraw excluded)
  M.render_near(p, r)              -> True when a drawn triangle passes within ~r of p (8u voxel occupancy)

Collision = every brush whose shader carries CONTENTS_SOLID or CONTENTS_PLAYERCLIP (the player's MASK_PLAYERSOLID).
Kernels are numba-compiled (dev tool only; never shipped in hzmconv).
"""
import math
import re
import struct
import zipfile

import numpy as np
from numba import njit

L_SHADERS, L_PLANES, L_SURFACES, L_DRAWVERTS, L_DRAWINDEXES = 0, 1, 3, 4, 5
L_BRUSHSIDES, L_BRUSHES, L_MODELS, L_ENTITIES = 11, 12, 13, 14
CONTENTS_SOLID, CONTENTS_PLAYERCLIP = 1, 0x10000
SURF_SKY, SURF_NODRAW = 0x4, 0x80
CELL = 64.0
VOX = 8.0

# player hulls (openmohaa-hzm/code/fgame/bg_pmove.cpp PM_CheckDuck, protocol >= MOHTA): x/y +-15, z from 0 to
STAND_H, CROUCH_H, PRONE_H = 94.0, 54.0, 20.0
STEP = 18.0             # STEPSIZE
HALF = 15.0


def parse_entities(text):
    ents = []
    for blk in re.findall(r"\{([^{}]*)\}", text):
        ents.append(dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', blk)))
    return ents


@njit(cache=True)
def _trace(planes, nsides, bmin, bmax, gstart, glist, gx0, gy0, gw, gh, start, end, mins, maxs, mark, stamp):
    """CM_TraceThroughBrush over the candidate brushes of the grid cells the swept box touches."""
    best = 1.0
    hitb = -1
    hn = np.zeros(3)
    startsolid = False
    lo0 = min(start[0], end[0]) + mins[0] - 1.0
    hi0 = max(start[0], end[0]) + maxs[0] + 1.0
    lo1 = min(start[1], end[1]) + mins[1] - 1.0
    hi1 = max(start[1], end[1]) + maxs[1] + 1.0
    lo2 = min(start[2], end[2]) + mins[2] - 1.0
    hi2 = max(start[2], end[2]) + maxs[2] + 1.0
    cx0 = max(0, int((lo0 - gx0) // CELL))
    cx1 = min(gw - 1, int((hi0 - gx0) // CELL))
    cy0 = max(0, int((lo1 - gy0) // CELL))
    cy1 = min(gh - 1, int((hi1 - gy0) // CELL))
    eps = 0.125
    for cx in range(cx0, cx1 + 1):
        for cy in range(cy0, cy1 + 1):
            c = cx * gh + cy
            for k in range(gstart[c], gstart[c + 1]):
                b = glist[k]
                if mark[b] == stamp:
                    continue
                mark[b] = stamp
                if bmax[b, 0] < lo0 or bmin[b, 0] > hi0 or bmax[b, 1] < lo1 or bmin[b, 1] > hi1 \
                        or bmax[b, 2] < lo2 or bmin[b, 2] > hi2:
                    continue
                enter = -1.0
                leave = 1.0
                getout = False
                startout = False
                en = np.zeros(3)
                miss = False
                for s in range(nsides[b]):
                    nx = planes[b, s, 0]
                    ny = planes[b, s, 1]
                    nz = planes[b, s, 2]
                    d = planes[b, s, 3]
                    # expand the plane by the box: the corner that reaches furthest against the normal
                    off = nx * (mins[0] if nx > 0 else maxs[0]) + ny * (mins[1] if ny > 0 else maxs[1]) \
                        + nz * (mins[2] if nz > 0 else maxs[2])
                    dd = d - off
                    d1 = nx * start[0] + ny * start[1] + nz * start[2] - dd
                    d2 = nx * end[0] + ny * end[1] + nz * end[2] - dd
                    if d2 > 0:
                        getout = True
                    if d1 > 0:
                        startout = True
                    if d1 > 0 and (d2 >= eps or d2 >= d1):
                        miss = True
                        break
                    if d1 <= 0 and d2 <= 0:
                        continue
                    if d1 > d2:
                        f = (d1 - eps) / (d1 - d2)
                        if f < 0:
                            f = 0.0
                        if f > enter:
                            enter = f
                            en[0] = nx
                            en[1] = ny
                            en[2] = nz
                    else:
                        f = (d1 + eps) / (d1 - d2)
                        if f > 1:
                            f = 1.0
                        if f < leave:
                            leave = f
                if miss:
                    continue
                if not startout:
                    startsolid = True
                    if not getout:
                        best = 0.0
                        hitb = b
                    continue
                if enter < leave and enter > -1 and enter < best:
                    if enter < 0:
                        enter = 0.0
                    best = enter
                    hitb = b
                    hn[0] = en[0]
                    hn[1] = en[1]
                    hn[2] = en[2]
    return best, hitb, hn, startsolid


@njit(cache=True)
def _ray_tris(tri, gstart, glist, gx0, gy0, gw, gh, a, b, mark, stamp):
    """Moeller-Trumbore, nearest drawn triangle along a->b (fraction)."""
    best = 1.0
    d0 = b[0] - a[0]
    d1 = b[1] - a[1]
    d2 = b[2] - a[2]
    # walk the cells the segment's bbox covers (segments are short in our use)
    cx0 = max(0, int((min(a[0], b[0]) - gx0) // CELL))
    cx1 = min(gw - 1, int((max(a[0], b[0]) - gx0) // CELL))
    cy0 = max(0, int((min(a[1], b[1]) - gy0) // CELL))
    cy1 = min(gh - 1, int((max(a[1], b[1]) - gy0) // CELL))
    for cx in range(cx0, cx1 + 1):
        for cy in range(cy0, cy1 + 1):
            c = cx * gh + cy
            for k in range(gstart[c], gstart[c + 1]):
                t = glist[k]
                if mark[t] == stamp:
                    continue
                mark[t] = stamp
                v0x, v0y, v0z = tri[t, 0, 0], tri[t, 0, 1], tri[t, 0, 2]
                e1x, e1y, e1z = tri[t, 1, 0] - v0x, tri[t, 1, 1] - v0y, tri[t, 1, 2] - v0z
                e2x, e2y, e2z = tri[t, 2, 0] - v0x, tri[t, 2, 1] - v0y, tri[t, 2, 2] - v0z
                px = d1 * e2z - d2 * e2y
                py = d2 * e2x - d0 * e2z
                pz = d0 * e2y - d1 * e2x
                det = e1x * px + e1y * py + e1z * pz
                if abs(det) < 1e-9:
                    continue
                inv = 1.0 / det
                tx, ty, tz = a[0] - v0x, a[1] - v0y, a[2] - v0z
                u = (tx * px + ty * py + tz * pz) * inv
                if u < 0 or u > 1:
                    continue
                qx = ty * e1z - tz * e1y
                qy = tz * e1x - tx * e1z
                qz = tx * e1y - ty * e1x
                v = (d0 * qx + d1 * qy + d2 * qz) * inv
                if v < 0 or u + v > 1:
                    continue
                f = (e2x * qx + e2y * qy + e2z * qz) * inv
                if 0 <= f < best:
                    best = f
    return best


def _grid(lo, hi, boxes):
    gx0, gy0 = lo[0] - CELL, lo[1] - CELL
    gw = int((hi[0] - gx0) // CELL) + 2
    gh = int((hi[1] - gy0) // CELL) + 2
    cells = [[] for _ in range(gw * gh)]
    for i, (bl, bh) in enumerate(boxes):
        for cx in range(max(0, int((bl[0] - gx0) // CELL)), min(gw - 1, int((bh[0] - gx0) // CELL)) + 1):
            for cy in range(max(0, int((bl[1] - gy0) // CELL)), min(gh - 1, int((bh[1] - gy0) // CELL)) + 1):
                cells[cx * gh + cy].append(i)
    gstart = np.zeros(gw * gh + 1, np.int64)
    for c in range(gw * gh):
        gstart[c + 1] = gstart[c] + len(cells[c])
    glist = np.array([i for c in cells for i in c], np.int64)
    return gstart, glist, gx0, gy0, gw, gh


class MapGeo:
    @classmethod
    def load(cls, pk3, mapname):
        z = zipfile.ZipFile(pk3)
        names = {n.lower(): n for n in z.namelist()}
        data = z.read(names[f"maps/{mapname}.bsp".lower()])
        m = cls()
        m.pk3, m.mapname = pk3, mapname
        m.files = names
        m._z = z
        m._parse(data)
        return m

    def read(self, name):
        n = self.files.get(name.lower())
        return self._z.read(n) if n else None

    def _parse(self, data):
        ident, ver, _ck = struct.unpack_from("<4sii", data, 0)
        lumps = [struct.unpack_from("<ii", data, 12 + 8 * i) for i in range(28)]

        def lump(i):
            o, l = lumps[i]
            return data[o:o + l]
        sh = lump(L_SHADERS)
        self.shaders = [(struct.unpack_from("<64s", sh, i)[0].split(b"\0")[0].decode("latin-1"),) +
                        struct.unpack_from("<II", sh, i + 64) for i in range(0, len(sh), 140)]
        pl = np.frombuffer(lump(L_PLANES), np.float32).reshape(-1, 4).astype(np.float64)
        bs = np.frombuffer(lump(L_BRUSHES), np.int32).reshape(-1, 3)
        sd = np.frombuffer(lump(L_BRUSHSIDES), np.int32).reshape(-1, 3)
        solid = [(cf & (CONTENTS_SOLID | CONTENTS_PLAYERCLIP)) != 0 for _n, _sf, cf in self.shaders]
        keep = [i for i in range(len(bs)) if solid[bs[i, 2]]]
        maxs = max(int(bs[i, 1]) for i in keep)
        self.bplanes = np.zeros((len(keep), maxs, 4))
        self.bnsides = np.zeros(len(keep), np.int64)
        self.bshader = np.zeros(len(keep), np.int64)
        for j, i in enumerate(keep):
            f, n, s = bs[i]
            self.bnsides[j] = n
            self.bshader[j] = s
            for k in range(n):
                self.bplanes[j, k] = pl[sd[f + k, 0]]
        # sides 0..5 are the axial bevels: -x,+x,-y,+y,-z,+z (flbsp.add_brush_planes / CM_BoundBrush)
        self.bmin = np.stack([-self.bplanes[:, 0, 3], -self.bplanes[:, 2, 3], -self.bplanes[:, 4, 3]], 1)
        self.bmax = np.stack([self.bplanes[:, 1, 3], self.bplanes[:, 3, 3], self.bplanes[:, 5, 3]], 1)
        # render triangles (every drawn surface; sky and nodraw excluded)
        srf = lump(L_SURFACES)
        dv = lump(L_DRAWVERTS)
        di = np.frombuffer(lump(L_DRAWINDEXES), np.int32)
        vstride = 4 * (3 + 2 + 2 + 3) + 4
        nv = len(dv) // vstride
        xyz = np.zeros((nv, 3))
        for i in range(nv):
            xyz[i] = struct.unpack_from("<3f", dv, i * vstride)
        tris, tsh = [], []
        ssz = struct.calcsize("<12i3f9f2if")
        for i in range(0, len(srf), ssz):
            s = struct.unpack_from("<12i", srf, i)
            shader, _fog, _typ, fv, nvv, fi, ni = s[:7]
            nm, sf, cf = self.shaders[shader]
            if sf & (SURF_SKY | SURF_NODRAW) or "/sky/" in nm:
                continue
            idx = di[fi:fi + ni] + fv
            t = xyz[idx].reshape(-1, 3, 3)
            tris.append(t)
            tsh += [shader] * len(t)
        self.rtri = np.concatenate(tris) if tris else np.zeros((0, 3, 3))
        self.rshader = np.array(tsh, np.int64)
        allp = self.rtri.reshape(-1, 3)
        lo = np.minimum(allp.min(0), self.bmin.min(0))
        hi = np.maximum(allp.max(0), self.bmax.max(0))
        self.lo, self.hi = lo, hi
        self.bg = _grid(lo, hi, list(zip(self.bmin, self.bmax)))
        self.rg = _grid(lo, hi, list(zip(self.rtri.min(1), self.rtri.max(1))))
        self._bmark = np.zeros(len(self.bnsides), np.int64)
        self._rmark = np.zeros(len(self.rtri), np.int64)
        self._stamp = 0
        el = lump(L_ENTITIES).split(b"\0")[0].decode("latin-1")
        self.entities = parse_entities(el)
        # the map's own step height (converted maps: worldspawn "hzm_stepsize", HZM engine sv_stepSize), else STEPSIZE
        ws = next((e for e in self.entities if e.get("classname") == "worldspawn"), {})
        self.step = float(ws.get("hzm_stepsize", 0) or 0) or STEP
        self._vox = None

    # -------------------------------------------------------------- queries
    def trace(self, start, end, mins, maxs):
        self._stamp += 1
        s = np.asarray(start, np.float64)
        e = np.asarray(end, np.float64)
        f, b, n, ss = _trace(self.bplanes, self.bnsides, self.bmin, self.bmax, *self.bg, s, e,
                             np.asarray(mins, np.float64), np.asarray(maxs, np.float64), self._bmark, self._stamp)
        return f, s + (e - s) * f, b, n, ss

    def hull(self, h):
        return (-HALF, -HALF, 0.0), (HALF, HALF, h)

    def render_ray(self, a, b):
        self._stamp += 1
        return _ray_tris(self.rtri, *self.rg, np.asarray(a, np.float64), np.asarray(b, np.float64), self._rmark,
                         self._stamp)

    def voxels(self):
        """8u occupancy of every drawn triangle (sampled at 4u)"""
        if self._vox is None:
            occ = set()
            for a, b, c in self.rtri:
                e1, e2 = b - a, c - a
                n1 = max(1, int(math.ceil(np.linalg.norm(e1) / 4.0)))
                n2 = max(1, int(math.ceil(np.linalg.norm(e2) / 4.0)))
                u, v = np.meshgrid(np.arange(n1 + 1) / n1, np.arange(n2 + 1) / n2)
                u, v = u.ravel(), v.ravel()
                k = u + v <= 1.0
                p = a + np.outer(u[k], e1) + np.outer(v[k], e2)
                occ.update(map(tuple, np.floor(p / VOX).astype(np.int64).tolist()))
            self._vox = occ
        return self._vox

    def render_near(self, p, r=8.0):
        occ = self.voxels()
        k = [int(math.floor(x / VOX)) for x in p]
        n = int(math.ceil(r / VOX))
        for dx in range(-n, n + 1):
            for dy in range(-n, n + 1):
                for dz in range(-n, n + 1):
                    if (k[0] + dx, k[1] + dy, k[2] + dz) in occ:
                        return True
        return False

    def ground(self, x, y, ztop, zbot, h=STAND_H):
        """feet height of a player box dropped from ztop (None = nothing to stand on above zbot, or starts in solid)"""
        mins, maxs = self.hull(h)
        f, end, b, n, ss = self.trace((x, y, ztop), (x, y, zbot), mins, maxs)
        if ss or f >= 1.0:
            return None, n, b
        return end[2], n, b


@njit(cache=True)
def _cast_many(tri, gstart, glist, gx0, gy0, gw, gh, origins, dirs, maxd, mark):
    """nearest drawn-triangle distance for each (origin, dir) ray up to maxd (-1 = nothing): a 2D DDA over the
    64u grid so a long ray only tests the cells it crosses"""
    n = origins.shape[0]
    out = np.full(n, -1.0)
    stamp = 0
    for r in range(n):
        stamp += 1
        ox, oy, oz = origins[r, 0], origins[r, 1], origins[r, 2]
        dx, dy, dz = dirs[r, 0], dirs[r, 1], dirs[r, 2]
        best = maxd
        cx = int((ox - gx0) // CELL)
        cy = int((oy - gy0) // CELL)
        stepx = 1 if dx > 0 else -1
        stepy = 1 if dy > 0 else -1
        tdx = CELL / abs(dx) if abs(dx) > 1e-9 else 1e30
        tdy = CELL / abs(dy) if abs(dy) > 1e-9 else 1e30
        nbx = gx0 + (cx + (1 if dx > 0 else 0)) * CELL
        nby = gy0 + (cy + (1 if dy > 0 else 0)) * CELL
        tmx = (nbx - ox) / dx if abs(dx) > 1e-9 else 1e30
        tmy = (nby - oy) / dy if abs(dy) > 1e-9 else 1e30
        t0 = 0.0
        while t0 <= best:
            if cx < 0 or cy < 0 or cx >= gw or cy >= gh:
                break
            c = cx * gh + cy
            for k in range(gstart[c], gstart[c + 1]):
                t = glist[k]
                if mark[t] == stamp:
                    continue
                mark[t] = stamp
                v0x, v0y, v0z = tri[t, 0, 0], tri[t, 0, 1], tri[t, 0, 2]
                e1x, e1y, e1z = tri[t, 1, 0] - v0x, tri[t, 1, 1] - v0y, tri[t, 1, 2] - v0z
                e2x, e2y, e2z = tri[t, 2, 0] - v0x, tri[t, 2, 1] - v0y, tri[t, 2, 2] - v0z
                px = dy * e2z - dz * e2y
                py = dz * e2x - dx * e2z
                pz = dx * e2y - dy * e2x
                det = e1x * px + e1y * py + e1z * pz
                if abs(det) < 1e-9:
                    continue
                inv = 1.0 / det
                tx, ty, tz = ox - v0x, oy - v0y, oz - v0z
                u = (tx * px + ty * py + tz * pz) * inv
                if u < 0 or u > 1:
                    continue
                qx = ty * e1z - tz * e1y
                qy = tz * e1x - tx * e1z
                qz = tx * e1y - ty * e1x
                v = (dx * qx + dy * qy + dz * qz) * inv
                if v < 0 or u + v > 1:
                    continue
                f = (e2x * qx + e2y * qy + e2z * qz) * inv
                if 0.5 < f < best:
                    best = f
            if tmx < tmy:
                t0 = tmx
                tmx += tdx
                cx += stepx
            else:
                t0 = tmy
                tmy += tdy
                cy += stepy
        if best < maxd:
            out[r] = best
    return out


def cast_many(M, origins, dirs, maxd):
    mark = np.zeros(len(M.rtri), np.int64)
    return _cast_many(M.rtri, *M.rg, np.asarray(origins, np.float64), np.asarray(dirs, np.float64), float(maxd), mark)
