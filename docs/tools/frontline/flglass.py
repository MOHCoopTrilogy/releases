#!/usr/bin/env python3
"""Frontline's window glass (our code; runs inside the converter on the player's PC).

Frontline's glass panes are not in the level meshes: each pane exists only as collision of material 13 (+ the
special-surface bit) in the .cdb chunks, one pane per flag word (the pane's index sits in the high bits, 0x80000d,
0x80080d, ...), and the game draws it itself. Unconverted, every window of the level showed straight through to the
room behind (the Bazar de Varzy shop on 1_1: the inner door and crates instead of the original's dark glass).

panes() groups those triangles into panes (one per chunk + flag word; a pane two chunks both carry is kept once) and
leaves out the panes a drawn card already covers (a mesh triangle of one of `cover_tex`, coplanar within 2u, holding
the pane's centre): that card is the disc's own drawing of the pane. Gate: fl_levels.json "glass" per level.
"""
import math
import struct


def _normal(a, b, c):
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(sum(x * x for x in n))
    return None if ln < 1e-9 else tuple(x / ln for x in n)


def _inside(p, t, n, slack=1.0):
    def cr(o, x):
        u = [x[k] - o[k] for k in range(3)]
        v = [p[k] - o[k] for k in range(3)]
        w = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        return sum(w[k] * n[k] for k in range(3))
    s = (cr(t[0], t[1]), cr(t[1], t[2]), cr(t[2], t[0]))
    return all(x >= -slack for x in s) or all(x <= slack for x in s)


def panes(coll, X, cards, mat=13, special=1 << 23):
    """coll: [(chunk name, verts, [(a, b, c, flags)])] (disc); X: disc -> map; cards: drawn triangles (map units) of
    the textures that already draw a pane. Returns ([[tri, ...] per pane], report)."""
    groups = {}
    for name, vs, ts in coll:
        P = None
        for a, b, c, f in ts:
            if (f & 0x7FF) != mat or not (f & special):
                continue
            if P is None:
                P = [X(v) for v in vs]
            groups.setdefault((name, f), []).append((P[a], P[b], P[c]))
    seen = set()
    out = []
    rep = {"groups": len(groups), "panes": 0, "duplicates": 0, "covered": 0}
    cn = [(t, _normal(*t)) for t in cards]
    cn = [(t, n) for t, n in cn if n is not None]
    for key in sorted(groups):
        tris = groups[key]
        sig = tuple(sorted({tuple(round(q) for q in p) for t in tris for p in t}))
        if sig in seen:
            rep["duplicates"] += 1
            continue
        seen.add(sig)
        pts = [p for t in tris for p in t]
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        if any(abs(sum((c[k] - t[0][k]) * n[k] for k in range(3))) <= 2.0 and _inside(c, t, n) for t, n in cn):
            rep["covered"] += 1
            continue
        out.append(tris)
    rep["panes"] = len(out)
    return out, rep


def surface(tris, light):
    """one pane -> (verts, indexes) for flbsp.add_soup: planar st over the pane's own extent (0..1 on its two longest
    in-plane axes), so a pane texture maps once per pane."""
    n = None
    for t in tris:
        n = _normal(*t)
        if n:
            break
    n = n or (0.0, 0.0, 1.0)
    ax = sorted(range(3), key=lambda k: abs(n[k]))[:2]       # the two axes the plane spreads along
    if ax[0] == 2:
        ax = [ax[1], 2]                                       # upright panes: s across, t up
    pts = [p for t in tris for p in t]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    verts, idx = [], []
    for t in tris:
        for p in t:
            s = (p[ax[0]] - lo[ax[0]]) / max(1e-6, hi[ax[0]] - lo[ax[0]])
            tt = 1.0 - (p[ax[1]] - lo[ax[1]]) / max(1e-6, hi[ax[1]] - lo[ax[1]])
            idx.append(len(verts))
            verts.append((tuple(p), (s, tt), n, tuple(light) + (255,)))
    return verts, idx


# ---------------------------------------------------------------------------------------------------------------------
# [r100 glass_r100] the disc's own pane objects (decode: decodeaudit\fl\r100\blocks FINDINGS sections 3 + 4)
#
# Each cell's art (<level>_ART_c<n>.cpt) header words 11 / 12 = table offset / count of animated objects. Object k of
# cell c IS collision surface id k of chunk c (all 191 on 1_1 within 0.3 m): the breakable window panes. Per object
# (12 words): word 3 -> geometry (vb, ib, nv, ni at +12, 28-byte verts as the cell draws), words 5.. up to 5 frame
# texture records, word 10 flags (frames & 7, mode >> 3 & 3, delay >> 6 & 0xff). The quads are NOT in the cell draw
# list, so flcore.meshes() never yields them. 1_1: 191 panes, all play-once, 179 of 3 frames (intact, cracked,
# broken), 12 of 2, six texture sets.
def _rec_tex(L, cell, buf, h, ptr):
    """a texture record pointer of a cell -> flcore texture key (flcore.Level.meshes' resolve, same rules)"""
    S1, n1, S2, n2 = h[3], h[4], h[5], h[6]
    rec = struct.unpack_from("<32I", buf, ptr)
    k = L._tex_from(cell, buf, rec)
    if k:
        return k
    if S1 <= ptr < S1 + 128 * n1:
        return L.resolve_base(rec[31]) if rec[25] else None
    if S2 <= ptr < S2 + 128 * n2 and rec[31] < len(L.base_tex2):
        return L._tex_from(f"{L.level}_ART.cpt", L.base, L.base_tex2[rec[31]])
    return None


