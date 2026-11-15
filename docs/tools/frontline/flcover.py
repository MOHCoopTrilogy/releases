#!/usr/bin/env python3
"""[flfix2 round 21] Frontline's AI cover points ("waypoints") for the converted mission. Our code; runs on the
player's PC inside the converter and writes only numbers (positions, angles, flags) into the BSP's entity lump and
the generated data script - never Frontline text or art.

Decoded 2026-11-15 from the 1_1 .bpd and the emulator's script-VM traces (docs/proposals/flpolish_2026-11-10/
FIDELITY.md round 21):

.bpd section-3 record, kind (word 3) 5, type hash (word 18) 0x9101C906 = a cover point; 116 bytes:
  words 4..6   position (disc metres)            words 7..10  quaternion (w, x, y, z): the facing = toward the threat
  word 13      byte 1 = team allowed to use it: 0 any, 1 Allied, 2 Axis (the actor record's own team byte)
  word 14      link tag: the same number sits in word 14 of the breakable crate (BreakingWoodBoxSwap) the point leans
               on (a crate carries one point per side, Allied facing one way and Axis the other)
  word 28      type: 1 corner, wall on the right (step out left), 2 corner, wall on the left, 4 behind low cover
               (crates, parapets: fire over it), 80 one point (meaning not decoded)
Type hash 0x5B607813 (word 28 = 8, string "MGPoint") = a mounted-gun point. Record 0 (hash 0x2070A66D) is not one.
Evidence: 84 of 85 traced AISETCOVERPOINT calls (and all 259 GETWAYPOINTINFO calls) take a section-3 record number
of a 0x9101C906 record; the 85th is -1 (clear). Allies took team 0/1 points only, Germans team 0/2 only.

MOHAA (openmohaa navigate.cpp): an info_pathnode with spawnflags AI_CORNER_LEFT 16 / AI_CORNER_RIGHT 32 / AI_CRATE
128 / AI_COVER 4 is a cover node the Actor cover state finds (PathSearch::FindPotentialCover), claims one man per node
and fights from (GetSpecialAttack). A corner node's yaw points AWAY from the threat (the enemy must lie 150-210
degrees off it) and corner_left is the one whose open side is on the right as you face the threat - measured on the
stock maps' own corner nodes (m1l1, m2l1, m2l3, m3l2, m4l0: wall behind 123/123, behind-right blocked 60/61 for
corner_left, behind-left 58/62 for corner_right). A crate node faces the cover (enemy within 40 degrees of its yaw).
So: disc 1 -> corner_right, yaw + 180; disc 2 -> corner_left, yaw + 180; disc 4 -> crate, yaw as is.
"""
import math

import flscene

COVER_HASH = 0x9101C906
MG_HASH = 0x5B607813
AI_COVER, AI_CORNER_LEFT, AI_CORNER_RIGHT, AI_CRATE = 4, 16, 32, 128
# disc type -> (MOHAA spawnflags, yaw added to the disc facing)
NODE_OF_TYPE = {1: (AI_CORNER_RIGHT, 180.0), 2: (AI_CORNER_LEFT, 180.0), 4: (AI_CRATE, 0.0), 80: (AI_COVER, 0.0)}
BODY = 15.0 + 6.0       # MOHAA body half-width plus a margin: a node this close to a crate box starts in it


def _w(e):
    return flscene.words(e)


def records(L):
    """[(record, team, tag, type, is_mg)] of the level's cover and mounted-gun points, in record order"""
    out = []
    for e in L.entities():
        w = _w(e)
        if len(w) < 29 or w[3] != 5 or w[18] not in (COVER_HASH, MG_HASH):
            continue
        out.append((e, (w[13] >> 8) & 255, w[14], w[28], w[18] == MG_HASH))
    return out


