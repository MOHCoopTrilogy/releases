#!/usr/bin/env python
"""gen_coop_wake_skc.py - the Higgins wake clip re-encoded as SKC v13 ([user 2026-09-06, bug-2508]).

WHAT IT WRITES
  hzm-mohaa-coop-mod/models/fx/wake/coop_wake.skc   1 frame, 2 channels, SKAN version 13

WHY. models/fx/coop_wake.tik keeps `path models/fx/wake` + `skelmodel wake.skd` (retail Pak0) but its
animations pointed at retail's `wake.skc`, which is SKAN version 11. SkeletorCacheFileCallback
(openmohaa-hzm/code/tiki/tiki_files.cpp:578-592) accepts only TIKI_SKC_HEADER_OLD_VERSION 13 and
TIKI_SKC_HEADER_VERSION 14 (tiki/tiki_shared.h:72-73) and returns NULL for anything else, so TIKI init
aborted and the wake never appeared. This writes the same single frame as a v13 file beside the retail
skd, under a coop name (TRAPS T6: one name, one coop file).

THE RETAIL v11 FILE, AS READ (re-read the bytes, do not trust this table - `--dump` prints them):
  header  ident SKAN, version 11, then a 64-byte name field ("wake.skc") the v13 layout does not have;
          @80 frameTime 1/30, @96 ofsFrames 2160, @108 numChannels 2 (@72/@112 are 0xCDCDCDCD junk)
  frame   @2160: bounds (-401.39 -268.54 74.69)..(720.93 275.79 143.86), radius 785.17, delta (0 0 0),
          then the channel values INLINE (no angleDelta / iOfsChannels as v13 has):
          'Box02 pos' = (0 0 0 <junk w>), 'Box02 rot' = (0 0.7071 0.7071 0)
  names   'Box02 pos' @2240, 'Box02 rot' @2272 (32-byte stride; the file ends 8 bytes short)
The channel assignment is PROVEN, not assumed: posing wake.skd's 44 verts through the rot quaternion
reproduces the frame bounds exactly (x -401.4..720.9, y -268.5..275.8, z 74.7..143.9), which is also
why the tik header says the posed mesh sits +39..+75 u ABOVE its origin at scale 0.52 (bound it at
hull z, not water z) and forward is model -X (the 209 u lobe; the 375 u +X lobe trails).

The v13 writer is gen_coop_sea.build_skc, unchanged and self-tested against the shipping
models/coop_helmets/us_helmetfit.skc byte-for-byte before it writes ours. flags is 0: the only SKC
header flag the skeletor consults is TAF_DELTADRIVEN (skeletor.cpp:55-76) and a static clip has no
delta; loop/one-shot comes from the tik anim def, not from here.

    python docs/tools/gen_coop_wake_skc.py            # write + verify
    python docs/tools/gen_coop_wake_skc.py --check    # re-parse the shipped file, exit 1 on drift
    python docs/tools/gen_coop_wake_skc.py --dump     # print the retail v11 bytes it decodes
"""
import argparse
import math
import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
sys.path.insert(0, HERE)
import gen_coop_sea as sea  # noqa: E402  (the SKC v13 writer + its selftest; also puts skdlib on sys.path)
import skdlib  # noqa: E402

PAK0_CANDIDATES = (
    "G:/mohaa-gl2/main/Pak0.pk3",
    "G:/GOG/Medal of Honor - Allied Assault War Chest/main/Pak0.pk3",
)
RETAIL_SKC = "models/fx/wake/wake.skc"
RETAIL_SKD = "models/fx/wake/wake.skd"
OUT_SKC = os.path.join(MOD, "models", "fx", "wake", "coop_wake.skc")
REF_SKC = os.path.join(MOD, "models", "coop_helmets", "us_helmetfit.skc")

CHANNELS = ("Box02 pos", "Box02 rot")      # the order the retail file stores them in
TIK_SCALE = 0.52                           # coop_wake.tik `scale 0.52`, for the report only

