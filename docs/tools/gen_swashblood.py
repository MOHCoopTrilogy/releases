# -*- coding: utf-8 -*-
"""GENERATOR for textures/coop_fx/swashblood.tga - blood slicks in the swash on Omaha's tidal sand strip
[user 2026-09-06, bug-2508]. Drawn by stage 3 of hzm-mohaa-coop-mod/scripts/zz_coop_wetsand.shader,
clamped in T, `blendFunc blend`, translated in T by the wet line's own wavetrant (sin 0.45 0.75 0 0.08).

WHAT IT IS. The ocean pass (docs/proposals/ocean_2026-09-06, item 1) hands the blood in the swash from
the waterline sheet to the sand strip: the sheet's blood stage tiles T twice so no bake can pin an edge to
it, and its edge is straight. On the sand strip T is the shore distance (1.0 = sea edge, 0 = land edge,
zz_coop_wetsand.shader header) and clampmapy holds it, so the reach of the blood can be BAKED INTO ALPHA.
It must be baked: this shader has no deform, gl2 folds it into lightall, and lightall drops
`alphaGen sCoord/tCoord` (bug-2486) - texture alpha is the only alpha lightall honours.

HOW IT IS BUILT. Two ingredients, both already in the repo:
  * the slick field follows gen_bloodwash.py's rule (bug-2230) - every term has an INTEGER period, so it
    tiles along the beach with no seam; the strip's S is one texture per 256 u and restarts per quad, so
    only an integer period is seamless (bug-2493) - but is built from plane waves and wrapped value noise
    instead of sine products (see WAVES/NOISE for why). Thresholded to a target coverage with
    gen_bloodwash's soft shoulder and gamma, retinted with its venous palette [user 2026-09-01], thin
    edges brighter than thick middles.
  * the reach rides gen_wetsand.py's per-column offset o(s) (bug-2493) at 1.0x, so the blood's ragged
    edge IS the wet line's rag - the two stages share one wavetrant, so they stay aligned at every phase.

WHERE THE BLOOD SITS, in texture t (v = t - o(s)):
    alpha 0 for v <= 0.30, ramp to 1 by 0.45 (the wet line's rest position - the gradient's grey starts
    at v 0.45, its ramp at 0.25..0.45), full to 0.80, ramp to 0 by 0.88, 0 above; every row t >= 0.96 is
    forced black AND transparent (top guard, ramped from 0.92) so the clamped sea-edge row cannot smear
    when the wave pushes v past 1, and the land-edge row is transparent by the same window so the clamp
    at v < 0 draws nothing either.
    On the world (T = t - wave): at rest the slicks cover the landward T 0..0.45 behind the wet line;
    at the trough they ride out to T 0.65..1.0 with the draining water; through the flood they slide
    landward under the sheet and off the strip - blood carried by the swash, not painted on the beach.

DXT5 SAFETY. r_ext_compressed_textures compresses an RGBA upload to DXT5, which quantises alpha per 4x4
block between two endpoints: every ramp here is at least 20 rows long, and transparent texels next to a
slick carry the THIN blood colour rather than black, so neither DXT colour interpolation nor bilinear
filtering can darken a slick's edge into a halo (blendFunc blend never samples the colour of an alpha-0
texel except through those two paths). The guard rows are the one place RGB is black, and they are
asserted.

18-byte TGA header (the 13-byte header of 2026-09-06, bug-2493, read every row 5 bytes off), 256x256,
32-bit BGRA, descriptor 8, first file row = t 1.0 (the sea edge) exactly as gen_wetsand.py writes its
foam. DETERMINISTIC: no randomness, re-running reproduces the file byte for byte; --check verifies that
without writing. Run from anywhere: python docs/tools/gen_swashblood.py [--check]
"""

import argparse
import math
import os
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "hzm-mohaa-coop-mod", "textures", "coop_fx", "swashblood.tga")
W = 256
H = 256

# ---- the slick field. gen_bloodwash.py's sum of sin(x)*sin(y) PRODUCTS at integer frequencies is seamless,
# but on its own (there it is multiplied by an authored source) it is a plaid: the products cross-hatch,
# and its lowest band is one 256 u blob per tile, which repeats visibly along the beach. Kept seamless the
# same way - every term has an INTEGER period in both axes - but built from PLANE WAVES sin(fx*x + fy*y + ph)
# at mixed directions (no cross-hatch) plus two octaves of value noise on a WRAPPED lattice (a 256-period
# lattice tiles by construction), so a tile carries a dozen slicks of 20..60 u and the repeat is not read.
# |fy| >= |fx| on most waves elongates the slicks along the beach (S), the way the swash smears them.
WAVES = [(1, 2, 1.00, 0.00), (2, -3, 0.85, 1.31), (-3, 2, 0.70, 2.60), (2, 5, 0.60, 0.77), (4, -4, 0.50, 3.94),
         (-5, 3, 0.45, 5.21), (3, 7, 0.35, 1.90), (6, -5, 0.30, 4.47), (-7, 6, 0.25, 0.35), (5, 9, 0.20, 2.22)]
