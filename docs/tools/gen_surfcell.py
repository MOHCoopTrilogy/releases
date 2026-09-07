# -*- coding: utf-8 -*-
"""gen_surfcell.py - the along-shore CELL MASK for Omaha's surf.

WHY THIS EXISTS. Every effect on m3l1a's beach is driven by tCoord, i.e. by distance from the shore,
and tCoord cannot vary along the beach. The result is that the foam, the wash, the wet line and the
crest are all perfectly straight bands running the full 15872 world units of shoreline - the user's
"a lot of perfect symmetry ... it all looks like a straight line". Real surf is not like that: wave
height varies along a crest, some stretches break hard and some barely break, and the whitewater has
places it is reliably loud and places it is reliably quiet.

The only channel on this engine that can carry along-shore variation is a TEXTURE, and the only way
to apply one to an existing stage without spending a stage is a second texture bundle. Both renderers
multiply a second bundle's ALPHA into the stage alpha unconditionally:
  gl2  code/renderergl2/glsl/generic_fp.glsl  ->  `alpha *= color2.a;` whenever u_Texture1Env != 0
  gl1  code/renderergl1/tr_shade.c            ->  GL_TexEnv(pStage->multitextureEnv), default
                                                  GL_MODULATE, which multiplies RGB *and* alpha
So a texture whose RGB is 255 everywhere and whose ALPHA carries the pattern is a pure gate: RGB is
multiplied by 1 and left alone, alpha is modulated. It costs one texture fetch and no stage.

  NEVER write `nextbundle add` for these masks. Under ADD the second bundle's RGB is ADDED
  (generic_fp.glsl and GL_COMBINE_RGB GL_ADD), so an all-white mask would blow the stage to white.
  A bare `nextbundle` is what you want.

WHAT IT ENCODES, and what it honestly does not.

  1. A BROAD FIELD, harmonics n = 3..40 with amplitude ~1/n, normalised to 0.72..1.00. This is the
     part that kills periodicity everywhere rather than at a handful of places, and it is the better
     answer to "perfect symmetry" than holes are. At the map's 15872 u shoreline, n = 3..40 is a
     wavelength band of 5290 u down to 397 u, i.e. 134 m to 10 m.

  2. FIVE EMBAYMENTS where the whitewater drops to 30%. Their spacing (2950/3570/3180/3580 u, mean
     3320 u = 84 m) is 2.9-3.5x the geometric surf-zone width, inside the 1.5-4x band that real
     rhythmic shoreline morphology occupies, and their widths (620-1100 u = 16-28 m) match observed
     15-30 m. The cosine shoulders run over 60% of each half-width so the gaps survive two or three
     mip levels rather than dissolving at range.

     BE HONEST IN THE SHADER HEADER: rip currents at Omaha on 6 June are UNATTESTED. The official
     history describes a smooth, gentle tidal flat, and channel rips need bar-and-channel morphology,
     which a dissipative terrace is the least likely regime to carry. These are megacusp and
     runnel-drainage embayments - truer to the documented shore-parallel runnels the men waded, and a
     truer description of what this actually draws, which is an along-shore modulation of whitewater
     and not a jet.

  3. A CROSS-SHORE SHEAR of 0.015 (238 u across the sheet, 9.6 degrees) so that the outer break-line
     gap and the inner wash gap do not stack into a vertical no-surf stripe. NOT 0.045: that is a 27
     degree cant, six times the wave-band angle, and reads as diagonal corduroy fighting the crests.

THREE FILES ARE WRITTEN.
  surfcell.tga       the mask itself, for the shoreline sheet's foam and crest stages.
  surfcell_soft.tga  the same field with a raised floor, for the blood - blood is deposited on sand
                     and should not switch off with the surf, only vary with it.
  surfcell_m.tga     mirrored in s, and ramping to fully open by t ~ 0.40, for the open sea. The sea
                     patch's raw t is 0 at the seam and 1 at y -8000, so the necks stop reaching at
                     y ~ -4500, about 1.7 surf-zone widths offshore. Without that decay the lanes hold
                     full strength for 148 m and simply become new wallpaper on a new surface.

USAGE
  python docs/tools/gen_surfcell.py            write the three masks
  python docs/tools/gen_surfcell.py --flat     write alpha 255 everywhere: a no-op multiply, i.e. the
                                               kill switch, with no shader edit and no vid_restart
  python docs/tools/gen_surfcell.py --check    re-read what is on disk and re-run every assert

The mod tree gitignores *.tga, so these ship from the working copy and are reproducible from here.
"""
import sys, os, math, struct

