"""make_chunks3.py <spec.json> - make_chunks2 (capped crumble chunks) + BREACH SITES.
A structure may carry "breaches": [{"n":1,"axis":n,"sign":so,"box":[[x0,y0,z0],[x1,y1,z1]],"hole_r":130,"K":10,"seed":3,"depth":360,"interior":true,
 "cu":..,"cv":..}]:
  * the wall volume inside `box` is carved out of the chunk piece(s) (frame boxes stay in the chunk, the centre becomes model breach_N_intact == stock look);
  * breach_N_damaged = the same panel rebuilt as wedge brushes around a RAGGED hole (front/back polygons at different radii -> splayed jagged edge with visible
    wall thickness), front faces textured by an affine fit of the stock surface (same texture + lightmap), edge faces burnt (vertex colours), back face capped,
    plus a scorch ring (decal shader textures/hzm/breach_scorch) hugging the hole polygon 1.2 u in front of the wall;
  * breach_N_interior = surface-only exposed interior behind the hole (back/side walls, collapsed floor + ceiling, rubble stones, girder, pipe, ember glow quads),
    vertex-lit with a warm fire-glow tint.
Entities: intact (svflags +broadcast), damaged (notsolid, hide, +broadcast), interior (hide, +broadcast). Models are local-coordinate, pivot = panel centre on the OUTER face."""
import os, sys, json, struct, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bspedit as E
import breachgeo as G
from make_subs import auto_surfaces
from make_chunks import read_vert, clip_poly, VF, INF, clip3

def box_sub(P, C):
    frame = []; mn = list(P[0]); mx = list(P[1])
    for a in range(3):
        if mn[a] < C[0][a] - 0.01:
            m = list(mx); m[a] = C[0][a]; frame.append((list(mn), m)); mn[a] = C[0][a]
        if mx[a] > C[1][a] + 0.01:
            n_ = list(mn); n_[a] = C[1][a]; frame.append((n_, list(mx))); mx[a] = C[1][a]
    return frame

