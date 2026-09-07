# -*- coding: utf-8 -*-
"""GENERATOR for textures/coop_fx/caustic_dim.tga (bug-2509): retail textures/misc_outside/caustic.jpg (Pak2,
256x256) scaled to 18% so the additive seabed stage in zz_coop_seabed.shader can use rgbGen identity - the
first cut relied on rgbGen const 0.35 and drew as bright white bands on gl2. Brightness lives in the texture,
which every renderer path honours. 18-byte TGA header, 24-bit, per-row luminance printed."""
import zipfile, io, struct, glob, sys
from PIL import Image
GAIN = float(sys.argv[1]) if len(sys.argv) > 1 else 0.18
src = None
for pat in ("G:/mohaa-gl2/main/*.pk3", "G:/GOG/Medal of Honor - Allied Assault War Chest/main/*.pk3"):
    for p in sorted(glob.glob(pat)):
        z = zipfile.ZipFile(p)
        for n in z.namelist():
            if n.lower() == "textures/misc_outside/caustic.jpg": src = (p, n)
        if src: break
    if src: break
assert src, "caustic.jpg not found"
im = Image.open(io.BytesIO(zipfile.ZipFile(src[0]).read(src[1]))).convert("RGB")
w, h = im.size; px = im.load()
rows = []
for y in range(h):
    row = bytearray()
    for x in range(w):
        r, g, b = px[x, y]
        row += bytes((int(b * GAIN + 0.5), int(g * GAIN + 0.5), int(r * GAIN + 0.5)))   # BGR
    rows.append(bytes(row))
hdr = bytes([0, 0, 2]) + struct.pack('<HHB', 0, 0, 0) + struct.pack('<HHHHBB', 0, 0, w, h, 24, 0); assert len(hdr) == 18
out = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\coop_fx\caustic_dim.tga"
open(out, "wb").write(hdr + b"".join(rows))
lum = [sum(px[x, y]) / 3 for y in range(h) for x in range(w)]
print("source %s %dx%d mean lum %.1f max %d; gain %.2f -> mean %.1f max %d; wrote %s (%d bytes)" % (src[0].split('/')[-1], w, h, sum(lum) / len(lum), int(max(lum)), GAIN, sum(lum) / len(lum) * GAIN, int(max(lum) * GAIN), out, 18 + w * h * 3))