OUTDIR = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx"
W, H = 2048, 256                 # s across the beach, t across the surf zone
BEACH_X0, BEACH_X1 = -7872.0, 8000.0
BEACH_LEN = BEACH_X1 - BEACH_X0  # 15872 u

PSI = 0.015                      # cross-shore shear, in units of s per unit of t
FIELD_LO, FIELD_HI = 0.72, 1.00  # the broad field's range
GAP_DEPTH = 0.30                 # embayment floor as a fraction
FLOOR = 0.20                     # nothing is ever fully closed
SOFT_FLOOR = 0.55                # the blood mask's floor
SEA_OPEN_T = 0.40                # the mirrored mask is fully open by this t

# five embayments: world x centre, full width in world units
EMBAYMENTS = [(-6400.0, 700.0), (-3450.0, 1100.0), (120.0, 620.0), (3300.0, 950.0), (6880.0, 780.0)]
SHOULDER = 0.60                  # cosine shoulder as a fraction of each half-width

N_LO, N_HI = 3, 40               # broad-field harmonics
# SPECTRAL TILT. The design called for amplitudes proportional to 1/n over n = 3..40 AND for 14-32
# cells along the beach at a 15-32 m spacing. Measured, those two are inconsistent by a factor of
# five: with a 1/n law this sum crosses its own mean only 3 times over the whole 15872 u, i.e. cells
# 134 m across. The cell count is the requirement that is tied to the physical target, so it is the
# one kept. Solved over the same harmonic range - deliberately NOT extended, since more harmonics
# buy resolution the mask does not need and cost mip robustness - the exponent that lands in the
# middle of the band is 0.20: 17 cells, 934 u = 23.7 m, against the design's own "cells about 22 m
# across". Raise it toward 0.5 for fewer, larger, smoother cells; lower it toward 0.1 for more.
EXP = 0.20


def phases(n_lo, n_hi):
    """Fixed, reproducible phases. A hash of the harmonic number, not a PRNG, so the file is
    bit-identical on every machine and every Python version."""
    out = {}
    for n in range(n_lo, n_hi + 1):
        # an irrational multiplier gives a well-spread, deterministic sequence in [0, 2pi)
        out[n] = (n * 2.399963229728653) % (2.0 * math.pi)
    return out


PH = phases(N_LO, N_HI)


def broad(s):
    """Sum of 1/n harmonics over s in [0,1), then normalised by the caller."""
    v = 0.0
    for n in range(N_LO, N_HI + 1):
        v += math.cos(2.0 * math.pi * n * s + PH[n]) * (n ** (-EXP))
    return v


# Normalise the broad field to FIELD_LO..FIELD_HI using its true extrema, sampled densely enough that
# the peak cannot be missed: the highest harmonic is n = 40, so 64 samples per cycle at n = 40.
_SAMP = N_HI * 64
_vals = [broad(i / float(_SAMP)) for i in range(_SAMP)]
_BMIN, _BMAX = min(_vals), max(_vals)


def field(s):
    x = (broad(s) - _BMIN) / (_BMAX - _BMIN)          # 0..1
    return FIELD_LO + (FIELD_HI - FIELD_LO) * x


