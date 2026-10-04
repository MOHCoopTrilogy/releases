# -*- coding: utf-8 -*-
"""m3l2-only shader separation, as a byte-exact BSP patch (no recompile, no geometry change).

What it changes in maps/m3l2.bsp (retail main/Pak5.pk3, sha256 pinned):
  * the SHADER lump is rewritten at the end of the file (header entry 0 re-pointed; the old bytes stay where they
    were, unreferenced) with:
      - entry ROAD_CURVE (the 66 road curve patches) and ROAD_PLANAR (the planar road / bridge faces) renamed
        textures/wilderness/m3l3grass_bocroad -> textures/hzm_m3l2/road  (flags, contents, fence mask untouched)
      - TWO appended entries: textures/hzm_m3l2/farmyard (ROAD_PLANAR flags) and ../farmyard_b (barnyard flags)
  * the shaderNum of the courtyard faces (YARD) and barnyard faces (BARN) -> those entries (4 bytes each, in place).
Nothing else moves: every other lump is byte-identical at its original offset, so the lightmap lump hash that the
staged foliage-shadow patch (maps/<map>.hzmlm) keys on, the brush indices cmpatch uses, and every surface / brush /
static-model index are unchanged. Brush sides keep their shader indices (collision, footstep and impact flags are
the same flag words). The map CHECKSUM does NOT change: CM_Checksum (cm_load.c:759-777) returns the header's stored
checksum field (bytes 8-11), which this patch never writes - so an older client still joins (and sees the old ground).
Two entries are appended: FARMYARD for the courtyard faces and FARMYARD_B for the barnyard faces, because the
farmyard is world-projected (tcGen vector) and gl2 builds the relief tangent frame from the BSP's OWN uv: each group
gets projection vectors along its own uv basis (uv_basis()), so the generated relief is lit from the right side.
"""
import hashlib, struct

BSP_SHA = None                 # filled/verified by the caller (retail main/Pak5.pk3 maps/m3l2.bsp)
ROAD_CURVE = 286
ROAD_PLANAR = 58
OLD_NAME = b"textures/wilderness/m3l3grass_bocroad"
ROAD = b"textures/hzm_m3l2/road"
YARD = b"textures/hzm_m3l2/farmyard"
YARD_B = b"textures/hzm_m3l2/farmyard_b"
# courtyard strips (4317 4318 4321 4322), east passage (4319 4320), gate passage between the moat bank and the
# courtyard (1314) - all currently ROAD_PLANAR. The NW path (2081 2082) and the east lane (1211 2160 2161) stay ROAD:
# they border the terrain grass, and the road texture's grass shoulders are what soften that edge.
YARD_SURFS = (4317, 4318, 4321, 4322, 4319, 4320, 1314)
# optional: the barnyard floor at the late-map barn (bocage_stevereq, shader entry 90, 128 u repeat)
BARN_ENTRY = 90
BARN_SURFS = (2624, 2625, 2626, 2627, 2628, 2630, 2631, 2632)
SH_SZ, SURF_SZ = 140, 108
PERIOD = 512.0        # world units per farmyard texture repeat (gen_m3l2_ground.FARM_PERIOD)


def tcgen_vectors(b, period=PERIOD):
    """{shader name: (s vector, t vector)} - world-xy projection along each group's OWN uv axes (see docstring)."""
    out = {}
    for name, surfs in ((YARD, YARD_SURFS), (YARD_B, BARN_SURFS)):
        us, ut = uv_basis(b, surfs)
        out[name.decode()] = ((us[0] / period, us[1] / period, 0.0), (ut[0] / period, ut[1] / period, 0.0))
    return out


def lumps(b):
    ident, version = struct.unpack_from("<4si", b, 0)
    assert ident == b"2015" and version == 19, (ident, version)
    return [list(struct.unpack_from("<ii", b, 12 + 8 * i)) for i in range(28)]


def uv_basis(b, surfs):
    """unit world-xy directions of +s and +t shared by the faces (asserted common), for tcGen vector."""
    import numpy as np
    L = lumps(b)
    dv = b[L[4][0]:L[4][0] + L[4][1]]
    nv = len(dv) // 44
    V = np.frombuffer(dv[:nv * 44], dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2),
                                                     ("n", "<f4", 3), ("c", "u1", 4)]))
    IX = np.frombuffer(b[L[5][0]:L[5][0] + L[5][1]], "<i4")
    out = []
    for s in surfs:
        o = L[3][0] + s * SURF_SZ
        sn, fog, st, fv, nvx, fi, nix = struct.unpack_from("<7i", b, o)
        idx = IX[fi:fi + nix] + fv
        P, S = V["xyz"][idx].astype(float), V["st"][idx].astype(float)
        A = np.c_[P[:, 0] - P[:, 0].mean(), P[:, 1] - P[:, 1].mean()]
        gs = np.linalg.lstsq(A, S[:, 0] - S[:, 0].mean(), rcond=None)[0]
        gt = np.linalg.lstsq(A, S[:, 1] - S[:, 1].mean(), rcond=None)[0]
        out.append((gs / np.linalg.norm(gs), gt / np.linalg.norm(gt)))
    us = np.mean([o[0] for o in out], 0)
    ut = np.mean([o[1] for o in out], 0)
    assert all(np.dot(o[0], us) > 0.999 and np.dot(o[1], ut) > 0.999 for o in out), "faces do not share a uv basis"
    return us / np.linalg.norm(us), ut / np.linalg.norm(ut)


