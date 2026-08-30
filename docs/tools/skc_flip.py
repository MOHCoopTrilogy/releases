"""Flip a prone .skc onto its back - byte-level, no Blender.

CORRECTED per the 2026-08-26 research pass (bug-2122). The first version had three defects,
each independently confirmed against the engine's own math (skeletorbones.cpp, SkelMat4.h,
q_math.c ports tested numerically):

1. WRONG MULTIPLY SIDE. q' = R*q rotates about the bone's LOCAL X - which for the prone root
   points 47 degrees below horizontal - so the body lay on its SIDE. A model-space roll is a
   POST-multiply: q' = q*R. Cross-checked against retail pose_c(back): its root differs from
   the prone root by exactly (180 roll about model X) o (180 yaw).
2. SILENT POS NO-OP. Action-class skcs (54ch) carry NO "Bip01 pos" channel; the old tool's pos
   transform and lift did nothing, and at runtime the missing channel ZERO-FILLS
   (skeletorbones.cpp GetLerpValue3) - the root fell from z=24.256 to 0: the half-sunk body.
   The supine BASE must be flipped from a MOVEMENT-class source (rifle_prone_legs.skc, 73ch);
   action overlays (aim/shoot) legitimately carry no pos and inherit the base's.
3. FEET ARE MODEL-SPACE IK TARGETS ("Bip01 L/R Foot pos/rot" drive the leg IK directly, no
   parent multiply - skeletorbones.cpp:694-824). They must receive the SAME rigid transform or
   the legs stay prone-crossed.

The rigid transform, R = 180 about model X, mirror line z = c (FK midpoint of the prone flesh,
[2.30, 35.69] -> c = 19.0 anim units; TIKI scale 0.52 applies after):
    rot channels (root + feet): q' = q * (1,0,0,0)
    pos channels (root + feet): (x, y, z) -> (x, -y, 2c - z)
    frame delta:                (dx, dy, dz) -> (dx, -dy, dz);  angleDelta -> -angleDelta
    bounds:                     x unchanged; y -> [-y1, -y0]; z -> [2c - z1, 2c - z0]

Usage: python docs/tools/skc_flip.py <in-pak-path> <out-path> [c=19.0] [--action]
       --action permits a source with no "Bip01 pos" (overlay anims); otherwise that is an
       ERROR, because it silently produced the sunk body once already.
"""
import io, math, os, struct, sys, zipfile, glob

ROOTS = [r"G:/mohaa-gl2/main", r"G:/mohaa-gl2/mainta", r"G:/mohaa-gl2/maintt"]
ROT_CH = ("bip01 rot", "bip01 l foot rot", "bip01 r foot rot")
# The spine chain, hips -> head. Counter-rolling these UN-TWISTS the upper body out of the root's
# flip: the hips and legs stay rolled onto the back while the chest, arms, head - and therefore the
# gun, which hangs off this chain - come back up. Measured justification: retail's own prone TURN
# (rifle_prone_turn_left) swings the root through 125 degrees while the spine counter-rotates against
# it (spine pitch 9.6 -> -15.6, spine1 2.9 -> -16.3) and the body lifts ~1.8u. A soldier turning over
# on the ground articulates; he does not rotate as one rigid piece, which is what the first cut did.
SPINE_CH = ("bip01 spine rot", "bip01 spine1 rot", "bip01 spine2 rot", "bip01 neck rot",
            "bip01 head rot")
POS_CH = ("bip01 pos", "bip01 l foot pos", "bip01 r foot pos")


def read_from_paks(relpath):
    rel = relpath.lower().replace(chr(92), "/")
    best = None
    for root in ROOTS:
        for pk in sorted(glob.glob(os.path.join(root, "*.pk3"))):
            try:
                z = zipfile.ZipFile(pk)
            except Exception:
                continue
            for n in z.namelist():
                if n.lower().replace(chr(92), "/") == rel:
                    best = z.read(n)
    assert best, "not found in any pak: " + relpath
    return bytearray(best)


def qmul(a, b):  # (x,y,z,w)
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def qaxis(deg):
    """Quaternion for a rotation of `deg` about model +X, as (x,y,z,w)."""
    h = math.radians(deg) * 0.5
    return (math.sin(h), 0.0, 0.0, math.cos(h))


