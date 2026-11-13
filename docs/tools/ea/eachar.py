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
import easkin
import shpx

CHUNK_MODEL = 0x88c9c893
CHUNK_TEX = 0x0c3ddc52
KEY_TEXTURE = 0xa768ffbc
STOCK_SKD = "models/human/german_wehrmact_officer/german_officer.skd"
# (disc body, the character names that wear it, label). Each is converted; the map script uses one only once it has
# passed the still-sheet QA (level.ea_chr_own[character], set from OWN below)
CHARS = [("Body_MRpartisanFemaleA_LOD1", ("RussianFemalePartisan",), "partisan_female"),
         ("Body_MGgermanInfantry_LOD1", ("GermanInfantryWinterizedA",), "german_infantry"),
         ("Body_MGofficer_LOD1", ("GermanOfficerA",), "german_officer"),
         ("Body_MGssOfficer_LOD1", ("Nemesis_WaffenSScommander",), "ss_officer"),
         ("Body_MRpartisanLeader_LOD1", ("PartisanLeader",), "partisan_leader"),
         ("Body_MRpartisan_LOD1", ("RussianPartisanA", "RussianPartisanA2", "RussianPartisanA3"), "partisan")]
# the characters whose own models have passed the client still sheet (face, front, side, back, run, fire, no breaks)
OWN = {"RussianFemalePartisan"}   # 2026-11-13 user approved her client sheet (SHEET_partisan_female_v1)

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
    # rows written bottom-up: the engine's TGA loader IGNORES the top-down flag (it warns "declares top-down image,
    # ignoring") - a top-down file loads upside down, which put her face texture on her legs and the boot on her face
    rows = [bytes(px[i * w * 4:(i + 1) * w * 4]) for i in range(h)]
    return struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08) + b"".join(reversed(rows))


def _mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(A, x):
    return tuple(A[i][0] * x[0] + A[i][1] * x[1] + A[i][2] * x[2] for i in range(3))


_I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _rot_mat(u, v):
    """the 3x3 matrix turning direction u onto direction v the short way (no twist about either)"""
    u, v = _norm(u), _norm(v)
    c = _dot(u, v)
    ax = _cross(u, v)
    s = math.sqrt(_dot(ax, ax))
    if s < 1e-9:
        if c > 0:
            return [r[:] for r in _I3]
        p = _norm(_cross(u, (1.0, 0.0, 0.0) if abs(u[0]) < 0.9 else (0.0, 1.0, 0.0)))
        return [[2 * p[i] * p[j] - (1.0 if i == j else 0.0) for j in range(3)] for i in range(3)]
    k = _mul(ax, 1.0 / s)
    K = [[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]]
    K2 = _mm(K, K)
    return [[_I3[i][j] + s * K[i][j] + (1 - c) * K2[i][j] for j in range(3)] for i in range(3)]


