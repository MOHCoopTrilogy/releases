#!/usr/bin/env python3
"""European Assault character skins and skeleton, read from a level stream. Our own code, stdlib only; runs on the
PLAYER's PC inside the converter (eachar.py), output only into the player's own converted pak.

Reverse-engineered 2026-11-12 on the user's own Xbox USA disc (1_11, level_a.str):

skeleton - a chunk of type 0x0bcfa9ed (the human rig, one per level stream; it holds JO_pelvis). From the chunk's
  word at +0x10 (call it B): B+0x18 bone count n, B+0x1c n u32 record offsets (from B). Record r:
    r+0x10 .. r+0x4f  the bone's inverse bind matrix, 4 rows of f32x4, row-vector convention
                      (local = model * R + T; rows 0-2 = R, row 3 = T); so the joint sits at -T R^T in model space
    r+0x58            the joint's name hash (the animation JointLists name joints by it)
    r+0x5c            parent bone index (u32, 0xffffffff for record 0, 'character_root')
    r+0x70            name, 16 bytes ('JO_pelvis', 'JO_shoulder_L', ...)
  Bone index = record index (character_root 0, JO_pelvis 1 ...). Model space is metres, z up, the character faces
  +Y and its LEFT side is -X. The bind pose is an A-pose (arms 45 degrees down, hands flat, fingers straight).
skin - per sub-mesh k of a model ELF (eachar.read_model): vertex buffers __VB:::__GPvb_<s>_<k>_<model>.mesh with a
  20-byte header (word 1 byte size, word 2 stride):
    s16 position f32x3   s17 uv f32x2   s18 colour u8x4
    s19 normal: Xbox NORMPACKED3 (x 11 bits, y 11 bits, z 10 bits, signed) - outward, unit length
    s20 matrix-palette slot, i16 = vertex-shader constant register: -96, -92 ... in steps of 4 (one matrix per
        slot). Register -40 is reserved (not a slot), so slot = (s + 96) / 4, one less above -40.
  The render-method record __RM:::__GP_RM_<model>.mesh_k carries, 12 bytes before its relocation to
  'EAGLAnimationBuffer', (slot count, palette offset). Palette entries are 16 bytes: f32 w0, f32 w1, f32 0, f32 v;
  int(v) packs the two bones: bone A = byte 3, bone B = byte 2, weights w0 / w1 (a single bone: w0 = 1, B = 0).
  Palettes are per sub-mesh. A relocation to an __EAGL::GeoPrimState with ABM_BLEND marks an alpha-blended piece.
"""
import struct

import eachar

CHUNK_SKEL = 0x0bcfa9ed

# EA bone -> MOHAA stock human bone (the stock animations drive only Bip01). Fingers, eyelids, brows, jaw and helmet
# have no Bip01 counterpart: they ride the hand / head. The same table serves retargeting EA's own animations.
EA_TO_BIP = {
    "character_root": "Bip01 Pelvis", "JO_anchor": "Bip01 Pelvis", "JO_csw": "Bip01 Pelvis",
    "JO_pelvis": "Bip01 Pelvis", "JO_lumbar1": "Bip01 Spine", "JO_lumbar2": "Bip01 Spine1",
    "JO_thoracic": "Bip01 Spine2", "JO_aim": "Bip01 Spine2", "JO_neck": "Bip01 Neck",
    "JO_head": "Bip01 Head", "JO_helmet": "Bip01 Head", "JO_jaw": "Bip01 Head", "JO_bonehead": "Bip01 Head",
    "JO_eyeLid_L": "Bip01 Head", "JO_eyeLid_R": "Bip01 Head", "JO_brow_L": "Bip01 Head", "JO_brow_R": "Bip01 Head",
}
for _s in "LR":
    EA_TO_BIP.update({
        "JO_clavicleScapula_" + _s: "Bip01 %s Clavicle" % _s,
        "JO_shoulder_" + _s: "Bip01 %s UpperArm" % _s, "JO_uparm_" + _s: "Bip01 %s UpperArm" % _s,
        "JO_elbow_" + _s: "Bip01 %s Forearm" % _s, "JO_loarm_" + _s: "Bip01 %s Forearm" % _s,
        "JO_wrist_" + _s: "Bip01 %s Hand" % _s, "JO_object_" + _s: "Bip01 %s Hand" % _s,
        "JO_hip_" + _s: "Bip01 %s Thigh" % _s, "JO_knee_" + _s: "Bip01 %s Calf" % _s,
        "JO_ankle_" + _s: "Bip01 %s Foot" % _s, "JO_ball_" + _s: "Bip01 %s Toe0" % _s,
    })
    for _f in ("thm", "pnt", "rng"):
        for _j in "ABC":
            EA_TO_BIP["JO_%s%s_%s" % (_f, _j, _s)] = "Bip01 %s Hand" % _s


