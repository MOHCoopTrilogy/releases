"""make_subs.py <spec.json> - promote brush+surface sets of ANY AA v19 BSP into new LOCAL-coordinate submodels (entity origin = pivot).
spec: {"src": "...bsp", "dst": "...bsp", "subs": [{"name": "x", "origin": [x,y,z], "brushes": [ids], "surfaces": [ids] | "auto"}], "entity_class": "script_object"}
Everything appended (indices of stock data never move); planes / verts / equations are copied shifted by -origin so the model rotates about its pivot;
drawindexes are shared (relative to firstVert). World copies: brush -> contents-0 nodraw clone, surface -> nodraw shader. Closed pose == stock (entity origin puts it back)."""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bspedit as E

def auto_surfaces(b, brush_ids, pl, dv, sf, claimed, tol=1.5, partial=None):
    """surfaces of type 1/2 fully inside one chosen brush's bounds (+tol), with the shader of one of that brush's sides and (planar) on one of its side planes.
    `claimed` (set) makes each surface belong to one submodel only; `partial` collects surfaces that touch a chosen brush's plane but stick out of its bounds (ghost-face risk)."""
    boxes = []
    for i in brush_ids:
        mn, mx = E.brush_aabb(b, i, pl); fs, ns, sh, sides = b.brush(i)
        boxes.append((mn, mx, [pl[s[0]] for s in sides], set(s[1] for s in sides)))
    out = []
    for i in range(len(sf) // 108):
        shn, fog, typ, fv, nv = struct.unpack_from("<5i", sf, i * 108)
        if typ not in (1, 2) or nv <= 0 or i in claimed: continue
        pts = [struct.unpack_from("<3f", dv, (fv + k) * 44) for k in range(nv)]
        for mn, mx, P, shs in boxes:
            if shn not in shs: continue
            inside = [all(mn[j] - tol <= p[j] <= mx[j] + tol for j in range(3)) for p in pts]
            onplane = typ == 2 or any(all(abs(q[0]*p[0] + q[1]*p[1] + q[2]*p[2] - q[3]) <= tol for p in pts) for q in P)
            if all(inside) and onplane: out.append(i); break
            if partial is not None and any(inside) and onplane: partial.append(i); break
    return out

def build(spec):
    b = E.Bsp(open(spec["src"], "rb").read())
    sh = b.shaders(); pl = b.planes()
    nodraw = next(i for i, s in enumerate(sh) if s[0] == "textures/common/nodraw")
    shl = b.lumps[E.IX["shaders"]]
    rec = bytearray(shl[nodraw * 140:nodraw * 140 + 140]); struct.pack_into("<i", rec, 68, 0)
    dead = len(sh); shl += rec
    plL, bl, sl, sfl, dvl, eqL, mdl = (b.lumps[E.IX[n]] for n in ("planes", "brushes", "brushsides", "surfaces", "drawverts", "sideeq", "models"))
    nmod0 = len(mdl) // 40; sf0 = bytes(sfl); dv0 = bytes(dvl); eq0 = bytes(eqL)
    ents = bytearray(b.get("ents")); assert ents.endswith(b"}\n\x00"); add = ""
    report = []; claimed = set()
    for k, S in enumerate(spec["subs"]):
        o = S["origin"]; bids = S["brushes"]
        part = []
        surfs = auto_surfaces(b, bids, pl, dv0, sf0, claimed, partial=part) if S.get("surfaces", "auto") == "auto" else S["surfaces"]
        surfs = list(surfs) + [x for x in S.get("surfaces_extra", []) if x not in surfs]
        claimed.update(surfs)
        assert not (set(bids) & set(spec.get("_used_b", []))), "brush reused"
        # planes
        pmap = {}
        def np_(pi):
            if pi not in pmap:
                x, y, z, d = pl[pi]; pmap[pi] = len(plL) // 16
                plL.extend(struct.pack("<4f", x, y, z, d - (x * o[0] + y * o[1] + z * o[2])))
            return pmap[pi]
        eqmap = {}
        def ne(ei):
            if ei < 0 or ei * 32 + 32 > len(eq0): return ei
            if ei not in eqmap:
                s4 = list(struct.unpack_from("<4f", eq0, ei * 32)); t4 = list(struct.unpack_from("<4f", eq0, ei * 32 + 16))
                s4[3] += s4[0] * o[0] + s4[1] * o[1] + s4[2] * o[2]; t4[3] += t4[0] * o[0] + t4[1] * o[1] + t4[2] * o[2]
                eqmap[ei] = len(eqL) // 32; eqL.extend(struct.pack("<4f", *s4) + struct.pack("<4f", *t4))
            return eqmap[ei]
        nb0, ns0 = len(bl) // 12, len(sl) // 12; ns = ns0; bmn = [1e9] * 3; bmx = [-1e9] * 3
        for i in bids:
            fs, n, shn, sides = b.brush(i); mn, mx = E.brush_aabb(b, i, pl)
            bmn = [min(bmn[j], mn[j]) for j in range(3)]; bmx = [max(bmx[j], mx[j]) for j in range(3)]
            bl.extend(struct.pack("<3i", ns, n, shn))
            for pn, sshn, eq in sides: sl.extend(struct.pack("<3i", np_(pn), sshn, ne(eq)))
            ns += n
        if not S.get("keep_world"): [struct.pack_into("<3i", bl, i * 12, *b.brush(i)[:2], dead) for i in bids]        # neutralise world copy (reads sides unchanged)
        nsf0 = len(sfl) // 108
        for i in surfs:
            r = bytearray(sf0[i * 108:i * 108 + 108]); shn, fog, typ, fv, nv = struct.unpack_from("<5i", r, 0)
            struct.pack_into("<i", r, 12, len(dvl) // 44)                                   # new firstVert
            for v in range(nv):
                x, y, z = struct.unpack_from("<3f", dv0, (fv + v) * 44); vr = bytearray(dv0[(fv + v) * 44:(fv + v) * 44 + 44])
                struct.pack_into("<3f", vr, 0, x - o[0], y - o[1], z - o[2]); dvl.extend(vr)
            # lightmapOrigin (floats 9..11 of the record after 9 ints) and, for patches, the two lod-bound vectors
            lo = list(struct.unpack_from("<3f", r, 48)); struct.pack_into("<3f", r, 48, *[lo[j] - o[j] for j in range(3)])
            if typ == 2:
                for off in (60, 72):
                    v3 = struct.unpack_from("<3f", r, off); struct.pack_into("<3f", r, off, *[v3[j] - o[j] for j in range(3)])
            sfl.extend(r)
            if not S.get("keep_world"): struct.pack_into("<i", sfl, i * 108, nodraw)
        mdl.extend(struct.pack("<6f4i", *[bmn[j] - o[j] for j in range(3)], *[bmx[j] - o[j] for j in range(3)], nsf0, len(surfs), nb0, len(bids)))
        add += '{\n"model" "*%d"\n"classname" "%s"\n"targetname" "%s"\n"origin" "%g %g %g"\n}\n' % (nmod0 + k, spec.get("entity_class", "script_object"), S["name"], *o)
        for kk, vv in S.get("ent_keys", {}).items(): add = add[:-2] + '"%s" "%s"\n}\n' % (kk, vv)
        report.append((S["name"], nmod0 + k, len(bids), len(surfs), [round(v) for v in bmn], [round(v) for v in bmx], surfs, sorted(set(part) - set(surfs))))
    for i in spec.get("static_hide", []):          # static model entries cannot be deleted without renumbering smidx/leaf refs: park them far below the map (never in frustum)
        z = struct.unpack_from("<f", b.lumps[E.IX["smdef"]], i * 164 + 136)[0]
        struct.pack_into("<f", b.lumps[E.IX["smdef"]], i * 164 + 136, z - 30000.0)
    names = {S["name"]: nmod0 + k for k, S in enumerate(spec["subs"])}
    for ent in spec.get("extra_ents", []):
        ent = {k: ("*%d" % names[v[1:]] if isinstance(v, str) and v.startswith("@") else v) for k, v in ent.items()}
        add += chr(123) + chr(10) + "".join("\"%s\" \"%s\"" % kv + chr(10) for kv in ent.items()) + chr(125) + chr(10)
    b.lumps[E.IX["ents"]] = bytearray(bytes(ents[:-1]) + add.encode("latin1") + b"\x00")
    open(spec["dst"], "wb").write(b.tobytes())
    return report
if __name__ == "__main__":
    for r in build(json.load(open(sys.argv[1]))): print(r[:6], "surfaces", len(r[6]), "PARTIAL(left in world)", r[7][:20])
