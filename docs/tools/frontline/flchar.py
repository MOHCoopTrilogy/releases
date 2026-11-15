#!/usr/bin/env python3
"""Frontline characters as MOHAA skeletal models. Our own code; runs on the PLAYER's PC inside the converter, and its
output (meshes, textures) goes only into the player's own converted pak. Nothing Frontline-derived is shipped.

User approval 2026-11-15 ("Bring over Frontline characters"); the route is the European Assault one (docs/tools/ea/
eachar.py, option C): the disc's own skinned meshes and textures, re-posed onto MOHAA's stock Bip01 skeleton so the
stock animations drive them, one level of body-only smoothing, surfaces cut under the engine's skeletal limits.
The mission script uses a character's own model only once it has passed the sheet QA (OWN below ->
level.fl_chr_own[hash]); until then the stock model plays it.

Reverse-engineered 2026-11-15 on the user's own Xbox USA disc (level 1_1, level.viv):

character definitions - levelfile.lfc: typed (u32 type, u32 value) pairs (0 / 4 = file offset of a C string,
  1 = int, 2 = f32, 3 = name hash). A character is the run
    skl, body .dmf, body texture, head .dmf, head texture, int, int, hat .msh, hat offset x y z (f32, or 0),
    collision .cls x3, #hash
  and a placed actor (.bpd section 3, kind 3) names it by that hash in its record word 18.
skeleton - <x>.skl ('SKL1'): u16 bone count at +6, u32 hierarchy offset at +8; at 0x20 per bone (f32 x y z = the
  joint's offset in its PARENT's bind frame, i32 depth); names at 0x704, 20 bytes each; hierarchy nodes from the
  offset: (u8 child count, u8 depth, u8 bone index, u8 0, u32 parent node, u32 children...); attach points at 0xf20
  (24 bytes: name 16, u32 bone, u32 offset of a row-vector 4x4 matrix in that bone's frame): head, VisionCone,
  rt_hand, lt_hand. Metres, z up, the character faces +y, his left is -x (the EA convention).
mesh - <x>.dmf ('DMF', version 6), u32 words from 0x1c: 1, weight count, weight table, mesh count, mesh records,
  texture-name count, texture names (16 bytes each), group count, groups, materials, ?, bone count (70), bone names
  (16 bytes each, at 0x5c), bind rotations (at 0x4c0: per bone 3 x i16, 65536 = 360 degrees, x y z; the bone's local
  rotation is Ry Rz Rx - picked of the six orders by the tightest joints), 1.0, 1.0.
  weights (4 bytes): u8 bone A, u8 bone B (A's parent), u16 weight of A / 4096 (B gets the rest).
  mesh record (60 bytes): word 11 kind (39 skinned, 167 the head's base shape, 259 a morph target), word 12 its
  texture index, word 13 batch count, word 14 offset of the batch offset table.
  batch: (u32 palette count, palette offset (u8 weight indices), vertex count, positions, uvs); positions = 12 bytes
  then per vertex f32 x y z, nx ny nz in bone A's bind frame; uvs = 12 bytes then per vertex f32 u, v, 3 x palette
  slot. Each batch is one triangle strip whose pieces are joined by repeated vertices.
  'MOHF_Body' / 'MOHF_Head' in the texture names are filled from the character definition.
heads - UHM1_1.dmf: one head (kind 167) + 37 morph targets (kind 259, deltas); the base shape is used (neutral).
textures - tpk<l>.tpk ('TPAC'): u32 count, name table (16 bytes), offset table; each entry an Xbox texture header
  (pixels, palette, ..., format word: format byte 0x0b = P8, log2 w / h in bits 20-23 / 24-27), 256-entry BGRA
  palette, pixels Morton-swizzled. GR5 keys its unused area with pure magenta.
hats - ordinary object meshes (.msh, flcore.Level.mesh) on the skeleton's 'head' attach point plus the definition's
  offset.
"""
import glob
import math
import os
import struct
import zipfile

import shpx

ZIP_NOTE = "frontline characters"
STOCK_SKD = "models/human/german_wehrmact_officer/german_officer.skd"
EULER_ORDER = "yzx"

