"""[flguns] copy of docs/proposals/ironsights_2026-09-28/tools/skdlib.py for the converter bundle (disc guns: reads the
base gun's SKD / SKC from the player's install). SKD v5 / SKC v13 reader + SKD writer.

Layouts from openmohaa-hzm/code/tools/md5_2_skX/skx_format.h and the engine loaders
(tiki_skel.cpp, skeletor_loadanimation.cpp, renderergl1/tr_model.cpp).

Conventions verified in-source:
  - vertex weight offset is BONE-LOCAL, ROW-vector:  p_model = offset * M3 + t   (SkelWeightGetXyz)
  - bone local matrix for SKELBONE_POSROT = QuatToMat(<name> rot channel), translation
    = <name> pos channel  (skelBone_PosRot::GetDirtyTransform)
  - world = local * parent  (SkelMat4::Multiply(incoming, parent), row-vector)
  - SKC raw v13: 48-byte header, then numFrames * 48-byte frames, then
    numFrames * numChannels * vec4 of channel data.  (ConvertSkelFileToGame)
"""
import struct

# ---------------------------------------------------------------- SKD reading

JT_NAMES = {0: "ROTATION", 1: "POSROT", 2: "IKSHOULDER", 3: "IKELBOW",
            4: "IKWRIST", 5: "HOSEROT", 6: "AVROT", 7: "ZERO"}


def cstr(b):
    z = b.find(b"\0")
    return (b[:z] if z >= 0 else b).decode("latin-1")


class Bone:
    __slots__ = ("index", "name", "parent", "jointType", "basedata", "channels", "refs")


class Surface:
    __slots__ = ("index", "name", "numTriangles", "numVerts", "tri_bytes", "vert_bytes",
                 "verts", "raw_off", "has_collapse", "texofs")


class Skd:
    pass


def read_skd(data):
    m = Skd()
    assert data[0:4] == b"SKMD", data[0:4]
    (m.version,) = struct.unpack_from("<i", data, 4)
    m.name = cstr(data[8:72])
    (m.numSurfaces, m.numBones, m.ofsBones, m.ofsSurfaces, m.ofsEnd) = struct.unpack_from("<5i", data, 72)
    m.lodIndex = struct.unpack_from("<10i", data, 92)
    m.bones = []
    off = m.ofsBones
    for i in range(m.numBones):
        b = Bone()
        b.index = i
        b.name = cstr(data[off:off + 32])
        b.parent = cstr(data[off + 32:off + 64])
        (b.jointType, ofsValues, ofsChannels, ofsRefs, ofsEnd) = struct.unpack_from("<5i", data, off + 64)
        b.basedata = struct.unpack_from("<10f", data, off + ofsValues) if ofsValues else ()
        # channel names: NUL-separated strings from ofsChannels to ofsRefs
        chblob = data[off + ofsChannels: off + ofsRefs] if ofsChannels else b""
        b.channels = [s.decode("latin-1") for s in chblob.split(b"\0") if s]
        rblob = data[off + ofsRefs: off + ofsEnd] if ofsRefs else b""
        b.refs = [s.decode("latin-1") for s in rblob.split(b"\0") if s]
        m.bones.append(b)
        off += ofsEnd
    m.surfaces = []
    off = m.ofsSurfaces
    for i in range(m.numSurfaces):
        s = Surface()
        s.index = i
        s.raw_off = off
        s.name = cstr(data[off + 4:off + 68])
        (s.numTriangles, s.numVerts, staticSurfProcessed, ofsTri, ofsVerts,
         ofsCollapse, ofsSurfEnd, ofsCollapseIdx) = struct.unpack_from("<8i", data, off + 68)
        s.tri_bytes = data[off + ofsTri: off + ofsTri + s.numTriangles * 12]
        s.has_collapse = bool(ofsCollapse)
        # walk verts (variable length)
        voff = off + ofsVerts
        vstart = voff
        verts = []
        texofs = []
        for v in range(s.numVerts):
            voff_start = voff
            normal = struct.unpack_from("<3f", data, voff)
            texc = struct.unpack_from("<2f", data, voff + 12)
            (nw, nm) = struct.unpack_from("<2i", data, voff + 20)
            voff += 28
            # ORDER: morphs first, THEN weights  (tiki_main.cpp endian-swap loop)
            ml = []
            for w in range(nm):
                (mi,) = struct.unpack_from("<i", data, voff)
                offv = struct.unpack_from("<3f", data, voff + 4)
                voff += 16
                ml.append((mi, offv))
            wl = []
            for w in range(nw):
                (bi,) = struct.unpack_from("<i", data, voff)
                (bw,) = struct.unpack_from("<f", data, voff + 4)
                offv = struct.unpack_from("<3f", data, voff + 8)
                voff += 20
                wl.append((bi, bw, offv))
            verts.append((normal, texc, wl, ml))
            texofs.append(voff_start + 12)
        s.verts = verts
        s.texofs = texofs   # absolute byte offset of each vertex's (u, v) floats - for in-place UV patches
        s.vert_bytes = data[vstart:voff]
        m.surfaces.append(s)
        off += ofsSurfEnd
    return m


# ---------------------------------------------------------------- SKC reading

class Skc:
    pass