# Re-posing a disc body onto the stock skeleton. Each piece is a group of EA bones that moves as one: its EA joint ->
# tip direction is turned onto the stock bone's joint -> tip direction (the turn chained from the parent piece, so a
# limb swings without twisting), its EA joint lands on the stock joint (or, 'chain', where the parent piece carries
# it), and it is stretched along that direction to the stock bone length ('stretch'; 'rigid' keeps her own size).
# (piece, EA bones, EA joint, EA tip, stock joint, stock tip, parent, mode)
#   an EA tip is a bone, a pair of bones (their midpoint), or ('fwd', bone) = 6 cm straight ahead of that bone;
#   a stock tip ('x', bone) is that bone's own x axis.
def _pieces():
    P = [("torso", ("character_root", "JO_anchor", "JO_csw", "JO_pelvis", "JO_lumbar1", "JO_lumbar2", "JO_thoracic",
                    "JO_aim"), "JO_pelvis", "JO_neck", "Bip01 Pelvis", "Bip01 Neck", None, "stretch"),
         ("neck", ("JO_neck",), "JO_neck", "JO_head", "Bip01 Neck", "Bip01 Head", "torso", "rigid"),
         ("head", ("JO_head", "JO_helmet", "JO_jaw", "JO_bonehead", "JO_eyeLid_L", "JO_eyeLid_R", "JO_brow_L",
                   "JO_brow_R"), "JO_head", ("fwd", "JO_head"), "Bip01 Head", ("x", "eyes bone"), "neck", "chain")]
    # (the head: her straight-ahead gaze onto the stock 'eyes bone' x axis, which is the stock gaze; the eye
    # POSITIONS differ - the stock eyes sit 62 degrees above the head joint, hers 33 - and aiming one at the
    # other tipped her face 29 degrees up)
    for s in "LR":
        fing = tuple("JO_%s%s_%s" % (f, j, s) for f in ("thm", "pnt", "rng") for j in "ABC")
        P += [("clav" + s, ("JO_clavicleScapula_" + s,), "JO_clavicleScapula_" + s, "JO_shoulder_" + s,
               "Bip01 %s Clavicle" % s, "Bip01 %s UpperArm" % s, "torso", "stretch"),
              ("upper" + s, ("JO_shoulder_" + s, "JO_uparm_" + s), "JO_shoulder_" + s, "JO_elbow_" + s,
               "Bip01 %s UpperArm" % s, "Bip01 %s Forearm" % s, "clav" + s, "stretch"),
              ("fore" + s, ("JO_elbow_" + s, "JO_loarm_" + s), "JO_elbow_" + s, "JO_wrist_" + s,
               "Bip01 %s Forearm" % s, "Bip01 %s Hand" % s, "upper" + s, "stretch"),
              ("hand" + s, ("JO_wrist_" + s, "JO_object_" + s) + fing, "JO_wrist_" + s,
               ("JO_pntA_" + s, "JO_rngA_" + s), "Bip01 %s Hand" % s, ("x", "Bip01 %s Hand" % s), "fore" + s, "rigid"),
              ("thigh" + s, ("JO_hip_" + s,), "JO_hip_" + s, "JO_knee_" + s, "Bip01 %s Thigh" % s,
               "Bip01 %s Calf" % s, "torso", "stretch"),
              ("calf" + s, ("JO_knee_" + s,), "JO_knee_" + s, "JO_ankle_" + s, "Bip01 %s Calf" % s,
               "Bip01 %s Foot" % s, "thigh" + s, "stretch"),
              ("foot" + s, ("JO_ankle_" + s,), "JO_ankle_" + s, "JO_ball_" + s, "Bip01 %s Foot" % s,
               "Bip01 %s Toe0" % s, "calf" + s, "stretch"),
              ("toe" + s, ("JO_ball_" + s,), "JO_ball_" + s, ("fwd", "JO_ball_" + s), "Bip01 %s Toe0" % s,
               ("x", "Bip01 %s Toe0" % s), "foot" + s, "rigid")]
    return P


def _xf(t, x):
    a, sa, R, u, k = t
    r = _mv(R, _sub(x, a))
    return _add(sa, _add(r, _mul(u, (k - 1.0) * _dot(r, u))))


