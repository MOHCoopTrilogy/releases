# -*- coding: utf-8 -*-
"""GENERATOR for textures/coop_fx/wetsand_swash.tga and wetsand_foam.tga (bugs 2485, 2493), the two textures
zz_coop_wetsand.shader draws on Omaha's tidal sand strip. Checked in 2026-09-06 after the ocean research
pass found the shipped assets had no generator in the repo (TRAPS T2: a generated asset without its
generator cannot be regenerated or audited). Run from anywhere: python docs/tools/gen_wetsand.py
Reads retail wash2.jpg from the installed paks (needs PIL); writes the two TGAs and prints the per-row
RGB*alpha check that caught the 13-byte-header and black-band bakes. Original notes follow.
"""

import struct, zipfile, glob, math, sys
OUT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx"
W = 256; H = 256

def off(s):   # s in [0,1), periodic; T units
    return (0.050 * math.sin(2 * math.pi * s)
          + 0.030 * math.sin(2 * math.pi * 3 * s + 1.7)
          + 0.018 * math.sin(2 * math.pi * 5 * s + 0.6)
          + 0.012 * math.sin(2 * math.pi * 11 * s + 2.9))

offs = [off((c + 0.5) / W) for c in range(W)]
print("offset range %.3f .. %.3f T" % (min(offs), max(offs)))
assert max(abs(o) for o in offs) <= 0.105

def t_of_row(r):
    return (H - 1 - r + 0.5) / H

# ---------------- swash: 24-bit, desc 0 (as shipped)
rows = []
for r in range(H):
    t = t_of_row(r)
    row = bytearray()
    for c in range(W):
        v = t - offs[c]
        if v >= 0.45:   g = 168
        elif v <= 0.25: g = 255
        else:           g = int(round(168 + (255 - 168) * (0.45 - v) / 0.20))
        row += bytes((g, g, g))
    rows.append(bytes(row))
hdr = bytes([0, 0, 2]) + struct.pack('<HHB', 0, 0, 0) + struct.pack('<HHHHBB', 0, 0, W, H, 24, 0); assert len(hdr) == 18
open(OUT + r"\wetsand_swash.tga", "wb").write(hdr + b"".join(rows))

# ---------------- foam: wash2 band -> RGBA, desc 8 (as shipped). wash2 ships as a JPEG (retail Pak2 256^2,
# the HD project pak 1024^2); decoded with PIL. MEASURED on the decoded rows: the foam band is image rows
# ~52..124 of 256 (top-down), luminance peak ~row 96, black everywhere else. That band is resampled to
# t 0.60..0.90 of this texture, band top at 0.90.
import io
from PIL import Image
SRC = ("G:/mohaa-gl2/maintt/zzzzz-AA_HD_Project_Pak3.pk3", "textures/misc_outside/wash2.jpg")
im = Image.open(io.BytesIO(zipfile.ZipFile(SRC[0]).read(SRC[1]))).convert("RGB")
sw, sh = im.size; spx = im.load(); K = sh / 256.0
print("wash2 %dx%d from %s" % (sw, sh, SRC[0].split('/')[-1]))
BAND_TOP, BAND_BOT = 52.0, 124.0          # in 256-row units, top-down
def wash2_rgb(td, c):
    rr = (BAND_BOT - (td - 0.60) / 0.30 * (BAND_BOT - BAND_TOP)) * K   # source row (float, top-down)
    r0 = int(math.floor(rr)); fr = rr - r0
    r0 = max(0, min(sh - 1, r0)); r1 = max(0, min(sh - 1, r0 + 1))
    sc = min(sw - 1, int(c * sw / W))
    a_ = spx[sc, r0]; b_ = spx[sc, r1]
    rgb = tuple(int(round(a_[k] * (1 - fr) + b_[k] * fr)) for k in range(3))
    return (rgb[2], rgb[1], rgb[0])       # TGA is BGR

def alpha_of(t):
    if t <= 0.50: return 0.0
    if t < 0.60:  return (t - 0.50) / 0.10
    if t <= 0.88: return 1.0
    if t < 0.95:  return (0.95 - t) / 0.07
    return 0.0

rows = []
for r in range(H):
    t = t_of_row(r)
    row = bytearray()
    for c in range(W):
        td = t - 0.7 * offs[c]           # the foam edge rides the same wander, a little damped
        a = alpha_of(td)
        if 0.60 <= td <= 0.90 and t < 0.97:
            bgr = wash2_rgb(td, c)
        else:
            bgr = (0, 0, 0)
        if t >= 0.97:                    # the clamped sea-edge rows: black AND transparent, whatever o(s) does
            a = 0.0; bgr = (0, 0, 0)
        row += bytes((bgr[0], bgr[1], bgr[2], int(round(a * 255))))
    rows.append(bytes(row))
hdr = bytes([0, 0, 2]) + struct.pack('<HHB', 0, 0, 0) + struct.pack('<HHHHBB', 0, 0, W, H, 32, 8); assert len(hdr) == 18
open(OUT + r"\wetsand_foam.tga", "wb").write(hdr + b"".join(rows))

# ---------------- the check: per-row RGB*alpha for the foam, per-row min/max for the swash
fd = open(OUT + r"\wetsand_foam.tga", "rb").read(); foff = 18
print("foam per-row mean(RGB)*alpha (every 16th row):")
for r in range(0, H, 16):
    row = fd[foff + r * W * 4: foff + (r + 1) * W * 4]
    px = [row[i * 4:(i + 1) * 4] for i in range(W)]
    lum = sum((q[0] + q[1] + q[2]) / 3 for q in px) / W
    al = sum(q[3] for q in px) / W / 255
    amin = min(q[3] for q in px); amax = max(q[3] for q in px)
    print("  row %3d t=%.3f  rgb %5.1f  alpha %.2f (min %3d max %3d)  eff %5.1f" % (r, t_of_row(r), lum, al, amin, amax, lum * al))
top = fd[foff: foff + W * 4]
assert max(top[i * 4 + 3] for i in range(W)) == 0 and max(top[i * 4:i * 4 + 3][0] for i in range(W)) == 0, "sea-edge row must be black+transparent"
sd = open(OUT + r"\wetsand_swash.tga", "rb").read()
print("swash per-row min/max grey (every 16th row):")
for r in range(0, H, 16):
    row = sd[18 + r * W * 3: 18 + (r + 1) * W * 3]
    g = [row[i * 3] for i in range(W)]
    print("  row %3d t=%.3f  min %3d max %3d" % (r, t_of_row(r), min(g), max(g)))
print("sizes: swash %d foam %d" % (len(sd), len(fd)))