# the character definitions whose own models have passed the client sheet QA (front, side, back, face, run, fire,
# crouch, no breaks). Every other Frontline character keeps the stock model in game until the user approves its sheet.
OWN = {"645ffd2b",    # 2026-11-15 user approved (main German, SHEET_fl_645ffd2b_ingame_645_v11)
       "7f9a5a86",    # 2026-11-15 user approved (capped officer, SHEET_fl_7f9a5a86_ingame_7f9_v5)
       "dca82ce9",    # 2026-11-15 user approved (GI, SHEET_fl_dca82ce9_ingame_dca_v5)
       # 2026-11-15 user approved the remaining 17 (SHEET_fl_<hash>_ingame_b_*, QA_batch17_overview)
       "031add4e", "9a138cf4", "ed14bc62", "2e091524", "590e25b2", "c76ab011", "b06d8087", "c18e036f", "588752d5",
       "3f817f27", "e6930b3c", "9719a637", "45a17d53", "42ccb94a", "abaf1c7f", "35cb89dc", "07d5b007"}

# Frontline bone -> MOHAA stock human bone (the stock animations drive only Bip01). Fingers have no counterpart:
# they ride the hand.
FL_TO_BIP = {"Top": "Bip01 Pelvis", "Hip": "Bip01 Pelvis", "spine1": "Bip01 Spine", "spine2": "Bip01 Spine1",
             "chest": "Bip01 Spine2", "DO_NOT_TOUCH": "Bip01 Spine2", "neck1": "Bip01 Neck", "neck2": "Bip01 Neck",
             "head": "Bip01 Head"}
for _s in "LR":
    FL_TO_BIP.update({"scapula_" + _s: "Bip01 %s Clavicle" % _s, "uparm_" + _s: "Bip01 %s UpperArm" % _s,
                      "loarm_" + _s: "Bip01 %s Forearm" % _s, "hand" + _s: "Bip01 %s Hand" % _s,
                      "thigh_" + _s: "Bip01 %s Thigh" % _s, "calf_" + _s: "Bip01 %s Calf" % _s,
                      "ankle_" + _s: "Bip01 %s Foot" % _s, "toe_" + _s: "Bip01 %s Toe0" % _s})
    for _f in "ABCDE":
        for _j in "123":
            FL_TO_BIP["digit_%s%s%s" % (_s, _f, _j)] = "Bip01 %s Hand" % _s

# the stock human skeleton in a standing pose (eachar.POSE: soviet_infantry1, AI off; gettagposition /
# gettagangles, model space cm, facing +X): position, (pitch, yaw, roll)
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


# ---------------- disc readers ----------------
def _cstr(b, o):
    return b[o:b.index(b"\0", o)].decode("latin-1")


def chardefs(lfc):
    """{hash: {skl, body, bt, head, ht, ints, hat, off}} from levelfile.lfc"""
    n = len(lfc) // 4
    W = struct.unpack_from("<%dI" % n, lfc)
    lo = 0x400
    out = {}

    def sval(v):
        return _cstr(lfc, v) if lo < v < len(lfc) and 32 <= lfc[v] < 127 else None
    i = 1
    while i + 1 < n:
        s = sval(W[i]) if W[i - 1] == 0 else None
        if not (s and s.lower().endswith(".skl")):
            i += 1
            continue
        toks, j = [], i - 1
        while j + 1 < n and len(toks) < 40:
            t, v = W[j], W[j + 1]
            j += 2
            if t == 3:
                toks.append(("#", v))
                break
            if t in (0, 4) and sval(v):
                toks.append(("s", sval(v)))
            elif t == 1:
                toks.append(("i", v))
            elif t == 2:
                toks.append(("f", struct.unpack("<f", struct.pack("<I", v))[0]))
            else:
                toks.append(("?", v))
        i = j
        if not toks or toks[-1][0] != "#":
            continue
        ss = [v for k, v in toks if k == "s"]
        if len(ss) < 5 or not ss[1].upper().startswith("BM") or not ss[3].upper().startswith("UHM"):
            continue
        hat = next((v for v in ss if v.lower().endswith(".msh")), None)
        off = [0.0, 0.0, 0.0]
        if hat:
            k0 = next(k for k, (kk, v) in enumerate(toks) if kk == "s" and v == hat)
            for q in range(3):
                kk, v = toks[k0 + 1 + q] if k0 + 1 + q < len(toks) else ("?", 0)
                off[q] = v if kk == "f" else 0.0
        out["%08x" % toks[-1][1]] = {"skl": ss[0], "body": ss[1], "bt": ss[2], "head": ss[3], "ht": ss[4],
                                     "ints": tuple(v for k, v in toks if k == "i")[:2], "hat": hat, "off": tuple(off)}
    return out


