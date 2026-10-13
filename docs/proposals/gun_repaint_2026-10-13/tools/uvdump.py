"""UV islands of the surfaces that use one sheet, for every skd that shares it: island table (uv box, bone-space
box, mean normal) + the island outlines drawn over today's sheet (work/uv_<tag>_<skd>.png) + today's sheet as PNG.

    python uvdump.py <tag> <texture stem> <surface|all> <skd vpath or file> [<skd> ...]
"""
import os, sys, json
import numpy as np
from PIL import Image
import rplib as L


def main():
    tag, stem, surf = sys.argv[1:4]
    old, vp, pak = L.read_image(stem)
    H, W = old.shape[:2]
    print("sheet", vp, pak, W, H)
    os.makedirs(L.WORK, exist_ok=True)
    oim = Image.fromarray(old.astype(np.uint8))
    oim.save(os.path.join(L.WORK, "old_%s.png" % tag))
    rep = {}
    sc = max(1, int(round(1024 / max(W, H))))
    for src in sys.argv[4:]:
        S = L.load_skd(src)
        base = os.path.splitext(os.path.basename(src))[0]
        print(base, "surfaces:", {k: (len(v["tris"]), v["n"]) for k, v in S.items()})
        for name, s in S.items():
            if surf != "all" and name != surf:
                continue
            rows = L.island_rows(s)
            for r in rows:
                print("  ", name, json.dumps(r))
            rep[base + ":" + name] = rows
            print("   uv range", s["uv"].min(0).round(3), s["uv"].max(0).round(3))
            L.island_map(s, W * sc, H * sc, os.path.join(L.WORK, "uv_%s_%s_%s.png" % (tag, base, name)), under=oim)
    json.dump(rep, open(os.path.join(L.WORK, "islands_%s.json" % tag), "w"), indent=1)


if __name__ == "__main__":
    main()
