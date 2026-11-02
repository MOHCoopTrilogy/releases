"""make_chunks.py <spec.json> - split big axial brushes along one axis into named LOCAL-coordinate script_object chunks (crumble pieces).
spec: {"src","dst","structures":[{"name","axis":0|1|2,"cuts":[c1,c2..],"brushes":[ids],"pivot":"base"|"center"}], "entity_class":"script_object"}
Chunk n of structure S = every listed brush clipped to [cut_{n-1}, cut_n] on the axis (open ends at +-inf), as ONE submodel; entity name crumble_<S>_<n+1>, origin = pivot.
Draw surfaces of each brush (auto: inside the brush box, on a side plane, same shader) are clipped triangle-wise to the same range (st / lightmap uv / normal / colour interpolated)
and appended; the originals are neutralised (brush -> contents-0 clone, surface -> nodraw). The cut faces between chunks get NO surface (hidden until chunks separate).
Patches / faces larger than their brush stay in the world (reported)."""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bspedit as E
from make_subs import auto_surfaces

VF = "<3f2f2f3f4B"      # drawvert, 44 bytes
INF = 1e9

def read_vert(dv, k):
    v = struct.unpack_from(VF, dv, k * 44); return list(v)

def lerp(a, b, t):
    o = [a[i] + (b[i] - a[i]) * t for i in range(10)]
    o += [int(round(a[10 + i] + (b[10 + i] - a[10 + i]) * t)) for i in range(4)]
    return o

def clip_poly(poly, ax, val, keep_ge):
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da = (a[ax] - val) * (1 if keep_ge else -1); db = (b[ax] - val) * (1 if keep_ge else -1)
        if da >= 0: out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db); out.append(lerp(a, b, t))
    return out

def clip3(poly, n, d):
    """keep n.p <= d (+eps) of a 3d polygon (list of [x,y,z])"""
    out = []
    m = len(poly)
    for i in range(m):
        a, b = poly[i], poly[(i + 1) % m]
        da = n[0]*a[0] + n[1]*a[1] + n[2]*a[2] - d; db = n[0]*b[0] + n[1]*b[1] + n[2]*b[2] - d
        if da <= 0.01: out.append(a)
        if (da <= 0.01) != (db <= 0.01):
            tt = da / (da - db); out.append([a[k] + (b[k] - a[k]) * tt for k in range(3)])
    return out