def read_skl(b):
    n = struct.unpack_from("<H", b, 6)[0]
    hier = struct.unpack_from("<I", b, 8)[0]
    names = [b[0x704 + 20 * i:0x704 + 20 * i + 16].split(b"\0")[0].decode("latin-1") for i in range(n)]
    loc = [struct.unpack_from("<3f", b, 0x20 + 16 * i) for i in range(n)]
    par, at, nodes, o = [-1] * n, {}, [], hier
    while len(nodes) < n and o + 8 <= len(b):
        nc, idx = b[o], b[o + 2]
        at[o] = idx
        nodes.append((idx, struct.unpack_from("<I", b, o + 4)[0]))
        o += 8 + 4 * nc
    for idx, pp in nodes:
        if idx < n:
            par[idx] = at.get(pp, -1)
    att = {}
    for k in range(4):
        q = 0xf20 + 24 * k
        if q + 24 > len(b):
            break
        nm = b[q:q + 16].split(b"\0")[0].decode("latin-1")
        bi, mo = struct.unpack_from("<2I", b, q + 16)
        if bi < n and mo + 64 <= len(b):
            M = struct.unpack_from("<16f", b, mo)
            att[nm] = (bi, [M[0:3], M[4:7], M[8:11]], M[12:15])
    return {"names": names, "par": par, "loc": loc, "attach": att}


def read_dmf(b):
    W = lambda o: struct.unpack_from("<I", b, o)[0]
    nb = W(0x48)
    names = [b[0x5c + 16 * i:0x6c + 16 * i].split(b"\0")[0].decode("latin-1") for i in range(nb)]
    rot = [struct.unpack_from("<3h", b, 0x4c0 + 6 * i) for i in range(nb)]
    wts = [struct.unpack_from("<BBH", b, W(0x24) + 4 * i) for i in range(W(0x20))]
    tex = [b[W(0x34) + 16 * i:W(0x34) + 16 * i + 16].split(b"\0")[0].decode("latin-1") for i in range(W(0x30))]
    meshes = []
    for i in range(W(0x28)):
        ws = struct.unpack_from("<15I", b, W(0x2c) + 0x3c * i)
        batches = []
        for j in range(ws[13]):
            npal, pp, nv, vp, up = struct.unpack_from("<5I", b, W(ws[14] + 4 * j))
            pal = list(b[pp:pp + npal])
            P = [struct.unpack_from("<6f", b, vp + 12 + 24 * k) for k in range(nv)]
            U = [struct.unpack_from("<3f", b, up + 12 + 12 * k) for k in range(nv)]
            batches.append((pal, P, U))
        meshes.append({"kind": ws[11], "tex": tex[ws[12]] if ws[12] < len(tex) else None, "batches": batches})
    return {"names": names, "rot": rot, "wts": wts, "meshes": meshes}


def read_tpk(b):
    """{NAME (upper case): (w, h, rgba bytes)}"""
    n, no, to = struct.unpack_from("<3I", b, 4)
    out = {}
    for i in range(n):
        nm = b[no + 16 * i:no + 16 * i + 16].split(b"\0")[0].decode("latin-1").upper()
        e = struct.unpack_from("<I", b, to + 4 * i)[0]
        pix, pal, _c, _a, _b, fmt = struct.unpack_from("<6I", b, e)
        if (fmt >> 8) & 0xff != 0x0b:
            continue
        w, h = 1 << ((fmt >> 20) & 15), 1 << ((fmt >> 24) & 15)
        P = [b[pal + 4 * k:pal + 4 * k + 4] for k in range(256)]
        lut = [bytes((p[2], p[1], p[0], p[3])) for p in P]
        mt = shpx.morton_table(w, h)
        px = b[pix:pix + w * h]
        out[nm] = (w, h, b"".join(lut[px[mt[k]]] for k in range(w * h)))
    return out


# ---------------- small maths (as eachar.py) ----------------
def _sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def _add(a, b): return tuple(a[i] + b[i] for i in range(3))
def _mul(a, s): return tuple(v * s for v in a)
def _dot(a, b): return sum(a[i] * b[i] for i in range(3))
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    l = math.sqrt(_dot(a, a)) or 1.0
    return _mul(a, 1.0 / l)


_I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(A, x):
    return tuple(A[i][0] * x[0] + A[i][1] * x[1] + A[i][2] * x[2] for i in range(3))


def _axes(p, y, r):
    p, y, r = (math.radians(v) for v in (p, y, r))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    fwd = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return [fwd, _mul(right, -1.0), up]


def _rot_mat(u, v):
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


def _axis_rot(k, a):
    c, s = math.cos(a), math.sin(a)
    K = [[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]]
    K2 = _mm(K, K)
    return [[_I3[i][j] + s * K[i][j] + (1 - c) * K2[i][j] for j in range(3)] for i in range(3)]


def _R1(axis, a):
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    if axis == "y":
        return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _euler(e):
    a = [v * 2.0 * math.pi / 65536.0 for v in e]
    M = [r[:] for r in _I3]
    for ax in EULER_ORDER:
        M = _mm(M, _R1(ax, a["xyz".index(ax)]))
    return M