def embayment(s):
    """1.0 outside the gaps, GAP_DEPTH at each centre, cosine shoulders."""
    x = BEACH_X0 + s * BEACH_LEN
    g = 1.0
    for cx, wid in EMBAYMENTS:
        half = wid * 0.5
        d = abs(x - cx)
        if d >= half:
            continue
        flat = half * (1.0 - SHOULDER)
        if d <= flat:
            k = 1.0
        else:
            u = (d - flat) / (half - flat)            # 0 at the flat edge, 1 at the outer edge
            k = 0.5 * (1.0 + math.cos(math.pi * (1.0 - u)))
            k = 1.0 - k
        g = min(g, 1.0 - (1.0 - GAP_DEPTH) * k)
    return g


def amp(s, t):
    """The mask value at (s, t), sheared so the inner and outer gaps do not stack."""
    ss = (s + PSI * t) % 1.0
    return max(FLOOR, min(1.0, field(ss) * embayment(ss)))


def tga(pixels_bgra):
    """18-byte uncompressed 32-bit TGA. The 13-byte-header bug (bug-2485) cost a session once: the
    colour-map specification is five bytes and is mandatory even when there is no colour map."""
    hdr = struct.pack("<BBBHHBHHHHBB",
                      0,        # id length
                      0,        # colour map type
                      2,        # uncompressed true-colour
                      0, 0, 0,  # colour map spec: origin, length, entry size
                      0, 0,     # x, y origin
                      W, H,     # width, height
                      32,       # bits per pixel
                      8)        # 8 alpha bits, origin bottom-left
    assert len(hdr) == 18, "TGA header must be 18 bytes, got %d" % len(hdr)
    return hdr + pixels_bgra


def build(flat=False):
    """Returns (main, soft, mirrored) as BGRA byte strings."""
    main = bytearray(W * H * 4)
    soft = bytearray(W * H * 4)
    mirr = bytearray(W * H * 4)
    for r in range(H):
        t = r / float(H - 1)
        # the sea mask opens up as it goes offshore
        open_k = 1.0 if t >= SEA_OPEN_T else (t / SEA_OPEN_T)
        for c in range(W):
            s = c / float(W)
            if flat:
                a = 1.0
                a_soft = 1.0
                a_m = 1.0
            else:
                a = amp(s, t)
                a_soft = SOFT_FLOOR + (1.0 - SOFT_FLOOR) * ((a - FLOOR) / (1.0 - FLOOR))
                a_m = amp((1.0 - s) % 1.0, t)
                a_m = a_m + (1.0 - a_m) * open_k
            i = (r * W + c) * 4
            for buf, v in ((main, a), (soft, a_soft), (mirr, a_m)):
                buf[i + 0] = 255      # B
                buf[i + 1] = 255      # G
                buf[i + 2] = 255      # R  - white, so a MODULATE second bundle leaves colour alone
                buf[i + 3] = int(round(255.0 * max(0.0, min(1.0, v))))
    return bytes(main), bytes(soft), bytes(mirr)