def flip(data, c, allow_action, untwist=0.0, lift=0.0):
    R = (1.0, 0.0, 0.0, 0.0)  # 180 deg about model-space +X (the body's long axis)
    numChannels, ofsNames, numFrames = struct.unpack_from("<3i", data, 36)
    assert 0 < numFrames < 100000 and 0 < numChannels < 1000, (numFrames, numChannels)

    names = []
    for i in range(numChannels):
        raw = bytes(data[ofsNames + 32 * i : ofsNames + 32 * i + 32])
        names.append(raw.split(b"\0")[0].decode("latin-1").lower())
    rot_idx = [i for i, n in enumerate(names) if n in ROT_CH]
    pos_idx = [i for i, n in enumerate(names) if n in POS_CH]
    spine_idx = [i for i, n in enumerate(names) if n in SPINE_CH]
    # Spread the counter-roll evenly down the chain. No single joint can carry it - a human tops out
    # near 45 degrees of thoracic rotation - so distributing it across every spine bone present is
    # both the anatomically honest option and the one that reads as a body propping itself up.
    per = (untwist / float(len(spine_idx))) if (spine_idx and untwist) else 0.0
    Runt = qaxis(-per) if per else None
    assert any(n == "bip01 rot" for n in names), "no root rot channel; " + ", ".join(names[:8])
    if not any(n == "bip01 pos" for n in names):
        assert allow_action, (
            "source has NO 'Bip01 pos' - it is an ACTION overlay. Flipping it as a base "
            "produced the half-sunk body once already (bug-2122). Pass --action if this is "
            "deliberately an overlay that inherits the base's root."
        )

    # totalDelta y mirrors; totalAngleDelta negates
    tx, ty, tz = struct.unpack_from("<3f", data, 20)
    struct.pack_into("<3f", data, 20, tx, -ty, tz)
    tad, = struct.unpack_from("<f", data, 32)
    struct.pack_into("<f", data, 32, -tad)

    for f in range(numFrames):
        base = 48 + 48 * f
        b = list(struct.unpack_from("<6f", data, base))
        x0, y0, z0, x1, y1, z1 = b
        struct.pack_into("<6f", data, base, x0, -y1, 2 * c - z1, x1, -y0, 2 * c - z0)
        dx, dy, dz = struct.unpack_from("<3f", data, base + 28)
        struct.pack_into("<3f", data, base + 28, dx, -dy, dz)
        ad, = struct.unpack_from("<f", data, base + 40)
        struct.pack_into("<f", data, base + 40, -ad)
        ofsCh, = struct.unpack_from("<i", data, base + 44)
        for ci in rot_idx:
            o = ofsCh + 16 * ci
            q = struct.unpack_from("<4f", data, o)
            struct.pack_into("<4f", data, o, *qmul(q, R))  # POST-multiply: model-space roll
        for ci in pos_idx:
            o = ofsCh + 16 * ci
            x, y, z, w = struct.unpack_from("<4f", data, o)
            zz = 2 * c - z
            if names[ci] == "bip01 pos":
                zz += lift  # the body pushes up off the ground as it comes over (retail turn: ~1.8u)
            struct.pack_into("<4f", data, o, x, -y, zz, w)
        if Runt is not None:
            for ci in spine_idx:
                o = ofsCh + 16 * ci
                q = struct.unpack_from("<4f", data, o)
                struct.pack_into("<4f", data, o, *qmul(q, Runt))
    return data


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--action" and not a.startswith("--")]
    allow_action = "--action" in sys.argv
    src, dst = args[0], args[1]
    c = float(args[2]) if len(args) > 2 else 19.0
    untwist = 0.0
    lift = 0.0
    for a in sys.argv[1:]:
        if a.startswith("--untwist="): untwist = float(a.split("=", 1)[1])
        elif a.startswith("--lift="):  lift = float(a.split("=", 1)[1])
    d = flip(read_from_paks(src), c, allow_action, untwist, lift)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    io.open(dst, "wb").write(bytes(d))
    print("flipped %s -> %s (c=%.1f%s, %d bytes)" % (src, dst, c, ", action-overlay" if allow_action else "", len(d)))
