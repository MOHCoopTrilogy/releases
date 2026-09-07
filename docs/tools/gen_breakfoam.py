# -*- coding: utf-8 -*-
"""GENERATOR for textures/coop_fx/breakfoam.tga - the break line of a SPILLING shorebreak on Omaha.

[user 2026-09-06/07, bug-2519] REWRITTEN from a resample into a procedural bake. The old version read
the foam band back out of wetsand_foam.tga and moved it to T 0.55-0.72 of the waterline sheet. It was a
straight ruled band, 256 columns wide, tiling 62 times along the beach - one of the stripes the user
photographed from above and described as "a lot of perfect symmetry ... it all looks like a straight
line". Nothing about a resample could fix that: the source had no along-shore structure to move.

WHAT A SPILLING BREAK ACTUALLY LOOKS LIKE, and what each term here is for.

  Omaha on 6 June 1944 is a dissipative sand terrace at about 1:34 in the drawn surf zone, under a
  Force 4-5 WNW wind with Hs around 0.9-1.1 m and Tp 5.5-6.3 s. The Iribarren number puts that firmly
  in the SPILLING regime: foam is born at the crest and trails landward for two to three seconds, so
  the idiom is a sharp seaward face and a fading trail, never a plunging lip.

  * `wob(s)` - the break line is not straight. Real surf scallops on beach cusps, and the runup
    maximum varies wave to wave by a large fraction of its own length. Harmonics n = 14..25 under an
    n^-1.2 law give 16 scallops over the 15872 u beach, i.e. one about every 25 m, which is inside the
    observed cusp band. The amplitude is +/-0.075 T = +/-106 u = +/-2.7 m of cross-shore wander.
    DO NOT extend this to higher n: adding n = 26..62 under the same law pushes n_rms from ~18 to
    ~24.6 and destroys the cell count, and roughening thickness at that scale adds no zero crossings.

  * `rough(s)` - a separate, much finer band at n = 40..130 (lambda 122..397 u = 3.1..10.1 m) which
    modulates the band's THICKNESS by +/-15% and its BRIGHTNESS by +/-10%. This is the texture within
    a single break, not the shape of the break.

  * `gate(s)` - some stretches of a real beach break hard and some barely break at all, so the beach
    has places. Deliberately mild here (0.80..1.00) because zz_coop_shoreline.shader stage 2 also
    carries the coarser along-shore cell mask on its second bundle (bug-2518); the two multiply, and
    two aggressive gates would switch the surf off.

  * `age(s)` / `L1(s)` - whitecap foam decays over a measured 1.4-4.8 s. The trail length varies along
    the beach so neighbouring patches persist differently, which is most of what stops a foam band
    reading as a printed stripe.

  * The COLOUR ages. Fresh crest foam under solid overcast is near-neutral and faintly cool, not
    brilliant white; a sand-laden shorebreak warms toward khaki as it ages and carries sediment. So
    desaturate first, and warm only the tail.

THE HARD CLIP AT T 0.80 IS NOT NEGOTIABLE. The sheet carries `deformVertexes flap`, and past a certain
T it passes UNDER the sand strip on the flap trough - foam baked past that point would appear and
vanish along the whole 403 m at once, every cycle, which is worse than the artefact it was drawing.
With the flap now halved to `0 2 0 .08 0 2` (bug-2514) the crossing sits near T 0.90, and stage 2's own
`tcMod wavetrant` surges the band a further +/-0.06 at runtime, so 0.80 + 0.06 = 0.86 clears it. Use
`--conservative` (clip 0.75) if the flap is ever restored to 4/4.

GEOMETRY. The waterline sheet's raw T is 0 at y -2167 (seaward) and 1 at y -759 (landward), 1408 u per
1.0 T. The band centre `Tc = 0.58` is y -1350. The surviving trail is 0.80 - (0.58 + 0.075) = 0.145 T
= 204 u = about 2.3 s at the bore speed, inside the whitecap-decay window.

TGA: 18-byte header (a 13-byte one shipped once and cost a session), type 2, 32 bpp, desc 0x08, raw
BGRA, no footer. The engine's LoadTGA puts the file's FIRST row at t = 1, so row 0 is the LANDWARD edge
and row H-1 the seaward one. Both are forced fully transparent.

SHADER PAIRING: this texture is now 2048 wide and spans the whole beach ONCE, so stage 2 must read
`tcMod scale 1 1`, not the old `scale 62 1`. That also puts it in phase with the cell mask on its
second bundle, which is authored in the same raw texcoords.

  python docs/tools/gen_breakfoam.py                write the texture
  python docs/tools/gen_breakfoam.py --flat         wob/gate/wid/age constant: the old straight band
  python docs/tools/gen_breakfoam.py --conservative clip at T 0.75 instead of 0.80
  python docs/tools/gen_breakfoam.py --check        re-read what is on disk and re-run every assert
"""
import struct, sys, math