def patch(b, yard_surfs=YARD_SURFS, barn_surfs=BARN_SURFS):
    L = lumps(b)
    so, sl = L[0]
    sh = bytearray(b[so:so + sl])
    n = sl // SH_SZ
    assert sl % SH_SZ == 0
    for k in (ROAD_CURVE, ROAD_PLANAR):
        nm = bytes(sh[k * SH_SZ:k * SH_SZ + 64]).split(b"\0")[0]
        assert nm.lower() == OLD_NAME, (k, nm)
    new_entry = bytearray(sh[ROAD_PLANAR * SH_SZ:(ROAD_PLANAR + 1) * SH_SZ])
    new_entry[0:64] = YARD.ljust(64, b"\0")
    new_b = bytearray(sh[BARN_ENTRY * SH_SZ:(BARN_ENTRY + 1) * SH_SZ])
    assert bytes(new_b[0:64]).split(b"\0")[0].lower() == b"textures/misc_outside/bocage_stevereq"
    new_b[0:64] = YARD_B.ljust(64, b"\0")
    for k in (ROAD_CURVE, ROAD_PLANAR):
        sh[k * SH_SZ:k * SH_SZ + 64] = ROAD.ljust(64, b"\0")
    sh += new_entry
    sh += new_b
    yard_idx, barn_idx = n, n + 1
    out = bytearray(b)
    pad = (-len(out)) % 4
    out += b"\0" * pad
    new_off = len(out)
    out += sh
    struct.pack_into("<ii", out, 12, new_off, len(sh))
    fo, fl = L[3]
    for group, want, idx in ((yard_surfs, ROAD_PLANAR, yard_idx), (barn_surfs, BARN_ENTRY, barn_idx)):
        for s in group:
            o = fo + s * SURF_SZ
            cur = struct.unpack_from("<i", out, o)[0]
            assert cur == want, (s, cur)
            struct.pack_into("<i", out, o, idx)
    return bytes(out), dict(yard_index=yard_idx, barn_index=barn_idx, shader_count=n + 2, shader_lump_offset=new_off,
                            yard_surfs=list(yard_surfs), barn_surfs=list(barn_surfs))


def verify(orig, new, yard_surfs=YARD_SURFS + BARN_SURFS):
    """every byte outside the header lump-0 entry, the yard shaderNum words and the appended tail is identical."""
    Lo, Ln = lumps(orig), lumps(new)
    assert Lo[1:] == Ln[1:], "only lump 0 may move"
    fo = Lo[3][0]
    allowed = set(range(12, 20))
    for s in yard_surfs:
        allowed |= set(range(fo + s * SURF_SZ, fo + s * SURF_SZ + 4))
    a, c = memoryview(orig), memoryview(new)
    diff = [i for i in range(0, len(orig), 1) if a[i] != c[i]] if False else None
    # fast compare in chunks
    bad = []
    step = 1 << 16
    for i in range(0, len(orig), step):
        if a[i:i + step] != c[i:i + step]:
            for j in range(i, min(len(orig), i + step)):
                if a[j] != c[j] and j not in allowed:
                    bad.append(j)
    assert not bad, "unexpected byte changes at %s" % bad[:10]
    so, sl = Ln[0]
    sh = new[so:so + sl]
    names = [sh[i * SH_SZ:i * SH_SZ + 64].split(b"\0")[0] for i in range(sl // SH_SZ)]
    old = orig[Lo[0][0]:Lo[0][0] + Lo[0][1]]
    oldn = [old[i * SH_SZ:i * SH_SZ + 64].split(b"\0")[0] for i in range(len(old) // SH_SZ)]
    changed = [i for i in range(len(oldn)) if names[i] != oldn[i]]
    assert changed == sorted((ROAD_PLANAR, ROAD_CURVE)), changed
    for i in range(len(oldn)):          # flags/contents/fence identical for every original entry
        assert sh[i * SH_SZ + 64:(i + 1) * SH_SZ] == old[i * SH_SZ + 64:(i + 1) * SH_SZ]
    assert names[-2:] == [YARD, YARD_B] and len(names) == len(oldn) + 2
    assert new[8:12] == orig[8:12], "header checksum field must not change"
    return dict(changed_entries=changed, appended=2, bytes_added=len(new) - len(orig),
                sha256=hashlib.sha256(new).hexdigest())
