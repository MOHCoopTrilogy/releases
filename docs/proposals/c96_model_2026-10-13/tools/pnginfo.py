# PNG header facts without decoding (run with python -I). usage: pnginfo.py <file>...
import struct, sys
CT = {0: "grey", 2: "RGB", 3: "palette", 4: "grey+alpha", 6: "RGBA"}
for p in sys.argv[1:]:
    with open(p, "rb") as f:
        h = f.read(33)
    ok = h[:8] == b"\x89PNG\r\n\x1a\n" and h[12:16] == b"IHDR"
    w, hh, bd, ct = struct.unpack(">IIBB", h[16:26])
    print(p.replace("\\", "/").split("/")[-1], "png_ok=%s" % ok, "%dx%d" % (w, hh), "%d-bit" % bd, CT.get(ct, ct))
