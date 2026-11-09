#!/usr/bin/env python3
"""Minimal MOHAA BSP (version 19) writer. Our own code; stdlib only.

The spec is the engine itself: openmohaa-hzm/code/qcommon/qfiles.h (lumps,
structs) and cm_load.c / renderergl*/tr_bsp.c (what the loaders require).

What it emits:
  * render geometry as MST_TRIANGLE_SOUP surfaces, lightmap -1, vertex colour
    = the source's baked light (the renderer uses LIGHTMAP_BY_VERTEX for soups)
  * collision as convex brushes. CM_BoundBrush reads the brush bounds from
    sides 0..5, so every brush starts with its 6 axial planes (-x,+x,-y,+y,
    -z,+z) exactly like q3map's bevels.
  * an axis-aligned kd-tree of nodes/leafs, one cluster (0), one area (0), no
    visibility lump (CM and the renderer treat that as "everything visible")
  * model 0 = the world, plus optional inline brush models (*1, *2 ...)
  * the entity string
Light grid / terrain / static models / sphere lights are left empty.
Everything is written in a fixed order so the output is byte-deterministic.
"""
import math
import struct
import zlib

HEADER_LUMPS = 28
L_SHADERS, L_PLANES, L_LIGHTMAPS, L_SURFACES, L_DRAWVERTS, L_DRAWINDEXES = 0, 1, 2, 3, 4, 5
L_LEAFBRUSHES, L_LEAFSURFACES, L_LEAFS, L_NODES, L_SIDEEQ, L_BRUSHSIDES, L_BRUSHES = 6, 7, 8, 9, 10, 11, 12
L_MODELS, L_ENTITIES = 13, 14

CONTENTS_SOLID = 1
SURF_NODRAW = 0x80
SURF_NOLIGHTMAP = 0x100


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    l = math.sqrt(_dot(a, a))
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else None


