"""gen_hd_ramp.py - the one texture behind the HD hold-progress ring / bars (cgame cg_hdprogress.c).

    python docs/tools/gen_hd_ramp.py            # write docs/tools/assets/fixes/textures/hud/coop_hd_ramp.tga
    python docs/tools/gen_hd_ramp.py --check    # exit 1 if the file on disk differs from a rebuild

WHY A RAMP. The engine's 2D path has no anti-aliasing: a coloured quad is either on or off per pixel, which is what made
the old DBNO ring (a necklace of whole-pixel boxes) and the heal/place bars (flat rectangles) look low-definition.
cgame now draws the ring and the bars as real geometry (triangles, so any angle and any radius) and gives every edge a
feather of ~1.4 screen pixels whose alpha comes from this texture: s = 0 is fully transparent, s = 1 is fully opaque,
the curve in between is a smoothstep. White RGB everywhere, so a tint never leaves a dark or light fringe.
1024 texels wide so the ramp is smooth when the feather is stretched; 16 rows because a 1-row texture is rejected by
some drivers' mip path. It is looked up with the NoMip shader loader and CLAMPED coordinates inside [0,1] only.

Shipped through the fixes pak (docs/tools/gen_fixes_pak.py, manifest entry "new": the mod tree never holds it).
"""
import os, struct, sys

W, H = 1024, 16
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fixes", "textures", "hud", "coop_hd_ramp.tga")


def smoothstep(x):
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    return x * x * (3.0 - 2.0 * x)


def build():
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, W, H, 32, 0x28)  # top-left origin, 8 alpha bits
    row = bytearray()
    for x in range(W):
        a = int(round(255.0 * smoothstep((x + 0.5) / W)))
        row += bytes((255, 255, 255, a))   # BGRA
    return hdr + bytes(row) * H


def main():
    data = build()
    if "--check" in sys.argv:
        ok = os.path.isfile(OUT) and open(OUT, "rb").read() == data
        print("OK" if ok else "FAIL coop_hd_ramp.tga differs from a rebuild")
        return 0 if ok else 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(data)
    print("wrote", OUT, len(data), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