def bind(skl, dmf):
    """{bone name: (joint (model space, m), R (bind frame -> model))}"""
    rot = dict(zip(dmf["names"], dmf["rot"]))
    out = {}
    n = len(skl["names"])
    Jw, Rw = [None] * n, [None] * n
    for i in range(n):           # parents precede their children in the .skl
        p, t = skl["par"][i], skl["loc"][i]
        Rl = _euler(rot.get(skl["names"][i], (0, 0, 0)))
        if p < 0:
            Jw[i], Rw[i] = tuple(t), Rl
        else:
            Jw[i], Rw[i] = _add(Jw[p], _mv(Rw[p], t)), _mm(Rw[p], Rl)
        out[skl["names"][i]] = (Jw[i], Rw[i])
    return out


# ---------------- re-pose onto the stock skeleton (eachar.repose with Frontline's bones) ----------------
def _pieces():
    P = [("torso", ("Top", "Hip", "spine1", "spine2", "chest", "DO_NOT_TOUCH"), "Hip", "neck1",
          "Bip01 Pelvis", "Bip01 Neck", None, "stretch"),
         ("neck", ("neck1", "neck2"), "neck1", "head", "Bip01 Neck", "Bip01 Head", "torso", "rigid"),
         ("head", ("head",), "head", ("fwd", "head"), "Bip01 Head", ("x", "eyes bone"), "neck", "chain")]
    for s in "LR":
        fing = tuple("digit_%s%s%s" % (s, f, j) for f in "ABCDE" for j in "123")
        P += [("clav" + s, ("scapula_" + s,), "scapula_" + s, "uparm_" + s, "Bip01 %s Clavicle" % s,
               "Bip01 %s UpperArm" % s, "torso", "stretch"),
              ("upper" + s, ("uparm_" + s,), "uparm_" + s, "loarm_" + s, "Bip01 %s UpperArm" % s,
               "Bip01 %s Forearm" % s, "clav" + s, "stretch"),
              ("fore" + s, ("loarm_" + s,), "loarm_" + s, "hand" + s, "Bip01 %s Forearm" % s, "Bip01 %s Hand" % s,
               "upper" + s, "stretch"),
              ("hand" + s, ("hand" + s,) + fing, "hand" + s, ("digit_%sB1" % s, "digit_%sD1" % s),
               "Bip01 %s Hand" % s, ("x", "Bip01 %s Hand" % s), "fore" + s, "rigid"),
              ("thigh" + s, ("thigh_" + s,), "thigh_" + s, "calf_" + s, "Bip01 %s Thigh" % s, "Bip01 %s Calf" % s,
               "torso", "stretch"),
              ("calf" + s, ("calf_" + s,), "calf_" + s, "ankle_" + s, "Bip01 %s Calf" % s, "Bip01 %s Foot" % s,
               "thigh" + s, "stretch"),
              ("foot" + s, ("ankle_" + s,), "ankle_" + s, "toe_" + s, "Bip01 %s Foot" % s, "Bip01 %s Toe0" % s,
               "calf" + s, "stretch"),
              ("toe" + s, ("toe_" + s,), "toe_" + s, ("fwd", "toe_" + s), "Bip01 %s Toe0" % s,
               ("x", "Bip01 %s Toe0" % s), "foot" + s, "rigid")]
    return P


FINGER_CURL = (30.0, 45.0, 30.0)      # knuckle, middle, tip (the stock hands are modelled in a grip)
THUMB_CURL = (10.0, 15.0, 15.0)


def _xf(t, x):
    a, sa, R, u, k = t
    r = _mv(R, _sub(x, a))
    return _add(sa, _add(r, _mul(u, (k - 1.0) * _dot(r, u))))


def to_moh(p, s):
    """Frontline model space (m, faces +y, left -x) -> MOHAA model space (cm, faces +x, left +y), times s"""
    return (p[1] * 100.0 * s, -p[0] * 100.0 * s, p[2] * 100.0 * s)


