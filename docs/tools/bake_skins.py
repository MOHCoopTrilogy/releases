"""Produce the two kinds of art gen_skins.py references.

1. textures/coop_skins/env_sheen.tga - ONE shared sphere map, used by every stage finish through
   `tcGen environment`. It is what makes gold and chrome read as metal rather than as a flat tint.
   Shipped once for all guns and all finishes, which is the whole point of the stage approach.

2. textures/coop_skins/<gun>/<tex>_<finish>.jpg - the BAKED finishes (blood, camo). These need
   detail placed against the actual UVs, which a uniform shader stage cannot do, so they are real
   images generated from the gun's own base texture.

The image functions come from gen_weapon_skins.py, which already tuned them with the user: the
base is split into a low-frequency shading term and a high-frequency detail term, and only the hue
is replaced, so screws and grain survive instead of being flooded over.
"""
import io
import os
import re
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
SKIN_TEX = os.path.join(MOD, "textures", "coop_skins")

# pull in the tuned finish functions without running that script's preview driver
_src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_weapon_skins.py"),
               encoding="utf-8").read()
exec(_src.split("VARIANTS = [")[0], globals())

BAKED = {
    "bloody":        lambda im: bloody(im),                                             # noqa: F821
    "camo_woodland": lambda im: camo(im, [(58, 66, 40), (86, 92, 56),                    # noqa: F821
                                          (44, 40, 30), (104, 98, 66)]),
    "camo_winter":   lambda im: camo(im, [(178, 182, 186), (140, 146, 152),              # noqa: F821
                                          (96, 102, 108), (206, 210, 213)], seed=11),
    "camo_desert":   lambda im: camo(im, [(176, 150, 104), (146, 120, 78),               # noqa: F821
                                          (198, 178, 138), (118, 98, 66)], seed=5),
}


def make_envmap(path, size=128):
    """A soft studio sphere map: bright top, dark horizon, a hot highlight up and to the left.

    Deliberately low contrast. tcGen environment ADDs this over the tinted diffuse, so anything
    punchy turns the whole gun into a mirror and destroys the base texture underneath.
    """
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    cx = cy = (size - 1) / 2.0
    nx, ny = (x - cx) / cx, (y - cy) / cy
    r2 = nx * nx + ny * ny
    inside = r2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - r2, 0, 1))

    grad = np.clip(0.45 + 0.55 * (-ny), 0, 1)                 # sky above, ground below
    hi = np.clip(1.0 - ((nx + 0.45) ** 2 + (ny + 0.5) ** 2) / 0.16, 0, 1) ** 2
    v = np.clip(grad * 0.62 + hi * 0.85 + nz * 0.10, 0, 1) * 255.0
    img = np.zeros((size, size, 3), np.uint8)
    for c in range(3):
        img[..., c] = (v * inside).astype(np.uint8)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(img).save(path)
    print("  envmap -> %s (%dx%d)" % (os.path.relpath(path, MOD), size, size))


def bake_for(stem, base_texes):
    made = 0
    for tex in sorted(set(base_texes)):
        img = from_paks(tex)                                                             # noqa: F821
        if img is None:
            print("  %-16s base texture missing: %s" % (stem, tex))
            continue
        outdir = os.path.join(SKIN_TEX, stem)
        os.makedirs(outdir, exist_ok=True)
        stub = os.path.splitext(os.path.basename(tex))[0]
        for key, fn in BAKED.items():
            arr = np.clip(fn(img), 0, 255).astype(np.uint8)
            out = os.path.join(outdir, "%s_%s.jpg" % (stub, key))
            Image.fromarray(arr).save(out, quality=92)
            made += 1
    print("  %-16s %d baked texture(s)" % (stem, made))
    return made


if __name__ == "__main__":
    make_envmap(os.path.join(SKIN_TEX, "env_sheen.tga"))
    total = 0
    for arg in sys.argv[1:]:
        stem, texes = arg.split("=", 1)
        total += bake_for(stem, texes.split(","))
    print("\n%d baked texture(s) written" % total)