def repose(skel, pose):
    """({EA bone index: (EA joint, stock joint, R, axis, k)}, s): the transforms carrying her bind pose (EA model space
    turned to MOHAA's: (y, -x, z) x 100 x s) onto the stock pose {bone: (pos, axes)}; s = her girth scale"""
    byname = {b["name"]: i for i, b in enumerate(skel)}
    ea = lambda nm: skel[byname[nm]]["pos"]
    s = math.dist(pose["Bip01 Pelvis"][0], pose["Bip01 Neck"][0]) / (100.0 * math.dist(ea("JO_pelvis"), ea("JO_neck")))
    E = {b["name"]: (b["pos"][1] * 100.0 * s, -b["pos"][0] * 100.0 * s, b["pos"][2] * 100.0 * s) for b in skel}

    def ea_pt(t):
        if isinstance(t, str):
            return E[t]
        if t[0] == "fwd":
            return _add(E[t[1]], (6.0, 0.0, 0.0))
        return _mul(_add(E[t[0]], E[t[1]]), 0.5)
    out, piece = {}, {}
    for name, bones, ej, et, sj, stp, parent, mode in _pieces():
        if ej not in E or sj not in pose:
            continue
        a, b = E[ej], ea_pt(et)
        sa = pose[sj][0]
        sb = _add(sa, _mul(pose[stp[1]][1][0], math.dist(a, b))) if isinstance(stp, tuple) else pose[stp][0]
        R0 = piece[parent][2] if parent in piece else _I3
        R = _mm(_rot_mat(_mv(R0, _sub(b, a)), _sub(sb, sa)), R0)
        u = _norm(_sub(sb, sa))
        k = max(0.6, min(1.6, math.dist(sa, sb) / max(0.1, math.dist(a, b)))) if mode == "stretch" else 1.0
        if mode == "chain" and parent in piece:
            sa = _xf(piece[parent], a)
        piece[name] = (a, sa, R, u, k)
        for bn in bones:
            if bn in byname:
                out[byname[bn]] = piece[name]
    # fingers: her bind hand is flat; the stock hands are modelled in a grip (the stock animations never move
    # fingers), so her fingers are curled toward the palm at each knuckle before the hand piece carries them
    for side in "LR":
        h = piece.get("hand" + side)
        w, kn = "JO_wrist_" + side, ("JO_pntA_" + side, "JO_rngA_" + side)
        if not h or w not in E or any(x not in E for x in kn):
            continue
        hu = _norm(_sub(ea_pt(kn), E[w]))
        across = _sub(E[kn[0]], E[kn[1]])
        pn = _norm(_cross(hu, across))
        mid = _mul(_add(E["JO_pelvis"], E["JO_neck"]), 0.5)
        if _dot(pn, _sub(mid, E[w])) < 0:           # the palm faces her body in the A-pose
            pn = _mul(pn, -1.0)
        for f, angs in (("pnt", FINGER_CURL), ("rng", FINGER_CURL), ("thm", THUMB_CURL)):
            M, t = h[2], _sub(h[1], _mv(h[2], h[0]))     # the hand piece as x -> M x + t
            for j, ang in zip("ABC", angs):
                jn = "JO_%s%s_%s" % (f, j, side)
                if jn not in E:
                    break
                nxt = "JO_%s%s_%s" % (f, chr(ord(j) + 1), side)
                fd = _norm(_sub(E[nxt], E[jn])) if nxt in E else hu
                Rc = _axis_rot(_norm(_cross(fd, pn)), math.radians(ang))
                # compose: x -> M (p + Rc (x - p)) + t
                p = E[jn]
                t = _add(t, _mv(M, _sub(p, _mv(Rc, p))))
                M = _mm(M, Rc)
                if jn in byname:
                    out[byname[jn]] = ((0.0, 0.0, 0.0), t, M, h[3], 1.0)
    return out, s


FINGER_CURL = (30.0, 45.0, 30.0)      # knuckle, middle, tip
THUMB_CURL = (10.0, 15.0, 15.0)


def _axis_rot(k, a):
    c, s = math.cos(a), math.sin(a)
    K = [[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]]
    K2 = _mm(K, K)
    return [[_I3[i][j] + s * K[i][j] + (1 - c) * K2[i][j] for j in range(3)] for i in range(3)]


# One level of Loop subdivision on the body sub-meshes (user decision 2026-11-13, option C: rounder elbows, knees and
# shoulders, no bloat), the Loop positions blended with the plain midpoint split by SMOOTH (1 = full Loop, which
# shrinks the mesh); weights and uvs interpolated linearly; head and neck vertices keep their place. All or nothing per
# character: if one body sub-mesh would pass the engine's 2,048 vertices per surface (2,000 kept as margin), the
# character keeps its own mesh (its upscaled textures still apply). SUBDIV: per-label override (0 = off).
SMOOTH = 0.6
SUBDIV = {}
SUBDIV_MAX = 2000


def _edge_count(tris):
    return len({(min(a, b), max(a, b)) for t in tris for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0]))})