def repose(B, pose):
    """({FL bone: (FL joint, stock joint, R, axis, k)}, s): the transforms carrying the disc bind pose onto the stock
    pose {bone: (pos, axes)}; s = the girth scale (stock pelvis-neck over his)"""
    s = math.dist(pose["Bip01 Pelvis"][0], pose["Bip01 Neck"][0]) / (100.0 * math.dist(B["Hip"][0], B["neck1"][0]))
    E = {nm: to_moh(j, s) for nm, (j, _r) in B.items()}

    def fl_pt(t):
        if isinstance(t, str):
            return E[t]
        if t[0] == "fwd":
            return _add(E[t[1]], (6.0, 0.0, 0.0))
        return _mul(_add(E[t[0]], E[t[1]]), 0.5)
    out, piece = {}, {}
    for name, bones, ej, et, sj, stp, parent, mode in _pieces():
        if ej not in E or sj not in pose:
            continue
        a, b = E[ej], fl_pt(et)
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
            out[bn] = piece[name]
    # fingers: the disc's bind hand is flat, the stock hands hold a grip (the stock animations never move fingers):
    # each finger is curled toward the palm at its three joints before the hand piece carries it (as eachar.py)
    for side in "LR":
        h = piece.get("hand" + side)
        w, kn = "hand" + side, ("digit_%sB1" % side, "digit_%sD1" % side)
        if not h or w not in E or any(x not in E for x in kn):
            continue
        hu = _norm(_sub(fl_pt(kn), E[w]))
        pn = _norm(_cross(hu, _sub(E[kn[0]], E[kn[1]])))
        mid = _mul(_add(E["Hip"], E["neck1"]), 0.5)
        if _dot(pn, _sub(mid, E[w])) < 0:           # the palm faces the body in the A-pose
            pn = _mul(pn, -1.0)
        for f, angs in (("B", FINGER_CURL), ("C", FINGER_CURL), ("D", FINGER_CURL), ("E", FINGER_CURL),
                        ("A", THUMB_CURL)):
            M, t = h[2], _sub(h[1], _mv(h[2], h[0]))
            for j, ang in zip("123", angs):
                jn = "digit_%s%s%s" % (side, f, j)
                if jn not in E:
                    break
                nxt = "digit_%s%s%d" % (side, f, int(j) + 1)
                fd = _norm(_sub(E[nxt], E[jn])) if nxt in E else hu
                Rc = _axis_rot(_norm(_cross(fd, pn)), math.radians(ang))
                p = E[jn]
                t = _add(t, _mv(M, _sub(p, _mv(Rc, p))))
                M = _mm(M, Rc)
                out[jn] = ((0.0, 0.0, 0.0), t, M, h[3], 1.0)
    return out, s


# ---------------- geometry ----------------
def strip_tris(P):
    """a Frontline batch: one strip, pieces joined by repeated vertices"""
    T = []
    for i in range(len(P) - 2):
        a, b, c = P[i], P[i + 1], P[i + 2]
        if a == b or b == c or a == c:
            continue
        T.append((i, i + 1, i + 2) if i % 2 == 0 else (i + 1, i, i + 2))
    return T


SMOOTH = 0.6               # eachar.SMOOTH: Loop positions blended with the midpoint split (option C)
TIKI_MAX_VERTS = 999       # tiki_shared.h TIKI_MAX_VERTEXES 1000 / TIKI_MAX_TRIANGLES 2000
TIKI_MAX_TRIS = 1999


def _subdivide(V, N, W, uv, tris, k):
    """one level of Loop subdivision (eachar._subdivide); anything on the head or neck keeps its place"""
    edges = {}
    for t in tris:
        for a, b, c in ((t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1])):
            edges.setdefault((min(a, b), max(a, b)), []).append(c)
    nb = [set() for _ in V]
    bnd = [[] for _ in V]
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
            lp = _add(_mul(v, 0.75), _mul(_add(V[bnd[i][0]], V[bnd[i][1]]), 0.125)) if len(bnd[i]) == 2 else v
        else:
            n = len(nb[i])
            if n == 0:
                V2.append(v)
                continue
            beta = 3.0 / 16.0 if n == 3 else 3.0 / (8.0 * n)
            sm = (0.0, 0.0, 0.0)
            for j in nb[i]:
                sm = _add(sm, V[j])
            lp = _add(_mul(v, 1.0 - n * beta), _mul(sm, beta))
        V2.append(_add(v, _mul(_sub(lp, v), k * kv[i])))
    mid = {}
    for (a, b), opp in edges.items():
        lin = _mul(_add(V[a], V[b]), 0.5)
        lp = _add(_mul(_add(V[a], V[b]), 0.375), _mul(_add(V[opp[0]], V[opp[1]]), 0.125)) if len(opp) == 2 else lin
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


