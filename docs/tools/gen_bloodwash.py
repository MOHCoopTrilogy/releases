"""Regenerate textures/coop_fx/bloodwash.tga - the blood stage on Omaha's shoreline water.

WHY THIS TOOL EXISTS
--------------------
The first version of this texture (bug-2210) was pushed to FULL COVERAGE deliberately: the user could
not see any blood at all, so the fix was a wash with a lifted alpha floor - 100% of texels above alpha
25, minimum alpha 70, mean 134. That solved "I see no blood" and created two new problems the moment
the shader override actually started rendering (bug-2228):

  1. It was overwhelming. A sheet with no clear water in it reads as a red filter over the sea, not as
     blood in the water.
  2. It made the shader boundary obvious. The stage exists only on
     textures/misc_outside/deepbluesea_shoreline, which meets textures/misc_outside/deepbluesea at
     Y = -2160 - exactly where the Higgins run-in becomes the wading area. A uniform full-coverage
     tint that stops dead at that line draws the seam for you.

So the texture needs GAPS. Real clear water between real blood, so the eye reads discrete slicks. The
seam is handled separately, in the shader, by ramping the stage's alpha along T (T = 0.005 at the
seaward edge, 0.994 at the water's edge - measured from the BSP), so the blood fades to nothing at the
join and is strongest where the user asked for it: right at the edge of the water.

WHAT IT DOES
------------
Keeps the existing authored RGB - the colour was never the problem - and rebuilds only the ALPHA:

  * a seamless low-frequency field, built from a sum of sine products at INTEGER frequencies, so it
    tiles perfectly with no edge seam and needs no noise library;
  * multiplied by the original alpha, so the authored blob structure still drives where blood sits;
  * remapped through a threshold chosen to hit a target coverage, with a soft shoulder so slick edges
    stay feathered rather than cut out.

DETERMINISTIC: fixed seed, integer frequencies. Re-running reproduces the file byte for byte, and
--check verifies that without writing.
"""

import argparse
import math
import os
import sys

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
TEX = os.path.join(MOD, "textures", "coop_fx", "bloodwash.tga")
# The AUTHORED source, kept beside the tool rather than in the mod tree. This matters: the tool
# rebuilds alpha FROM the source, so if it read its own output every run would thin the texture
# further - the same compounding footgun as the gore generator (bug-2229). First run snapshots the
# current file here; every run after that reads the snapshot.
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bloodwash_src.tga")

# Fraction of texels that should carry any blood at all. The rest is clear water.
# 0.42 was picked by eye against the reference: enough that a slick reads at wading distance, sparse
# enough that you can see sea between the slicks.
TARGET_COVERAGE = 0.42

# (x frequency, y frequency, weight). Integer frequencies only - that is what makes it tileable.
# The low pair makes broad slicks; the higher pairs break their edges up so they do not read as blobs.
BANDS = [(1, 1, 1.00), (2, 1, 0.55), (1, 3, 0.45), (3, 2, 0.30), (5, 4, 0.18), (8, 7, 0.10)]
PHASE = [0.00, 1.31, 2.60, 0.77, 3.94, 5.21]


def field(w, h):
    """Seamless [0,1] low-frequency field."""
    rows = []
    norm = sum(b[2] for b in BANDS)
    for y in range(h):
        vy = 2.0 * math.pi * y / h
        row = []
        for x in range(w):
            vx = 2.0 * math.pi * x / w
            acc = 0.0
            for (fx, fy, wgt), ph in zip(BANDS, PHASE):
                acc += wgt * math.sin(fx * vx + ph) * math.sin(fy * vy + ph * 0.7)
            row.append((acc / norm + 1.0) * 0.5)
        rows.append(row)
    return rows


def build(src):
    w, h = src.size
    r, g, b, a = src.split()
    old = list(a.tobytes())
    f = field(w, h)

    # combine: authored structure x the seamless field
    comb = [0.0] * (w * h)
    for y in range(h):
        for x in range(w):
            i = y * w + x
            comb[i] = (old[i] / 255.0) * f[y][x]

    # pick the threshold that lands on TARGET_COVERAGE, then map through a soft shoulder so the
    # surviving slicks keep feathered edges instead of being punched out
    srt = sorted(comb)
    cut = srt[int((1.0 - TARGET_COVERAGE) * (len(srt) - 1))]
    span = max(1e-6, srt[-1] - cut)

    out = bytearray(w * h)
    for i, v in enumerate(comb):
        if v <= cut:
            out[i] = 0
            continue
        t = (v - cut) / span                 # 0..1 within the surviving range
        # Sparse has to mean STRONG WHERE PRESENT, or thinning the coverage just turns the sheet
        # into a faint haze - which looks like a mistake rather than like blood. The gamma pushes
        # most surviving texels toward the top of the range; the smoothstep keeps slick edges soft.
        t = t ** 0.38
        t = t * t * (3.0 - 2.0 * t)
        out[i] = int(round(255.0 * min(1.0, 0.30 + 0.70 * t)))

    return Image.merge("RGBA", (r, g, b, Image.frombytes("L", (w, h), bytes(out))))


def stats(im):
    d = list(im.split()[3].tobytes())
    n = len(d)
    return {
        "mean": sum(d) / n,
        "clear": 100.0 * sum(1 for x in d if x == 0) / n,
        "a25": 100.0 * sum(1 for x in d if x > 25) / n,
        "a140": 100.0 * sum(1 for x in d if x > 140) / n,
    }


def seam(im):
    """Mean absolute difference across the wrap edges - proves it still tiles."""
    a = im.split()[3]
    w, h = a.size
    d = list(a.tobytes())
    lr = sum(abs(d[y * w] - d[y * w + w - 1]) for y in range(h)) / h
    tb = sum(abs(d[x] - d[(h - 1) * w + x]) for x in range(w)) / w
    return lr, tb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(TEX):
        print("missing %s" % TEX)
        return 1
    if not os.path.exists(SRC):
        Image.open(TEX).convert("RGBA").save(SRC)
        print("  snapshotted the authored source -> %s" % os.path.relpath(SRC, REPO))
    src = Image.open(SRC)
    src.load()
    src = src.convert("RGBA")
    before = stats(src)
    print("  before: mean alpha %.1f, clear water %.1f%%, above 25 %.1f%%, above 140 %.1f%%"
          % (before["mean"], before["clear"], before["a25"], before["a140"]))

    out = build(src)
    after = stats(out)
    lr, tb = seam(out)
    print("  after : mean alpha %.1f, clear water %.1f%%, above 25 %.1f%%, above 140 %.1f%%"
          % (after["mean"], after["clear"], after["a25"], after["a140"]))
    print("  wrap seam: left/right %.1f, top/bottom %.1f (0 = perfectly tileable)" % (lr, tb))

    if args.check:
        print("  CHECK only - nothing written")
        return 0
    if args.write:
        out.save(TEX)
        print("  wrote %s" % os.path.relpath(TEX, REPO))
    else:
        print("  DRY RUN - pass --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
