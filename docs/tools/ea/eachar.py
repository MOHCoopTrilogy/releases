#!/usr/bin/env python3
"""European Assault characters as MOHAA skeletal models (converter 0.7.23). Our own code, stdlib only; runs on the
PLAYER's PC inside the converter, and its output (mesh, textures) goes only into the player's own converted pak.

So far one character: the partisan woman of 1_11 (Body_MRpartisanFemaleA_LOD1, character RussianFemalePartisan),
which the build played with a stock male Soviet model (user decision 2026-11-12: "Just use her model").

Reverse-engineered 2026-11-12 on the user's own Xbox USA disc (1_11, level_a.str):
  - a character body is a self-contained ELF chunk (type 0x88c9c893; ELF at +0x20): symbols __Model:::<name>.mesh,
    __BBOX, per sub-mesh k __RM:::__GP_RM_<name>.mesh_k and __VB:::__GPvb_<s>_<k>_<name>.mesh, s = 16 position
    (f32 x3, metres, z up, facing +Y), 17 uv (f32 x2), 18 colour, 19 packed normal, 20 bone (u8 matrix slot x4, u8);
    each VB starts with a 20-byte header whose word 1 is its byte size (stride in word 2);
  - the sub-mesh's index strip: in its render-method record the words (1, X, count, X + 0x20) give a u16 triangle
    strip of `count` indices at .data + X + 0x20 (repeated indices restart the strip; the disc's winding is clockwise);
  - its textures: a character definition holds (model chunk id, 0x88c9c893) and, under key 0xa768ffbc, the
    (chunk id, 0x0c3ddc52) of its texture chunks (SHPX), the sub-meshes name their shape (BODY, CTR0) by relocation.
The skin: the stock human skeleton (german_officer.skd's bone block, read from the player's install) in a stock
standing pose (bone frames read from the engine, model space, cm; numbers below), scaled to her height with the arms
re-aimed at her own wrists; every vertex rides the nearest bone segment rigidly. The stock human animations drive it.
"""
import math
import struct
import zipfile
import glob
import os

import eacpt
import shpx

CHUNK_MODEL = 0x88c9c893
CHUNK_TEX = 0x0c3ddc52
KEY_TEXTURE = 0xa768ffbc
STOCK_SKD = "models/human/german_wehrmact_officer/german_officer.skd"
CHARS = [("Body_MRpartisanFemaleA_LOD1", "RussianFemalePartisan", "partisan_female")]

# the stock human skeleton in a standing pose (soviet_infantry1, AI off; gettagposition / gettagangles, model space cm,
# facing +X): position, (pitch, yaw, roll) - only the bones the skin uses
POSE = {
    "Bip01 Pelvis": ((-1.1, 0.08, 101.69), (-81.5, 86.0, 180.0)),
    "Bip01 Spine": ((-4.32, 1.29, 108.28), (-83.147, 156.656, 111.31)),
    "Bip01 Spine1": ((-5.78, 1.92, 121.45), (-72.634, -178.797, 89.486)),
    "Bip01 Spine2": ((-9.32, 1.84, 132.7), (-85.933, -26.444, -60.778)),
    "Bip01 Neck": ((-7.95, 1.16, 154.39), (-61.386, -0.924, -85.854)),
    "Bip01 Head": ((-4.97, 1.11, 159.85), (-78.0, -4.0, -90.0)),
    "eyes bone": ((0.11, 0.75, 169.5), (2.0, -4.0, 0.0)),
    "Bip01 L Clavicle": ((-2.42, 4.6, 146.14), (-6.283, 106.024, 2.96)),
    "Bip01 L UpperArm": ((-6.45, 18.63, 147.75), (76.852, 92.291, 27.705)),
    "Bip01 L Forearm": ((-6.68, 24.45, 122.82), (68.463, 5.352, -56.729)),
    "Bip01 L Hand": ((2.81, 25.34, 98.66), (62.906, 3.907, -146.392)),
    "Bip01 R Clavicle": ((-2.15, -1.18, 145.94), (-2.421, -100.521, 176.127)),
    "Bip01 R UpperArm": ((-4.82, -15.6, 146.56), (72.8, -112.997, 140.086)),
    "Bip01 R Forearm": ((-7.78, -22.57, 122.1), (73.728, -34.712, -144.044)),
    "Bip01 R Hand": ((-1.8, -26.71, 97.17), (69.346, -60.904, -81.444)),
    "Bip01 L Thigh": ((-0.47, 9.14, 100.33), (73.408, 86.94, 155.846)),
    "Bip01 L Calf": ((0.24, 22.35, 55.91), (71.783, 146.932, -146.455)),
    "Bip01 L Foot": ((-11.82, 30.21, 12.18), (80.442, 157.307, -161.852)),
    "Bip01 L Toe0": ((-5.29, 40.76, 0.72), (2.467, 49.342, 96.088)),
    "Bip01 R Thigh": ((-1.73, -8.98, 103.05), (84.895, -42.191, 54.283)),
    "Bip01 R Calf": ((1.32, -11.75, 56.88), (84.143, -156.109, -59.397)),
    "Bip01 R Foot": ((-2.97, -13.66, 11.08), (89.219, -64.922, 34.185)),
    "Bip01 R Toe0": ((9.74, -15.99, 0.2), (-0.439, -9.105, 89.354)),
}