def art_panes(L):
    """every animated pane object of the level: dict(cell, obj, frames[keys], mode, delay, verts, uvs, cols, tris)
    in disc units (the flcore.meshes() layout)"""
    out = []
    for cell in L.cells:
        buf = L.comp[cell]
        h = struct.unpack_from("<16I", buf, 0)
        o, n = h[11], h[12]
        if not o or not n or o + 4 * n > len(buf):
            continue
        for i in range(n):
            p = struct.unpack_from("<I", buf, o + 4 * i)[0]
            w = struct.unpack_from("<12I", buf, p)
            vb, ib, nv, ni = struct.unpack_from("<IIHH", buf, w[3] + 12)
            if nv < 3 or ni < 3 or vb + 28 * nv > len(buf):
                continue
            verts, uvs, cols = [], [], []
            for k in range(nv):
                x, y, z, _n, col, u, v = struct.unpack_from("<3fII2f", buf, vb + 28 * k)
                verts.append((x, y, z))
                uvs.append((u, v))
                cols.append(((col >> 16) & 255, (col >> 8) & 255, col & 255, (col >> 24) & 255))
            idx = struct.unpack_from("<%dH" % ni, buf, ib)
            tris = []
            for t in range(ni - 2):
                a, b, c = idx[t], idx[t + 1], idx[t + 2]
                if a == b or b == c or a == c or max(a, b, c) >= nv:
                    continue
                tris.append((a, b, c) if t % 2 == 0 else (b, a, c))
            fl = w[10]
            frames = [_rec_tex(L, cell, buf, h, w[5 + k]) for k in range(fl & 7)]
            if not tris or not frames or frames[0] is None:
                continue
            out.append({"cell": cell, "obj": i, "frames": frames, "mode": (fl >> 3) & 3, "delay": (fl >> 6) & 0xFF,
                        "verts": verts, "uvs": uvs, "cols": cols, "tris": tris})
    return out


PAD = 4                                       # texels of edge repeat above / below each atlas slot (no seam bleed)


def atlas(L, frames):
    """frames (texture keys) -> (w, h, rgba, n, frame_h): the frames stacked top to bottom, each resized to frame 0's
    size and padded by PAD repeated edge rows, so the map shows frame k by shifting t by k / n"""
    t0 = L.texture(frames[0])
    W, H = t0["w"], t0["h"]
    rows = []
    for k in frames:
        t = (L.texture(k) if k else None) or t0
        if (t["w"], t["h"]) != (W, H):
            from PIL import Image
            t = {"w": W, "h": H, "rgba": Image.frombytes("RGBA", (t["w"], t["h"]), bytes(t["rgba"]))
                 .resize((W, H), Image.LANCZOS).tobytes()}
        fr = [bytes(t["rgba"][r * W * 4:(r + 1) * W * 4]) for r in range(H)]
        rows += [fr[0]] * PAD + fr + [fr[-1]] * PAD
    return W, len(rows), b"".join(rows), len(frames), H


def slot_t(v, H):
    """a frame-local t (0..1) -> t inside slot 0 of the padded atlas, in slot units (tcMod scale 1 1/n maps the slot)"""
    v = min(max(v, 0.0), 1.0)
    return (PAD + v * H) / (H + 2.0 * PAD)


