"""shade73.py - the menu scene's soft wall-shadow decals (v1.10.73, the bug-10768 follow-up).

A multiply decal (blendFunc GL_DST_COLOR GL_ZERO / filter) draws NOTHING in the menu Scene3D (in-game test quads, bug-10768),
so every shadow sheet uses the posters' recipe (gen_posters68.py): a BLACK RGBA tga whose alpha is the shadow, plain
blendFunc blend, no sort decal / polygonOffset. Shared by gen_attic68_props.py (the source) and gen_shadows73.py (the v1.10.73
pak patch), so the two can never drift.

Densities are the old multiplies' own (dst * v/255 == dst * (1 - a) with a = 255 - v): the rack's core 150 -> alpha 105, the
screen's 170 -> alpha 85 (the posters' core alpha is 85 too).
"""
from PIL import Image, ImageDraw, ImageFilter

# (size, core rectangle, core alpha, blur) - the same geometry as the v1.10.68 multiplies
RACK_SHADE = (256, (56, 40, 200, 214), 255 - 150, 16)
SCREEN_SHADE = (256, (40, 30, 216, 236), 255 - 170, 14)


def shade_tga(path, spec):
    size, rect, alpha, blur = spec
    a = Image.new("L", (size, size), 0)
    ImageDraw.Draw(a).rectangle(rect, fill=alpha)
    a = a.filter(ImageFilter.GaussianBlur(blur))
    Image.merge("RGBA", (Image.new("L", (size, size), 0),) * 3 + (a,)).save(path)


def shade_shader(name, tex):
    return ("%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/%s.tga\n\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}"
            % (name, tex))
