#!/usr/bin/env python3
"""A small deterministic 'drop and settle' for smart-object pieces the original leaves to its rigid-body physics.
Our own code, stdlib only; runs on the PLAYER's PC inside the converter.

Why (2026-11-15, user-approved option (a)): the XD_108 building corners of 1_11 are smart objects of type 'rigid'
whose four render groups each carry a run-time model matrix (MOHMatrix::gN::MatAnim0, IDENTITY in the data). The
original simulates the pieces from load, so what a player sees is where they settle; the disc holds no pose. The
converter drops each piece (one render group = one rigid piece) under gravity alone, no initial velocity, onto the
level collision and the pieces already settled, and keeps the resting pose. No run-time fall.

Method - quasi-static, not a dynamics solver (deterministic, a few seconds in pure Python): a piece falls straight
down to its first contact; then, while its centre of mass is not over its support (the convex hull, in plan, of its
contact points), it tips about the support edge (or point) nearest the centre of mass, in small steps, each step
checked against the collision by swept segments, until a new contact catches it or it can tip no further. No
sliding and no bouncing: a piece comes to rest where it first finds a stable support. Pieces are settled lowest
first and each settled piece joins the collision of the next.
"""
import math

STEP_DEG = 1.0
MAX_TIPS = 400
EPS = 0.004          # metres: a point this close to a surface is in contact
CELL = 0.5


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _rot(axis, ang):
    x, y, z = _norm(axis)
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return ((c + x * x * C, x * y * C - z * s, x * z * C + y * s),
            (y * x * C + z * s, c + y * y * C, y * z * C - x * s),
            (z * x * C - y * s, z * y * C + x * s, c + z * z * C))


def _mv(m, v): return (_dot(m[0], v), _dot(m[1], v), _dot(m[2], v))


def _mm(a, b): return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


class Grid:
    """triangles hashed into vertical columns (x, y cells): every query is a segment or a vertical ray"""
    def __init__(self):
        self.cells = {}
        self.tris = []

    def add(self, tri):
        k = len(self.tris)
        self.tris.append(tri)
        xs, ys = [p[0] for p in tri], [p[1] for p in tri]
        for i in range(int(math.floor(min(xs) / CELL)), int(math.floor(max(xs) / CELL)) + 1):
            for j in range(int(math.floor(min(ys) / CELL)), int(math.floor(max(ys) / CELL)) + 1):
                self.cells.setdefault((i, j), []).append(k)

    def near(self, a, b):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        seen = set()
        for i in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
            for j in range(int(math.floor(y0 / CELL)), int(math.floor(y1 / CELL)) + 1):
                for k in self.cells.get((i, j), ()):
                    if k not in seen:
                        seen.add(k)
                        yield self.tris[k]


def _seg_tri(p, q, tri):
    """fraction t in [0, 1] where segment p->q first meets the (two-sided) triangle, else None (Moller-Trumbore)"""
    d = _sub(q, p)
    e1, e2 = _sub(tri[1], tri[0]), _sub(tri[2], tri[0])
    h = _cross(d, e2)
    a = _dot(e1, h)
    if abs(a) < 1e-12:
        return None
    f = 1.0 / a
    s = _sub(p, tri[0])
    u = f * _dot(s, h)
    if u < 0.0 or u > 1.0:
        return None
    qv = _cross(s, e1)
    v = f * _dot(d, qv)
    if v < 0.0 or u + v > 1.0:
        return None
    t = f * _dot(e2, qv)
    return t if 0.0 <= t <= 1.0 else None


def _first_hit(grid, pts_a, pts_b):
    """smallest fraction along the moves pts_a[i] -> pts_b[i] at which any point meets the collision (1.0 = none)"""
    best = 1.0
    for p, q in zip(pts_a, pts_b):
        for tri in grid.near(p, q):
            t = _seg_tri(p, q, tri)
            if t is not None and t < best:
                best = t
    return best


def _contacts(grid, pts):
    """points within EPS above a surface (a short vertical probe down)"""
    out = []
    for p in pts:
        a, q = (p[0], p[1], p[2] + EPS), (p[0], p[1], p[2] - 2 * EPS)
        for tri in grid.near(a, q):
            if _seg_tri(a, q, tri) is not None:
                out.append(p)
                break
    return out


