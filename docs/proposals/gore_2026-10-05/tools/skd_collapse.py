"""Offline prototype: bone-chain COLLAPSE dismemberment on a real MOHAA .skd.

Parses an SKMD (v5/v6) model, builds a bind pose from the bones' base offsets (identity
rotations), skins every vertex, then re-skins with a limb chain collapsed: every bone in
the chain gets matrix = 0 and translation = the cut joint's position, which is exactly
what a renderer Hook (after ragdoll Hook A in R_AddSkelSurfaces) would write into the
skelBoneCache. Prints a weight census at each cut and renders before/after stills.
"""
import struct, sys, zipfile, glob, os
import numpy as np

PAK = "G:/GOG/Medal of Honor - Allied Assault War Chest/main/Pak0.pk3"


def cstr(b):
    i = b.find(b"\0")
    return (b[:i] if i >= 0 else b).decode("latin-1")


def load(member):
    with zipfile.ZipFile(PAK) as z:
        for n in z.namelist():
            if n.lower() == member.lower():
                return z.read(n)
    raise SystemExit("missing " + member)


def parse_skd(d):
    assert d[:4] == b"SKMD", d[:4]
    ver = struct.unpack_from("<i", d, 4)[0]
    numSurf, numBones, ofsBones, ofsSurf = struct.unpack_from("<iiii", d, 72)
    bones = []
    o = ofsBones
    for _ in range(numBones):
        name = cstr(d[o:o + 32]); parent = cstr(d[o + 32:o + 64])
        btype, ofsBase, ofsCh, ofsBN, ofsEnd = struct.unpack_from("<iiiii", d, o + 64)
        base = struct.unpack_from("<3f", d, o + ofsBase)
        if btype == 2:  # IKSHOULDER: quat then pos
            base = struct.unpack_from("<3f", d, o + ofsBase + 16)
        if btype == 6:  # AVROT
            base = struct.unpack_from("<3f", d, o + ofsBase + 4)
        if btype in (5, 10, 11):  # HOSEROT*
            base = struct.unpack_from("<3f", d, o + ofsBase + 12)
        if btype == 1:  # POSROT: placeholder 1,1,1 -> animated position
            base = (0.0, 0.0, 0.0)
        bones.append(dict(name=name, parent=parent, type=btype, base=np.array(base)))
        o += ofsEnd
    surfs = []
    o = ofsSurf
    for _ in range(numSurf):
        ident = d[o:o + 4]
        name = cstr(d[o + 4:o + 68])
        nTri, nVert, _sp, ofsTri, ofsVert, ofsCol, ofsEnd, ofsColIdx = struct.unpack_from("<8i", d, o + 68)
        tris = np.array(struct.unpack_from("<%di" % (nTri * 3), d, o + ofsTri)).reshape(-1, 3)
        verts = []; uvs = []
        p = o + ofsVert
        for _v in range(nVert):
            nx, ny, nz, u, v, nW, nM = struct.unpack_from("<5f2i", d, p); p += 28
            p += nM * 16
            uvs.append((u, v))
            ws = []
            for _w in range(nW):
                bi, bw, ox, oy, oz = struct.unpack_from("<if3f", d, p); p += 20
                ws.append((bi, bw, np.array((ox, oy, oz))))
            verts.append(ws)
        surfs.append(dict(name=name, tris=tris, verts=verts, uv=uvs))
        o += ofsEnd
    return ver, bones, surfs


def bind_positions(bones):
    idx = {b["name"]: i for i, b in enumerate(bones)}
    pos = [None] * len(bones)
    for i, b in enumerate(bones):
        p = b["parent"]
        pp = pos[idx[p]] if p in idx and pos[idx[p]] is not None else np.zeros(3)
        pos[i] = pp + b["base"]
    return pos, idx


def descendants(bones, idx, root):
    kids = {root}
    changed = True
    while changed:
        changed = False
        for b in bones:
            if b["parent"] in {bones[k]["name"] for k in kids} and idx[b["name"]] not in kids:
                kids.add(idx[b["name"]]); changed = True
    return kids


def skin(surf, pos, collapsed=None, cutpos=None):
    out = []
    for ws in surf["verts"]:
        v = np.zeros(3)
        for bi, bw, off in ws:
            if collapsed and bi in collapsed:
                v += bw * cutpos  # matrix 0, translation = cut joint
            else:
                v += bw * (pos[bi] + off)
        out.append(v)
    return np.array(out)


def main():
    member = sys.argv[1] if len(sys.argv) > 1 else "models/human/german_wehrmact_soldier/heerprivate.skd"
    ver, bones, surfs = parse_skd(load(member))
    pos, idx = bind_positions(bones)
    print("SKD v%d  bones=%d  surfaces=%s" % (ver, len(bones), [(s["name"], len(s["verts"]), len(s["tris"])) for s in surfs]))
    print("bones:", [b["name"] for b in bones])
    return ver, bones, surfs, pos, idx


if __name__ == "__main__":
    main()
