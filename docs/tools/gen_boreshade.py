# -*- coding: utf-8 -*-
"""gen_boreshade.py - the TROUGH SHADOW that makes Omaha's surf read as three-dimensional.

[user 2026-09-07, bug-2525] "So is there no way to make the waves actually more 3d?"

THE ANSWER, AND WHY THIS IS THE ONLY MECHANISM. The waves in the surf zone are already real geometry -
models/fx/coop_surf.tik deforms actual vertices. They do not LOOK three-dimensional because nothing on
this beach is shaded, and that cannot be fixed:

  * every water shader is surfaceparm nolightmap with identity / identityLighting / wave stages;
  * m3l1a's worldspawn sundirection is "270 360 0", i.e. the light is at the EXACT ZENITH (confirmed
    live: "sun bridge: dir 0.000 0.000 1.000"), so a crest and a trough receive identical light and
    Lambert relief is structurally impossible even with a lighting stage;
  * deformVertexes writes tess.xyz and NEVER tess.normal (tr_shade_calc.c:136-151,
    generic_vp.glsl:139), and every vertex this generator's sibling bakes carries (0,0,n), so
    alphaGen dot, alphaGen lightingSpecular and tcGen environment all read a stale, identical,
    straight-up normal. They draw a distance vignette, not a wave.

So orientation can never drive brightness here. What CAN is this: the wave's shape is a deterministic
function of position and time, so the light and dark it WOULD have is equally deterministic, and can be
painted and moved with it. As of bug-2524 the painted crest and the geometric bore run at the same
speed and the same spacing, which is what makes that alignment hold instead of drifting.

The surf layer already carries the BRIGHT half - breakfoam.tga on every crest. This is the dark half.
A highlight with no shadow is a stripe; a highlight WITH a shadow is a form, and that pairing is the
whole of what human vision needs to read a rounded surface. It is fake, and it is the only shading
this engine will ever put on this water.

WHAT IT WRITES. textures/coop_fx/boreshade.tga, 2048 x 512 RGBA:
  * ALPHA is a smooth hump sitting HALF A PERIOD from breakfoam's own bright band. That band peaks at
    its texture t 0.577 (measured, not assumed), so this peaks at 0.077. Both stages tile at the same
    2.4238 and scroll at the same -0.2000, so the two stay exactly antiphase for ever.
  * RGB is a dark, slightly cool grey. It is drawn through blendFunc blend, so the stage pulls the
    water toward this colour in proportion to alpha - a shadow, not a smear.
  * Alpha peaks at SHADOW_PEAK. Keep it modest: the eye reads the crest-to-trough DIFFERENCE, and the
    foam is already adding on the other half of the cycle, so the two together are worth about twice
    what either is alone.
  * Rows 0 and H-1 are forced to alpha 0 so the tile wraps with no seam.

  python docs/tools/gen_boreshade.py            write it
  python docs/tools/gen_boreshade.py --check    re-read and re-run every assert
  python docs/tools/gen_boreshade.py --flat     alpha 0 everywhere: the kill switch, no shader edit
"""
import os
import sys
import math
import struct

OUT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx\boreshade.tga"
W, H = 2048, 512

FOAM_PEAK_T = 0.577          # measured off breakfoam.tga, not assumed
SHADOW_PEAK_T = (FOAM_PEAK_T + 0.5) % 1.0        # exactly antiphase = 0.077
SHADOW_WIDTH = 0.20          # half-width of the hump in t, i.e. the trough quarter of the period
SHADOW_PEAK = 0.34           # peak alpha
SHADE_RGB = (44, 56, 64)     # a dark, slightly cool grey - the colour a trough takes under overcast

# a mild along-shore modulation so the shadow is not a ruled line either; the same three-harmonic
# shape gen_coop_surf.py uses for its amplitude envelope, at a fraction of the depth
ENV_LO, ENV_HI = 0.72, 1.00

FLAT = "--flat" in sys.argv


def _ph(n):
    return (n * 2.399963229728653) % (2.0 * math.pi)


def _env_raw(s):
    return (0.60 * math.sin(2.0 * math.pi * s * 3.05 + _ph(3))
            + 0.28 * math.sin(2.0 * math.pi * s * 8.35 + _ph(7))
            + 0.12 * math.sin(2.0 * math.pi * s * 20.3 + _ph(13)))


