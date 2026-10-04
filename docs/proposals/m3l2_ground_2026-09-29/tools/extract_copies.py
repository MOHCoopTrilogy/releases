# Extract every stack copy of the named image bases to work/copies/ as PNG (level 0), print size/format/sha.
import hashlib, io, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "tools")))
import gen_terrain_pak_v3 as V3, gen_terrain_pak_v2 as V2
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
OUT = os.path.join(HERE, "..", "work", "copies")
st = V3.Stack(GOG)
for base in sys.argv[1:]:
    for ext in (".dds", ".jpg", ".tga", ".png"):
        for i, m in st.copies.get(base + ext, []):
            b = st.read(i, m)
            pak = os.path.basename(st.srcs[i][1]).replace(".pk3", "")
            gdir = os.path.basename(os.path.dirname(st.srcs[i][1]))
            if ext == ".dds" and b[84:88] == b"DX10":
                im = Image.open(io.BytesIO(b)); fmt = "dds DX10 fmt=%d" % int.from_bytes(b[128:132], "little")
                a = np.asarray(im.convert("RGB"))
            elif ext == ".dds":
                info = V2.dds_parse(b)
                a = V2.dds_decode_level(b, info, 0)[..., :3]
                fmt = "dds %s mips=%s" % (info.get("fourcc", info.get("fmt")), info.get("mips"))
            else:
                im = Image.open(io.BytesIO(b)); fmt = ext[1:] + " " + im.mode
                a = np.asarray(im.convert("RGB"))
            a = np.asarray(a, dtype=np.uint8)
            fn = "%s__%s_%s%s.png" % (os.path.basename(base), gdir, pak, ext.replace(".", "_"))
            Image.fromarray(a).save(os.path.join(OUT, fn))
            L = a.astype(float) @ [0.299, 0.587, 0.114]
            print("%-38s %-8s %-36s %-5s %4dx%-4d %-22s mean %s lstd %.1f sha %s" % (os.path.basename(base), gdir, pak, ext, a.shape[1], a.shape[0], fmt,
                  np.round(a.reshape(-1, 3).mean(0), 1), L.std(), hashlib.sha256(b).hexdigest()[:10]))
