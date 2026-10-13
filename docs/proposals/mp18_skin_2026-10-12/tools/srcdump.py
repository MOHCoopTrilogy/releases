"""Dump the material SOURCES (the mod's / game's own Kar98 wood and MP40 steel sheets, as the engine resolves
them from the shipped pak set, read-only) into work/src as PNG, with a 1024 preview each.
usage: python srcdump.py"""
import os, sys, io
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import vfs
WORK = os.path.join(HERE, "..", "work", "src")
STEMS = ["textures/models/weapons/kar98/kar98", "textures/models/weapons/mp40/mp40",
         "textures/models/weapons/mp40/metal1", "textures/models/weapons/mp40/metal2",
         "textures/models/weapons/mp40/metal3"]


def main():
    os.makedirs(WORK, exist_ok=True)
    for st in STEMS:
        name, w = vfs.resolve_image(st)
        if not name:
            print("MISSING", st); continue
        data = vfs.read(name)
        im = Image.open(io.BytesIO(data)).convert("RGB")
        base = st.split("/")[-1]
        im.save(os.path.join(WORK, base + ".png"))
        pv = im.copy(); pv.thumbnail((1024, 1024))
        pv.save(os.path.join(WORK, base + "_pv.jpg"), quality=85)
        print(st, "->", name, w, im.size)


if __name__ == "__main__":
    main()
