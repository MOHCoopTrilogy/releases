# -*- coding: utf-8 -*-
"""Read-only census of m3l2's ground: every BSP shader with its drawn area, ground share, world scale and
location; the WINNING shader definition (player stack, T6 precedence) and every copy of each image it names,
in engine lookup order (.dds first with r_ext_compressed_textures 1, then .jpg, then .tga).

    python analyze_m3l2.py [--map maps/m3l2.bsp] [--json out.json]

Single process. Reuses gen_terrain_pak_v3.Stack (retail paks + manifests/latest.json paks, FS_PathCmp order).
"""
import argparse, json, os, re, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "docs", "tools"))
import gen_terrain_pak_v3 as V3   # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
_TOK = re.compile(r'"[^"]*"|\{|\}|[^\s{}"]+')


def shader_blocks(txt):
    """{name lower: raw block text}"""
    txt2 = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    out, depth, name, start, buf = {}, 0, None, None, []
    for ln in txt2.replace("\r", "").split("\n"):
        clean = re.sub(r"//.*", "", ln)
        toks = _TOK.findall(clean)
        if depth > 0 or (toks and toks[0] == "{"):
            buf.append(ln)
        for t in toks:
            if t == "{":
                if depth == 0:
                    buf = [name or "", ln] if name else [ln]
                depth += 1
            elif t == "}":
                depth -= 1
                if depth == 0 and name is not None:
                    out.setdefault(name, "\n".join(buf))
                    name = None
            elif depth == 0:
                name = t.strip('"').lower().replace("\\", "/")
    return out


def winning_shader_defs(st):
    best = {}
    files = sorted(p for p in st.copies if p.startswith("scripts/") and p.endswith(".shader"))
    for path in files:
        i, m = st.winner(path)
        txt = st.read(i, m).decode("latin1")
        for nm, blk in shader_blocks(txt).items():
            old = best.get(nm)
            if old is None or i > old[0]:
                best[nm] = (i, path, blk)
    return best


def bsp_lumps(b):
    ident, version = struct.unpack_from("<4si", b, 0)
    n = 29 if version <= 18 else 28
    L = [struct.unpack_from("<ii", b, 12 + 8 * i) for i in range(n)]
    if version <= 18:
        L = L[:13] + L[14:]
    return lambda i: b[L[i][0]:L[i][0] + L[i][1]]