def _weld(V, N, W, uv, tris):
    """the strips repeat every shared vertex: weld equal position + uv + weights, so smoothing sees one surface"""
    key, remap, V2, N2, W2, uv2 = {}, [], [], [], [], []
    for i in range(len(V)):
        kk = (tuple(round(c, 3) for c in V[i]), round(uv[i][0], 5), round(uv[i][1], 5),
              tuple((bn, round(w, 3)) for bn, w in W[i]))
        if kk not in key:
            key[kk] = len(V2)
            V2.append(V[i])
            N2.append(N[i])
            W2.append(W[i])
            uv2.append(uv[i])
        else:
            j = key[kk]
            N2[j] = _add(N2[j], N[i])
        remap.append(key[kk])
    N2 = [_norm(n) for n in N2]
    T2 = [tuple(remap[x] for x in t) for t in tris]
    return V2, N2, W2, uv2, [t for t in T2 if len(set(t)) == 3]


def character_surfaces(defn, files, tpk, L=None):
    """the character in the DISC bind pose: [(V model m, N, W [(FL bone, w)], uv, tris, texture name, smooth)]"""
    skl = read_skl(files[defn["skl"]])
    out = []
    body = read_dmf(files[defn["body"]])
    B = bind(skl, body)
    for fname in (defn["body"], defn["head"]):
        d = body if fname == defn["body"] else read_dmf(files[fname])
        for mi, me in enumerate(d["meshes"]):
            if me["kind"] == 259:          # morph targets: the head stays at its base (neutral) shape
                continue
            tn = {"MOHF_BODY": defn["bt"], "MOHF_HEAD": defn["ht"]}.get((me["tex"] or "").upper(), me["tex"])
            if (tn or "").upper() not in tpk:
                # a piece whose texture is not on the level at all (BM03's chest piece names GR4, which no level
                # pack carries): not drawn - an untextured surface would show the engine's default shader
                continue
            V, N, W, UV, T = [], [], [], [], []
            for pal, P, U in me["batches"]:
                base = len(V)
                for p, u in zip(P, U):
                    a, b, w = d["wts"][pal[min(int(round(u[2] / 3.0)), len(pal) - 1)]]
                    w = max(0.0, min(1.0, w / 4096.0))
                    J, R = B[d["names"][a]]
                    V.append(_add(_mv(R, p[:3]), J))
                    N.append(_norm(_mv(R, p[3:6])))
                    W.append([(d["names"][a], w)] + ([(d["names"][b], 1.0 - w)] if w < 1.0 else []))
                    UV.append((u[0], u[1]))
                T += [(base + x, base + y, base + z) for x, y, z in strip_tris([tuple(p[:3]) for p in P])]
            out.append((V, N, W, UV, T, tn, fname == defn["body"] and mi == 0))
    if defn.get("hat") and L is not None and "head" in skl["attach"]:
        bi, A, At = skl["attach"]["head"]
        J, R = B[skl["names"][bi]]
        for k, dr in enumerate(L.mesh(defn["hat"])):
            V = [_add(_mv(R, _add(_vrow(_add(v, defn["off"]), A), At)), J) for v in dr["verts"]]
            nacc = [(0.0, 0.0, 0.0)] * len(V)
            for a, b, c in dr["tris"]:
                fn = _cross(_sub(V[b], V[a]), _sub(V[c], V[a]))
                for x in (a, b, c):
                    nacc[x] = _add(nacc[x], fn)
            N = [_norm(n) for n in nacc]
            W = [[(skl["names"][bi], 1.0)] for _ in V]
            out.append((V, N, W, list(dr["uvs"]), list(dr["tris"]), ("@", dr["tex"]), False))
    return out, B


def _vrow(v, A):
    """row vector times a 3x3 (the attach matrices are row-vector, D3D)"""
    return tuple(v[0] * A[0][j] + v[1] * A[1][j] + v[2] * A[2][j] for j in range(3))


# ---------------- writers ----------------
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


def tga(w, h, rgba):
    """bottom-up rows: the engine ignores the TGA top-down flag (bug-11142)"""
    rows = []
    for y in range(h - 1, -1, -1):
        r = rgba[y * w * 4:(y + 1) * w * 4]
        b = bytearray(r)
        b[0::4], b[2::4] = r[2::4], r[0::4]
        rows.append(bytes(b))
    return struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08) + b"".join(rows)


def colour_key(rgba):
    """GR5 marks its unused area with pure magenta: that becomes alpha 0 (cut out). (keyed?, new rgba)"""
    b = bytearray(rgba)
    n = 0
    for i in range(0, len(b), 4):
        if b[i] > 240 and b[i + 1] < 16 and b[i + 2] > 240:
            b[i + 3] = 0
            n += 1
    return n * 100 > len(b) // 4, bytes(b)