class Brushes:
    """the BSP's own solid world brushes (flbsp.BSP, before it is written), for a box-overlap test - the triangle grid
    alone missed the extra walls flcliff/flsheets add and the prisms' 4u thickness (5 of 103 nodes landed in solid)"""

    def __init__(self, B, cell=128.0):
        in_model = {i for m in B.models for i in m["brushes"]}
        self.cell = cell
        self.items = []
        self.g = {}
        for i, b in enumerate(B.brushes):
            if i in in_model or not (B.shaders[b["shader"]][2] & (1 | 0x10000)):
                continue
            lo, hi = b["bounds"]
            planes = [B.planes[p] for p, _s in b["sides"]]
            k = len(self.items)
            self.items.append((lo, hi, planes))
            for gx in range(int(lo[0] // cell), int(hi[0] // cell) + 1):
                for gy in range(int(lo[1] // cell), int(hi[1] // cell) + 1):
                    self.g.setdefault((gx, gy), []).append(k)

    def box_hits(self, lo, hi):
        c = [(lo[i] + hi[i]) / 2 for i in range(3)]
        h = [(hi[i] - lo[i]) / 2 for i in range(3)]
        seen = set()
        for gx in range(int(lo[0] // self.cell), int(hi[0] // self.cell) + 1):
            for gy in range(int(lo[1] // self.cell), int(hi[1] // self.cell) + 1):
                for k in self.g.get((gx, gy), ()):
                    if k in seen:
                        continue
                    seen.add(k)
                    blo, bhi, planes = self.items[k]
                    if any(lo[i] >= bhi[i] or hi[i] <= blo[i] for i in range(3)):
                        continue
                    if all(n0 * c[0] + n1 * c[1] + n2 * c[2] - (abs(n0) * h[0] + abs(n1) * h[1] + abs(n2) * h[2]) < d - 0.01
                           for n0, n1, n2, d in planes):
                        return True
        return False


def floor_at(grid, x, y, z0):
    """the floor under (x, y) nearest the disc point's height z0: the highest one within 20u above it, else the highest
    within 40u (a dug-in point below the converted floor) - searching 48u up stood points on the low wall they hide
    behind (rec 138, 115, 175, 176: 29-45u up)"""
    if grid is None:
        return z0
    z = grid.ground(x, y, z0 + 20, z0 - 96)
    return z if z is not None else grid.ground(x, y, z0 + 40, z0 - 96)


def walk_ok(B_, grid, a, b, lift, step=12.0):
    """[approximate navigate.cpp CheckMove] a body walks the straight line a -> b (x, y, floor z): every 12u it finds a
    floor no more than `lift` above and 256u below its last one and its box (step height to 94u) is clear of the brushes"""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(L // step))
    z = a[2]
    for i in range(1, n + 1):
        x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
        g = grid.ground(x, y, z + lift, z - 256) if grid is not None else z
        if g is None:
            return False
        if B_ is not None and B_.box_hits((x - 15.5, y - 15.5, max(g, z) + lift), (x + 15.5, y + 15.5, max(g, z) + 94.0)):
            return False
        z = g
    return abs(z - b[2]) <= lift + 2


def _free(B_, grid, obstacles, p, yaw, lift, max_r=96, step=4):
    """nearest spot to p where a MOHAA body stands clear of the brushes and the props, searched in rings, each ring from
    straight behind the point (away from its cover) round to the front; (spot, moved) or (None, -1)"""
    back = math.radians(yaw + 180)
    for r in range(0, max_r + 1, step):
        n = 1 if r == 0 else max(8, int(2 * math.pi * r / step))
        angs = sorted((2 * math.pi * k / n for k in range(n)),
                      key=lambda a: abs(math.atan2(math.sin(a - back), math.cos(a - back))))
        for a in angs:
            x, y = p[0] + r * math.cos(a), p[1] + r * math.sin(a)
            z = floor_at(grid, x, y, p[2])
            if z is None:
                continue
            if any(_in_box((x, y), ob, BODY) for ob in obstacles if math.dist(ob["pos"][:2], (x, y)) < 160):
                continue
            if B_ is not None and B_.box_hits((x - BODY, y - BODY, z + lift), (x + BODY, y + BODY, z + 94.0)):
                continue
            return (round(x), round(y), z), float(r)
    return None, -1.0


def _in_box(p, ob, margin):
    """p (x, y) inside obstacle ob's rotated footprint grown by margin"""
    a = math.radians(-ob["yaw"])
    dx, dy = p[0] - ob["pos"][0], p[1] - ob["pos"][1]
    lx, ly = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
    return (ob["lo"][0] - margin <= lx <= ob["hi"][0] + margin) and (ob["lo"][1] - margin <= ly <= ob["hi"][1] + margin)


def points(L, X, grid=None, obstacles=(), actors=(), B=None, lift=38.0):
    """the cover points in MOHAA units, placed where a MOHAA body can stand: [dict(k, rec, pos, yaw, type, team, tag,
    om, grp, flags, node_yaw, moved)]. `obstacles` = the solid inline props [dict(name, pos, yaw, lo, hi, tag)] (the
    crates), `actors` = [(pos, team, grp)] of the actor records for the inferred group, `B` = the BSP being built
    (its solid brushes), `lift` = the map's step height (k is 1-based; moved -1 = no free spot within 96u)."""
    mirror = X.m < 0
    B_ = Brushes(B) if B is not None else None
    points.last = (B_, grid, lift)
    out = []
    for e, team, tag, typ, is_mg in records(L):
        p = X(e["pos"])
        yaw = flscene.yaw(e, mirror)
        om = ""
        # the crate the point leans on (same tag within 3 m)
        hits = [ob for ob in obstacles if tag and ob.get("tag") == tag and math.dist(ob["pos"][:2], p[:2]) < 144]
        if hits:
            om = min(hits, key=lambda ob: math.dist(ob["pos"][:2], p[:2]))["name"]
        s, moved = _free(B_, grid, obstacles, p, yaw, lift)
        q = (float(s[0]), float(s[1]), float(s[2])) if s is not None else p
        # [I] inferred group: the waking message of the nearest actor record within 15 m that may use the point
        grp = 0
        best = 720.0 ** 2
        for apos, ateam, agrp in actors:
            if team and ateam and ateam != team:
                continue
            d = (apos[0] - q[0]) ** 2 + (apos[1] - q[1]) ** 2
            if d < best:
                best, grp = d, agrp
        flags, dyaw = (0, 0.0) if is_mg else NODE_OF_TYPE.get(typ, (AI_COVER, 0.0))
        out.append({"k": len(out) + 1, "rec": e["i"], "pos": q, "yaw": yaw % 360, "type": 8 if is_mg else typ,
                    "team": team, "tag": tag, "om": om, "grp": grp, "flags": flags,
                    "node_yaw": (yaw + dyaw) % 360, "moved": round(moved, 1)})
    return out


def nodes(cov, taken, nav=()):
    """the cover points that become info_pathnode entities: one per spot (a disc corner pair at one spot keeps its first
    record; MOHAA gives a node one flag and one yaw), none for a mounted-gun point, one that has no free spot, or one no
    navpoint node within 384u (the engine's link range) can be walked to in a straight line (`nav` = the navpoint
    nodes' (x, y, floor z); an unlinked cover node is one an actor picks and cannot reach). `taken` = set of (x, y)
    integer origins already used by the navpoint nodes (the engine drops a node whose origin equals another's after
    droptofloor - same x, y is enough). Marks c["node"] = 1 on the ones it returns (c["link"] = 0 when unlinked)."""
    B_, grid, lift = getattr(points, "last", (None, None, 38.0))
    out = []
    for c in cov:
        c["node"] = 0
        if not c["flags"] or c["moved"] < 0:
            continue
        if nav:
            near = sorted((q for q in nav if (q[0] - c["pos"][0]) ** 2 + (q[1] - c["pos"][1]) ** 2 < 384.0 ** 2),
                          key=lambda q: (q[0] - c["pos"][0]) ** 2 + (q[1] - c["pos"][1]) ** 2)[:12]
            c["link"] = int(any(walk_ok(B_, grid, c["pos"], q, lift) or walk_ok(B_, grid, q, c["pos"], lift) for q in near))
            if not c["link"]:
                continue
        x, y = int(round(c["pos"][0])), int(round(c["pos"][1]))
        if any(abs(x - n["xy"][0]) <= 8 and abs(y - n["xy"][1]) <= 8 for n in out):
            continue
        while (x, y) in taken:
            x += 1
        taken.add((x, y))
        c["node"] = 1
        out.append({"xy": (x, y), "z": c["pos"][2], "c": c})
    return [(n["xy"][0], n["xy"][1], n["z"], n["c"]) for n in out]


def data_lines(cov):
    """level.fl_cov_* for the generated data script"""
    ln = []
    for c in cov:
        k, p = c["k"], c["pos"]
        ln.append(f"\tlevel.fl_cov[{k}] = ( {p[0]:.0f} {p[1]:.0f} {p[2]:.0f} )")
        ln.append(f"\tlevel.fl_cov_yaw[{k}] = {c['yaw']:.0f}")
        ln.append(f"\tlevel.fl_cov_type[{k}] = {c['type']}")
        ln.append(f"\tlevel.fl_cov_team[{k}] = {c['team']}")
        ln.append(f"\tlevel.fl_cov_grp[{k}] = {c['grp']}")
        ln.append(f"\tlevel.fl_cov_tag[{k}] = {c['tag']}")
        ln.append(f"\tlevel.fl_cov_node[{k}] = {c.get('node', 0)}")
        ln.append(f"\tlevel.fl_cov_rec[{k}] = {c['rec']}")
        if c["om"]:
            ln.append(f'\tlevel.fl_cov_om[{k}] = "{c["om"]}"')
    ln.append(f"\tlevel.fl_cov_n = {len(cov)}")
    return ln