def build(spec):
    b = E.Bsp(open(spec["src"], "rb").read())
    sh = b.shaders(); pl = b.planes(); names = [s[0] for s in sh]
    nodraw = names.index("textures/common/nodraw")
    shl = b.lumps[E.IX["shaders"]]
    dead = next((i for i, s in enumerate(sh) if s[0] == "textures/common/nodraw" and s[2] == 0), None)
    if dead is None:
        rec = bytearray(shl[nodraw * 140:nodraw * 140 + 140]); struct.pack_into("<i", rec, 68, 0); dead = len(sh); shl += rec; names.append(names[nodraw]); sh.append(sh[nodraw])
    def add_shader(name, surf_flags=0):
        if name in names: return names.index(name)
        rec = bytearray(140); nb = name.encode("latin1"); rec[:len(nb)] = nb; struct.pack_into("<3i", rec, 64, surf_flags, 0, 0)
        shl.extend(rec); names.append(name); sh.append((name, surf_flags, 0, 0, "")); return len(names) - 1
    SH_SCORCH = add_shader("textures/hzm/breach_scorch"); SH_GLOW = add_shader("textures/hzm/breach_glow"); SH_STREAK = add_shader("textures/hzm/breach_streak")
    # vertex-lit twins of the stock concrete/metal shaders: stock ones are tex x $lightmap, and with no lightmap (-1) they draw fullbright pale,
    # so exposed/damaged faces use single-stage rgbGen vertex shaders (defined in scripts/hzm_breach.shader) to take the burnt / fire-glow tint.
    TWIN = {"textures/general_structure/jh_conc512a": "textures/hzm/breach_conc_a", "textures/general_structure/jh_conc512b": "textures/hzm/breach_conc_b",
            "textures/general_structure/jh_conc512c": "textures/hzm/breach_conc_c", "textures/general_structure/conc_rough1": "textures/hzm/breach_rough",
            "textures/german/rusty_iron": "textures/hzm/breach_iron", "textures/mohcommon/ibeam_1a": "textures/hzm/breach_ibeam"}
    def vlit(idx):
        n = names[idx]
        return add_shader(TWIN[n]) if n in TWIN else idx
    plL, bl, sl, sfl, dvl, eqL, mdl, ixl = (b.lumps[E.IX[n]] for n in ("planes", "brushes", "brushsides", "surfaces", "drawverts", "sideeq", "models", "drawidx"))
    sf0 = bytes(sfl); dv0 = bytes(dvl); eq0 = bytes(eqL); ix0 = bytes(ixl)
    nsurf0 = len(sf0) // 108
    sbb = []
    for i in range(nsurf0):
        shn, fog, typ, fv, nv = struct.unpack_from("<5i", sf0, i * 108)
        if typ != 1 or nv <= 0: sbb.append(None); continue
        pts = [struct.unpack_from("<3f", dv0, (fv + k) * 44) for k in range(nv)]
        sbb.append(([min(p[j] for p in pts) for j in range(3)], [max(p[j] for p in pts) for j in range(3)], shn))
    cap_color = spec.get("cap_color", [130, 130, 135])
    ents = bytearray(b.get("ents")); add = ""
    report = []; claimed = set(); consumed_b = set(); consumed_s = set()
    st = {"model": len(mdl) // 40}

    def covered(a, c, rmn, rmx):
        for i, bb in enumerate(sbb):
            if bb is None: continue
            mn, mx, shn = bb
            if mx[a] - mn[a] > 1.5 or abs(mn[a] - c) > 1.5: continue
            if all(mx[k] > rmn[k] + 1 and mn[k] < rmx[k] - 1 for k in range(3) if k != a): return True
        return False

    def clip_surface_box(si_, bmn, bmx, o):
        shn, fog, typ, fv, nv, fi, ni = struct.unpack_from("<7i", sf0, si_ * 108)
        idx = struct.unpack_from("<%di" % ni, ix0, fi * 4); vo = []; io = []
        for t in range(0, ni, 3):
            poly = [read_vert(dv0, fv + idx[t + k]) for k in range(3)]
            for a in range(3):
                if poly: poly = clip_poly(poly, a, bmn[a], True)
                if poly: poly = clip_poly(poly, a, bmx[a], False)
            if len(poly) < 3: continue
            base = len(vo)
            for p in poly:
                q = list(p); q[0] -= o[0]; q[1] -= o[1]; q[2] -= o[2]; vo.append(q)
            for k in range(1, len(poly) - 1): io += [base, base + k, base + k + 1]
        return vo, io

    def emit_surface(rec, vo, io):
        struct.pack_into("<4i", rec, 12, len(dvl) // 44, len(vo), len(ixl) // 4, len(io))
        for q in vo: dvl.extend(struct.pack(VF, *q))
        ixl.extend(struct.pack("<%di" % len(io), *io)); sfl.extend(rec)

    def new_rec(shader, vo, io, lmnum=-1, lm=(0, 0, 0, 0), normal=(0, 0, 1), fog=-1):
        rec = bytearray(108)
        struct.pack_into("<12i", rec, 0, shader, fog, 1, 0, len(vo), 0, len(io), lmnum, *lm)
        struct.pack_into("<3f", rec, 48, 0, 0, 0); struct.pack_into("<9f", rec, 60, 0, 0, 0, 0, 0, 0, *normal)
        struct.pack_into("<2if", rec, 96, 0, 0, 0.0); return rec

    def poly_surface(shader, pts3, normal, o, st_fn, color_fn, lmnum=-1, lm=(0, 0, 0, 0), lmuv_fn=None):
        """pts3 world coords polygon (CCW outward). returns (rec, vo, io)"""
        pts3 = list(pts3)[::-1]   # engine front face = CW seen from outside (stock surfaces: cross.n < 0)
        vo = []
        for p in pts3:
            s, t = st_fn(p); ls, lt = lmuv_fn(p) if lmuv_fn else (0.0, 0.0); c = color_fn(p)
            vo.append([p[0] - o[0], p[1] - o[1], p[2] - o[2], s, t, ls, lt, normal[0], normal[1], normal[2], c[0], c[1], c[2], c[3] if len(c) > 3 else 255])
        io = []
        for k in range(1, len(vo) - 1): io += [0, k, k + 1]
        return new_rec(shader, vo, io, lmnum, lm, normal), vo, io

    def finish_model(mn_, mx_, nsf0, nsurf, nb0, nbr, name, o, keys):
        mdl.extend(struct.pack("<6f4i", *mn_, *mx_, nsf0, nsurf, nb0, nbr))
        nonlocal_add = chr(123) + chr(10) + "".join("\"%s\" \"%s\"" % kv + chr(10) for kv in (("model", "*%d" % st["model"]), ("classname", spec.get("entity_class", "script_object")), ("targetname", name), ("origin", "%g %g %g" % tuple(o))) + tuple(keys)) + chr(125) + chr(10)
        st["model"] += 1; return nonlocal_add

    # ------------------------------------------------------------------ a model made of carved box pieces of stock brushes
    def emit_pieces(name, pieces, o, ghosts, S, bsurf, keys, capshader, lo_hi_ghost=None):
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
            fs, n, shn, sides = b.brush(bid); ob = E.brush_aabb(b, bid, pl)
            bl.extend(struct.pack("<3i", ns, n, shn))
            for si, (pn, sshn, eq) in enumerate(sides):
                done = False
                for a in range(3):
                    if si == 2 * a and pmn[a] > ob[0][a] + 0.01:
                        nrm = [0, 0, 0]; nrm[a] = -1; sl.extend(struct.pack("<3i", np_(plane=(nrm[0], nrm[1], nrm[2], -pmn[a])), nodraw, ne(eq))); done = True
                    elif si == 2 * a + 1 and pmx[a] < ob[1][a] - 0.01:
                        nrm = [0, 0, 0]; nrm[a] = 1; sl.extend(struct.pack("<3i", np_(plane=(nrm[0], nrm[1], nrm[2], pmx[a])), nodraw, ne(eq))); done = True
                if not done: sl.extend(struct.pack("<3i", np_(pi=pn), sshn, ne(eq)))
            ns += n
        nsf0 = len(sfl) // 108; nsurf = 0; vmn = [1e9] * 3; vmx = [-1e9] * 3
        def track(vo):
            for q in vo:
                for k in range(3): vmn[k] = min(vmn[k], q[k]); vmx[k] = max(vmx[k], q[k])
        for bid, pmn, pmx in pieces:
            for si_ in bsurf[bid]:
                r = bytearray(sf0[si_ * 108:si_ * 108 + 108]); shn, fog, typ, fv, nv, fi, ni = struct.unpack_from("<7i", r, 0)
                lo3 = list(struct.unpack_from("<3f", r, 48)); struct.pack_into("<3f", r, 48, *[lo3[j] - o[j] for j in range(3)])
                if typ == 2:
                    pts = [read_vert(dv0, fv + k) for k in range(nv)]
                    c = [sum(p[a] for p in pts) / nv for a in range(3)]
                    if not all(pmn[a] <= c[a] <= pmx[a] for a in range(3)): continue
                    struct.pack_into("<i", r, 12, len(dvl) // 44)
                    for p in pts:
                        q = list(p); q[0] -= o[0]; q[1] -= o[1]; q[2] -= o[2]; dvl.extend(struct.pack(VF, *q)); track([q])
                    for off in (60, 72):
                        v3 = struct.unpack_from("<3f", r, off); struct.pack_into("<3f", r, off, *[v3[j] - o[j] for j in range(3)])
                    sfl.extend(r); nsurf += 1; consumed_s.add(si_); continue
                vo, io = clip_surface_box(si_, pmn, pmx, o); consumed_s.add(si_)
                if not io: continue
                emit_surface(r, vo, io); track(vo); nsurf += 1
        for si_ in ghosts:
            r = bytearray(sf0[si_ * 108:si_ * 108 + 108]); lo3 = list(struct.unpack_from("<3f", r, 48))
            struct.pack_into("<3f", r, 48, *[lo3[j] - o[j] for j in range(3)])
            bmn_, bmx_ = lo_hi_ghost
            vo, io = clip_surface_box(si_, bmn_, bmx_, o)
            if not io: continue
            emit_surface(r, vo, io); track(vo); nsurf += 1
        ncap = 0
        for bid, pmn, pmx in pieces:
            fs, n, shn, sides = b.brush(bid); other = []
            for pn, sshn, eq in sides:
                x, y, z, d = pl[pn]
                if max(abs(x), abs(y), abs(z)) < 0.9999: other.append(((x, y, z), d))
            for a in range(3):
                for s in (-1, 1):
                    c = pmx[a] if s > 0 else pmn[a]
                    rmn = list(pmn); rmx = list(pmx); rmn[a] = c - 0.5; rmx[a] = c + 0.5
                    if covered(a, c, rmn, rmx): continue
                    u, v = (a + 1) % 3, (a + 2) % 3; rect = []
                    for (pu, pv) in ((pmn[u], pmn[v]), (pmx[u], pmn[v]), (pmx[u], pmx[v]), (pmn[u], pmx[v])):
                        p = [0, 0, 0]; p[a] = c; p[u] = pu; p[v] = pv; rect.append(p)
                    for nrm, d in other: rect = clip3(rect, nrm, d) if rect else rect
                    if len(rect) < 3: continue
                    area = abs(sum(rect[i][u] * rect[(i + 1) % len(rect)][v] - rect[(i + 1) % len(rect)][u] * rect[i][v] for i in range(len(rect)))) / 2
                    if area < 16: continue
                    if s > 0: rect = rect[::-1]   # engine front face = CW seen from outside (stock: cross.n < 0)
                    nrmv = [0, 0, 0]; nrmv[a] = s
                    vo = [[p[0] - o[0], p[1] - o[1], p[2] - o[2], p[u] / 512.0, p[v] / 512.0, 0.0, 0.0, nrmv[0], nrmv[1], nrmv[2], cap_color[0], cap_color[1], cap_color[2], 255] for p in rect]
                    io = []
                    for k in range(1, len(vo) - 1): io += [0, k, k + 1]
                    emit_surface(new_rec(capshader(bid), vo, io, -1, (0, 0, 0, 0), nrmv), vo, io); track(vo); nsurf += 1; ncap += 1
        bmn = [min(p[1][k] for p in pieces) for k in range(3)]; bmx = [max(p[2][k] for p in pieces) for k in range(3)]
        mn_ = [min(bmn[j] - o[j], vmn[j]) for j in range(3)]; mx_ = [max(bmx[j] - o[j], vmx[j]) for j in range(3)]
        consumed_b.update(p[0] for p in pieces)
        return finish_model(mn_, mx_, nsf0, nsurf, nb0, len(pieces), name, o, keys), (nsurf, ncap, bmn, bmx)

    # ------------------------------------------------------------------ BREACH: damaged panel + interior
    def emit_b(rec, vo, io):
        emit_surface(rec, vo, io)
        if not spec.get("two_sided"): return
        r2 = bytearray(rec)
        vo2 = [list(q[:7]) + [-q[7], -q[8], -q[9]] + list(q[10:]) for q in vo]
        io2 = []
        for t in range(0, len(io), 3): io2 += [io[t], io[t + 2], io[t + 1]]
        emit_surface(r2, vo2, io2)

    def build_breach(S, B, centre_pieces, bsurf, capshader):
        nonlocal add
        n = B["axis"]; so = B["sign"]; u, v = (n + 1) % 3, (n + 2) % 3
        cmn = [min(p[1][k] for p in centre_pieces) for k in range(3)]; cmx = [max(p[2][k] for p in centre_pieces) for k in range(3)]
        nf = cmx[n] if so > 0 else cmn[n]; nb = cmn[n] if so > 0 else cmx[n]
        umin, umax, vmin, vmax = cmn[u], cmx[u], cmn[v], cmx[v]
        cu = B.get("cu", (umin + umax) / 2); cv = B.get("cv", (vmin + vmax) / 2)
        o = [0.0, 0.0, 0.0]; o[n] = nf; o[u] = (umin + umax) / 2; o[v] = (vmin + vmax) / 2; o = [round(x, 1) for x in o]
        def P3(pu, pv, pn):
            p = [0.0, 0.0, 0.0]; p[n] = pn; p[u] = pu; p[v] = pv; return p
        # stock front surface -> affine texture + lightmap fit
        front_si = None
        for i, bb in enumerate(sbb):
            if bb is None: continue
            mn, mx, shn = bb
            if mx[n] - mn[n] > 1.5 or abs(mn[n] - nf) > 1.5: continue
            sn = struct.unpack_from("<3f", dv0, struct.unpack_from("<i", sf0, i * 108 + 12)[0] * 44 + 28)
            if sn[n] * so < 0.9: continue
            if mn[u] <= umin + 2 and mx[u] >= umax - 2 and mn[v] <= vmin + 2 and mx[v] >= vmax - 2: front_si = i; break
        if front_si is None:
            for i, bb in enumerate(sbb):
                if bb and bb[1][n] - bb[0][n] <= 1.5 and abs(bb[0][n] - nf) <= 1.5 and bb[0][u] <= cu <= bb[1][u] and bb[0][v] <= cv <= bb[1][v]: front_si = i; break
        if front_si is not None:
            shn_f, fog_f, typ_f, fv_f, nv_f = struct.unpack_from("<5i", sf0, front_si * 108)
            lmn_f = struct.unpack_from("<5i", sf0, front_si * 108 + 28)
            vv = [read_vert(dv0, fv_f + k) for k in range(nv_f)]
            Mst = G.fit_affine([x[:3] for x in vv], [x[3:5] for x in vv]); Mlm = G.fit_affine([x[:3] for x in vv], [x[5:7] for x in vv])
            col0 = vv[0][10:14]
        else:   # no stock face (new roof cap): cap shader, planar uv, unlit
            shn_f = capshader(centre_pieces[0][0]); lmn_f = (-1, 0, 0, 0, 0)
            Mst = np.zeros((2, 4)); Mst[0, u] = 1 / 512.0; Mst[1, v] = 1 / 512.0; Mlm = np.zeros((2, 4)); col0 = tuple(cap_color) + (255,)
        concrete = shn_f
        # hole polygon
        rk = random.Random(B.get("seed", 1) * 131 + 7)
        K0 = B.get("K0") or rk.randint(12, 20)
        hole = G.make_hole2(cu, cv, B["hole_r"], K0, B.get("seed", 1), umin, umax, vmin, vmax)
        K = len(hole)
        dirs = [(math.cos(h[0]), math.sin(h[0])) for h in hole]
        Hf = [(cu + hole[k][1] * dirs[k][0], cv + hole[k][1] * dirs[k][1]) for k in range(K)]
        Hb = [(cu + hole[k][2] * dirs[k][0], cv + hole[k][2] * dirs[k][1]) for k in range(K)]
        Dfrac = [h[3] for h in hole]
        Oo = [G.ray_rect((cu, cv), dirs[k], umin, umax, vmin, vmax) for k in range(K)]
        corners = [(umax, vmax), (umin, vmax), (umin, vmin), (umax, vmin)]
        def ang(pt):
            a = math.atan2(pt[1] - cv, pt[0] - cu); return a if a >= hole[0][0] else a + 2 * math.pi
        nbl_0 = len(bl) // 12; nsurf_0 = len(sfl) // 108
        pmap = {}
        def np_(plane):
            key = tuple(round(x, 4) for x in plane)
            if key not in pmap:
                x, y, z, d = plane; pmap[key] = len(plL) // 16; plL.extend(struct.pack("<4f", x, y, z, d - (x * o[0] + y * o[1] + z * o[2])))
            return pmap[key]
        wall_shader_brush = struct.unpack_from("<3i", bl, centre_pieces[0][0] * 12)[2] if centre_pieces[0][0] * 12 + 12 <= len(bl) else 0
        orig_brush_sh = E.Bsp.brush(b, centre_pieces[0][0])[2]
        st_fn = lambda p: G.apply_affine(Mst, p)
        lm_fn = lambda p: G.apply_affine(Mlm, p)
        vmn = [1e9] * 3; vmx = [-1e9] * 3
        def track(vo):
            for q in vo:
                for k in range(3): vmn[k] = min(vmn[k], q[k]); vmx[k] = max(vmx[k], q[k])
        nsurf = 0; nbr = 0
        for k in range(K):
            k2 = (k + 1) % K
            a0, a1 = hole[k][0], hole[k2][0] if k2 else hole[0][0] + 2 * math.pi
            fpoly = [Hf[k], Oo[k]]
            cs = [c for c in corners if a0 < ang(c) % (2 * math.pi) + (0 if ang(c) % (2 * math.pi) >= a0 else 2 * math.pi) < a1]
            cs2 = []
            for c in corners:
                aa = math.atan2(c[1] - cv, c[0] - cu)
                while aa < a0: aa += 2 * math.pi
                if aa < a1 - 1e-6: cs2.append((aa, c))
            cs2.sort(); fpoly += [c for _, c in cs2]; fpoly += [Oo[k2], Hf[k2]]
            bpoly = [Hb[k], Oo[k]] + [c for _, c in cs2] + [Oo[k2], Hb[k2]]
            dk = lambda d: nf + (nb - nf) * d
            pts = [P3(p[0], p[1], nf) for p in fpoly] + [P3(bpoly[i][0], bpoly[i][1], dk(Dfrac[k]) if i == 0 else dk(Dfrac[k2]) if i == len(bpoly) - 1 else nb) for i in range(len(bpoly))]
            tags = ['Hf', 'O'] + ['O'] * len(cs2) + ['O', 'Hf'] + ['Hb', 'O'] + ['O'] * len(cs2) + ['O', 'Hb']
            faces = G.hull(pts)
            # brush: axial six first (bbox), then non-axial hull planes
            P = np.array(pts); bmn_ = P.min(0); bmx_ = P.max(0)
            sides = []
            for a in range(3):
                nrm = [0, 0, 0]; nrm[a] = -1; sides.append((-1 if a == 0 else 0, -1 if a == 1 else 0, -1 if a == 2 else 0, -bmn_[a]))
                nrm = [0, 0, 0]; nrm[a] = 1; sides.append((1 if a == 0 else 0, 1 if a == 1 else 0, 1 if a == 2 else 0, bmx_[a]))
            for f in faces:
                nn = f["n"]
                if max(abs(nn[0]), abs(nn[1]), abs(nn[2])) > 0.9999: continue
                sides.append((nn[0], nn[1], nn[2], f["d"]))
            s0 = len(sl) // 12
            bl.extend(struct.pack("<3i", s0, len(sides), orig_brush_sh))
            for sd in sides: sl.extend(struct.pack("<3i", np_(sd), capshader(centre_pieces[0][0]), 0))
            nbr += 1
            for f in faces:
                idx = f["idx"]; ftags = {tags[i] for i in idx}; nn = f["n"]
                fp = [pts[i] for i in idx]
                if abs(nn[n]) > 0.999 and all(abs(p[n] - nf) < 0.2 for p in fp): kind = 'front'
                elif abs(nn[n]) > 0.999 and all(abs(p[n] - nb) < 0.2 for p in fp): kind = 'back'
                else:
                    def onray(dd):
                        return all(abs((p[u] - cu) * dd[1] - (p[v] - cv) * dd[0]) < 0.8 for p in fp)
                    if onray(dirs[k]) or onray(dirs[k2]) or ftags == {'O'}: continue     # wedge interface / outer boundary
                    kind = 'edge'
                if kind == 'front':
                    rec, vo, io = poly_surface(concrete, fp, nn, o, st_fn, lambda p: col0, lmn_f[0], lmn_f[1:5], lm_fn)
                elif kind == 'back':
                    rec, vo, io = poly_surface(vlit(capshader(centre_pieces[0][0])), fp, nn, o, lambda p: (p[u] / 512.0, p[v] / 512.0), lambda p: (110, 92, 78, 255))
                else:
                    frnd = random.Random(B.get("seed", 1) * 7919 + nsurf * 31 + k)
                    spall = frnd.random() ** 1.6 * (1.0 if frnd.random() < 0.6 else 0.25)     # fresh pale concrete where the wall spalled back
                    def ecol(p, nf=nf, so=so, n=n, spall=spall):
                        t = min(1.0, max(0.0, (abs(p[n] - nf)) / max(1.0, abs(nf - nb))))
                        c = (44 + 70 * t, 36 + 56 * t, 32 + 44 * t)
                        return (int(c[0] * (1 - spall) + 150 * spall), int(c[1] * (1 - spall) + 128 * spall), int(c[2] * (1 - spall) + 108 * spall), 255)
                    uvf = (lambda p: (p[u] / 128.0, p[v] / 128.0 + p[n] / 128.0))
                    rec, vo, io = poly_surface(vlit(capshader(centre_pieces[0][0])), fp, nn, o, uvf, ecol)
                emit_b(rec, vo, io); track(vo); nsurf += 1
        # scorch ring (decal): uneven radius per vertex, taller toward "up" (blast heat), clamped to the panel
        srnd = random.Random(B.get("seed", 1) * 977 + 5)
        upaxis = 0 if (u == 2) else (1 if v == 2 else None)       # which of the (u,v) axes is world up (None for the roof)
        def updot(dd): return 0.0 if upaxis is None else dd[upaxis]
        offz = nf + so * 1.2
        nrm = [0.0, 0.0, 0.0]; nrm[n] = float(so)
        sc_r = []
        for k in range(K):
            up = max(0.0, updot(dirs[k]))
            sc_r.append(srnd.uniform(1.25, 2.05) + 0.85 * up * srnd.uniform(0.3, 1.0))
        def clampuv(p): return (min(max(p[0], umin), umax), min(max(p[1], vmin), vmax))
        Gp = [clampuv((cu + (Hf[k][0] - cu) * sc_r[k], cv + (Hf[k][1] - cv) * sc_r[k])) for k in range(K)]
        for k in range(K):
            k2 = (k + 1) % K
            q = [P3(Hf[k][0], Hf[k][1], offz), P3(Gp[k][0], Gp[k][1], offz), P3(Gp[k2][0], Gp[k2][1], offz), P3(Hf[k2][0], Hf[k2][1], offz)]
            uvs = [(0.0, k / K), (1.0, k / K), (1.0, (k + 1) / K), (0.0, (k + 1) / K)]
            ccw = np.cross(np.array(q[1]) - np.array(q[0]), np.array(q[2]) - np.array(q[0]))[n] * so > 0
            order = [0, 3, 2, 1] if ccw else [0, 1, 2, 3]
            vo = [[q[i][0] - o[0], q[i][1] - o[1], q[i][2] - o[2], uvs[i][0], uvs[i][1], 0.0, 0.0, nrm[0], nrm[1], nrm[2], 255, 255, 255, 255] for i in order]
            io = [0, 1, 2, 0, 2, 3]
            emit_b(new_rec(SH_SCORCH, vo, io, -1, (0, 0, 0, 0), nrm), vo, io); track(vo); nsurf += 1
        # soot streaks running up from the lip (smoke/blast direction); walls only, clipped to the panel
        if upaxis is not None:
            cand = [k for k in range(K) if updot(dirs[k]) > 0.15]
            srnd.shuffle(cand)
            for si, k in enumerate(cand[:srnd.randint(4, 7)]):
                base = (Hf[k][0] * 0.9 + cu * 0.1, Hf[k][1] * 0.9 + cv * 0.1)
                wd = srnd.uniform(14.0, 48.0); ln = srnd.uniform(0.7, 2.2) * B["hole_r"] * 0.9
                drift = srnd.uniform(-0.25, 0.25)
                upv = [0.0, 0.0]; upv[upaxis] = 1.0
                side = [0.0, 0.0]; side[1 - upaxis] = 1.0
                top = (base[0] + upv[0] * ln + side[0] * drift * ln, base[1] + upv[1] * ln + side[1] * drift * ln)
                top = clampuv(top)
                if math.hypot(top[0] - base[0], top[1] - base[1]) < 25: continue
                wb = wd; wt = wd * 0.55
                p0 = (base[0] - side[0] * wb / 2, base[1] - side[1] * wb / 2); p1 = (base[0] + side[0] * wb / 2, base[1] + side[1] * wb / 2)
                p2 = (top[0] + side[0] * wt / 2, top[1] + side[1] * wt / 2); p3 = (top[0] - side[0] * wt / 2, top[1] - side[1] * wt / 2)
                zz = nf + so * (1.25 + 0.04 * si)
                q = [P3(p[0], p[1], zz) for p in (clampuv(p0), clampuv(p1), clampuv(p2), clampuv(p3))]
                uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
                ccw = np.cross(np.array(q[1]) - np.array(q[0]), np.array(q[2]) - np.array(q[0]))[n] * so > 0
                order = [0, 3, 2, 1] if ccw else [0, 1, 2, 3]
                vo = [[q[i][0] - o[0], q[i][1] - o[1], q[i][2] - o[2], uvs[i][0], uvs[i][1], 0.0, 0.0, nrm[0], nrm[1], nrm[2], 255, 255, 255, 255] for i in order]
                io = [0, 1, 2, 0, 2, 3]
                emit_b(new_rec(SH_STREAK, vo, io, -1, (0, 0, 0, 0), nrm), vo, io); track(vo); nsurf += 1
        # exposed rebar stubs sticking out of the broken edge (toward the hole axis, slightly proud of the wall)
        iron = vlit(names.index("textures/german/rusty_iron")) if "textures/german/rusty_iron" in names else vlit(capshader(centre_pieces[0][0]))
        rrnd = random.Random(B.get("seed", 1) * 4001 + 11)
        def rbar(c0, c1, thick):
            a0 = np.array(c0); a1 = np.array(c1); dvec = a1 - a0; Ln = np.linalg.norm(dvec)
            if Ln < 1e-3: return 0
            e = dvec / Ln; ref = np.array([1.0, 0, 0]) if abs(e[0]) < 0.9 else np.array([0, 1.0, 0]); s1 = np.cross(e, ref); s1 /= np.linalg.norm(s1); s2 = np.cross(e, s1)
            pts_ = []
            for t in (0, 1):
                for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1)): pts_.append(list(a0 + dvec * t + s1 * sa * thick + s2 * sb * thick))
            cnt = 0
            for f in G.hull(pts_):
                fp = [pts_[i] for i in f["idx"]]
                rec, vo, io = poly_surface(iron, fp, f["n"], o, lambda p: ((p[0] + p[1] + p[2]) / 48.0, p[2] / 48.0), lambda p: (128, 78, 46, 255))
                emit_b(rec, vo, io); track(vo); cnt += 1
            return cnt
        nreb = rrnd.randint(3, 6)
        for ri in range(nreb):
            k = rrnd.randrange(K)
            t = rrnd.uniform(0.25, 0.75)
            pf = P3(Hf[k][0], Hf[k][1], nf); pb = P3(Hb[k][0], Hb[k][1], nf + (nb - nf) * Dfrac[k])
            pe = [pf[j] + (pb[j] - pf[j]) * t for j in range(3)]
            toc = np.array([0.0, 0.0, 0.0]); toc[u] = cu - pe[u]; toc[v] = cv - pe[v]
            if np.linalg.norm(toc) < 1e-3: continue
            toc /= np.linalg.norm(toc)
            outw = np.array([0.0, 0.0, 0.0]); outw[n] = so
            for br_i in range(rrnd.randint(1, 3)):            # a small bundle of bars at slightly different angles
                dirv = toc * rrnd.uniform(0.7, 1.0) + outw * rrnd.uniform(0.05, 0.45) + np.array([rrnd.uniform(-0.25, 0.25) for _ in range(3)])
                dirv /= np.linalg.norm(dirv)
                ln_ = rrnd.uniform(26.0, 78.0)
                p1_ = np.array(pe) + dirv * ln_ * 0.6
                p2_ = p1_ + (dirv + np.array([0, 0, -0.35])) * ln_ * 0.4                # last part droops a little
                nsurf += rbar(pe, p1_, 1.3) + rbar(list(p1_), list(p2_), 1.2)
        mn_ = [min(cmn[j] - o[j], vmn[j]) for j in range(3)]; mx_ = [max(cmx[j] - o[j], vmx[j]) for j in range(3)]
        dmg = finish_model(mn_, mx_, nsurf_0, nsurf, nbl_0, nbr, "breach_%d_damaged" % B["n"], o, (("notsolid", "1"), ("hide", "1"), ("svflags", "+broadcast")))
        add += dmg
        # ----------------------------------------------------------- interior (surface-only)
        rep = {"n": B["n"], "pivot": o, "normal": [(so if a == n else 0) for a in range(3)], "panel": [round(x) for x in cmn] + [round(x) for x in cmx],
               "hole_r": B["hole_r"], "front_surface": front_si}
        if B.get("interior", True):
            nsurf_1 = len(sfl) // 108; vmn[:] = [1e9] * 3; vmx[:] = [-1e9] * 3; ni_ = 0
            D = B.get("depth", 360); W = (umax - umin) + 240; Hh = (vmax - vmin) + 120
            inn = -so                      # inward direction along n
            wall_in = nb + inn * 6         # just behind the back face
            back = nb + inn * D
            ucl, ucr = (umin + umax) / 2 - W / 2, (umin + umax) / 2 + W / 2
            vfl = vmin - 30; vce = vmax + 60
            rnd = random.Random(B.get("seed", 1) * 7 + 3)
            warm = lambda p, base=(88, 70, 58): None
            def glow_col(p, k=1.0):
                # warm fire-glow: strongest low and near the hole axis
                du = (p[u] - cu) / (W / 2); dv = (p[v] - vfl) / max(1.0, vce - vfl); dn = abs(p[n] - nb) / D
                g = max(0.0, 1.0 - 0.55 * abs(du) - 0.35 * dn) * (1.0 - 0.45 * dv) * k
                return (int(min(255, 44 + 150 * g)), int(min(255, 36 + 70 * g)), int(min(255, 32 + 26 * g)), 255)
            def surf_quad(shader, qpts, nrm, k=1.0, scale=256.0):
                if np.cross(np.array(qpts[1]) - np.array(qpts[0]), np.array(qpts[2]) - np.array(qpts[0])) @ np.array(nrm) < 0: qpts = qpts[::-1]
                rec, vo, io = poly_surface(shader, qpts, nrm, o, lambda p: (p[(0 if False else 0)] * 0 + (p[u] + p[n]) / scale, (p[v] + p[n]) / scale), lambda p: glow_col(p, k))
                emit_b(rec, vo, io); track(vo)
            def nrmv(axis, sign): r = [0.0, 0.0, 0.0]; r[axis] = float(sign); return r
            conc = vlit(capshader(centre_pieces[0][0])); rough = vlit(names.index("textures/general_structure/conc_rough1")) if "textures/general_structure/conc_rough1" in names else conc
            girder = vlit(names.index("textures/mohcommon/ibeam_1a")) if "textures/mohcommon/ibeam_1a" in names else conc
            pipe = vlit(names.index("textures/german/rusty_iron")) if "textures/german/rusty_iron" in names else conc
            # back wall, side walls
            surf_quad(conc, [P3(ucl, vfl - 70, back), P3(ucr, vfl - 70, back), P3(ucr, vce, back), P3(ucl, vce, back)], nrmv(n, so)); ni_ += 1
            for uu, sg in ((ucl, 1), (ucr, -1)):
                surf_quad(conc, [P3(uu, vfl - 70, wall_in), P3(uu, vfl - 70, back), P3(uu, vce, back), P3(uu, vce, wall_in)], nrmv(u, sg)); ni_ += 1
            # collapsed floor: two slabs (front one level, back one dropped and tilted) + riser
            mid = nb + inn * (D * 0.45)
            surf_quad(conc, [P3(ucl, vfl, wall_in), P3(ucr, vfl, wall_in), P3(ucr, vfl, mid), P3(ucl, vfl, mid)], nrmv(v, 1)); ni_ += 1
            surf_quad(conc, [P3(ucl, vfl, mid), P3(ucr, vfl, mid), P3(ucr, vfl - 70, mid), P3(ucl, vfl - 70, mid)], nrmv(n, -inn)); ni_ += 1
            surf_quad(rough, [P3(ucl, vfl - 70, mid), P3((ucl + ucr) / 2 + 40, vfl - 70, mid), P3((ucl + ucr) / 2 + 40, vfl - 30, back), P3(ucl, vfl - 90, back)], nrmv(v, 1)); ni_ += 1
            surf_quad(rough, [P3((ucl + ucr) / 2 + 40, vfl - 70, mid), P3(ucr, vfl - 70, mid), P3(ucr, vfl - 100, back), P3((ucl + ucr) / 2 + 40, vfl - 30, back)], nrmv(v, 1)); ni_ += 1
            # collapsed ceiling: front part intact, back part sagging 110 u
            surf_quad(conc, [P3(ucl, vce, wall_in), P3(ucl, vce, mid), P3(ucr, vce, mid), P3(ucr, vce, wall_in)], nrmv(v, -1)); ni_ += 1
            surf_quad(rough, [P3(ucl, vce, mid), P3(ucl, vce - 110, back), P3(ucr, vce - 60, back), P3(ucr, vce, mid)], nrmv(v, -1)); ni_ += 1
            # hanging girder (box hull) slanting from ceiling to the floor + a torn pipe across the top
            def box_surfaces(c, hx, hy, hz, shader, yawdeg=0, tilt=0.0, k=1.0):
                pts = []
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        for sz in (-1, 1):
                            pts.append([sx * hx, sy * hy, sz * hz])
                R = np.array(pts)
                if tilt:
                    ca, sa = math.cos(tilt), math.sin(tilt); R = R @ np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]).T
                if yawdeg:
                    ca, sa = math.cos(math.radians(yawdeg)), math.sin(math.radians(yawdeg)); R = R @ np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]]).T
                R = R + np.array(c)
                for f in G.hull([list(r) for r in R]):
                    fp = [list(R[i]) for i in f["idx"]]
                    rec, vo, io = poly_surface(shader, fp, f["n"], o, lambda p: ((p[0] + p[1]) / 128.0, p[2] / 128.0), lambda p: glow_col(p, k)); emit_b(rec, vo, io); track(vo)
            # girder in WORLD axes: build in (u,v,n) frame then map
            def to_world(local_pts, c_u, c_v, c_n):
                out = []
                for lp in local_pts:
                    w = [0.0, 0.0, 0.0]; w[u] = c_u + lp[0]; w[v] = c_v + lp[1]; w[n] = c_n + lp[2]; out.append(w)
                return out
            def blob(cu_, cv_, cn_, r_, shader, k=1.0, npts=9):
                local = [[rnd.uniform(-1, 1) * r_, rnd.uniform(0.05, 1) * r_ * 0.7, rnd.uniform(-1, 1) * r_] for _ in range(npts)]
                wp = to_world(local, cu_, cv_, cn_)
                for f in G.hull(wp):
                    fp = [wp[i] for i in f["idx"]]
                    rec, vo, io = poly_surface(shader, fp, f["n"], o, lambda p: ((p[u] + p[n]) / 96.0, (p[v] + p[n]) / 96.0), lambda p: glow_col(p, k)); emit_b(rec, vo, io); track(vo)
            def beam(c0, c1, thick, shader, k=1.0):
                a0 = np.array(c0); a1 = np.array(c1); dvec = a1 - a0; L = np.linalg.norm(dvec); e = dvec / L
                ref = np.array([1.0, 0, 0]) if abs(e[0]) < 0.9 else np.array([0, 1.0, 0]); s1 = np.cross(e, ref); s1 /= np.linalg.norm(s1); s2 = np.cross(e, s1)
                pts = []
                for t in (0, 1):
                    for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1)): pts.append(list(a0 + dvec * t + s1 * sa * thick + s2 * sb * thick))
                for f in G.hull(pts):
                    fp = [pts[i] for i in f["idx"]]
                    rec, vo, io = poly_surface(shader, fp, f["n"], o, lambda p: ((p[0] + p[1] + p[2]) / 64.0, (p[2]) / 64.0), lambda p: glow_col(p, k)); emit_b(rec, vo, io); track(vo)
            cuu = (umin + umax) / 2
            beam(P3(cuu - W * 0.2, vce, mid + inn * 20), P3(cuu + W * 0.1, vfl - 40, mid + inn * 160), 9, girder)
            beam(P3(ucl, vce - 30, mid), P3(ucr, vce - 70, mid + inn * 40), 6, pipe, 0.9)
            beam(P3(cuu - W * 0.35, vfl - 20, wall_in + inn * 40), P3(cuu - W * 0.05, vfl + 60, mid + inn * 20), 5, girder)  # rebar-like bent bar
            for (du_, dn_, rr, kk) in ((-0.28, 0.12, 52, 1.1), (0.15, 0.2, 70, 1.15), (0.32, 0.08, 40, 1.0), (-0.05, 0.38, 60, 1.05)):
                blob(cuu + du_ * W, vfl + 10, nb + inn * (D * dn_ + 30), rr, rough, kk)
            # ember glow quads (additive) hanging in front of the rubble
            for du_, dn_, sz in ((-0.2, 0.25, 90), (0.2, 0.3, 120)):
                c_ = P3(cuu + du_ * W, vfl + 55, nb + inn * (D * dn_)); q = [P3(c_[u] - sz, c_[v] - sz * 0.6, c_[n]), P3(c_[u] + sz, c_[v] - sz * 0.6, c_[n]), P3(c_[u] + sz, c_[v] + sz, c_[n]), P3(c_[u] - sz, c_[v] + sz, c_[n])]
                if np.cross(np.array(q[1]) - np.array(q[0]), np.array(q[2]) - np.array(q[0])) @ np.array(nrmv(n, so)) < 0: q = q[::-1]
                uv = {0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)}
                vo = [[p[0] - o[0], p[1] - o[1], p[2] - o[2], 0, 0, 0, 0, nrmv(n, so)[0], nrmv(n, so)[1], nrmv(n, so)[2], 255, 255, 255, 255] for p in q]
                for i, uvp in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
                    vo[i][3], vo[i][4] = uvp
                emit_b(new_rec(SH_GLOW, vo, [0, 1, 2, 0, 2, 3], -1, (0, 0, 0, 0), nrmv(n, so)), vo, [0, 1, 2, 0, 2, 3]); track(vo)
            nsurf_i = len(sfl) // 108 - nsurf_1
            imn = [vmn[j] for j in range(3)]; imx = [vmx[j] for j in range(3)]
            inte = finish_model(imn, imx, nsurf_1, nsurf_i, len(bl) // 12, 0, "breach_%d_interior" % B["n"], o, (("hide", "1"), ("svflags", "+broadcast")))
            add += inte
            rep["interior_bbox_world"] = [round(imn[j] + o[j]) for j in range(3)] + [round(imx[j] + o[j]) for j in range(3)]; rep["interior_surfaces"] = nsurf_i
        rep["damaged_surfaces"] = nsurf; rep["damaged_brushes"] = nbr
        return rep

    # ------------------------------------------------------------------ main loop over structures
    for S in spec["structures"]:
        ax = S["axis"]; cuts = sorted(S["cuts"]); rng = list(zip([-INF] + cuts, cuts + [INF]))
        bsurf = {}; allpart = set()
        for bid in S["brushes"]:
            part = []
            bsurf[bid] = auto_surfaces(b, [bid], pl, dv0, sf0, claimed, partial=part)
            claimed.update(bsurf[bid]); allpart.update(part)
        ub_mn = [min(E.brush_aabb(b, bid, pl)[0][k] for bid in S["brushes"]) - 3 for k in range(3)]
        ub_mx = [max(E.brush_aabb(b, bid, pl)[1][k] for bid in S["brushes"]) + 3 for k in range(3)]
        ghosts = []
        for si_ in sorted(allpart - claimed):
            bb = sbb[si_]
            if bb and all(bb[0][k] >= ub_mn[k] and bb[1][k] <= ub_mx[k] for k in range(3)): ghosts.append(si_)
        claimed.update(ghosts)
        for x in S.get("surfaces_extra", []):
            if x not in claimed: ghosts.append(x); claimed.add(x)
        report.append(("GHOSTS", S["name"], ghosts))
        def capshader(bid, S=S):
            if S.get("cap_shader"): return names.index(S["cap_shader"])
            for sd in b.brush(bid)[3]:
                n_ = names[sd[1]]
                if not any(k in n_ for k in ("caulk", "nodraw", "clip", "hint", "skip", "sky", "shadow")): return sd[1]
            return names.index("textures/general_structure/jh_conc512b")
        for ci, (lo, hi) in enumerate(rng):
            pieces = []
            for bid in S["brushes"]:
                mn, mx = E.brush_aabb(b, bid, pl)
                if hi <= mn[ax] + 0.01 or lo >= mx[ax] - 0.01: continue
                pmn = list(mn); pmx = list(mx); pmn[ax] = max(mn[ax], lo); pmx[ax] = min(mx[ax], hi)
                pieces.append((bid, pmn, pmx))
            if not pieces: continue
            bmn = [min(p[1][k] for p in pieces) for k in range(3)]; bmx = [max(p[2][k] for p in pieces) for k in range(3)]
            o = [(bmn[0] + bmx[0]) / 2, (bmn[1] + bmx[1]) / 2, bmn[2] if S.get("pivot", "base") == "base" else (bmn[2] + bmx[2]) / 2]
            o = [round(v, 1) for v in o]
            # carve breach panels out of this chunk's pieces
            centres = {}
            cur = list(pieces)
            for B in S.get("breaches", []):
                Bm, BM = B["box"]; new = []; cen = []
                for (bid, pmn, pmx) in cur:
                    C0 = [max(pmn[k], Bm[k]) for k in range(3)]; C1 = [min(pmx[k], BM[k]) for k in range(3)]
                    if all(C1[k] - C0[k] > 0.5 for k in range(3)):
                        cen.append((bid, C0, C1))
                        for fm, fx in box_sub((pmn, pmx), (C0, C1)): new.append((bid, fm, fx))
                    else: new.append((bid, pmn, pmx))
                if cen: centres[B["n"]] = (B, cen); cur = new
            name = "crumble_%s_%d" % (S["name"], ci + 1)
            keys = tuple(spec.get("ent_keys", {}).items())
            ent, (nsurf, ncap, _, _) = emit_pieces(name, cur, o, ghosts, S, bsurf, keys, capshader, ([-INF] * 3 if lo < -INF / 2 else [-INF, -INF, -INF], [INF] * 3))
            add += ent
            report.append(("CHUNK", name, st["model"] - 1, S["name"], o, [round(v) for v in bmn], [round(v) for v in bmx], len(cur), nsurf, ncap))
            for nbr_, (B, cen) in centres.items():
                co = [0.0, 0.0, 0.0]
                n_ = B["axis"]; so = B["sign"]; u_, v_ = (n_ + 1) % 3, (n_ + 2) % 3
                cmn = [min(p[1][k] for p in cen) for k in range(3)]; cmx = [max(p[2][k] for p in cen) for k in range(3)]
                co[n_] = cmx[n_] if so > 0 else cmn[n_]; co[u_] = (cmn[u_] + cmx[u_]) / 2; co[v_] = (cmn[v_] + cmx[v_]) / 2; co = [round(x, 1) for x in co]
                ent, (ns2, nc2, _, _) = emit_pieces("breach_%d_intact" % B["n"], cen, co, [], S, bsurf, (("svflags", "+broadcast"),), capshader, ([-INF] * 3, [INF] * 3))
                add += ent
                rep = build_breach(S, B, cen, bsurf, capshader)
                rep["structure"] = S["name"]; rep["intact_surfaces"] = ns2; rep["chunk"] = name
                report.append(("BREACH", rep))
    for bid in consumed_b: struct.pack_into("<3i", bl, bid * 12, *b.brush(bid)[:2], dead)
    for si_ in consumed_s | claimed: struct.pack_into("<i", sfl, si_ * 108, nodraw)
    b.lumps[E.IX["ents"]] = bytearray(bytes(ents[:-1]) + add.encode("latin1") + b"\x00")
    open(spec["dst"], "wb").write(b.tobytes())
    return report

if __name__ == "__main__":
    for r in build(json.load(open(sys.argv[1]))): print(r)