def posed(surfs, B, pose):
    """the surfaces re-posed onto the stock skeleton, MOHAA model space cm, weights on Bip01 bones"""
    T, s = repose(B, pose)
    out = []
    for V, N, W, uv, tris, tex, smooth in surfs:
        V2, N2, W2 = [], [], []
        for x0, n0, wl in zip(V, N, W):
            x, n = to_moh(x0, s), (n0[1], -n0[0], n0[2])
            acc, nacc, tw, merged = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, {}
            for bn, w in wl:
                t = T.get(bn) or T["Hip"]
                acc = _add(acc, _mul(_xf(t, x), w))
                nacc = _add(nacc, _mul(_mv(t[2], n), w))
                tw += w
                bip = FL_TO_BIP.get(bn, "Bip01 Pelvis")
                merged[bip] = merged.get(bip, 0.0) + w
            tw = tw or 1.0
            V2.append(_mul(acc, 1.0 / tw))
            N2.append(_norm(nacc))
            W2.append(sorted(((bn, w / tw) for bn, w in merged.items()), key=lambda q: -q[1]))
        out.append((V2, N2, W2, uv, tris, tex, smooth))
    return out, s


def skd(label, surfs, bone_block, nbones, bidx, smooth=SMOOTH):
    """SKD v5 bytes and [(surface, texture)]"""
    J = {nm: (p, _axes(*a)) for nm, (p, a) in POSE.items()}
    blobs, names = [], []
    for k, (V, N, W, uv, tris, tex, sm) in enumerate(surfs):
        out_t = []
        for t in tris:          # each triangle faces the way the disc's own normals say (MOHAA: (e1 x e2) outward)
            fn = _cross(_sub(V[t[1]], V[t[0]]), _sub(V[t[2]], V[t[0]]))
            out_t.append(t if _dot(fn, _add(_add(N[t[0]], N[t[1]]), N[t[2]])) >= 0 else (t[0], t[2], t[1]))
        V, N, W, uv, out_t = _weld(V, N, W, list(uv), out_t)
        if sm and smooth:
            V, N, W, uv, out_t = _subdivide(V, N, W, uv, out_t, smooth)
        chunks, cur, cmap = [], [], {}
        for t in out_t:
            new = sum(1 for x in t if x not in cmap)
            if cur and (len(cmap) + new > TIKI_MAX_VERTS or len(cur) + 1 > TIKI_MAX_TRIS):
                chunks.append((cur, cmap))
                cur, cmap = [], {}
            for x in t:
                if x not in cmap:
                    cmap[x] = len(cmap)
            cur.append(t)
        if cur:
            chunks.append((cur, cmap))
        for c, (ct, cmap) in enumerate(chunks):
            order = sorted(cmap, key=cmap.get)
            vb = bytearray()
            for j in order:
                bp, ax = J[W[j][0][0]]
                nn = N[j]
                vb += struct.pack("<3f2f2i", _dot(nn, ax[0]), _dot(nn, ax[1]), _dot(nn, ax[2]), uv[j][0], uv[j][1],
                                  len(W[j]), 0)
                for bn, w in W[j]:
                    bp, ax = J[bn]
                    dv = _sub(V[j], bp)
                    vb += struct.pack("<if3f", bidx[bn], w, _dot(dv, ax[0]), _dot(dv, ax[1]), _dot(dv, ax[2]))
            tb = b"".join(struct.pack("<3i", cmap[t[0]], cmap[t[1]], cmap[t[2]]) for t in ct)
            nV, nT = len(order), len(ct)
            sn = "%s_%d" % (label, k) if len(chunks) == 1 else "%s_%d_%d" % (label, k, c)
            names.append((sn, tex))
            ofsTri = 100
            ofsVerts = ofsTri + len(tb)
            ofsColl = ofsVerts + len(vb)
            ofsCollIdx = ofsColl + 4 * nV
            ofsEnd = ofsCollIdx + 4 * nV
            hdr = struct.pack("<4s64s8i", b"SKL ", sn.encode().ljust(64, b"\0"), nT, nV, 0, ofsTri, ofsVerts,
                              ofsColl, ofsEnd, ofsCollIdx)
            blobs.append(hdr + tb + bytes(vb) + struct.pack("<%di" % nV, *range(nV)) + struct.pack("<%di" % nV,
                                                                                                    *([0] * nV)))
    body = b"".join(blobs)
    total = 148 + len(bone_block) + len(body)
    head = struct.pack("<4si64s5i10i4i", b"SKMD", 5, ("fl_" + label).encode()[:63].ljust(64, b"\0"), len(blobs),
                       nbones, 148, 148 + len(bone_block), total, *([0] * 10), 0, total, 0, total)
    return head + bone_block + body, names