NOISE = [(8, 0.55), (16, 0.30), (32, 0.15)]   # (lattice cells per tile, weight) - wrapped, so seamless
SEED = 2508


def _hash01(i, j, k):
    """Deterministic lattice hash in [0,1) - no random module, so every platform bakes the same bytes."""
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791) ^ SEED
    h = (h * 2654435761) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return (h & 0xFFFFFF) / float(0x1000000)


def _vnoise(x, y, cells, k):
    """Value noise on a lattice that wraps every `cells` cells - seamless across the tile by construction."""
    gx = x * cells / float(W); gy = y * cells / float(H)
    i0 = int(math.floor(gx)); j0 = int(math.floor(gy))
    fx = gx - i0; fy = gy - j0
    fx = fx * fx * (3.0 - 2.0 * fx); fy = fy * fy * (3.0 - 2.0 * fy)
    i1 = (i0 + 1) % cells; j1 = (j0 + 1) % cells; i0 %= cells; j0 %= cells
    a = _hash01(i0, j0, k); b_ = _hash01(i1, j0, k); c = _hash01(i0, j1, k); d = _hash01(i1, j1, k)
    return (a * (1 - fx) + b_ * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


# Fraction of texels INSIDE the full-reach band that carry blood. Sparser than the sheet's 0.42: on sand
# the slicks read against a dark wet ground, and clear sand between them is what makes them slicks.
TARGET_COVERAGE = 0.38

# gen_bloodwash.py's venous palette [user 2026-09-01]: THIN = feathered edge, THICK = middle of a slick.
RED_R_THIN, RED_G_THIN, RED_B_THIN = 106, 21, 16
RED_R_THICK, RED_G_THICK, RED_B_THICK = 58, 8, 6

# The reach window in v = t - o(s); see the module docstring.
REACH_LAND_0, REACH_LAND_1 = 0.30, 0.45
REACH_SEA_1, REACH_SEA_0 = 0.80, 0.88
GUARD_1, GUARD_0 = 0.92, 0.96          # in raw t: alpha ramps to 0 by 0.96, rows above are black+transparent


def off(s):
    """gen_wetsand.py's per-column wander o(s), s in [0,1) periodic, in T units. Copied verbatim - the
    blood's rag must be the wet line's rag, so this must not drift from that file."""
    return (0.050 * math.sin(2 * math.pi * s)
            + 0.030 * math.sin(2 * math.pi * 3 * s + 1.7)
            + 0.018 * math.sin(2 * math.pi * 5 * s + 0.6)
            + 0.012 * math.sin(2 * math.pi * 11 * s + 2.9))


def t_of_row(r):
    return (H - 1 - r + 0.5) / H


def field():
    """Seamless [0,1] slick field: plane waves plus wrapped value noise, both integer-period in S and T."""
    wnorm = sum(w[2] for w in WAVES)
    nnorm = sum(n[1] for n in NOISE)
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            acc = 0.0
            for fx, fy, wgt, ph in WAVES:
                acc += wgt * math.sin(2.0 * math.pi * (fx * x / float(W) + fy * y / float(H)) + ph)
            pw = (acc / wnorm + 1.0) * 0.5
            vn = sum(wgt * _vnoise(x, y, cells, k) for k, (cells, wgt) in enumerate(NOISE)) / nnorm
            row.append(0.55 * pw + 0.45 * vn)
        rows.append(row)
    return rows


def reach(v):
    if v <= REACH_LAND_0:
        return 0.0
    if v < REACH_LAND_1:
        return (v - REACH_LAND_0) / (REACH_LAND_1 - REACH_LAND_0)
    if v <= REACH_SEA_1:
        return 1.0
    if v < REACH_SEA_0:
        return (REACH_SEA_0 - v) / (REACH_SEA_0 - REACH_SEA_1)
    return 0.0


def guard(t):
    if t <= GUARD_1:
        return 1.0
    if t < GUARD_0:
        return (GUARD_0 - t) / (GUARD_0 - GUARD_1)
    return 0.0


def build():
    offs = [off((c + 0.5) / W) for c in range(W)]
    assert max(abs(o) for o in offs) <= 0.105, "o(s) drifted from gen_wetsand.py"
    f = field()

    # slick alpha: threshold the field so TARGET_COVERAGE of the full-reach band survives, then
    # gen_bloodwash's shoulder (gamma toward strong-where-present, smoothstep for feathered edges)
    inband = []
    for r in range(H):
        t = t_of_row(r)
        for c in range(W):
            if reach(t - offs[c]) >= 1.0 and guard(t) >= 1.0:
                inband.append(f[r][c])
    srt = sorted(inband)
    cut = srt[int((1.0 - TARGET_COVERAGE) * (len(srt) - 1))]
    span = max(1e-6, srt[-1] - cut)

    def slick(v):
        if v <= cut:
            return 0.0
        x = (v - cut) / span
        x = x ** 0.38
        x = x * x * (3.0 - 2.0 * x)
        return min(1.0, 0.30 + 0.70 * x)

    rows = []
    for r in range(H):
        t = t_of_row(r)
        g = guard(t)
        row = bytearray()
        for c in range(W):
            v = t - offs[c]
            a = slick(f[r][c]) * reach(v) * g
            if a <= 0.0:
                if t >= GUARD_0:
                    bgr = (0, 0, 0)                                   # guard rows: black AND transparent
                else:
                    bgr = (RED_B_THIN, RED_G_THIN, RED_R_THIN)        # DXT/bilinear halo fill, never drawn
                a8 = 0
            else:
                k = a                                                 # thickness drives the hue
                rr = int(round(RED_R_THIN + (RED_R_THICK - RED_R_THIN) * k))
                gg = int(round(RED_G_THIN + (RED_G_THICK - RED_G_THIN) * k))
                bb = int(round(RED_B_THIN + (RED_B_THICK - RED_B_THIN) * k))
                bgr = (bb, gg, rr)
                a8 = int(round(a * 255))
            row += bytes((bgr[0], bgr[1], bgr[2], a8))
        rows.append(bytes(row))
    hdr = bytes([0, 0, 2]) + struct.pack('<HHB', 0, 0, 0) + struct.pack('<HHHHBB', 0, 0, W, H, 32, 8)
    assert len(hdr) == 18
    return hdr + b"".join(rows), cut


def check(data):
    """The per-row RGB*alpha dump that caught the black-band and 13-byte-header bakes (bug-2485/2493)."""
    assert len(data) == 18 + W * H * 4, len(data)
    print("swashblood per-row (every 8th row): mean rgb of drawn texels, mean alpha, texels with alpha>0, eff = mean(lum*alpha)")
    for r in range(0, H, 8):
        row = data[18 + r * W * 4: 18 + (r + 1) * W * 4]
        px = [row[i * 4:(i + 1) * 4] for i in range(W)]
        drawn = [q for q in px if q[3] > 0]
        rgb = ("%3d/%3d/%3d" % (sum(q[2] for q in drawn) / len(drawn), sum(q[1] for q in drawn) / len(drawn),
                                sum(q[0] for q in drawn) / len(drawn))) if drawn else "  -/  -/  -"
        al = sum(q[3] for q in px) / W / 255
        eff = sum((q[0] + q[1] + q[2]) / 3 * q[3] / 255 for q in px) / W
        print("  row %3d t=%.3f  rgb(drawn) %s  alpha %.2f  drawn %3d/256  eff %5.1f"
              % (r, t_of_row(r), rgb, al, len(drawn), eff))
    top = data[18: 18 + W * 4]
    bot = data[18 + (H - 1) * W * 4: 18 + H * W * 4]
    assert max(top[i * 4 + 3] for i in range(W)) == 0, "sea-edge row must be transparent"
    assert max(max(top[i * 4:i * 4 + 3]) for i in range(W)) == 0, "sea-edge row must be black"
    assert max(bot[i * 4 + 3] for i in range(W)) == 0, "land-edge row must be transparent"
    # tiles along S: the field and o(s) are periodic, so column 0 and column 255 must be neighbours
    seam = 0.0
    for r in range(H):
        a0 = data[18 + r * W * 4 + 3]
        a1 = data[18 + r * W * 4 + (W - 1) * 4 + 3]
        seam += abs(a0 - a1)
    print("S wrap seam (mean |alpha col0 - col255|): %.1f (0 = seamless; a neighbour-step is ~%.1f)"
          % (seam / H, 255.0 / 40))
    cov = sum(1 for i in range(W * H) if data[18 + i * 4 + 3] > 0) / float(W * H)
    print("coverage of the whole texture: %.1f%%; size %d bytes" % (100 * cov, len(data)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with the shipped file")
    args = ap.parse_args()
    data, cut = build()
    print("field cut for %.0f%% in-band coverage: %.3f" % (100 * TARGET_COVERAGE, cut))
    check(data)
    if args.check:
        old = open(OUT, "rb").read() if os.path.exists(OUT) else b""
        print("CHECK: %s" % ("identical" if old == data else "DIFFERS from the shipped file"))
        return 0 if old == data else 1
    with open(OUT, "wb") as fh:
        fh.write(data)
    print("wrote %s" % os.path.relpath(OUT, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