def checks(main, soft, mirr, flat):
    """Every guard that would have caught a real defect in this project's history."""
    def alphas(buf):
        return [buf[i * 4 + 3] for i in range(W * H)]

    def row_alphas(buf, r):
        return [buf[(r * W + c) * 4 + 3] for c in range(W)]

    def rgb_is_white(buf):
        return all(buf[i * 4 + k] == 255 for i in range(0, W * H, 97) for k in range(3))

    for name, buf in (("surfcell", main), ("surfcell_soft", soft), ("surfcell_m", mirr)):
        assert len(buf) == W * H * 4, "%s: short pixel block" % name
        assert rgb_is_white(buf), "%s: RGB must be 255 everywhere or a MODULATE bundle tints the stage" % name

    if flat:
        for name, buf in (("surfcell", main), ("surfcell_soft", soft), ("surfcell_m", mirr)):
            assert min(alphas(buf)) == 255, "%s: --flat must be a no-op multiply" % name
        print("  --flat: all three masks are alpha 255 (a no-op multiply)")
        return

    a_main = alphas(main)
    lo, hi = min(a_main), max(a_main)
    assert lo >= int(255 * FLOOR) - 1, "surfcell: floor breached, %d" % lo
    assert hi >= 250, "surfcell: never fully open, max %d" % hi

    mid = row_alphas(main, H // 2)
    # CELL COUNT is a property of the BROAD FIELD, and must be measured on it alone. Measuring it on
    # the composite row instead gives 5 rather than 17, and the reason is worth keeping: the field
    # spans 0.72..1.00 while the five embayments dip to 0.216, which drags the composite's mean to
    # 0.672 - below the field's own minimum. Outside the gaps the signal then never crosses its mean,
    # so the count degenerates into "how many embayments are there". The gaps are asserted separately
    # below; this is the texture of the surf.
    fs = [field(c / float(W)) for c in range(W)]
    mf = sum(fs) / float(len(fs))
    crossings = sum(1 for i in range(1, len(fs)) if (fs[i - 1] - mf) * (fs[i] - mf) < 0)
    cells = crossings // 2
    assert 14 <= cells <= 32, "surfcell: %d cells along the beach, want 14..32" % cells
    spacing_u = BEACH_LEN / max(cells, 1)
    spacing_m = spacing_u * 0.0254
    assert 15.0 <= spacing_m <= 32.0, "surfcell: mean cell spacing %.1f m, want 15..32" % spacing_m

    # the five gaps must actually be gaps at the mid row
    for cx, wid in EMBAYMENTS:
        s_c = (cx - BEACH_X0) / BEACH_LEN
        col = int(round(((s_c - PSI * 0.5) % 1.0) * W)) % W
        assert mid[col] <= int(255 * (GAP_DEPTH + 0.22)), \
            "surfcell: gap at x %.0f is not a gap (alpha %d)" % (cx, mid[col])

    # the soft mask must never close as hard as the main one
    a_soft = alphas(soft)
    assert min(a_soft) >= int(255 * SOFT_FLOOR) - 1, "surfcell_soft: floor breached"

    # the mirrored mask must be fully open by SEA_OPEN_T and modulated near the seam
    r_open = int(round(SEA_OPEN_T * (H - 1)))
    assert min(row_alphas(mirr, r_open)) >= 254, "surfcell_m: not open by t %.2f" % SEA_OPEN_T
    assert min(row_alphas(mirr, 0)) < 250, "surfcell_m: not modulated at the seam"

    print("  cells %d, mean spacing %.0f u = %.1f m, alpha %d..%d" % (cells, spacing_u, spacing_m, lo, hi))
    print("  five embayments verified at the mid row; soft floor %d; sea mask open by t %.2f"
          % (min(a_soft), SEA_OPEN_T))


def main_():
    flat = "--flat" in sys.argv
    if "--check" in sys.argv:
        bufs = []
        for nm in ("surfcell.tga", "surfcell_soft.tga", "surfcell_m.tga"):
            p = os.path.join(OUTDIR, nm)
            raw = open(p, "rb").read()
            assert len(raw) == 18 + W * H * 4, "%s: size %d" % (nm, len(raw))
            bufs.append(raw[18:])
        checks(bufs[0], bufs[1], bufs[2], flat)
        print("CHECK: the three masks on disk pass every assert")
        return

    main, soft, mirr = build(flat)
    checks(main, soft, mirr, flat)
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    for nm, buf in (("surfcell.tga", main), ("surfcell_soft.tga", soft), ("surfcell_m.tga", mirr)):
        p = os.path.join(OUTDIR, nm)
        data = tga(buf)
        open(p, "wb").write(data)
        print("wrote %s  %d x %d  %d bytes" % (p, W, H, len(data)))


if __name__ == "__main__":
    main_()