# the verifier's read, asserted against the bytes
EXPECT_BMIN = (-401.4, -268.5, 74.7)
EXPECT_BMAX = (720.9, 275.8, 143.9)
EXPECT_RADIUS = 785.2
EXPECT_ROT = (0.0, 0.7071, 0.7071, 0.0)
TOL = 0.1


def find_pak0():
    for p in PAK0_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("Pak0.pk3 not found at any of: %s" % ", ".join(PAK0_CANDIDATES))


def read_retail_v11(data):
    """Decode the single frame of retail wake.skc (SKAN 11). Returns a dict of the fields we carry over."""
    assert data[0:4] == b"SKAN", data[0:4]
    (version,) = struct.unpack_from("<i", data, 4)
    assert version == 11, ("retail wake.skc is not v11 any more?", version)
    name = skdlib.cstr(data[8:72])
    assert name == "wake.skc", name
    (frame_time,) = struct.unpack_from("<f", data, 80)
    (ofs_frames,) = struct.unpack_from("<i", data, 96)
    (num_channels,) = struct.unpack_from("<i", data, 108)
    assert abs(frame_time - 1.0 / 30.0) < 1e-6, frame_time
    assert num_channels == 2, num_channels
    assert 0 < ofs_frames < len(data), ofs_frames
    # channel names: found by content, 32-byte stride, pos first
    ofs_pos = data.find(b"Box02 pos\x00")
    ofs_rot = data.find(b"Box02 rot\x00")
    assert ofs_pos > 0 and ofs_rot == ofs_pos + 32, (ofs_pos, ofs_rot)
    # frame: bounds(6f) radius(f) delta(3f) then numChannels * vec4 inline
    (b0, b1, b2, b3, b4, b5, radius) = struct.unpack_from("<7f", data, ofs_frames)
    delta = struct.unpack_from("<3f", data, ofs_frames + 28)
    assert delta == (0.0, 0.0, 0.0), delta
    pos = struct.unpack_from("<4f", data, ofs_frames + 40)
    rot = struct.unpack_from("<4f", data, ofs_frames + 56)
    assert ofs_frames + 72 == ofs_pos - 8, ("frame does not end where the name table begins", ofs_frames, ofs_pos)
    bmin, bmax = (b0, b1, b2), (b3, b4, b5)
    for a, e in zip(bmin + bmax, EXPECT_BMIN + EXPECT_BMAX):
        assert abs(a - e) < TOL, (bmin, bmax)
    assert abs(radius - EXPECT_RADIUS) < TOL, radius
    assert pos[0] == 0.0 and pos[1] == 0.0 and pos[2] == 0.0, pos      # w is 0xCDCDCDCD junk in the file
    for a, e in zip(rot, EXPECT_ROT):
        assert abs(a - e) < 1e-3, rot
    assert abs(math.sqrt(sum(c * c for c in rot)) - 1.0) < 1e-5, ("rot is not a unit quaternion", rot)
    return {
        "frame_time": frame_time, "bmin": bmin, "bmax": bmax, "radius": radius,
        "pos": (0.0, 0.0, 0.0, 0.0), "rot": rot,
        "ofs_frames": ofs_frames, "ofs_pos": ofs_pos, "ofs_rot": ofs_rot, "version": version,
    }


def prove_pose(skd_bytes, rot, bmin, bmax):
    """The rot channel posed onto wake.skd must land the mesh inside the frame bounds exactly -
    that is what proves which vec4 is the rotation and which the position."""
    m = skdlib.read_skd(skd_bytes)
    assert m.numBones == 1 and m.bones[0].name == "Box02" and m.bones[0].jointType == 1, \
        [(b.name, b.jointType) for b in m.bones]
    assert sorted(m.bones[0].channels) == sorted(CHANNELS), m.bones[0].channels
    M = skdlib.mat4(skdlib.quat_to_mat3(rot), (0.0, 0.0, 0.0))
    pts = [skdlib.xform_point(w[0][2], M) for s in m.surfaces for w in (v[2] for v in s.verts)]
    lo = tuple(min(p[i] for p in pts) for i in range(3))
    hi = tuple(max(p[i] for p in pts) for i in range(3))
    for a, e in zip(lo + hi, bmin + bmax):
        assert abs(a - e) < 0.01, ("posed mesh does not match the frame bounds", lo, hi, bmin, bmax)
    return len(pts), lo, hi