def skeleton(d):
    """[{name, parent, pos (model space, m), axes (3 model-space vectors: the bind frame's local x, y, z)}] or None"""
    for p, cid, typ, sz in eachar._chunks(d):
        if typ != CHUNK_SKEL or d.find(b"JO_pelvis\0", p, p + sz) < 0:
            continue
        b = p + 0x10
        n = struct.unpack_from("<I", d, b + 0x18)[0]
        offs = struct.unpack_from("<%dI" % n, d, b + 0x1c)
        out = []
        for o in offs:
            r = b + o
            M = struct.unpack_from("<16f", d, r + 0x10)
            R = (M[0:3], M[4:7], M[8:11])
            T = M[12:15]
            jh, par = struct.unpack_from("<II", d, r + 0x58)
            out.append({"name": d[r + 0x70:r + 0x80].split(b"\0")[0].decode("latin-1"), "hash": jh,
                        "parent": -1 if par == 0xffffffff else par,
                        "pos": tuple(-sum(T[j] * R[k][j] for j in range(3)) for k in range(3)),
                        "axes": [tuple(R[k][j] for k in range(3)) for j in range(3)]})
        return out
    return None


def _sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def normpacked3(u):
    return (_sx(u, 11) / 1023.0, _sx(u >> 11, 11) / 1023.0, _sx(u >> 22, 10) / 511.0)


def slot_index(s):
    return (s + 96) // 4 - (1 if s > -40 else 0)


def skin_data(d, name):
    """per sub-mesh (in eachar.read_model's order) {nrm: [unit vectors], wts: [[(ea bone index, weight), ...]]}"""
    key = ("__Model:::%s.mesh" % name).encode()
    at = d.find(key)
    if at < 0:
        return None
    for p, cid, typ, sz in eachar._chunks(d):
        if typ == eachar.CHUNK_MODEL and p <= at < p + sz and d[p + 0x20:p + 0x24] == b"\x7fELF":
            break
    else:
        return None
    data, dsize, syms, rel = eachar._elf(d, p + 0x20)
    rms = sorted((v, n) for n, v in syms.items() if n.startswith("__RM:::__GP_RM_%s.mesh_" % name))
    out = []
    for k, (rv, rn) in enumerate(rms):
        kk = rn.rsplit("_", 1)[1]
        vb = {s: syms.get("__VB:::__GPvb_%d_%s_%s.mesh" % (s, kk, name)) for s in (16, 17, 19, 20)}
        if vb[16] is None or vb[17] is None:
            continue          # eachar.read_model skips these too: keep the two lists aligned
        n = struct.unpack_from("<I", d, data + vb[16] + 4)[0] // 12
        hi = rms[k + 1][0] if k + 1 < len(rms) else dsize
        nrm = [normpacked3(u) for u in struct.unpack_from("<%dI" % n, d, data + vb[19] + 20)] if vb[19] else None
        wts = None
        ab = [o for o, sn in rel if rv <= o < hi and sn == "__const MATRIX4:::EAGLAnimationBuffer"]
        if vb[20] is not None and ab:
            cnt, ptr = struct.unpack_from("<II", d, data + ab[0] - 12)
            pal = []
            for i in range(cnt):
                w0, w1, _z, v = struct.unpack_from("<4f", d, data + ptr + 16 * i)
                iv = int(v)
                pal.append([(iv >> 24) & 255, w0] if w1 <= 0.0 else [(iv >> 24) & 255, w0, (iv >> 16) & 255, w1])
            wts = []
            for s in struct.unpack_from("<%dh" % n, d, data + vb[20] + 20):
                e = pal[min(max(slot_index(s), 0), cnt - 1)]
                wts.append([(e[0], e[1])] if len(e) == 2 else [(e[0], e[1]), (e[2], e[3])])
        out.append({"nrm": nrm, "wts": wts, "rm": rn})
    return out