_E = [_env_raw(i / 2048.0) for i in range(2049)]
_ELO, _EHI = min(_E), max(_E)


def env(s):
    return ENV_LO + (ENV_HI - ENV_LO) * ((_env_raw(s) - _ELO) / (_EHI - _ELO))


def hump(t):
    """Wrapped cosine hump centred on SHADOW_PEAK_T. Wrapped, because the tile must be seamless."""
    d = abs(((t - SHADOW_PEAK_T + 0.5) % 1.0) - 0.5)      # shortest distance on the ring
    if d >= SHADOW_WIDTH:
        return 0.0
    x = d / SHADOW_WIDTH
    return 0.5 * (1.0 + math.cos(math.pi * x))            # 1 at the centre, 0 at the edge, smooth


def t_of_row(r):
    return (H - 1 - r + 0.5) / H


def build():
    px = bytearray(W * H * 4)
    peak = 0.0
    for r in range(H):
        t = t_of_row(r)
        base = 0.0 if (FLAT or r == 0 or r == H - 1) else hump(t) * SHADOW_PEAK
        for c in range(W):
            a = base * (1.0 if FLAT else env(c / float(W)))
            if a <= 0.0:
                continue
            peak = max(peak, a)
            o = (r * W + c) * 4
            px[o + 0] = SHADE_RGB[2]      # B
            px[o + 1] = SHADE_RGB[1]      # G
            px[o + 2] = SHADE_RGB[0]      # R
            px[o + 3] = int(round(255.0 * min(1.0, a)))
    return bytes(px), peak


def header():
    h = bytes([0, 0, 2]) + struct.pack("<HHB", 0, 0, 0) + struct.pack("<HHHHBB", 0, 0, W, H, 32, 8)
    assert len(h) == 18, "TGA header must be 18 bytes"
    return h


def checks(px, peak):
    assert len(px) == W * H * 4, "short pixel block"

    def row(r):
        return px[r * W * 4:(r + 1) * W * 4]

    for r in (0, H - 1):
        q = row(r)
        assert max(q[i * 4 + 3] for i in range(W)) == 0, "row %d must be alpha 0 so the tile wraps" % r
    if FLAT:
        assert peak == 0.0
        print("  --flat: alpha 0 everywhere, a no-op blend")
        return
    # the hump must sit antiphase to the foam
    best_r, best_a = 0, -1
    for r in range(H):
        q = row(r)
        a = sum(q[i * 4 + 3] for i in range(0, W, 7)) / float(W // 7)
        if a > best_a:
            best_r, best_a = r, a
    tp = t_of_row(best_r)
    d = abs(((tp - FOAM_PEAK_T + 0.5) % 1.0) - 0.5)
    assert d > 0.40, "shadow peak t %.3f is only %.3f from the foam's %.3f - they must be antiphase" % (tp, d, FOAM_PEAK_T)
    assert 0.20 <= peak <= 0.50, "peak alpha %.3f outside the sane band" % peak
    # nothing may be darker than the shadow colour itself
    mx = max(max(row(r)[i * 4 + k] for i in range(0, W, 31) for k in range(3)) for r in range(0, H, 7))
    assert mx <= max(SHADE_RGB), "RGB above the shadow colour"
    print("  shadow peak at t %.3f, %.3f from the foam peak at %.3f (antiphase)" % (tp, d, FOAM_PEAK_T))
    print("  peak alpha %.3f toward RGB %s; rows 0 and %d clear so the tile wraps" % (peak, SHADE_RGB, H - 1))


def main():
    if "--check" in sys.argv:
        fd = open(OUT, "rb").read()
        assert len(fd) == 18 + W * H * 4, "size %d" % len(fd)
        body = fd[18:]
        pk = max(body[i * 4 + 3] for i in range(W * H)) / 255.0
        checks(body, pk)
        print("CHECK: boreshade.tga on disk passes every assert")
        return
    px, peak = build()
    checks(px, peak)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(header() + px)
    print("wrote %s  %d x %d  %d bytes" % (OUT, W, H, 18 + len(px)))


if __name__ == "__main__":
    main()