class BSP:
    def __init__(self):
        self.shaders = []          # (name, surfaceFlags, contentFlags)
        self._shader_ix = {}
        self.planes = []           # (nx,ny,nz,d) stored in +/- pairs
        self._plane_ix = {}
        self.surfaces = []         # dict(shader, verts[(xyz, st, normal, rgba)], indexes, bounds)
        self.brushes = []          # dict(shader, sides[(plane, shader)], bounds)
        self.models = []           # extra inline models: dict(surfaces[ids], brushes[ids])
        self.entities = []         # list of ordered (key, value) lists

    # ---------- tables ----------
    def shader(self, name, surface_flags=0, content_flags=0):
        if name not in self._shader_ix:
            self._shader_ix[name] = len(self.shaders)
            self.shaders.append((name, surface_flags, content_flags))
        return self._shader_ix[name]

    def plane(self, n, d):
        key = (round(n[0], 5), round(n[1], 5), round(n[2], 5), round(d, 3))
        if key in self._plane_ix:
            return self._plane_ix[key]
        neg = (-key[0], -key[1], -key[2], -key[3])
        if neg in self._plane_ix:
            return self._plane_ix[neg] ^ 1
        ix = len(self.planes)
        self.planes.append(key)
        self.planes.append(neg)
        self._plane_ix[key] = ix
        self._plane_ix[neg] = ix + 1
        return ix

    # ---------- content ----------
    def add_soup(self, shader_ix, verts, indexes):
        """verts: list of (xyz, st, normal, rgba); indexes: flat triangle list."""
        lo = [min(v[0][k] for v in verts) for k in range(3)]
        hi = [max(v[0][k] for v in verts) for k in range(3)]
        self.surfaces.append({"shader": shader_ix, "verts": verts, "indexes": list(indexes), "bounds": (lo, hi)})
        return len(self.surfaces) - 1

    def add_brush_planes(self, shader_ix, planes_nd, lo, hi):
        """planes_nd: extra (normal, dist) planes; 6 axial bevels are prepended."""
        sides = []
        for axis in range(3):
            for sign in (-1, 1):
                n = [0.0, 0.0, 0.0]
                n[axis] = float(sign)
                d = -lo[axis] if sign < 0 else hi[axis]
                sides.append((self.plane(tuple(n), d), shader_ix))
        for n, d in planes_nd:
            sides.append((self.plane(n, d), shader_ix))
        self.brushes.append({"shader": shader_ix, "sides": sides, "bounds": (list(lo), list(hi))})
        return len(self.brushes) - 1

    def add_prism(self, shader_ix, a, b, c, thickness, centered=False):
        """Thin convex brush on triangle abc. centered=False: the slab lies behind the face (front face = abc's
        normal). centered=True: the slab straddles the face (+-thickness/2) - independent of the source winding,
        which Frontline's collision does not keep consistent (a reversed floor would otherwise grow a slab
        UPWARD and every such triangle becomes a step the navmesh cannot climb)."""
        n = _norm(_cross(_sub(b, a), _sub(c, a)))
        if n is None:
            return None
        d = _dot(n, a)
        front = thickness / 2.0 if centered else 0.0
        back_d = thickness - front
        top = [(p[0] + n[0] * front, p[1] + n[1] * front, p[2] + n[2] * front) for p in (a, b, c)]
        back = [(p[0] - n[0] * back_d, p[1] - n[1] * back_d, p[2] - n[2] * back_d) for p in (a, b, c)]
        planes = [(n, d + front), ((-n[0], -n[1], -n[2]), -(d - back_d))]
        for p, q in ((a, b), (b, c), (c, a)):
            e = _norm(_cross(_sub(q, p), n))       # outward for a CCW-from-front triangle
            if e is None:
                return None
            planes.append((e, _dot(e, p)))
        pts = top + back
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
        # the edge normals must point away from the opposite vertex
        for (e, dd), opp in zip(planes[2:], (c, a, b)):
            if _dot(e, opp) - dd > 0.01:
                return None
        return self.add_brush_planes(shader_ix, planes, lo, hi)

    def entity(self, kv):
        self.entities.append(kv)

    # ---------- tree ----------
    def _build_tree(self, surf_ids, brush_ids, max_items=24, max_depth=28):
        nodes, leafs, leafsurfs, leafbrushes = [], [], [], []
        sb = {i: self.surfaces[i]["bounds"] for i in surf_ids}
        bb = {i: self.brushes[i]["bounds"] for i in brush_ids}

        def bounds_of(ss, bs):
            lo, hi = [1e30] * 3, [-1e30] * 3
            for b in [sb[i] for i in ss] + [bb[i] for i in bs]:
                for k in range(3):
                    lo[k] = min(lo[k], b[0][k])
                    hi[k] = max(hi[k], b[1][k])
            if lo[0] > hi[0]:
                lo, hi = [0.0] * 3, [0.0] * 3
            return lo, hi

        def make_leaf(ss, bs, lo, hi):
            leafs.append((lo, hi, len(leafsurfs), len(ss), len(leafbrushes), len(bs)))
            leafsurfs.extend(sorted(ss))
            leafbrushes.extend(sorted(bs))
            return -(len(leafs))  # -(leaf+1)

        def rec(ss, bs, lo, hi, depth):
            if len(ss) + len(bs) <= max_items or depth >= max_depth:
                return make_leaf(ss, bs, lo, hi)
            axis = max(range(3), key=lambda k: hi[k] - lo[k])
            cents = sorted([(sb[i][0][axis] + sb[i][1][axis]) / 2 for i in ss] +
                           [(bb[i][0][axis] + bb[i][1][axis]) / 2 for i in bs])
            split = float(round(cents[len(cents) // 2]))
            if not (lo[axis] < split < hi[axis]):
                return make_leaf(ss, bs, lo, hi)
            fs = [i for i in ss if sb[i][1][axis] > split]
            bs_ = [i for i in ss if sb[i][0][axis] < split]
            fb = [i for i in bs if bb[i][1][axis] > split]
            bb_ = [i for i in bs if bb[i][0][axis] < split]
            # items exactly on the plane on both sides: put them on both
            fs += [i for i in ss if sb[i][1][axis] == split == sb[i][0][axis]]
            if len(fs) + len(fb) == len(ss) + len(bs) and len(bs_) + len(bb_) == len(ss) + len(bs):
                return make_leaf(ss, bs, lo, hi)
            n = [0.0, 0.0, 0.0]
            n[axis] = 1.0
            pnum = self.plane(tuple(n), split)
            me = len(nodes)
            nodes.append(None)
            flo, fhi = list(lo), list(hi)
            flo[axis] = split
            blo, bhi = list(lo), list(hi)
            bhi[axis] = split
            c0 = rec(fs, fb, flo, fhi, depth + 1)
            c1 = rec(bs_, bb_, blo, bhi, depth + 1)
            nodes[me] = (pnum, c0, c1, lo, hi)
            return me

        lo, hi = bounds_of(surf_ids, brush_ids)
        lo = [x - 64 for x in lo]
        hi = [x + 64 for x in hi]
        root = rec(list(surf_ids), list(brush_ids), lo, hi, 0)
        if root < 0:  # degenerate: a single leaf - still need one node
            n = (1.0, 0.0, 0.0)
            nodes.append((self.plane(n, hi[0] + 1), root, root, lo, hi))
        return nodes, leafs, leafsurfs, leafbrushes, (lo, hi)

    # ---------- write ----------
    def write(self, path):
        world_s = [i for i in range(len(self.surfaces)) if not any(i in m["surfaces"] for m in self.models)]
        world_b = [i for i in range(len(self.brushes)) if not any(i in m["brushes"] for m in self.models)]
        # order: world surfaces/brushes first, then each inline model's (contiguous ranges)
        s_order = world_s + [i for m in self.models for i in m["surfaces"]]
        b_order = world_b + [i for m in self.models for i in m["brushes"]]
        s_remap = {old: new for new, old in enumerate(s_order)}
        b_remap = {old: new for new, old in enumerate(b_order)}

        nodes, leafs, leafsurfs, leafbrushes, (wlo, whi) = self._build_tree(world_s, world_b)

        lumps = [b""] * HEADER_LUMPS
        lumps[L_SHADERS] = b"".join(
            struct.pack("<64sIII64s", n.encode()[:63], sf, cf, 0, b"") for n, sf, cf in self.shaders)
        lumps[L_PLANES] = b"".join(struct.pack("<4f", *p) for p in self.planes)

        sv, si, ss_ = bytearray(), bytearray(), bytearray()
        nverts = nidx = 0
        for old in s_order:
            s = self.surfaces[old]
            for xyz, st, nrm, rgba in s["verts"]:
                sv += struct.pack("<3f2f2f3f4B", *xyz, *st, 0.0, 0.0, *nrm, *rgba)
            si += struct.pack(f"<{len(s['indexes'])}i", *s["indexes"])
            ss_ += struct.pack("<12i3f9f2if", s["shader"], -1, 3, nverts, len(s["verts"]), nidx, len(s["indexes"]),
                               -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0)
            nverts += len(s["verts"])
            nidx += len(s["indexes"])
        lumps[L_SURFACES], lumps[L_DRAWVERTS], lumps[L_DRAWINDEXES] = bytes(ss_), bytes(sv), bytes(si)

        lumps[L_LEAFSURFACES] = struct.pack(f"<{len(leafsurfs)}i", *[s_remap[i] for i in leafsurfs])
        lumps[L_LEAFBRUSHES] = struct.pack(f"<{len(leafbrushes)}i", *[b_remap[i] for i in leafbrushes])
        lumps[L_LEAFS] = b"".join(
            struct.pack("<2i3i3i8i", 0, 0, *[int(math.floor(x)) for x in lo], *[int(math.ceil(x)) for x in hi],
                        fs, ns, fb, nb, 0, 0, 0, 0)
            for lo, hi, fs, ns, fb, nb in leafs)
        lumps[L_NODES] = b"".join(
            struct.pack("<3i3i3i", p, c0, c1, *[int(math.floor(x)) for x in lo], *[int(math.ceil(x)) for x in hi])
            for p, c0, c1, lo, hi in nodes)

        bs, bsd = bytearray(), bytearray()
        nsides = 0
        for old in b_order:
            b = self.brushes[old]
            bs += struct.pack("<3i", nsides, len(b["sides"]), b["shader"])
            for pnum, sh in b["sides"]:
                bsd += struct.pack("<3i", pnum, sh, 0)
            nsides += len(b["sides"])
        lumps[L_BRUSHES], lumps[L_BRUSHSIDES] = bytes(bs), bytes(bsd)

        mods = [struct.pack("<3f3f4i", *wlo, *whi, 0, len(world_s), 0, len(world_b))]
        so, bo = len(world_s), len(world_b)
        for m in self.models:
            lo, hi = [1e30] * 3, [-1e30] * 3
            for i in m["surfaces"]:
                for k in range(3):
                    lo[k] = min(lo[k], self.surfaces[i]["bounds"][0][k]); hi[k] = max(hi[k], self.surfaces[i]["bounds"][1][k])
            for i in m["brushes"]:
                for k in range(3):
                    lo[k] = min(lo[k], self.brushes[i]["bounds"][0][k]); hi[k] = max(hi[k], self.brushes[i]["bounds"][1][k])
            mods.append(struct.pack("<3f3f4i", *lo, *hi, so, len(m["surfaces"]), bo, len(m["brushes"])))
            so += len(m["surfaces"]); bo += len(m["brushes"])
        lumps[L_MODELS] = b"".join(mods)

        ent = ""
        for kv in self.entities:
            ent += "{\n" + "".join(f'"{k}" "{v}"\n' for k, v in kv) + "}\n"
        lumps[L_ENTITIES] = ent.encode("latin-1") + b"\0"

        hdr_len = 12 + 8 * HEADER_LUMPS
        body, table = bytearray(), []
        for data in lumps:
            off = hdr_len + len(body)
            table.append((off if data else 0, len(data)))
            body += data
            while len(body) % 4:
                body += b"\0"
        checksum = zlib.crc32(bytes(body)) & 0x7FFFFFFF
        hdr = struct.pack("<4sii", b"2015", 19, checksum) + b"".join(struct.pack("<ii", o, l) for o, l in table)
        with open(path, "wb") as f:
            f.write(hdr + bytes(body))
        return {"surfaces": len(self.surfaces), "brushes": len(self.brushes), "planes": len(self.planes),
                "nodes": len(nodes), "leafs": len(leafs), "bytes": len(hdr) + len(body),
                "bounds": (wlo, whi)}