def build(spec):
    b = E.Bsp(open(spec["src"], "rb").read())
    sh = b.shaders(); pl = b.planes()
    nodraw = next(i for i, s in enumerate(sh) if s[0] == "textures/common/nodraw")
    shl = b.lumps[E.IX["shaders"]]
    if not any(s[0] == "textures/common/nodraw" and s[2] == 0 for s in sh):
        rec = bytearray(shl[nodraw * 140:nodraw * 140 + 140]); struct.pack_into("<i", rec, 68, 0); dead = len(sh); shl += rec
    else:
        dead = next(i for i, s in enumerate(sh) if s[0] == "textures/common/nodraw" and s[2] == 0)
    plL, bl, sl, sfl, dvl, eqL, mdl, ixl = (b.lumps[E.IX[n]] for n in ("planes", "brushes", "brushsides", "surfaces", "drawverts", "sideeq", "models", "drawidx"))
    sf0 = bytes(sfl); dv0 = bytes(dvl); eq0 = bytes(eqL); ix0 = bytes(ixl)
    nmod0 = len(mdl) // 40
    ents = bytearray(b.get("ents")); add = ""
    report = []; claimed = set(); consumed_b = set(); consumed_s = set()
    modelnum = nmod0
    for S in spec["structures"]:
        ax = S["axis"]; cuts = sorted(S["cuts"]); rng = list(zip([-INF] + cuts, cuts + [INF]))
        # surfaces per brush (auto), claimed once
        bsurf = {}
        for bid in S["brushes"]:
            part = []
            bsurf[bid] = auto_surfaces(b, [bid], pl, dv0, sf0, claimed, partial=part)
            claimed.update(bsurf[bid])
            if part: report.append(("PARTIAL", S["name"], bid, sorted(set(part) - set(bsurf[bid]))[:8]))
        # ghosts: partial surfaces (shared strips) lying inside the structure's brush union and claimed by nobody -> go with the chunks
        ub_mn = [min(E.brush_aabb(b, bid, pl)[0][k] for bid in S["brushes"]) - 3 for k in range(3)]
        ub_mx = [max(E.brush_aabb(b, bid, pl)[1][k] for bid in S["brushes"]) + 3 for k in range(3)]
        ghosts = []
        for (kind, nm, bid_, ids) in [r for r in report if r[0] == "PARTIAL" and r[1] == S["name"]]:
            pass
        names = [s[0] for s in sh]
        capname = S.get("cap_shader")
        def cap_shader_for(bid):
            if capname: return next(i for i, n in enumerate(names) if n == capname)
            for sd in b.brush(bid)[3]:
                n = names[sd[1]]
                if not any(k in n for k in ("caulk", "nodraw", "clip", "hint", "skip", "sky")): return sd[1]
            return next(i for i, n in enumerate(names) if n.endswith("jh_conc512b"))
        ex = [x for x in S.get("surfaces_extra", []) if x not in claimed]
        if ex:
            bsurf[S["brushes"][0]] = list(bsurf[S["brushes"][0]]) + ex; claimed.update(ex)
        for ci, (lo, hi) in enumerate(rng):
            pieces = []      # (bid, mn, mx)
            for bid in S["brushes"]:
                r = E.brush_aabb(b, bid, pl); mn, mx = r
                if hi <= mn[ax] + 0.01 or lo >= mx[ax] - 0.01: continue
                pmn = list(mn); pmx = list(mx); pmn[ax] = max(mn[ax], lo); pmx[ax] = min(mx[ax], hi)
                pieces.append((bid, pmn, pmx))
            if not pieces: continue
            bmn = [min(p[1][k] for p in pieces) for k in range(3)]; bmx = [max(p[2][k] for p in pieces) for k in range(3)]
            o = [(bmn[0] + bmx[0]) / 2, (bmn[1] + bmx[1]) / 2, bmn[2] if S.get("pivot", "base") == "base" else (bmn[2] + bmx[2]) / 2]
            o = [round(v, 1) for v in o]
            pmap = {}
            def np_(pi=None, plane=None):
                key = pi if pi is not None else tuple(plane)
                if key not in pmap:
                    x, y, z, d = pl[pi] if pi is not None else plane
                    pmap[key] = len(plL) // 16; plL.extend(struct.pack("<4f", x, y, z, d - (x * o[0] + y * o[1] + z * o[2])))
                return pmap[key]
            eqmap = {}
            def ne(ei):
                if ei < 0 or ei * 32 + 32 > len(eq0): return ei
                if ei not in eqmap:
                    s4 = list(struct.unpack_from("<4f", eq0, ei * 32)); t4 = list(struct.unpack_from("<4f", eq0, ei * 32 + 16))
                    s4[3] += s4[0] * o[0] + s4[1] * o[1] + s4[2] * o[2]; t4[3] += t4[0] * o[0] + t4[1] * o[1] + t4[2] * o[2]
                    eqmap[ei] = len(eqL) // 32; eqL.extend(struct.pack("<4f", *s4) + struct.pack("<4f", *t4))
                return eqmap[ei]
            nb0 = len(bl) // 12; ns = len(sl) // 12
            for bid, pmn, pmx in pieces:
                fs, n, shn, sides = b.brush(bid)
                bl.extend(struct.pack("<3i", ns, n, shn))
                for si, (pn, sshn, eq) in enumerate(sides):
                    if si == 2 * ax and lo > -INF / 2 and lo > E.brush_aabb(b, bid, pl)[0][ax]:
                        nrm = [0, 0, 0]; nrm[ax] = -1; pn2 = np_(plane=(nrm[0], nrm[1], nrm[2], -lo)); sl.extend(struct.pack("<3i", pn2, nodraw, ne(eq)))
                    elif si == 2 * ax + 1 and hi < INF / 2 and hi < E.brush_aabb(b, bid, pl)[1][ax]:
                        nrm = [0, 0, 0]; nrm[ax] = 1; pn2 = np_(plane=(nrm[0], nrm[1], nrm[2], hi)); sl.extend(struct.pack("<3i", pn2, nodraw, ne(eq)))
                    else:
                        sl.extend(struct.pack("<3i", np_(pi=pn), sshn, ne(eq)))
                ns += n
            nsf0 = len(sfl) // 108; nsurf = 0
            for bid, pmn, pmx in pieces:
                for si_ in bsurf[bid]:
                    r = bytearray(sf0[si_ * 108:si_ * 108 + 108]); shn, fog, typ, fv, nv, fi, ni = struct.unpack_from("<7i", r, 0)
                    lo3 = list(struct.unpack_from("<3f", r, 48))
                    struct.pack_into("<3f", r, 48, *[lo3[j] - o[j] for j in range(3)])
                    if typ == 2:      # patch: whole, to the chunk containing its centre
                        pts = [read_vert(dv0, fv + k) for k in range(nv)]
                        c = sum(p[ax] for p in pts) / nv
                        if not (lo <= c < hi): continue
                        struct.pack_into("<i", r, 12, len(dvl) // 44)
                        for p in pts:
                            q = list(p); q[0] -= o[0]; q[1] -= o[1]; q[2] -= o[2]; dvl.extend(struct.pack(VF, *q))
                        for off in (60, 72):
                            v3 = struct.unpack_from("<3f", r, off); struct.pack_into("<3f", r, off, *[v3[j] - o[j] for j in range(3)])
                        sfl.extend(r); nsurf += 1; consumed_s.add(si_); continue
                    idx = struct.unpack_from("<%di" % ni, ix0, fi * 4)
                    verts_out = []; idx_out = []
                    for t in range(0, ni, 3):
                        poly = [read_vert(dv0, fv + idx[t + k]) for k in range(3)]
                        if lo > -INF / 2: poly = clip_poly(poly, ax, lo, True)
                        if hi < INF / 2 and poly: poly = clip_poly(poly, ax, hi, False)
                        if len(poly) < 3: continue
                        base = len(verts_out)
                        for p in poly:
                            q = list(p); q[0] -= o[0]; q[1] -= o[1]; q[2] -= o[2]; verts_out.append(q)
                        for k in range(1, len(poly) - 1): idx_out += [base, base + k, base + k + 1]
                    consumed_s.add(si_)
                    if not idx_out: continue
                    struct.pack_into("<4i", r, 12, len(dvl) // 44, len(verts_out), len(ixl) // 4, len(idx_out))
                    for q in verts_out: dvl.extend(struct.pack(VF, *q))
                    ixl.extend(struct.pack("<%di" % len(idx_out), *idx_out))
                    sfl.extend(r); nsurf += 1
            mdl.extend(struct.pack("<6f4i", *[bmn[j] - o[j] for j in range(3)], *[bmx[j] - o[j] for j in range(3)], nsf0, nsurf, nb0, len(pieces)))
            name = "crumble_%s_%d" % (S["name"], ci + 1)
            add += chr(123) + chr(10) + "".join("\"%s\" \"%s\"" % kv + chr(10) for kv in (("model", "*%d" % modelnum), ("classname", spec.get("entity_class", "script_object")), ("targetname", name), ("origin", "%g %g %g" % tuple(o))) + tuple(spec.get("ent_keys", {}).items())) + chr(125) + chr(10)
            report.append(("CHUNK", name, modelnum, S["name"], o, [round(v) for v in bmn], [round(v) for v in bmx], len(pieces), nsurf))
            modelnum += 1
            consumed_b.update(p[0] for p in pieces)
    for bid in consumed_b: struct.pack_into("<3i", bl, bid * 12, *b.brush(bid)[:2], dead)
    for si_ in consumed_s: struct.pack_into("<i", sfl, si_ * 108, nodraw)
    b.lumps[E.IX["ents"]] = bytearray(bytes(ents[:-1]) + add.encode("latin1") + b"\x00")
    open(spec["dst"], "wb").write(b.tobytes())
    return report

if __name__ == "__main__":
    for r in build(json.load(open(sys.argv[1]))): print(r)