OUT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx\breakfoam.tga"
W, H = 2048, 512
BEACH_LEN = 15872.0              # world u of shoreline that s 0..1 covers
T_PER_U = 1408.0                 # world u per 1.0 of the sheet's T

TC = 0.58                        # band centre in sheet T
CUSP_AMP = 0.075                 # scallop half-amplitude in T  (band 0.05..0.09)
WID_BASE = 0.028                 # Gaussian half-width of the seaward breaking face, in T (~39 u)
GATE_LO, GATE_HI = 0.80, 1.00    # along-shore strength, deliberately mild (the cell mask does the rest)
TRAIL_CLIP = 0.80                # hard clip; --conservative uses 0.75
TRAIL_CUT = 0.22                 # smoothstep window that ends the trail, in T
FRESH_WIN = 0.30                 # how far behind the face foam still counts as fresh, in T
ALPHA_PEAK = 0.28                # 72/255; 0.46 is the ceiling before this layer blooms
FRESH = (198, 200, 199)          # neutral, faintly cool
AGED = (166, 158, 144)           # mildly warm khaki

WOB_N = (14, 25); WOB_P = 1.2    # the scallops
ROUGH_N = (40, 130); ROUGH_P = 1.2   # thickness/brightness texture, 3.1..10.1 m
GATE_N = (5, 13); GATE_P = 1.0   # which stretches break hard
AGE_N = (7, 17); AGE_P = 1.0     # how long each patch persists

FLAT = "--flat" in sys.argv
if "--conservative" in sys.argv:
    TRAIL_CLIP = 0.75


def _ph(n):
    """Deterministic, machine-independent phases: an irrational multiplier, not a PRNG."""
    return (n * 2.399963229728653) % (2.0 * math.pi)


def _series(nlo, nhi, p):
    b = {n: n ** (-p) for n in range(nlo, nhi + 1)}

    def f(s):
        return sum(b[n] * math.cos(2.0 * math.pi * n * s + _ph(n)) for n in b)
    # normalise against the true extrema, sampled at 64x the highest harmonic
    m = nhi * 64
    vs = [f(i / float(m)) for i in range(m)]
    lo, hi = min(vs), max(vs)
    return f, lo, hi


_wob_f, _wob_lo, _wob_hi = _series(*WOB_N, WOB_P)
_rgh_f, _rgh_lo, _rgh_hi = _series(*ROUGH_N, ROUGH_P)
_gat_f, _gat_lo, _gat_hi = _series(*GATE_N, GATE_P)
_age_f, _age_lo, _age_hi = _series(*AGE_N, AGE_P)


def _sym(f, lo, hi, s):
    """-1..1"""
    return 2.0 * (f(s) - lo) / (hi - lo) - 1.0


def _unit(f, lo, hi, s):
    """0..1"""
    return (f(s) - lo) / (hi - lo)


def wob(s):
    return 0.0 if FLAT else CUSP_AMP * _sym(_wob_f, _wob_lo, _wob_hi, s)


def rough(s):
    return 0.0 if FLAT else _sym(_rgh_f, _rgh_lo, _rgh_hi, s)


def gate(s):
    if FLAT:
        return GATE_HI
    g = GATE_LO + (GATE_HI - GATE_LO) * _unit(_gat_f, _gat_lo, _gat_hi, s)
    return max(0.0, min(1.0, g * (1.0 + 0.10 * rough(s))))


def wid(s):
    return WID_BASE if FLAT else WID_BASE * (1.0 + 0.15 * rough(s))


def age(s):
    return 1.0 if FLAT else 0.7 + 0.6 * _unit(_age_f, _age_lo, _age_hi, s)


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def t_of_row(r):
    return (H - 1 - r + 0.5) / H


def profile(s, t):
    """Returns (alpha 0..1 before normalisation, freshness 0..1)."""
    if t > TRAIL_CLIP:
        return 0.0, 0.0
    u = t - (TC + wob(s))
    g = gate(s)
    if u <= 0.0:
        a = g * math.exp(-(u / wid(s)) ** 2)          # the breaking face, sharp
    else:
        l1 = 0.18 * age(s)
        a = g * math.exp(-u / l1) * (1.0 - smoothstep(u / TRAIL_CUT))   # the spilling trail
    fresh = max(0.0, min(1.0, 1.0 - max(u, 0.0) / FRESH_WIN))
    return a, fresh