def _subdivide(V, N, W, uv, tris, k):
    edges = {}
    for t in tris:
        for a, b, c in ((t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1])):
            edges.setdefault((min(a, b), max(a, b)), []).append(c)
    nb = [set() for _ in V]
    bnd = [[] for _ in V]
    # the body only: anything riding the head or neck keeps its shape (the face shrank off its mouth card)
    kv = [0.0 if any(bn in ("Bip01 Head", "Bip01 Neck") for bn, _w in w) else 1.0 for w in W]
    for (a, b), opp in edges.items():
        nb[a].add(b)
        nb[b].add(a)
        if len(opp) != 2:
            bnd[a].append(b)
            bnd[b].append(a)

    def mixw(ws):
        acc = {}
        for wl, f in ws:
            for bn, w in wl:
                acc[bn] = acc.get(bn, 0.0) + w * f
        return sorted(acc.items(), key=lambda q: -q[1])
    V2, N2, W2, uv2 = [], list(N), list(W), list(uv)
    for i, v in enumerate(V):
        if bnd[i]:
            if len(bnd[i]) == 2:
                lp = _add(_mul(v, 0.75), _mul(_add(V[bnd[i][0]], V[bnd[i][1]]), 0.125))
            else:
                lp = v                        # a corner / non-manifold vertex stays put
        else:
            n = len(nb[i])
            beta = 3.0 / 16.0 if n == 3 else 3.0 / (8.0 * n)
            s = (0.0, 0.0, 0.0)
            for j in nb[i]:
                s = _add(s, V[j])
            lp = _add(_mul(v, 1.0 - n * beta), _mul(s, beta))
        V2.append(_add(v, _mul(_sub(lp, v), k * kv[i])))
    mid = {}
    for (a, b), opp in edges.items():
        lin = _mul(_add(V[a], V[b]), 0.5)
        if len(opp) == 2:
            lp = _add(_mul(_add(V[a], V[b]), 0.375), _mul(_add(V[opp[0]], V[opp[1]]), 0.125))
        else:
            lp = lin
        mid[(a, b)] = len(V2)
        V2.append(_add(lin, _mul(_sub(lp, lin), k * min(kv[a], kv[b]))))
        N2.append(_norm(_add(N[a], N[b])))
        W2.append(mixw(((W[a], 0.5), (W[b], 0.5))))
        uv2.append(((uv[a][0] + uv[b][0]) * 0.5, (uv[a][1] + uv[b][1]) * 0.5))
    T2 = []
    for t in tris:
        m01, m12, m20 = (mid[(min(x, y), max(x, y))] for x, y in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])))
        T2 += [(t[0], m01, m20), (m01, t[1], m12), (m20, m12, t[2]), (m01, m12, m20)]
    return V2, N2, W2, uv2, T2