def _hull2d(pts):
    pts = sorted(set((round(p[0], 4), round(p[1], 4)) for p in pts))
    if len(pts) < 3:
        return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, hi = half(pts), half(reversed(pts))
    return lo[:-1] + hi[:-1]


def _inside(poly, c):
    if len(poly) < 3:
        return False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < -1e-6:
            return False
    return True


def _pivot(poly, c):
    """the support's edge (a, b) or point (a, a) nearest the centre of mass, in plan"""
    if len(poly) == 1:
        return poly[0], poly[0]
    best, bd = None, 1e9
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ab = (b[0] - a[0], b[1] - a[1])
        L = ab[0] ** 2 + ab[1] ** 2 or 1e-12
        t = max(0.0, min(1.0, ((c[0] - a[0]) * ab[0] + (c[1] - a[1]) * ab[1]) / L))
        pr = (a[0] + ab[0] * t, a[1] + ab[1] * t)
        dd = (pr[0] - c[0]) ** 2 + (pr[1] - c[1]) ** 2
        if dd < bd:
            bd, best = dd, (a, b) if 0 < t < 1 or len(poly) == 2 else ((a, a) if t == 0 else (b, b))
    return best


def settle_piece(grid, pts, log=None):
    """(R, t): the rigid move (world) that settles the point set pts on the grid's collision"""
    R = ((1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0))
    T = (0.0, 0.0, 0.0)
    com = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
    cur = list(pts)

    def apply(rot, piv, shift):
        return [_add(_add(_mv(rot, _sub(p, piv)), piv), shift) for p in cur]
    # 1. straight down to the first contact (at most 30 m)
    down = [(p[0], p[1], p[2] - 30.0) for p in cur]
    f = _first_hit(grid, cur, down)
    if f >= 1.0:
        return None                                   # nothing under it: leave the piece where it is
    dz = -30.0 * f + EPS
    cur = [(p[0], p[1], p[2] + dz) for p in cur]
    T = (0.0, 0.0, dz)
    com = (com[0], com[1], com[2] + dz)
    for it in range(MAX_TIPS):
        cs = _contacts(grid, cur)
        if not cs:
            # lost contact after a tip: fall again
            down = [(p[0], p[1], p[2] - 30.0) for p in cur]
            f = _first_hit(grid, cur, down)
            if f >= 1.0:
                break
            dz = -30.0 * f + EPS
            cur = [(p[0], p[1], p[2] + dz) for p in cur]
            T = _add(T, (0.0, 0.0, dz))
            com = (com[0], com[1], com[2] + dz)
            continue
        poly = _hull2d(cs)
        if log:
            log("it %d contacts %d hull %d com %s" % (it, len(cs), len(poly), ["%.2f" % x for x in com]))
        if _inside(poly, com):
            break                                     # stable
        a, b = _pivot(poly, com)
        zp = min(c[2] for c in cs)
        piv = (a[0], a[1], zp)
        if a == b:
            axis = _cross((0.0, 0.0, 1.0), (com[0] - a[0], com[1] - a[1], 0.0))
        else:
            axis = (b[0] - a[0], b[1] - a[1], 0.0)
            # tip so the centre of mass goes down: about the edge, toward the com side
            if _dot(_cross(axis, (0.0, 0.0, 1.0)), (com[0] - a[0], com[1] - a[1], 0.0)) > 0:
                axis = _mul(axis, -1.0)
            axis = _mul(axis, -1.0)
        if _dot(axis, axis) < 1e-12:
            break
        step = math.radians(STEP_DEG)
        rot = _rot(axis, step)
        # the com must go down under this rotation, else turn the other way
        c2 = _add(_mv(rot, _sub(com, piv)), piv)
        if c2[2] > com[2]:
            rot = _rot(axis, -step)
            c2 = _add(_mv(rot, _sub(com, piv)), piv)
        new = apply(rot, piv, (0.0, 0.0, 0.0))
        # lift the pivot side by EPS so the supporting points do not count as hitting their own support
        lifted = [(p[0], p[1], p[2] + EPS) for p in cur]
        f = _first_hit(grid, lifted, [(p[0], p[1], p[2] + EPS) for p in new])
        if f < 1.0:
            # partial step to the new contact, then re-evaluate
            ang = step * f * 0.98
            if log:
                log("  blocked at f=%.3f" % f)
            if ang < 1e-5:
                break
            rot = _rot(axis, ang if _add(_mv(_rot(axis, ang), _sub(com, piv)), piv)[2] <= com[2] else -ang)
            new = apply(rot, piv, (0.0, 0.0, 0.0))
            c2 = _add(_mv(rot, _sub(com, piv)), piv)
        R = _mm(rot, R)
        T = _add(_mv(rot, _sub(T, piv)), piv)
        cur, com = new, c2
    return R, T


