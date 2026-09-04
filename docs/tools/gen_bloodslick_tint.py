"""Retint textures/coop_fx/bloodslick.tga - the blood POOL sheet - to the same red as the surf wash.

WHY
---
2026-09-01: the user asked for the blood in Omaha's water to be redder. gen_bloodwash.py retinted
bloodslick's sibling, textures/coop_fx/bloodwash.tga (the shader stage on the shoreline water), from a
near-black 14/1/0 to a real 134/21/16. An adversarial audit then pointed out that only ONE of the two
blood assets had been touched, and measurement confirms it:

    bloodwash.tga   visible RGB 134 / 21 / 16   (retinted)
    bloodslick.tga  visible RGB   9 /  1 /  0   maxR 13   <- still essentially black

bloodslick is the more visible of the two. It is the plane spawned by coop_waterBlood (24 in the surf),
by every coop_beachGore cluster, and by every scripted death - flank cut-downs, the disembark slaughter,
the bangalore charge. Drawn with `rgbGen identity` (scripts/coop_bloodslick.shader), a 9/1/0 sheet does
not read as blood, it reads as a dark stain, which is exactly what the user has been describing.

WHAT IT DOES
------------
Keeps the ALPHA untouched - the blob shapes are authored and are not the problem - and drives RGB off
the alpha, so the thin feathered edge of a pool is bright arterial and the thick middle is dark and
venous. Flat red would read as paint.

THE PALETTE IS IMPORTED FROM gen_bloodwash.py, not copied. One place defines what blood looks like in
this mod; retune it there and both sheets follow. That is the whole reason this is a generator and not
a one-off edit.

DETERMINISTIC and idempotent-safe: it reads an authored SOURCE snapshot kept beside the tool, never its
own output, so re-running cannot compound the tint - the same footgun that destroyed 229 gore shader
blocks in bug-2229 and that gen_bloodwash.py guards against the same way.
"""

import io
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
TEX = os.path.join(MOD, "textures", "coop_fx", "bloodslick.tga")
SRC = os.path.join(HERE, "bloodslick_src.tga")

# --- the single source of truth for what blood looks like here
_gb = io.open(os.path.join(HERE, "gen_bloodwash.py"), encoding="utf-8").read()
_pal = _gb[_gb.index("RED_R_THIN"):]
_pal = _pal[:_pal.index("\n\n")]
exec(_pal, globals())          # RED_R_THIN/G/B, RED_R_THICK/G/B


def visible(im):
    r, g, b, a = [list(c.tobytes()) for c in im.split()]
    sel = [i for i, v in enumerate(a) if v > 25]
    n = max(1, len(sel))
    return (sum(r[i] for i in sel) / n, sum(g[i] for i in sel) / n,
            sum(b[i] for i in sel) / n, max([r[i] for i in sel] or [0]), len(sel), len(a))


def main():
    write = "--write" in sys.argv
    if not os.path.exists(TEX):
        print("missing %s" % TEX)
        return 1
    if not os.path.exists(SRC):
        Image.open(TEX).convert("RGBA").save(SRC)
        print("  snapshotted the authored source -> %s" % os.path.relpath(SRC, REPO))

    src = Image.open(SRC)
    src.load()
    src = src.convert("RGBA")
    w, h = src.size
    a = list(src.split()[3].tobytes())

    br = visible(src)
    print("  before: visible RGB %.0f/%.0f/%.0f  maxR %d  coverage %.1f%%"
          % (br[0], br[1], br[2], br[3], 100.0 * br[4] / br[5]))

    rr, gg, bb = bytearray(w * h), bytearray(w * h), bytearray(w * h)
    for i in range(w * h):
        v = a[i]
        if v == 0:
            continue                       # fully clear - RGB is never sampled there
        t = v / 255.0                      # 0 = the feathered edge, 1 = the deepest part of the pool
        rr[i] = int(round(RED_R_THIN + (RED_R_THICK - RED_R_THIN) * t))   # noqa: F821
        gg[i] = int(round(RED_G_THIN + (RED_G_THICK - RED_G_THIN) * t))   # noqa: F821
        bb[i] = int(round(RED_B_THIN + (RED_B_THICK - RED_B_THIN) * t))   # noqa: F821

    out = Image.merge("RGBA", (
        Image.frombytes("L", (w, h), bytes(rr)),
        Image.frombytes("L", (w, h), bytes(gg)),
        Image.frombytes("L", (w, h), bytes(bb)),
        src.split()[3],
    ))
    af = visible(out)
    print("  after : visible RGB %.0f/%.0f/%.0f  maxR %d  coverage %.1f%% (alpha untouched)"
          % (af[0], af[1], af[2], af[3], 100.0 * af[4] / af[5]))

    if write:
        out.save(TEX)
        print("\n  wrote %s" % os.path.relpath(TEX, REPO))
    else:
        print("\n  DRY RUN - pass --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