def build():
    raw = [[0.0] * W for _ in range(H)]
    frs = [[0.0] * W for _ in range(H)]
    peak = 0.0
    for r in range(H):
        t = t_of_row(r)
        if r == 0 or r == H - 1:
            continue
        for c in range(W):
            s = c / float(W)
            a, f = profile(s, t)
            raw[r][c] = a
            frs[r][c] = f
            if a > peak:
                peak = a
    k = (ALPHA_PEAK / peak) if peak > 0 else 0.0
    px = bytearray(W * H * 4)
    for r in range(H):
        for c in range(W):
            a = raw[r][c] * k
            f = frs[r][c]
            rr = AGED[0] + (FRESH[0] - AGED[0]) * f
            gg = AGED[1] + (FRESH[1] - AGED[1]) * f
            bb = AGED[2] + (FRESH[2] - AGED[2]) * f
            o = (r * W + c) * 4
            if a <= 0.0:
                continue                       # already zero: black and transparent
            px[o + 0] = int(round(bb))
            px[o + 1] = int(round(gg))
            px[o + 2] = int(round(rr))
            px[o + 3] = int(round(255.0 * min(1.0, a)))
    return bytes(px)


def header():
    hdr = bytes([0, 0, 2]) + struct.pack("<HHB", 0, 0, 0) + struct.pack("<HHHHBB", 0, 0, W, H, 32, 8)
    assert len(hdr) == 18, "TGA header must be 18 bytes"
    return hdr


def checks(px):
    assert len(px) == W * H * 4, "short pixel block"

    def row(r):
        return px[r * W * 4:(r + 1) * W * 4]

    top, bot = row(0), row(H - 1)
    assert max(top[i * 4 + 3] for i in range(W)) == 0 and max(top[i * 4 + k] for i in range(W) for k in range(3)) == 0, \
        "landward (t=1) row must be black and transparent"
    assert max(bot[i * 4 + 3] for i in range(W)) == 0 and max(bot[i * 4 + k] for i in range(W) for k in range(3)) == 0, \
        "seaward (t=0) row must be black and transparent"

    peak_eff = 0.0; peak_row = 0; first_a = last_a = None; peak_prod = 0.0
    for r in range(H):
        q = row(r)
        lum = sum((q[i * 4] + q[i * 4 + 1] + q[i * 4 + 2]) / 3.0 for i in range(W)) / W
        al = sum(q[i * 4 + 3] for i in range(W)) / float(W) / 255.0
        amax = max(q[i * 4 + 3] for i in range(W))
        eff = lum * al
        if eff > peak_eff:
            peak_eff, peak_row = eff, r
        for i in range(0, W, 7):
            p = max(q[i * 4], q[i * 4 + 1], q[i * 4 + 2]) / 255.0 * (q[i * 4 + 3] / 255.0)
            if p > peak_prod:
                peak_prod = p
        if amax > 0:
            if first_a is None:
                first_a = r
            last_a = r
    assert first_a is not None, "the band is empty"
    print("  alpha > 0 on rows %d..%d = T %.3f..%.3f" % (first_a, last_a, t_of_row(last_a), t_of_row(first_a)))
    print("  peak eff %.1f/255 at row %d (T %.3f);  peak RGB*alpha %.4f" % (peak_eff, peak_row, t_of_row(peak_row), peak_prod))
    assert t_of_row(first_a) <= TRAIL_CLIP + 1e-6, \
        "band reaches T %.3f, past the submerge clip %.2f" % (t_of_row(first_a), TRAIL_CLIP)
    assert peak_eff > 20.0, "band is black"
    assert peak_prod <= 0.22 + 1e-6, "peak RGB*alpha %.4f over the 0.22 bloom budget" % peak_prod

    if FLAT:
        print("  --flat: wob/gate/wid/age constant, i.e. the old straight band")
        return
    ws = [wob(c / float(W)) for c in range(W)]
    assert max(abs(v) for v in ws) <= 0.09 + 1e-9, "max |wob| %.4f over 0.09" % max(abs(v) for v in ws)
    m = sum(ws) / len(ws)
    cr = sum(1 for i in range(1, len(ws)) if (ws[i - 1] - m) * (ws[i] - m) < 0)
    cells = cr // 2
    sp = BEACH_LEN / max(cells, 1)
    print("  scallops %d, mean spacing %.0f u = %.1f m, wander +/-%.0f u = +/-%.1f m"
          % (cells, sp, sp * 0.0254, max(abs(v) for v in ws) * T_PER_U, max(abs(v) for v in ws) * T_PER_U * 0.0254))
    assert 14 <= cells <= 32, "%d scallops, want 14..32" % cells
    assert 15.0 <= sp * 0.0254 <= 32.0, "mean spacing %.1f m, want 15..32" % (sp * 0.0254)


def main():
    if "--check" in sys.argv:
        fd = open(OUT, "rb").read()
        assert len(fd) == 18 + W * H * 4, "size %d" % len(fd)
        checks(fd[18:])
        print("CHECK: breakfoam.tga on disk passes every assert")
        return
    px = build()
    checks(px)
    open(OUT, "wb").write(header() + px)
    print("wrote %s  %d x %d  %d bytes" % (OUT, W, H, 18 + len(px)))


if __name__ == "__main__":
    main()