def actor_chars(L):
    """{definition hash: (team, [class names])} for the level's placed actors (.bpd kind 3, record word 18)"""
    out = {}
    for e in L.entities():
        w = struct.unpack_from("<%dI" % (e["size"] // 4), e["raw"])
        if len(w) < 19 or w[3] != 3:
            continue
        cls = e["strs"][1] if len(e["strs"]) > 1 else "?"
        h = "%08x" % w[18]
        t = (w[13] >> 8) & 255
        tm, cl = out.get(h, (t, []))
        cl.append(cls)
        out[h] = (tm, cl)
    return out


def build(L, level, mohaa_base, files, log=print):
    """write every placed character's own model into the converted pak; returns data-script lines"""
    if not mohaa_base:
        return []
    sk = _stock_bones(mohaa_base)
    if not sk:
        log("flchar: stock skeleton not found in the install; characters keep the stock models")
        return []
    bone_block, nbones, bidx = sk
    lfc = L.files.get("levelfile.lfc")
    tpk = read_tpk(L.files.get("tpk%s.tpk" % level, b"")) if L.files.get("tpk%s.tpk" % level) else {}
    if not lfc:
        return []
    defs = chardefs(lfc)
    lines, shader, made = [], [], 0
    tdir = "textures/fl_%s_chr" % level
    written = set()
    for h, (team, classes) in sorted(actor_chars(L).items()):
        defn = defs.get(h)
        if not defn or any(defn[k] not in L.files for k in ("skl", "body", "head")):
            continue
        try:
            surfs, B = character_surfaces(defn, L.files, tpk, L)
            ps, s = posed(surfs, B, {nm: (p, _axes(*a)) for nm, (p, a) in POSE.items()})
            label = "chr_" + h
            data, names = skd(label, ps, bone_block, nbones, bidx)
        except Exception as e:          # never fail the conversion: the character keeps the stock model
            log("flchar: %s skipped (%s)" % (h, e))
            continue
        mdir = "models/human/fl_%s" % level
        files["%s/%s.skd" % (mdir, label)] = data
        tik_surf = []
        for sn, tex in names:
            if isinstance(tex, tuple):            # a hat draw: its own SHPX image
                im = L.texture(tex[1]) if tex[1] else None
                key = tex[1].replace(".msh@", "_").replace(".", "_").lower() if tex[1] else None
                img = (im["w"], im["h"], bytes(im["rgba"])) if im and im.get("rgba") is not None else None
            else:
                key = (tex or "").lower()
                img = tpk.get((tex or "").upper())
            if not img:
                continue
            shname = "fl_%s_chr_%s" % (level, key)
            if key not in written:
                written.add(key)
                w, hh, rgba = img
                keyed, rgba = colour_key(rgba)
                cut = keyed or any(rgba[i] < 128 for i in range(3, len(rgba), 4))
                files["%s/%s.tga" % (tdir, key)] = tga(w, hh, rgba)
                shader.append("%s\n{\n\tcull none\n\t{\n\t\tmap %s/%s.tga\n%s\t\trgbGen lightingSpherical\n\t}\n}\n\n" % (
                    shname, tdir, key, "\t\talphaFunc GE128\n\t\tdepthWrite\n" if cut else ""))
            tik_surf.append("\tsurface %s shader %s\n" % (sn, shname))
        axis = team == 2
        tik = ("TIKI\nsetup\n{\n\tscale 0.52\n\tpath %s\n\tskelmodel %s.skd\n%s\tpath models/human/protoanimations\n"
               "\tradius 20\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname Actor\n\t\tsetsize \"-16 -16 0\" \"16 16 92\"\n"
               "\t\t%s\n\t\thealth 100\n\t}\n}\n\n$include models/human/new_generic_human.tik\n"
               "$include models/human/animation/dialogue/%s.tik\n") % (
            mdir, label, "".join(tik_surf), "german" if axis else "american",
            "generic_dialogue_german" if axis else "generic_dialogue_US")
        tikp = "models/human/fl_%s_%s.tik" % (level, label)
        files[tikp] = tik.encode()
        lines.append('\tlevel.fl_chr_tik["%s"] = "%s"' % (h, tikp))
        if h in OWN:
            lines.append('\tlevel.fl_chr_own["%s"] = 1' % h)
        log("flchar: %s (%s %s/%s, %s) -> %s, %d surfaces, scale %.3f" % (
            h, "axis" if axis else "allied", defn["body"], defn["bt"], ",".join(sorted(set(classes))), tikp,
            len(names), s))
        made += 1
    if shader:
        files["scripts/fl_%s_chars.shader" % level] = "".join(shader).encode()
    lines.append("\tlevel.fl_chr_n = %d" % made)
    return lines