def build(retail):
    return sea.build_skc(retail["frame_time"], retail["bmin"], retail["bmax"], retail["radius"],
                         CHANNELS, [retail["pos"], retail["rot"]], flags=0)


def verify_written(skc, retail):
    a = skdlib.read_skc(skc)
    assert a.version == 13 and a.flags == 0 and a.numFrames == 1 and a.numChannels == 2, \
        (a.version, a.flags, a.numFrames, a.numChannels)
    assert list(a.channels) == list(CHANNELS), a.channels
    assert abs(a.frameTime - retail["frame_time"]) < 1e-9
    (bmin0, bmin1, bmin2, bmax0, bmax1, bmax2, radius) = struct.unpack_from("<7f", skc, 48)
    assert (bmin0, bmin1, bmin2) == retail["bmin"] and (bmax0, bmax1, bmax2) == retail["bmax"]
    assert radius == retail["radius"]
    assert skdlib.skc_channel(a, 0, 0) == retail["pos"]
    assert skdlib.skc_channel(a, 0, 1) == retail["rot"]
    (ofs_ch,) = struct.unpack_from("<i", skc, 48 + 44)
    assert ofs_ch == 96 and a.nBytesUsed == len(skc) == 96 + 32 + 64, (ofs_ch, a.nBytesUsed, len(skc))
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="re-parse the shipped file; write nothing; exit 1 on drift")
    ap.add_argument("--dump", action="store_true", help="print the decoded retail v11 fields and exit")
    args = ap.parse_args()

    pak = find_pak0()
    z = zipfile.ZipFile(pak)
    retail_bytes = z.read(RETAIL_SKC)
    retail = read_retail_v11(retail_bytes)
    nverts, lo, hi = prove_pose(z.read(RETAIL_SKD), retail["rot"], retail["bmin"], retail["bmax"])
    print("retail %s from %s: %d bytes, SKAN %d, frame @%d, names @%d/@%d" % (
        RETAIL_SKC, pak, len(retail_bytes), retail["version"], retail["ofs_frames"], retail["ofs_pos"], retail["ofs_rot"]))
    print("  frameTime %.6f bounds (%.1f %.1f %.1f)..(%.1f %.1f %.1f) radius %.1f" % (
        (retail["frame_time"],) + retail["bmin"] + retail["bmax"] + (retail["radius"],)))
    print("  'Box02 pos' %s  'Box02 rot' (%.4f %.4f %.4f %.4f)" % ((retail["pos"],) + retail["rot"]))
    print("  wake.skd: %d verts posed through rot -> x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f (= frame bounds)" % (
        (nverts,) + (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])))
    print("  at tik scale %.2f: x %.1f..%.1f (forward is -X, the short lobe), z %.1f..%.1f above the origin" % (
        TIK_SCALE, lo[0] * TIK_SCALE, hi[0] * TIK_SCALE, lo[2] * TIK_SCALE, hi[2] * TIK_SCALE))
    if args.dump:
        return

    sea.selftest_skc_writer(open(REF_SKC, "rb").read())
    skc = build(retail)
    verify_written(skc, retail)

    if args.check:
        have = open(OUT_SKC, "rb").read() if os.path.exists(OUT_SKC) else None
        if have != skc:
            print("DRIFT %s" % os.path.relpath(OUT_SKC, ROOT))
            sys.exit(1)
        verify_written(have, retail)
        print("ok    %s (%d bytes, SKAN 13, 1 frame, 2 channels, re-parsed)" % (os.path.relpath(OUT_SKC, ROOT), len(have)))
        return

    os.makedirs(os.path.dirname(OUT_SKC), exist_ok=True)
    open(OUT_SKC, "wb").write(skc)
    verify_written(open(OUT_SKC, "rb").read(), retail)
    print("wrote %s (%d bytes, SKAN 13, 1 frame, 2 channels)" % (os.path.relpath(OUT_SKC, ROOT), len(skc)))


if __name__ == "__main__":
    main()
