"""shade73.py - the menu scene's soft wall-shadow decals behind the rack (MP room) and the pull-down screen (attic), v1.10.73.

Two faults, both found with in-game stills (docs/proposals/leaderboard_2026-11-10/PLAN.md, bug-10768 follow-up):
 1. A multiply decal (blendFunc GL_DST_COLOR GL_ZERO / filter) draws NOTHING in the menu Scene3D (bug-10768), so the sheet is
    the posters' recipe (gen_posters68.py): a BLACK RGBA tga whose alpha is the shadow, plain blendFunc blend.
 2. Switching the blend alone changed no pixel (a before/after diff of the v1.10.72 and v1.10.73 stills: max 1.7 / 2.0 levels):
    an opaque-red debug texture showed both quads DO draw, but the old images put their whole dark core in the middle of the
    sheet - exactly behind the cabinet and the screen fabric, which hide it. So the shadow is now shaped from the prop's own
    outline: the occluder rectangles grown a little, dropped (the lamps hang above), blurred, and faded to nothing before the
    sheet's edge (no hard border). Only the halo that falls PAST the prop is ever seen - which is what a contact shadow is.

shade_halo works in world units on the decal's own quad: quad = (x_lo, x_hi, z_lo, z_hi) on the wall, occluders = the same for
each part of the prop; mirror_u is the quad's u direction (True when u = 0 lies at x_hi, as the rack's quad_c corners have it).
Image row 0 = the quad's top (write_model's flip_v uvs).
"""
import numpy as np
from PIL import Image, ImageFilter

# the rack (MP room left wall): the shadow quad of gen_attic68_props (rack lo/hi -16 / +16 in x, -14 / +8 in z) and the cabinet
# (the lamp's hood is left out: it sits at the quad's top edge, where a halo would be cut). From the v1.10.72 models
# (hzm_hub_rack.skd: cabinet x 44.6..99.5, z 59.2..127.5; hzm_hub_rackshadow quad x 28.6..115.5, z 45.2..152.9).
RACK = dict(quad=(28.6, 115.5, 45.2, 152.9), occ=[(44.6, 99.5, 59.2, 127.5)], mirror_u=True)
# the pull-down screen (attic right wall): quad x 38..124, z 38..139; the fabric (SCR_X0..X1 47..115, from the slat at SZ0 50 up to
# the roller case) and the case + caps (x 43.4..118.6, z 128..137.2)
SCREEN = dict(quad=(38.0, 124.0, 38.0, 139.0), occ=[(47.0, 115.0, 46.0, 130.0), (43.4, 118.6, 128.0, 137.2)], mirror_u=False)


def shade_halo(path, spec, size=256, spread=2.0, drop=2.5, blur=2.2, alpha=150, fade=1.5):
    x0, x1, z0, z1 = spec["quad"]
    pu, pv = size / (x1 - x0), size / (z1 - z0)            # pixels per unit
    a = np.zeros((size, size), np.float32)
    for ox0, ox1, oz0, oz1 in spec["occ"]:
        ox0, ox1, oz0, oz1 = ox0 - spread, ox1 + spread, oz0 - spread - drop, oz1 + spread - drop
        c0, c1 = (ox0 - x0) * pu, (ox1 - x0) * pu
        if spec["mirror_u"]:
            c0, c1 = size - c1, size - c0
        r0, r1 = (z1 - oz1) * pv, (z1 - oz0) * pv
        a[max(0, int(round(r0))):min(size, int(round(r1))), max(0, int(round(c0))):min(size, int(round(c1)))] = 1.0
    im = Image.fromarray(np.uint8(a * 255)).filter(ImageFilter.GaussianBlur(blur * (pu + pv) / 2))
    a = np.asarray(im, np.float32) / 255
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    edge = np.minimum(np.minimum(xx, size - 1 - xx) / pu, np.minimum(yy, size - 1 - yy) / pv)
    a = a * np.clip(edge / fade, 0, 1) * alpha
    al = Image.fromarray(np.uint8(np.clip(a + 0.5, 0, 255)))
    Image.merge("RGBA", (Image.new("L", (size, size), 0),) * 3 + (al,)).save(path)


def shade_shader(name, tex):
    return ("%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tclampmap textures/menu/%s.tga\n\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}"
            % (name, tex))