def pane_shader(name, img, n):
    """[r100 glass_r100] a pane's frame atlas. `tcMod offset fromEntity fromEntity` adds the drawn entity's
    shader_data (cg_ents.c copies s.tag_num / s.skinNum raw; the script's `shader offset 0 <k / 16384>` packs k into
    skinNum, OFFSET_TO_PKT = x * 2^14), so t moves k whole units before `scale 1 1/n` picks one slot: frame k. A fresh
    entity has skinNum 0 = frame 0 (intact); s gets tag_num (-1 unbound), a whole number, invisible on these s-repeating
    panes. renderergl1 has the tcMod; renderergl2 has it from engine branch fl-glass-r100 (an older gl2 warns
    "unknown tcMod" once per shader and draws frame 0 always = a static pane)."""
    return (name + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tcull none\n\t{\n\t\tmap " + img
            + "\n\t\tblendFunc blend\n\t\trgbGen vertex\n\t\ttcMod offset fromEntity fromEntity\n"
            + "\t\ttcMod scale 1 %.6f\n\t}\n}\n" % (1.0 / n))


# ---------------------------------------------------------------------------------------------------------------------
# [r100 glass_r100] model lighting volumes (decode: blocks FINDINGS section 3; default rig: xemu RAM 0x1443f0, r100)
#
# <level>_P.bpd section 6 (header word pairs at 16 + 8 * i): 48-byte volumes = an axis-aligned box (6 f32), then
# (count, offset) of its planes and of its lights; 48-byte lights: type (1 ambient, 2 directional), 3 pad words, dir
# f32 x3, rgb f32 x3, scale f32. The game multiplies the scale by 2.2 at load. Characters, props, projectiles and held
# weapons draw with the set of the volume they stand in, else with the level's default rig (1 ambient + 3
# directional; on 1_1 two of the directionals are zero - read from RAM, the file that holds it is not identified).
def light_volumes(L):
    d = L.files.get(f"{L.level}_P.bpd")
    if not d or len(d) < 16 + 8 * 7:
        return []
    o, c = struct.unpack_from("<2I", d, 16 + 8 * 6)
    out = []
    for i in range(c):
        if o + 48 * (i + 1) > len(d):
            break
        bb = struct.unpack_from("<6f", d, o + 48 * i)
        _n1, _p1, n2, p2 = struct.unpack_from("<4I", d, o + 48 * i + 0x18)
        lights = []
        for k in range(n2):
            if p2 + 48 * (k + 1) > len(d):
                break
            w = struct.unpack_from("<I3I3f3ff", d, p2 + 48 * k)
            lights.append({"type": w[0], "dir": w[4:7], "rgb": w[7:10], "scale": w[10] * 2.2})
        out.append({"lo": bb[0:3], "hi": bb[3:6], "lights": lights})
    return out


def fold(lights, k_dir):
    """a disc light set -> one grid colour (0..255): ambient + k_dir x directional. The MOHAA grid holds one colour per
    cell and the converted map has no sun / sphere lights, so the light's direction is lost; k_dir is the share of
    the directional light a model shows on average (a judgement: fl_levels.json "model_light" "dir_fold")."""
    c = [0.0, 0.0, 0.0]
    for li in lights:
        f = li["scale"] * (1.0 if li["type"] == 1 else k_dir)
        for j in range(3):
            c[j] += li["rgb"][j] * f
    return tuple(min(255.0, 255.0 * x) for x in c)


def light_grid(L, X, spec):
    """fl_levels.json "model_light" -> flbsp.BSP.light_grid (map units): the default rig outdoors, each volume's set
    inside its box. None when the level has no (enabled) spec."""
    if not spec or not spec.get("enabled"):
        return None
    k = float(spec.get("dir_fold", 0.5))
    vols = light_volumes(L)
    boxes = []
    for v in vols:
        a, b = X(v["lo"]), X(v["hi"])
        boxes.append((tuple(min(a[j], b[j]) for j in range(3)), tuple(max(a[j], b[j]) for j in range(3)),
                      fold(v["lights"], k)))
    rig = [{"type": int(li["type"]), "rgb": li["rgb"], "scale": float(li["scale"])} for li in spec.get("default_rig", [])]
    return {"default": fold(rig, k) if rig else (150.0, 150.0, 150.0), "boxes": boxes, "volumes": len(vols)}


def emit(L, B, X, tdir, files, shader_lines, tga_bytes, surf_flags, spec):
    """[r100 glass_r100] fl_levels.json "glass" "source": "art": draw every pane object from its own quad, uvs, vertex
    colours and frame textures (one padded frame atlas + shader per texture set). "entities" (default true): each pane
    is its own inline model, script_object targetname fl_pane_f<frames> (the map steps a pane with `shader offset 0
    <k / 16384>`, clamped at frames - 1); false = static world surfaces showing frame 0. Returns the report."""
    panes = art_panes(L)
    ents = spec.get("entities", True)
    sh, rep = {}, {"source": "art", "panes": 0, "sets": 0, "entities": 0, "frames": {}}
    for p in panes:
        fr = tuple(p["frames"])
        if fr not in sh:
            w, h, rgba, n, fh = atlas(L, list(fr))
            short = fr[0].split("@")[-1]
            name = tdir + "hzm_pane_" + short + "_%d" % len(sh)
            files[name + ".tga"] = tga_bytes(w, h, rgba)
            shader_lines.append(pane_shader(name, name + ".tga", n))
            sh[fr] = (B.shader(name, surf_flags, 0), fh)
            rep["sets"] += 1
        six, fh = sh[fr]
        P = [tuple(X(v)) for v in p["verts"]]
        nrm = None
        for a, b, c in p["tris"]:
            nrm = _normal(P[a], P[b], P[c])
            if nrm:
                break
        nrm = nrm or (0.0, 0.0, 1.0)
        verts = [(P[i], (p["uvs"][i][0], slot_t(p["uvs"][i][1], fh)), nrm, tuple(p["cols"][i])) for i in range(len(P))]
        sid = B.add_soup(six, verts, [i for t in p["tris"] for i in t])
        rep["panes"] += 1
        k = str(len(fr))
        rep["frames"][k] = rep["frames"].get(k, 0) + 1
        if ents:
            B.models.append({"surfaces": [sid], "brushes": []})
            B.entity([("classname", "script_object"), ("model", "*%d" % len(B.models)),
                      ("targetname", "fl_pane_f%d" % len(fr))])
            rep["entities"] += 1
    return rep