def skin(model, sdata, skel, bone_block, nbones, bidx, label):
    """SKD v5 bytes: her sub-meshes on the stock skeleton, re-posed to the stock standing pose (POSE) piece by piece and
    weighted with the disc's own one- and two-bone blends, each EA bone carried by its Bip01 counterpart"""
    J = {nm: (p, _axes(*a)) for nm, (p, a) in POSE.items()}
    T, s = repose(skel, J)
    blobs, surf_names = [], []
    smooth = SUBDIV.get(label, SMOOTH)
    if smooth and any(len(pos) + _edge_count(tris) > SUBDIV_MAX for pos, uv, tris, shape in model["meshes"]
                      if shape and "#a" not in shape):
        smooth = 0.0
    model["smoothed"] = smooth
    for k, ((pos, uv, tris, shape), sd) in enumerate(zip(model["meshes"], sdata)):
        V, N, W = [], [], []
        for j, p in enumerate(pos):
            x = (p[1] * 100.0 * s, -p[0] * 100.0 * s, p[2] * 100.0 * s)
            n0 = sd["nrm"][j] if sd["nrm"] else (0.0, 0.0, 1.0)
            n0 = (n0[1], -n0[0], n0[2])
            acc, nacc, tw, merged = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, {}
            for bi, w in sd["wts"][j]:
                t = T.get(bi) or T[1]
                acc = _add(acc, _mul(_xf(t, x), w))
                nacc = _add(nacc, _mul(_mv(t[2], n0), w))
                tw += w
                bip = easkin.EA_TO_BIP.get(skel[bi]["name"], "Bip01 Pelvis")
                merged[bip] = merged.get(bip, 0.0) + w
            tw = tw or 1.0
            V.append(_mul(acc, 1.0 / tw))
            N.append(_norm(nacc))
            W.append(sorted(((bn, w / tw) for bn, w in merged.items()), key=lambda q: -q[1]))
        # winding: each triangle faces the way the disc's own normals say (MOHAA wants (e1 x e2) outward)
        out_t = []
        for t in tris:
            fn = _cross(_sub(V[t[1]], V[t[0]]), _sub(V[t[2]], V[t[0]]))
            out_t.append(t if _dot(fn, _add(_add(N[t[0]], N[t[1]]), N[t[2]])) >= 0 else (t[0], t[2], t[1]))
        if smooth and shape and "#a" not in shape:
            V, N, W, uv, out_t = _subdivide(V, N, W, list(uv), out_t, smooth)
        vb = bytearray()
        for j in range(len(V)):
            bp, ax = J[W[j][0][0]]
            nn = N[j]
            vb += struct.pack("<3f2f2i", _dot(nn, ax[0]), _dot(nn, ax[1]), _dot(nn, ax[2]), uv[j][0], uv[j][1],
                              len(W[j]), 0)
            for bn, w in W[j]:
                bp, ax = J[bn]
                dv = _sub(V[j], bp)
                vb += struct.pack("<if3f", bidx[bn], w, _dot(dv, ax[0]), _dot(dv, ax[1]), _dot(dv, ax[2]))
        tb = b"".join(struct.pack("<3i", *t) for t in out_t)
        nV, nT = len(V), len(out_t)
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
    skel = easkin.skeleton(stream)
    made = 0
    for mname, chr_names, label in CHARS:
        m = read_model(stream, mname)
        if not m or not m["meshes"]:
            continue
        sd = easkin.skin_data(stream, mname)
        if not skel or not sd or len(sd) != len(m["meshes"]) or any(x["wts"] is None for x in sd):
            log("eachar: %s: no disc skeleton / skin weights; the character keeps the stock model" % mname)
            continue
        skd, surfs = skin(m, sd, skel, bone_block, nbones, bidx, label)
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
                        shname, tname, "\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\tdepthWrite\n" if cut
                        else "")).encode()
                # '#a' (GeoPrimState ABM_BLEND) pieces are alpha-BLENDED as on the disc: the German helmet carries a
                # soft shadow card under its brim (alpha 0..222 gradient) that an alpha test drew as a solid black
                # band across his eyes; the opaque texels still write depth
            tik_surf.append("\tsurface %s shader %s\n" % (sn, shname))
        axis = label.startswith(("german", "ss_"))   # as the stock German tiks: 'german' and the German dialogue
        tik = ("TIKI\nsetup\n{\n\tscale 0.52\n\tpath %s\n\tskelmodel %s.skd\n%s\tpath models/human/protoanimations\n"
               "\tradius 20\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname Actor\n\t\tsetsize \"-16 -16 0\" \"16 16 92\"\n"
               "\t\t%s\n\t\thealth 100\n\t}\n}\n\n$include models/human/animation/dialogue/%s.tik\n"
               "$include models/human/new_generic_human.tik\n") % (
            mdir, label, "".join(tik_surf), "german" if axis else "american",
            "generic_dialogue_german" if axis else "generic_dialogue_ru")
        tikp = "models/human/ea_%s_%s.tik" % (level, label)
        files[tikp] = tik.encode()
        for chr_name in chr_names:
            lines.append('\tlevel.ea_chr_tik["%s"] = "%s"' % (chr_name, tikp))
            if chr_name in OWN:
                lines.append('\tlevel.ea_chr_own["%s"] = 1' % chr_name)
        log("eachar: %s -> %s (%d sub-meshes, %d verts, textures %s, %s)" % (
            mname, tikp, len(surfs), sum(len(x[0]) for x in m["meshes"]), sorted(m["textures"]),
            "smoothed" if m.get("smoothed") else "own mesh (too dense to smooth)"))
        made += 1
    return made
