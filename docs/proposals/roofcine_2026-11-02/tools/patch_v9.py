"""patch_v9.py - derive make_chunks5.py (map v9) from the v7 builder make_chunks4_v7.py. Run once; the output is committed next to it.

v9 adds two breach-spec keys (everything else is byte-for-byte the v7 builder, which reproduces the shipped v7b map exactly):
  "notch": true      ROOF-EDGE NOTCH. The hole is centred ON the top edge of a wall panel (u axis must be world z): the panel is
                     doubled upward (virtual), the ragged hole is built as usual, then every surface of the damaged model is clipped at
                     the real top. Result: a jagged U bite out of the roofline, wall thickness showing on its flanks, soot below it.
                     Surface-only (no collision brushes: the roof is out of reach; the model is a cinematic prop like breach_N_interior).
                     The interior behind it is clipped at int_zmax (default top - 14): a roofless gutted room seen through the bite.
  "int_ceil": z      the interior's ceiling (its +u wall when u is world z) is capped at world z. Fixes the v7 top-tier interiors (sites 6,
                     18, 19, 20, 21) whose ceiling slab sat at z 1310, 95 u ABOVE the 1216 roof: after a breach it showed above the
                     skyline as a flat brown slab ("three giant tables on top of the structure", user 2026-11-02).
  "int_zmax": z      clip the interior model at world z (nothing of it can rise above the roofline)."""
import os
H = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(H, "v7", "make_chunks4_v7.py")).read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b, 1)


# 1. a generic "clip the surfaces appended since surface s0 to z <= zloc" pass (local model coords), returning the new bounds
rep('''    def new_rec(shader, vo, io, lmnum=-1, lm=(0, 0, 0, 0), normal=(0, 0, 1), fog=-1):''', '''    def clip_from(s0, zloc):
        """v9: clip every surface appended at index >= s0 to local z <= zloc; drops what is left with no area. Returns (min, max)."""
        recs = []
        for i in range(s0, len(sfl) // 108):
            rec = bytearray(sfl[i * 108:(i + 1) * 108])
            fv, nv, fi, ni = struct.unpack_from("<4i", rec, 12)
            vv = [read_vert(dvl, fv + k) for k in range(nv)]
            ii = struct.unpack_from("<%di" % ni, ixl, fi * 4)
            recs.append((rec, vv, ii))
        if not recs: return [0.0] * 3, [0.0] * 3
        fv0 = struct.unpack_from("<i", sfl, s0 * 108 + 12)[0]; fi0 = struct.unpack_from("<i", sfl, s0 * 108 + 20)[0]
        del sfl[s0 * 108:]; del dvl[fv0 * 44:]; del ixl[fi0 * 4:]
        lo = [1e9] * 3; hi = [-1e9] * 3
        for rec, vv, ii in recs:
            vo = []; io = []
            for t in range(0, len(ii), 3):
                poly = clip_poly([vv[ii[t]], vv[ii[t + 1]], vv[ii[t + 2]]], 2, zloc, False)
                if len(poly) < 3: continue
                base = len(vo); vo += [list(q) for q in poly]
                for k in range(1, len(poly) - 1): io += [base, base + k, base + k + 1]
            if not io: continue
            emit_surface(rec, vo, io)
            for q in vo:
                for k in range(3): lo[k] = min(lo[k], q[k]); hi[k] = max(hi[k], q[k])
        return lo, hi

    def new_rec(shader, vo, io, lmnum=-1, lm=(0, 0, 0, 0), normal=(0, 0, 1), fog=-1):''')

# 2. notch: virtual double-height panel, hole centred on the real top edge (after the stock front-face fit, which needs the real panel)
rep('''        concrete = shn_f
''', '''        concrete = shn_f
        notch = bool(B.get("notch")); ztop = None
        if notch:
            assert u == 2, "notch needs a wall whose u axis is world z"
            ztop = umax; umax = umax + (umax - umin); cu = B.get("cu", ztop)
''')

# 3. notch: no collision brushes for the damaged model
rep('''            s0 = len(sl) // 12
            bl.extend(struct.pack("<3i", s0, len(sides), orig_brush_sh))
            for sd in sides: sl.extend(struct.pack("<3i", np_(sd), capshader(centre_pieces[0][0]), 0))
            nbr += 1
''', '''            if not notch:
                s0 = len(sl) // 12
                bl.extend(struct.pack("<3i", s0, len(sides), orig_brush_sh))
                for sd in sides: sl.extend(struct.pack("<3i", np_(sd), capshader(centre_pieces[0][0]), 0))
                nbr += 1
''')

# 4. notch: clip the damaged model at the real top, then bound it by what is left
rep('''        mn_ = [min(cmn[j] - o[j], vmn[j]) for j in range(3)]; mx_ = [max(cmx[j] - o[j], vmx[j]) for j in range(3)]
        dmg = finish_model''', '''        if notch:
            lo_, hi_ = clip_from(nsurf_0, ztop - o[2]); nsurf = len(sfl) // 108 - nsurf_0
            vmn[:] = lo_; vmx[:] = hi_
            cmx = list(cmx); cmx[2] = min(cmx[2], ztop)
        mn_ = [min(cmn[j] - o[j], vmn[j]) for j in range(3)]; mx_ = [max(cmx[j] - o[j], vmx[j]) for j in range(3)]
        dmg = finish_model''')

# 5. interior: ceiling cap
rep('''            ucl, ucr = (umin + umax) / 2 - W / 2, (umin + umax) / 2 + W / 2
''', '''            ucl, ucr = (umin + umax) / 2 - W / 2, (umin + umax) / 2 + W / 2
            if B.get("int_ceil") is not None and u == 2: ucr = min(ucr, B["int_ceil"])
''')

# 6. interior: clip at int_zmax (notch default: just under the roofline)
rep('''            nsurf_i = len(sfl) // 108 - nsurf_1
            imn = [vmn[j] for j in range(3)]; imx = [vmx[j] for j in range(3)]''', '''            zmx = B.get("int_zmax", (ztop - 14) if notch else None)
            if zmx is not None:
                lo_, hi_ = clip_from(nsurf_1, zmx - o[2]); vmn[:] = lo_; vmx[:] = hi_
            nsurf_i = len(sfl) // 108 - nsurf_1
            imn = [vmn[j] for j in range(3)]; imx = [vmx[j] for j in range(3)]''')

rep('''from make_chunks import read_vert, clip_poly, VF, INF, clip3''', '''from make_chunks import read_vert, clip_poly, VF, INF, clip3   # v9: make_chunks5 = make_chunks4_v7 + notch / int_ceil / int_zmax''')
open(os.path.join(H, "v7", "make_chunks5.py"), "w").write(s)
print("make_chunks5.py written")