def read_skc(data):
    # SKC v14 (processed Breakthrough anims, e.g. It_W_Beretta.skc): skc14.py (port by the pistolsB batch agent)
    if data[4:8] == struct.pack('<i', 14):
        import flgunskc14 as skc14
        return skc14.read_skc14(data)
    a = Skc()
    assert data[0:4] == b"SKAN", data[0:4]
    (a.version, a.flags, a.nBytesUsed, a.frameTime) = struct.unpack_from("<3if", data, 4)
    a.totalDelta = struct.unpack_from("<3f", data, 20)
    (a.totalAngleDelta,) = struct.unpack_from("<f", data, 32)
    (a.numChannels, a.ofsChannelNames, a.numFrames) = struct.unpack_from("<3i", data, 36)
    a.channels = [cstr(data[a.ofsChannelNames + 32 * i: a.ofsChannelNames + 32 * i + 32])
                  for i in range(a.numChannels)]
    a.chan_base = 48 + 48 * a.numFrames
    a.data = data
    return a


def skc_channel(a, frame, chanidx):
    if getattr(a, 'version', 13) == 14:
        import flgunskc14 as skc14
        return skc14.skc_channel14(a, frame, chanidx)
    off = a.chan_base + 16 * (a.numChannels * frame + chanidx)
    return struct.unpack_from("<4f", a.data, off)


# ---------------------------------------------------------------- math (row-vector)

def quat_to_mat3(q):
    """QuatToMat from qcommon/q_math.c, verbatim (row-major m[r][c])."""
    x, y, z, w = q
    x2, y2, z2 = x + x, y + y, z + z
    xx, xy, xz = x * x2, x * y2, x * z2
    yy, yz, zz = y * y2, y * z2, z * z2
    wx, wy, wz = w * x2, w * y2, w * z2
    return [
        [1.0 - (yy + zz), xy - wz, xz + wy],
        [xy + wz, 1.0 - (xx + zz), yz - wx],
        [xz - wy, yz + wx, 1.0 - (xx + yy)],
    ]


def mat4(m3, t):
    return [m3[0][:], m3[1][:], m3[2][:], list(t)]


def mat4_mul(m1, m2):
    """SkelMat4::Multiply(m1, m2) -- row-vector: v*(m1*m2) == (v*m1)*m2."""
    out = [[0.0] * 3 for _ in range(4)]
    for c in range(3):
        for r in range(3):
            out[r][c] = m1[r][0] * m2[0][c] + m1[r][1] * m2[1][c] + m1[r][2] * m2[2][c]
        out[3][c] = m1[3][0] * m2[0][c] + m1[3][1] * m2[1][c] + m1[3][2] * m2[2][c] + m2[3][c]
    return out


IDENT4 = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0], [0, 0, 0]]


def xform_point(p, m):
    return tuple(p[0] * m[0][c] + p[1] * m[1][c] + p[2] * m[2][c] + m[3][c] for c in range(3))


def xform_dir(p, m):
    return tuple(p[0] * m[0][c] + p[1] * m[1][c] + p[2] * m[2][c] for c in range(3))


# ---------------------------------------------------------------- SKD writing

def build_container_skd(name, surfname, tri_bytes, verts, bone_block):
    """One-bone (index 0) container SKD v5, one surface, all verts single-weighted to bone 0.

    verts: list of (normal3, uv2, offset3)
    bone_block: raw 116-byte "Box01" bone block lifted from us_helmetfit.skd
    """
    numTriangles = len(tri_bytes) // 12
    numVerts = len(verts)
    vb = bytearray()
    for (normal, uv, off) in verts:
        vb += struct.pack("<3f2f2i", *normal, *uv, 1, 0)
        vb += struct.pack("<if3f", 0, 1.0, *off)
    assert len(vb) == numVerts * 48

    new_ofsTriangles = 100
    new_ofsVerts = new_ofsTriangles + numTriangles * 12
    new_ofsCollapse = new_ofsVerts + numVerts * 48
    new_ofsCollapseIndex = new_ofsCollapse + numVerts * 4
    new_ofsSurfEnd = new_ofsCollapseIndex + numVerts * 4

    sname64 = surfname.encode("latin-1")
    assert len(sname64) < 64
    sname64 += b"\x00" * (64 - len(sname64))
    surf_header = struct.pack("<4s64s8i", b"SKSF", sname64,
                              numTriangles, numVerts, 0,
                              new_ofsTriangles, new_ofsVerts, new_ofsCollapse,
                              new_ofsSurfEnd, new_ofsCollapseIndex)
    assert len(surf_header) == 100
    collapse_block = struct.pack(f"<{numVerts}i", *range(numVerts))
    collapseindex_block = struct.pack(f"<{numVerts}i", *([0] * numVerts))
    surface_bytes = surf_header + bytes(tri_bytes) + bytes(vb) + collapse_block + collapseindex_block
    assert len(surface_bytes) == new_ofsSurfEnd

    assert len(bone_block) == 116 and bone_block[0:6] == b"Box01\x00"
    total_size = 148 + len(bone_block) + len(surface_bytes)
    nm = name.encode("latin-1")
    assert len(nm) < 64
    name64 = nm + b"\x00" * (64 - len(nm))
    # lodIndex: copy the shape used by us_helmetfit.skd (passed in by caller via LOD_REF)
    header = struct.pack("<4si64s5i10i4i", b"SKMD", 5, name64,
                         1, 1, 148, 148 + len(bone_block), total_size,
                         *LOD_REF,
                         0, total_size, 0, total_size)
    assert len(header) == 148
    out = header + bone_block + surface_bytes
    assert len(out) == total_size
    return out


LOD_REF = (0,) * 10   # overwritten by the caller from us_helmetfit.skd