def census(b):
    lump = bsp_lumps(b)
    sh = lump(0)
    names = [sh[i * 140:i * 140 + 64].split(b"\0")[0].decode("latin1").lower().replace("\\", "/")
             for i in range(len(sh) // 140)]
    dv = lump(4)
    nv = len(dv) // 44
    V = np.frombuffer(dv[:nv * 44], dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2),
                                                     ("n", "<f4", 3), ("c", "u1", 4)]))
    IX = np.frombuffer(lump(5), "<i4")
    sfr = lump(3)
    S = {}
    def acc(sn):
        return S.setdefault(sn, dict(n=[0, 0, 0, 0], area=0.0, garea=0.0, U=[], pts=[], tris=[]))
    for i in range(len(sfr) // 108):
        sn, fog, st, fv, nvx, fi, nix = struct.unpack_from("<7i", sfr, i * 108)
        if not (0 <= sn < len(names)) or st not in (1, 2, 3):
            continue
        a = acc(sn)
        a["n"][st - 1] += 1
        if st in (1, 3) and nix >= 3:
            idx = IX[fi:fi + nix].reshape(-1, 3) + fv
        elif st == 2:
            pw, ph = struct.unpack_from("<2i", sfr, i * 108 + 96)
            if not (pw >= 2 and ph >= 2 and pw * ph == nvx):
                continue
            g = np.arange(pw * ph).reshape(ph, pw)
            q = np.stack([g[:-1, :-1].ravel(), g[:-1, 1:].ravel(), g[1:, :-1].ravel(), g[1:, 1:].ravel()], 1)
            idx = np.concatenate([q[:, [0, 1, 2]], q[:, [1, 3, 2]]]) + fv
        else:
            continue
        P = V["xyz"][idx].astype(np.float64)
        T = V["st"][idx].astype(np.float64)
        cr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ar = 0.5 * np.linalg.norm(cr, axis=1)
        nz = np.abs(cr[:, 2]) / np.maximum(np.linalg.norm(cr, axis=1), 1e-9)
        a["area"] += ar.sum()
        a["garea"] += ar[nz >= 0.7].sum()
        d1, d2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
        u = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]).sum()
        if ar.sum() > 1 and u > 1e-9:
            a["U"].append((float(np.sqrt(ar.sum() / u)), float(ar.sum())))
        for k in np.nonzero(nz >= 0.7)[0]:
            a["tris"].append((P[k].mean(0).tolist(), float(ar[k])))
    # terrain (LOD) patches: 388 bytes; x,y at +36? use the documented layout: flags(1) scale(1) lmCoords(2)
    # texCoords 8f @4, x,y (signed char *64) @36?  -> use the leaf-independent fields actually parsed below
    tr = lump(22)
    for i in range(len(tr) // 388):
        o = i * 388
        tc = struct.unpack_from("<8f", tr, o + 4)
        x, y = struct.unpack_from("<bb", tr, o + 36)
        iBaseHeight = struct.unpack_from("<h", tr, o + 38)[0]
        shn = struct.unpack_from("<H", tr, o + 40)[0]
        hts = np.frombuffer(tr[o + 304:o + 304 + 81], "u1")
        a = acc(shn)
        a["n"][3] += 1
        wx, wy = x * 64.0, y * 64.0
        wz = iBaseHeight + 2.0 * float(hts.mean())
        a["area"] += 512.0 * 512.0
        a["garea"] += 512.0 * 512.0
        a["pts"].append((wx + 256.0, wy + 256.0, wz))
        ss = max(abs(tc[4] - tc[0]), abs(tc[2] - tc[0]))
        tt = max(abs(tc[5] - tc[1]), abs(tc[3] - tc[1]))
        if ss > 1e-6 and tt > 1e-6:
            a["U"].append((512.0 / float(np.sqrt(ss * tt)), 512.0 * 512.0))
    ent = lump(14).decode("latin1", "replace")
    return names, S, ent


def image_copies(st, base):
    out = []
    for ext in (".dds", ".jpg", ".jpeg", ".tga", ".png"):
        cps = st.copies.get(base + ext, [])
        if cps:
            out.append((ext, [(st.name(i), m) for i, m in cps]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="maps/m3l2.bsp")
    ap.add_argument("--json")
    ap.add_argument("--min-garea", type=float, default=20000.0)
    a = ap.parse_args()
    st = V3.Stack(GOG)
    i, m = st.winner(a.map)
    print("BSP", a.map, "from", st.name(i))
    b = st.read(i, m)
    names, S, ent = census(b)
    defs = winning_shader_defs(st)
    table = V3.shader_table(st)
    rows = []
    for sn, s in S.items():
        nm = names[sn]
        U = None
        if s["U"]:
            v = np.array(sorted(s["U"]))
            cw = np.cumsum(v[:, 1])
            U = float(v[np.searchsorted(cw, cw[-1] / 2.0), 0])
        pts = [p for p, _ in s["tris"]] + list(s["pts"])
        bb = None
        if pts:
            P = np.array(pts)
            bb = [P.min(0).round().tolist(), P.max(0).round().tolist()]
        rows.append(dict(shader=nm, counts=s["n"], area=round(s["area"]), garea=round(s["garea"]), U=U, bbox=bb,
                         images=sorted(table.get(nm, {nm}))))
    rows.sort(key=lambda r: -r["garea"])
    print("\n%-52s %8s %10s %7s  %s" % ("shader", "pl/pa/ts/te", "ground u2", "U/rep", "bbox"))
    for r in rows:
        if r["garea"] < a.min_garea:
            continue
        c = r["counts"]
        print("%-52s %2d/%d/%d/%-3d %10d %7s  %s" % (r["shader"], c[0], c[1], c[2], c[3], r["garea"],
                                                   "%.0f" % r["U"] if r["U"] else "-", r["bbox"]))
    print("\n==== winning definitions + image copies (ground shaders)")
    for r in rows:
        if r["garea"] < a.min_garea:
            continue
        d = defs.get(r["shader"])
        print("\n##", r["shader"], "->", "NO DEF (image = name)" if d is None else "%s :: %s" % (st.name(d[0]), d[1]))
        if d:
            print(d[2])
        for im in r["images"]:
            for ext, cps in image_copies(st, im):
                print("   %s%s: %s" % (im, ext, " < ".join(n for n, _ in cps)))
    # remapshader / worldspawn keys
    for mm in re.finditer(r"\{[^{}]*\}", ent):
        blk = mm.group(0)
        if '"worldspawn"' in blk:
            print("\nworldspawn:", " ".join(blk.split()))
            break
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(dict(rows=rows), fh, indent=1)


if __name__ == "__main__":
    main()
