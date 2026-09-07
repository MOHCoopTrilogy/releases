# -*- coding: utf-8 -*-
"""GENERATOR for textures/coop_fx/breakfoam.tga [user 2026-09-06, bug-2508] - the break-line foam stage of
zz_coop_shoreline.shader (stage 2, reclaimed from a retail stage that drew alpha 0).

What it is: the wash2 foam band that gen_wetsand.py baked into wetsand_foam.tga (t 0.60-0.90 of that
texture, with its per-column rag), read back out of the SHIPPED wetsand_foam.tga rows and resampled so the
band sits at T 0.55-0.72 of the WATERLINE SHEET (raw T 0.005 at the seam, 0.994 at the land edge, 1408 u
per 1.0 T - LANE-A), i.e. y -1386..-1146, where the crests die at the hand-off knee (T 0.72). Alpha is
baked (the ragged window comes from the source's alpha, resampled the same way), so the stage needs no
alphaGen. Columns are rolled by 0.25 S (64 of 256) because the sheet's S at `tcMod scale 62 1` is
(x + 7872) / 256 while the sand strip's is 0.25 + (x + 7872) / 256 (ocean report s.0 item 1): after the
roll the foam's rag is the strip's rag at every x.

TGA: 18-byte header (the 13-byte header of 2026-09-06 is in the buglog), type 2, 32 bpp, desc 0x08, raw
BGRA, no footer; the engine's LoadTGA puts the file's FIRST row at t = 1 (verified for wetsand_foam.tga,
bug-2485). Per-row RGB*alpha is dumped so a black band or a mis-set window cannot ship unnoticed.

Run from anywhere: python docs/tools/gen_breakfoam.py
"""
import struct, sys

SRC = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx\wetsand_foam.tga"
OUT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx\breakfoam.tga"
W = 256; H = 256
SRC_T0, SRC_T1 = 0.60, 0.90     # where gen_wetsand.py put the band in the source (band top at 0.90)
DST_T0, DST_T1 = 0.55, 0.72     # where it goes on the waterline sheet
ROLL = 64                       # 0.25 S of a 256-column tile: the sand strip's S phase lead


def t_of_row(r):
    return (H - 1 - r + 0.5) / H


def row_of_t(t):
    return (H - 1 + 0.5) - t * H     # inverse of t_of_row, fractional


# ---------------- read the shipped source
sd = open(SRC, "rb").read()
idlen, cmt, itype, _cms, _cml, _cmb, _xo, _yo, sw, sh, bpp, desc = struct.unpack("<BBBHHBHHHHBB", sd[:18])
assert (idlen, cmt, itype, sw, sh, bpp) == (0, 0, 2, W, H, 32), "unexpected wetsand_foam.tga layout"
spx = sd[18:18 + W * H * 4]
assert len(spx) == W * H * 4, "short source pixel block"


def src_px(r, c):
    o = (r * W + c) * 4
    return spx[o], spx[o + 1], spx[o + 2], spx[o + 3]     # B G R A


def sample(t_src, c_src):
    """bilinear in T between source rows at fractional row row_of_t(t_src), one column."""
    rr = row_of_t(t_src)
    r0 = int(rr // 1); fr = rr - r0
    r0 = max(0, min(H - 1, r0)); r1 = max(0, min(H - 1, r0 + 1))
    a = src_px(r0, c_src); b = src_px(r1, c_src)
    return tuple(a[k] * (1 - fr) + b[k] * fr for k in range(4))


# ---------------- build
rows = []
for r in range(H):
    t = t_of_row(r)
    row = bytearray()
    for c in range(W):
        cs = (c + ROLL) % W
        t_src = SRC_T0 + (t - DST_T0) / (DST_T1 - DST_T0) * (SRC_T1 - SRC_T0)
        if 0.40 <= t_src <= 0.96 and 0.02 < t < 0.98:
            bb, gg, rr_, aa = sample(t_src, cs)
        else:
            bb = gg = rr_ = aa = 0.0
        row += bytes((int(round(bb)), int(round(gg)), int(round(rr_)), int(round(aa))))
    rows.append(bytes(row))

hdr = bytes([0, 0, 2]) + struct.pack("<HHB", 0, 0, 0) + struct.pack("<HHHHBB", 0, 0, W, H, 32, 8)
assert len(hdr) == 18, "TGA header must be 18 bytes"
open(OUT, "wb").write(hdr + b"".join(rows))

# ---------------- the check: per-row mean RGB, alpha, RGB*alpha
fd = open(OUT, "rb").read()
assert len(fd) == 18 + W * H * 4, "size %d" % len(fd)
print("breakfoam.tga %d bytes, header %s" % (len(fd), fd[:18].hex()))
print("per-row mean(RGB), alpha, eff = RGB*alpha (every 8th row, plus every row with alpha > 0):")
peak = (0, 0.0)
first_a = last_a = None
for r in range(H):
    row = fd[18 + r * W * 4: 18 + (r + 1) * W * 4]
    px = [row[i * 4:(i + 1) * 4] for i in range(W)]
    lum = sum((q[0] + q[1] + q[2]) / 3 for q in px) / W
    al = sum(q[3] for q in px) / W / 255
    amin = min(q[3] for q in px); amax = max(q[3] for q in px)
    eff = lum * al
    if eff > peak[1]:
        peak = (r, eff)
    if amax > 0:
        if first_a is None:
            first_a = r
        last_a = r
    if r % 8 == 0 or amax > 0:
        print("  row %3d t=%.3f  rgb %5.1f  alpha %.2f (min %3d max %3d)  eff %5.1f"
              % (r, t_of_row(r), lum, al, amin, amax, eff))
top = fd[18: 18 + W * 4]; bot = fd[18 + (H - 1) * W * 4: 18 + H * W * 4]
assert max(top[i * 4 + 3] for i in range(W)) == 0 and max(top[i * 4 + k] for i in range(W) for k in range(3)) == 0, \
    "sea-edge (t=1) row must be black + transparent"
assert max(bot[i * 4 + 3] for i in range(W)) == 0 and max(bot[i * 4 + k] for i in range(W) for k in range(3)) == 0, \
    "land-edge (t=0) row must be black + transparent"
print("alpha > 0 on rows %d..%d = t %.3f..%.3f (window incl. rag); peak eff %.1f/255 at row %d t=%.3f"
      % (first_a, last_a, t_of_row(first_a), t_of_row(last_a), peak[1], peak[0], t_of_row(peak[0])))
assert t_of_row(first_a) <= 0.80, "band must stay under the hand-off knee region (T 0.82)"
assert peak[1] > 20.0, "band is black - window over the wrong rows (the bug-2485 bake)"
print("OK")