def _chunks(d):
    n = struct.unpack_from("<I", d, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(d):
        cid, typ, sz, x = struct.unpack_from("<4I", d, p)
        if sz < 16:
            break
        yield p, cid, typ, sz
        p += sz


def _elf(d, e):
    shoff = struct.unpack_from("<I", d, e + 0x20)[0]
    shnum, shstr = struct.unpack_from("<HH", d, e + 0x30)
    sh = [struct.unpack_from("<10I", d, e + shoff + 40 * i) for i in range(shnum)]
    symk = next(i for i, s in enumerate(sh) if s[1] == 2)
    st = sh[sh[symk][6]]
    syms = {}
    for i in range(sh[symk][4], sh[symk][4] + sh[symk][5], 16):
        nm, val, size, info, oth, shn = struct.unpack_from("<IIIBBH", d, e + i)
        z = d.index(b"\0", e + st[4] + nm)
        syms[d[e + st[4] + nm:z].decode("latin-1")] = val
    datak = next(i for i, s in enumerate(sh) if s[1] == 1)
    relk = next((i for i, s in enumerate(sh) if s[1] == 9), None)
    names = [None] * (sh[symk][5] // 16)
    for j, i in enumerate(range(sh[symk][4], sh[symk][4] + sh[symk][5], 16)):
        nm = struct.unpack_from("<I", d, e + i)[0]
        z = d.index(b"\0", e + st[4] + nm)
        names[j] = d[e + st[4] + nm:z].decode("latin-1")
    rel = []
    if relk is not None:
        for i in range(sh[relk][4], sh[relk][4] + sh[relk][5], 8):
            off, info = struct.unpack_from("<II", d, e + i)
            rel.append((off, names[info >> 8]))
    return e + sh[datak][4], sh[datak][5], syms, rel


def _strip_tris(idx):
    return [t for t in eacpt.strip_tris(idx) if len(set(t)) == 3]


def read_model(d, name):
    """{meshes: [(pos, uv, tris, shape)], textures: {shape: shpx image}} or None"""
    key = ("__Model:::%s.mesh" % name).encode()
    at = d.find(key)
    if at < 0:
        return None
    for p, cid, typ, sz in _chunks(d):
        if typ == CHUNK_MODEL and p <= at < p + sz and d[p + 0x20:p + 0x24] == b"\x7fELF":
            break
    else:
        return None
    data, dsize, syms, rel = _elf(d, p + 0x20)
    rms = sorted((v, n) for n, v in syms.items() if n.startswith("__RM:::__GP_RM_%s.mesh_" % name))
    meshes = []
    for k, (rv, rn) in enumerate(rms):
        kk = rn.rsplit("_", 1)[1]
        vb = {s: syms.get("__VB:::__GPvb_%d_%s_%s.mesh" % (s, kk, name)) for s in (16, 17)}
        if None in vb.values():
            continue
        n = struct.unpack_from("<I", d, data + vb[16] + 4)[0] // 12
        pos = [struct.unpack_from("<3f", d, data + vb[16] + 20 + 12 * i) for i in range(n)]
        uv = [struct.unpack_from("<2f", d, data + vb[17] + 20 + 8 * i) for i in range(n)]
        hi = rms[k + 1][0] if k + 1 < len(rms) else dsize
        w = struct.unpack_from("<%dI" % ((hi - rv) // 4), d, data + rv)
        idx = None
        for i in range(len(w) - 3):
            if w[i] == 1 and 3 <= w[i + 2] < 65536 and w[i + 3] == w[i + 1] + 0x20 and w[i + 3] + 2 * w[i + 2] <= dsize:
                cand = struct.unpack_from("<%dH" % w[i + 2], d, data + w[i + 3])
                if max(cand) < n:
                    idx = cand
                    break
        if idx is None:
            continue
        shape, blend = None, False
        for off, sn in rel:
            if rv <= off < hi and "SHAPENAME=" in (sn or ""):
                shape = sn.split("SHAPENAME=")[1].split(",")[0]
            if rv <= off < hi and "GeoPrimState" in (sn or "") and "ABM_BLEND" in sn:
                blend = True
        # an alpha-blended sub-mesh (the face's eye cards, the cap) is cut out at half alpha: '#a' on its shape
        meshes.append((pos, uv, _strip_tris(idx), (shape + "#a") if shape and blend else shape))
    # textures: the character definition naming this model chunk lists its texture chunks
    tex_ids = []
    ref = struct.pack("<II", cid, CHUNK_MODEL)
    q = d.find(ref, p + sz)
    if q < 0:
        q = d.find(ref, 0, p)
    if q >= 0:
        for o in range(max(0, q - 600), q + 600, 4):
            if struct.unpack_from("<III", d, o)[:3] == (KEY_TEXTURE, 6, 8):
                tid, tty = struct.unpack_from("<II", d, o + 12)
                if tty == CHUNK_TEX and tid not in tex_ids:
                    tex_ids.append(tid)
    textures = {}
    for p2, cid2, typ2, sz2 in _chunks(d):
        if typ2 == CHUNK_TEX and cid2 in tex_ids:
            s = d.find(b"SHPX", p2, p2 + sz2)
            if s >= 0:
                for im in shpx.decode(d, s):
                    if im.get("rgba") is not None:
                        textures.setdefault(im["name"], im)
    return {"meshes": meshes, "textures": textures}


# ---------------- small vector helpers ----------------
def _sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def _add(a, b): return tuple(a[i] + b[i] for i in range(3))
def _mul(a, s): return tuple(v * s for v in a)
def _dot(a, b): return sum(a[i] * b[i] for i in range(3))
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    l = math.sqrt(_dot(a, a)) or 1.0
    return _mul(a, 1.0 / l)


def _axes(p, y, r):
    p, y, r = (math.radians(v) for v in (p, y, r))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    fwd = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return [fwd, _mul(right, -1.0), up]


def _rot_between(u, v):
    u, v = _norm(u), _norm(v)
    c = _dot(u, v)
    ax = _cross(u, v)
    s = math.sqrt(_dot(ax, ax))
    if s < 1e-6:
        return lambda x: x
    k = _mul(ax, 1.0 / s)
    return lambda x: _add(_add(_mul(x, c), _mul(_cross(k, x), s)), _mul(k, _dot(k, x) * (1 - c)))


def _stock_bones(mohaa_base):
    for pk in sorted(glob.glob(os.path.join(mohaa_base, "main", "*.pk3"))):
        try:
            z = zipfile.ZipFile(pk)
        except zipfile.BadZipFile:
            continue
        for n in z.namelist():
            if n.lower() == STOCK_SKD:
                b = z.read(n)
                nsurf, nbones, ofsb = struct.unpack_from("<3i", b, 72)
                o, idx = ofsb, {}
                for i in range(nbones):
                    idx[b[o:o + 32].split(b"\0")[0].decode()] = i
                    o += struct.unpack_from("<i", b, o + 80)[0]
                return b[ofsb:o], nbones, idx
    return None


def _tga(im):
    w, h, rgba = im["w"], im["h"], bytes(im["rgba"])
    px = bytearray(len(rgba))
    px[0::4], px[1::4], px[2::4], px[3::4] = rgba[2::4], rgba[1::4], rgba[0::4], rgba[3::4]
    return struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x28) + bytes(px)


def skin(model, bone_block, nbones, bidx, label):
    """SKD v5 bytes: her sub-meshes on the stock skeleton"""
    meshes = []
    for pos, uv, tris, shape in model["meshes"]:
        meshes.append(([(p[1] * 100.0, -p[0] * 100.0, p[2] * 100.0) for p in pos], uv, tris, shape))
    allv = [x for m in meshes for x in m[0]]
    r = max(v[2] for v in allv) / (POSE["eyes bone"][0][2] + 9.0)
    J = {nm: (_mul(p, r), _axes(*a)) for nm, (p, a) in POSE.items()}
    for side, sgn in (("L", 1), ("R", -1)):
        hand = [v for v in allv if sgn * v[1] > 45 and v[2] < 110]
        if not hand:
            continue
        tip = max(hand, key=lambda v: sgn * v[1])
        wr = [v for v in hand if sgn * v[1] > sgn * tip[1] - 14]
        wrist = tuple(sum(w[i] for w in wr) / len(wr) for i in range(3))
        sh = J["Bip01 %s UpperArm" % side][0]
        el = _add(sh, _mul(_sub(wrist, sh), 25.6 / (25.6 + 25.97)))
        hj = _add(sh, _mul(_sub(wrist, sh), 0.97))
        for bone, a, b in (("UpperArm", sh, el), ("Forearm", el, hj)):
            nm = "Bip01 %s %s" % (side, bone)
            R = _rot_between(J[nm][1][0], _sub(b, a))
            J[nm] = (a, [R(x) for x in J[nm][1]])
        nm = "Bip01 %s Hand" % side
        R = _rot_between(_axes(*POSE["Bip01 %s Forearm" % side][1])[0], _sub(hj, el))
        J[nm] = (hj, [R(x) for x in _axes(*POSE[nm][1])])
    seg_end = {"Bip01 Pelvis": "Bip01 Spine", "Bip01 Spine": "Bip01 Spine1", "Bip01 Spine1": "Bip01 Spine2",
               "Bip01 Spine2": "Bip01 Neck", "Bip01 Neck": "Bip01 Head", "Bip01 Head": None}
    for s in "LR":
        seg_end.update({"Bip01 %s Clavicle" % s: "Bip01 %s UpperArm" % s, "Bip01 %s UpperArm" % s: "Bip01 %s Forearm" % s,
                        "Bip01 %s Forearm" % s: "Bip01 %s Hand" % s, "Bip01 %s Hand" % s: None,
                        "Bip01 %s Thigh" % s: "Bip01 %s Calf" % s, "Bip01 %s Calf" % s: "Bip01 %s Foot" % s,
                        "Bip01 %s Foot" % s: "Bip01 %s Toe0" % s, "Bip01 %s Toe0" % s: None})
    seg = {}
    for bn, en in seg_end.items():
        a = J[bn][0]
        seg[bn] = (a, J[en][0] if en else _add(a, _mul(J[bn][1][0], 18.0 if bn == "Bip01 Head" else 10.0)))

    def dseg(p, a, e):
        d = _sub(e, a)
        t = max(0.0, min(1.0, _dot(_sub(p, a), d) / (_dot(d, d) or 1.0)))
        w = _sub(p, _add(a, _mul(d, t)))
        return math.sqrt(_dot(w, w)) + (6.0 if "Clavicle" in bn_ else 0.0)
    # her hem: the lowest point of the skirt's front / back flare (11 cm before or behind the body axis, within 10 cm of
    # the middle, so not the satchel on her side); thighs above it are under the skirt and ride the pelvis with it
    flare = [p[2] for m in meshes for p in m[0] if 40.0 < p[2] < 100.0 and abs(p[1]) < 10.0 and abs(p[0]) > 11.0]
    hem = min(flare) if flare else 1e9
    # a sub-mesh wholly at head height (her face, her cap) is a head piece
    head_mesh = [min(p[2] for p in m[0]) > J["Bip01 Neck"][0][2] - 12.0 for m in meshes]
    blobs, surf_names = [], []
    for k, (v, uv, tris, shape) in enumerate(meshes):
        nrm = [[0.0, 0.0, 0.0] for _ in v]
        for t in tris:
            fn = _cross(_sub(v[t[1]], v[t[0]]), _sub(v[t[2]], v[t[0]]))
            for j in t:
                for i in range(3):
                    nrm[j][i] -= fn[i]       # the disc's winding is clockwise: its face normals point inward
        # a strip can start on the other parity (the face sub-mesh does): outward test about the sub-mesh's centre;
        # inward -> flip its normals and its winding
        c = tuple(sum(p[i] for p in v) / len(v) for i in range(3))
        score = sum(1 if _dot(_norm(tuple(nrm[j])), _norm((p[0] - c[0], p[1] - c[1], 0.3 * (p[2] - c[2])))) > 0 else -1
                    for j, p in enumerate(v))
        flip = score < 0
        if flip:
            nrm = [[-x for x in n] for n in nrm]
        vb = bytearray()
        for j, p in enumerate(v):
            best, bd = None, 1e9
            for bn_ in seg:
                dd = dseg(p, *seg[bn_])
                if dd < bd:
                    best, bd = bn_, dd
            # skirt and coat-tail cloth (a thigh vertex more than 8 cm off the thigh bone) and the thighs under the skirt
            # ride the pelvis: on the thighs the panels swung apart and the legs pushed through with every stride
            if "Thigh" in best and (bd > 8.0 or p[2] > hem):
                best = "Bip01 Pelvis"
            # the head moves as one piece: the face and cap sub-meshes (bone slots 40-44 on the disc: her head bones)
            # and anything at head height ride the head bone; split over neck and spine, the face sheared and the
            # cap and hair slid over her eyes whenever the stock animations turned the head
            if head_mesh[k] or p[2] > J["Bip01 Head"][0][2] - 3.0:
                best = "Bip01 Head"
            bp, ax = J[best]
            dv = _sub(p, bp)
            nn = _norm(tuple(nrm[j]))
            vb += struct.pack("<3f2f2i", _dot(nn, ax[0]), _dot(nn, ax[1]), _dot(nn, ax[2]), uv[j][0], uv[j][1], 1, 0)
            vb += struct.pack("<if3f", bidx[best], 1.0, _dot(dv, ax[0]), _dot(dv, ax[1]), _dot(dv, ax[2]))
        tb = b"".join(struct.pack("<3i", *((t[0], t[1], t[2]) if flip else (t[0], t[2], t[1]))) for t in tris)
        nV, nT = len(v), len(tris)
        sn = "%s_%d" % (label, k)
        surf_names.append((sn, shape))
        ofsTri = 100
        ofsVerts = ofsTri + len(tb)
        ofsColl = ofsVerts + len(vb)
        ofsCollIdx = ofsColl + 4 * nV
        ofsEnd = ofsCollIdx + 4 * nV
        hdr = struct.pack("<4s64s8i", b"SKL ", sn.encode().ljust(64, b"\0"), nT, nV, 0, ofsTri, ofsVerts, ofsColl,
                          ofsEnd, ofsCollIdx)
        blobs.append(hdr + tb + bytes(vb) + struct.pack("<%di" % nV, *range(nV)) + struct.pack("<%di" % nV, *([0] * nV)))
    body = b"".join(blobs)
    total = 148 + len(bone_block) + len(body)
    head = struct.pack("<4si64s5i10i4i", b"SKMD", 5, ("ea_" + label).encode().ljust(64, b"\0"), len(blobs), nbones,
                       148, 148 + len(bone_block), total, *([0] * 10), 0, total, 0, total)
    return head + bone_block + body, surf_names


def build(stream, level, mohaa_base, files, lines, log=print):
    """write each known character's model into the converted pak; the data script names its .tik"""
    if not mohaa_base:
        return 0
    sk = _stock_bones(mohaa_base)
    if not sk:
        log("eachar: stock skeleton not found in the install; characters keep the stock models")
        return 0
    bone_block, nbones, bidx = sk
    made = 0
    for mname, chr_name, label in CHARS:
        m = read_model(stream, mname)
        if not m or not m["meshes"]:
            continue
        skd, surfs = skin(m, bone_block, nbones, bidx, label)
        mdir = "models/human/ea_%s" % level
        files["%s/%s.skd" % (mdir, label)] = skd
        shader_lines, tik_surf = [], []
        for sn, shape_f in surfs:
            shape, cut = (shape_f.split("#")[0], "#a" in shape_f) if shape_f else (None, False)
            im = m["textures"].get(shape) if shape else None
            if im is None:
                continue
            tname = "textures/ea_%s/%s_%s.tga" % (level, label, shape.lower())
            files[tname] = _tga(im)
            shname = "ea_%s_%s_%s%s" % (level, label, shape.lower(), "_a" if cut else "")
            if shname not in shader_lines:
                shader_lines.append(shname)
                files.setdefault("scripts/ea_%s_chars.shader" % level, b"")
                files["scripts/ea_%s_chars.shader" % level] += (
                    "%s\n{\n\tcull none\n\t{\n\t\tmap %s\n%s\t\trgbGen lightingSpherical\n\t}\n}\n\n" % (
                        shname, tname, "\t\talphaFunc GE128\n" if cut else "")).encode()
            tik_surf.append("\tsurface %s shader %s\n" % (sn, shname))
        tik = ("TIKI\nsetup\n{\n\tscale 0.52\n\tpath %s\n\tskelmodel %s.skd\n%s\tpath models/human/protoanimations\n"
               "\tradius 20\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname Actor\n\t\tsetsize \"-16 -16 0\" \"16 16 92\"\n"
               "\t\tamerican\n\t\thealth 100\n\t}\n}\n\n$include models/human/animation/dialogue/generic_dialogue_ru.tik\n"
               "$include models/human/new_generic_human.tik\n") % (mdir, label, "".join(tik_surf))
        tikp = "models/human/ea_%s_%s.tik" % (level, label)
        files[tikp] = tik.encode()
        lines.append('\tlevel.ea_chr_tik["%s"] = "%s"' % (chr_name, tikp))
        log("eachar: %s -> %s (%d sub-meshes, %d verts, textures %s)" % (
            mname, tikp, len(surfs), sum(len(x[0]) for x in m["meshes"]), sorted(m["textures"])))
        made += 1
    return made
