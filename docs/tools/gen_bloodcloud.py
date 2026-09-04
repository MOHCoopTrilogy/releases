"""Generate textures/coop_fx/coop_bloodcloud.tga - blood SUSPENDED IN WATER.

WHY
---
2026-09-02, the user on the Omaha underwater hold: "there doesnt seem to be a mix of blood in the
water when we go down". There was not, and there could not have been: every blood asset the sequence
had was a surface or gravity asset.

    coop_blooddrip.tik   both emitters carry `accel 0 0 -800` with collision + dietouch +
                         bouncedecal. `collision` with no argument masks CONTENTS_SOLID only
                         (cg_commands.cpp:2280), so the particles fall straight THROUGH the -520
                         water surface, reach the -576 sand in about 0.4s of their 1.2s life, and
                         die as decals on the seabed.
    coop_gorechunk.tik   no emitter at all - a static crossed-quad xbeam mesh, so it hangs
                         motionless like a prop.
    coop_bloodslick.tik  the retail waterPlane mesh laid flat: a mark ON a surface.

None of those is a cloud in a column of water. This texture is the missing third thing.

WHAT IT DOES
------------
Donor is retail textures/sprites/vsssource.tga - a 32x32 soft radial falloff, which is exactly the
shape a diffusing cloud wants and is not worth re-authoring by hand.

  * ALPHA IS UNTOUCHED. The soft radial falloff is the entire reason the sprite works; the shader
    draws it with alphaGen vertex so the emitter's own fadein/fadedelay still own the fade.
  * RGB IS DRIVEN OFF ALPHA, thin edges arterial and thick middles venous - the same rule
    gen_bloodslick_tint.py applies to the pool sheet. Flat red reads as paint.
  * IT STAYS 32x32. A sprite's world size is image width x spritescale x tempmodel scale
    (renderergl2/tr_sprite.c:47-50, :153), so upscaling would silently resize the effect; and a soft
    low-res sprite blown up to ~80 units is precisely the blur a diffusing cloud wants anyway.

THE PALETTE IS IMPORTED FROM gen_bloodwash.py, not copied - one place defines what blood looks like
in this mod, and retuning it there moves the wash, the slick and this cloud together.

PRIVATE TEXTURE PATH. textures/coop_fx/ exists only in the coop pk3. That matters beyond the bug-922
isolation rule: maintt/zzzzzz_hd_fx.pk3 already replaces textures/sprites/vsssource.tga at 64 instead
of 32, which silently doubles the world size of every effect drawing it. Owning the texture is the
only way to own the size of the effect.

DETERMINISTIC and idempotent-safe: it reads an authored SOURCE snapshot kept beside the tool, never
its own output, so re-running cannot compound the tint - the footgun that destroyed 229 gore shader
blocks in bug-2229 and that both sibling generators guard against the same way.
"""

import io
import os
import sys
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
TEX = os.path.join(MOD, "textures", "coop_fx", "coop_bloodcloud.tga")
SRC = os.path.join(HERE, "vsssource_src.tga")

GAME = [r"G:\GOG\Medal of Honor - Allied Assault War Chest\main",
        r"G:\GOG\Medal of Honor - Allied Assault War Chest\mainta",
        r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"]

# --- the single source of truth for what blood looks like here
_gb = io.open(os.path.join(HERE, "gen_bloodwash.py"), encoding="utf-8").read()
_pal = _gb[_gb.index("RED_R_THIN"):]
_pal = _pal[:_pal.index("\n\n")]
exec(_pal, globals())          # RED_R_THIN/G/B, RED_R_THICK/G/B

# [user, index 25086] "I also change my mind the blood effects in the water need to be darker".
# That reverses the earlier "make the blood in the water slightly redder" ask, and it was never
# actioned - so the shipped colour was the one the user had already changed their mind about, and
# this new cloud would have inherited it. The shared palette stays as it is (it is right for blood
# on SAND, which is what the wash and the slick are); water gets its own multiplier, because blood
# seen through a column of silty water genuinely is darker and browner than blood on a beach.
DARKEN = 0.62


def snapshot():
    """Pull the donor out of the retail paks ONCE, beside the tool. Never read our own output."""
    if os.path.exists(SRC):
        return
    for root in GAME:
        if not os.path.isdir(root):
            continue
        for f in sorted(os.listdir(root)):
            if not f.lower().endswith(".pk3"):
                continue
            try:
                z = zipfile.ZipFile(os.path.join(root, f))
            except Exception:
                continue
            for n in z.namelist():
                if n.lower().replace("\\", "/") == "textures/sprites/vsssource.tga":
                    io.open(SRC, "wb").write(z.read(n))
                    print("  snapshotted donor from %s :: %s" % (f, n))
                    return
    print("  ERROR: could not find textures/sprites/vsssource.tga in any pak")
    sys.exit(1)


def main():
    snapshot()
    im = Image.open(SRC).convert("RGBA")
    w, h = im.size
    px = im.load()

    lit = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                # keep fully transparent texels black so no halo survives a filtered mip
                px[x, y] = (0, 0, 0, 0)
                continue
            lit += 1
            # t = 0 at the feathered edge, 1 in the dense middle
            t = a / 255.0
            rr = int(round((RED_R_THIN + (RED_R_THICK - RED_R_THIN) * t) * DARKEN))
            gg = int(round((RED_G_THIN + (RED_G_THICK - RED_G_THIN) * t) * DARKEN))
            bb = int(round((RED_B_THIN + (RED_B_THICK - RED_B_THIN) * t) * DARKEN))
            px[x, y] = (rr, gg, bb, a)

    d = os.path.dirname(TEX)
    if not os.path.isdir(d):
        os.makedirs(d)
    im.save(TEX)

    r, g, b, a = [list(c.tobytes()) for c in im.split()]
    sel = [i for i, v in enumerate(a) if v > 25]
    n = max(1, len(sel))
    print("  wrote %s  %dx%d" % (TEX, w, h))
    print("  visible RGB  %.0f / %.0f / %.0f   over %d of %d texels"
          % (sum(r[i] for i in sel) / n, sum(g[i] for i in sel) / n,
             sum(b[i] for i in sel) / n, len(sel), len(a)))
    print("  palette      thin %d/%d/%d  ->  thick %d/%d/%d"
          % (RED_R_THIN, RED_G_THIN, RED_B_THIN, RED_R_THICK, RED_G_THICK, RED_B_THICK))


if __name__ == "__main__":
    main()