def settle(static_tris, pieces, log=print):
    """pieces: {name: [world points]} -> {name: (R, t)} (world: p' = R p + t); pieces settle lowest first"""
    g = Grid()
    for t in static_tris:
        g.add(t)
    out = {}
    for name in sorted(pieces, key=lambda n: (min(p[2] for p in pieces[n][0]), n)):
        pts, tris = pieces[name]
        res = settle_piece(g, pts)
        if res is None:
            log("easettle: %s has nothing under it - left in place" % name)
            continue
        R, T = res
        out[name] = res
        for tri in tris:
            g.add(tuple(_add(_mv(R, p), T) for p in tri))
    return out


def bodies(groups, iou=0.6):
    """render groups -> body index per group. Groups whose boxes nearly coincide (IoU >= iou) are layers of one piece
    (XD_108: the snow top and the rafter underside of the roof slab) and move together; the rest are bodies of their own"""
    def bb(v):
        return [min(p[i] for p in v) for i in range(3)], [max(p[i] for p in v) for i in range(3)]

    def vol(lo, hi):
        r = 1.0
        for i in range(3):
            r *= max(0.0, hi[i] - lo[i])
        return r
    boxes = [bb(v) for v in groups]
    body = list(range(len(groups)))

    def find(i):
        while body[i] != i:
            i = body[i]
        return i
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            a, b = boxes[i], boxes[j]
            inter = vol([max(a[0][k], b[0][k]) for k in range(3)], [min(a[1][k], b[1][k]) for k in range(3)])
            if inter / (vol(*a) + vol(*b) - inter + 1e-12) >= iou:
                body[find(j)] = find(i)
    return {i: find(i) for i in range(len(groups))}


def falling(stream):
    """the smart objects the original drops at load: those with a '<sob>__falling' state in the level stream
    (1_11: XD_108_large, XD_108_small, XD_108_side - nothing else in the level has one)"""
    import re
    return sorted(set(m.group(1).decode("latin-1") for m in re.finditer(rb"(\w{2,40})__falling\b", stream)))


def apply(stream, placed, coll, log=print):
    """settle the falling smart objects of easob.placed() output in place (their mesh vertices are moved) against
    the level's .cdb collision (eacore collision(): (name, verts, [(a, b, c, type)])). Returns the names touched."""
    names = set(falling(stream))
    todo = [(r, sob, ms) for r, sob, ms in placed if sob in names]
    if not todo:
        return []
    allv = [v for _r, _s, ms in todo for m in ms for v in m["verts"]]
    lo = [min(v[i] for v in allv) - 5.0 for i in range(3)]
    hi = [max(v[i] for v in allv) + 5.0 for i in range(3)]
    static = []
    for _n, vs, ts in coll:
        for t in ts:
            tri = (tuple(vs[t[0]]), tuple(vs[t[1]]), tuple(vs[t[2]]))
            if all(lo[0] < p[0] < hi[0] and lo[1] < p[1] < hi[1] and lo[2] < p[2] < hi[2] for p in tri):
                static.append(tri)
    pieces, owner = {}, {}
    for r, sob, ms in todo:
        b = bodies([m["verts"] for m in ms])
        for k, m in enumerate(ms):
            key = "%s/%s/b%d" % (r.name, sob, b[k])
            p = pieces.setdefault(key, ([], []))
            p[0].extend(m["verts"])
            p[1].extend((m["verts"][x], m["verts"][y], m["verts"][z]) for x, y, z in m["tris"])
            owner.setdefault(key, []).append(m)
    res = settle(static, pieces, log=log)
    touched = []
    for key in sorted(res):
        R, T = res[key]
        for m in owner[key]:
            m["verts"] = [tuple(_add(_mv(R, v), T)) for v in m["verts"]]
        tilt = math.degrees(math.acos(max(-1.0, min(1.0, R[2][2]))))
        log("easettle: %s settled (tilt %.1f deg)" % (key, tilt))
        touched.append(key)
    return touched
