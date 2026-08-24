#!/usr/bin/env python3
"""
DERIVE FIRST-PERSON GLOVE TEXTURES (bug-2080).

WHY THIS EXISTS. The armory's glove row needs the same glove in both views, but the third-person
hands (`models/human/hands/hand.skd`) and the first-person hands (`models/player/US_Army/
USarmyplyr.skd`) are DIFFERENT MESHES WITH DIFFERENT UV LAYOUTS. That is measured, not assumed:
across 1,878 third-person TIKs and 191 first-person ones, shipped content uses 27 distinct shaders
on the 3P `hand` surface and 11 on the 1P hand surfaces, and the intersection is EMPTY. The original
developers never once reused a hand texture across the two meshes. Painting a 3P glove onto the 1P
mesh would smear it.

The trilogy ships exactly THREE true first-person gloves (lthr_gloveview, grmn_winter_glove,
us_winterglove). Any roster larger than that needs first-person art that does not exist.

WHAT THIS DOES INSTEAD OF INVENTING ART. For each glove with no first-person twin, it takes the
NEAREST EXISTING 1P glove - which is already correct for the 1P UV layout - and recolours it to the
mean colour of the intended 3P glove. The result fits the mesh properly and reads as the same glove
in both views. It is a recolour, not a repaint: the weave, stitching and shading of the donor are
preserved, only the hue and level are moved.

    python docs/tools/gen_glove_views.py            # report
    python docs/tools/gen_glove_views.py --write    # write textures + shader
"""
import io
import os
import sys
import glob
import zipfile

from PIL import Image

MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
OUT_TEX = os.path.join(MOD, 'textures', 'models', 'human')
OUT_SHADER = os.path.join(MOD, 'scripts', 'coop_gloves.shader')
PAK_ROOTS = [r'G:\GOG\Medal of Honor - Allied Assault War Chest', r'G:\mohaa-gl2']

# derived name, 1P donor (correct UVs), 3P target (colour reference)
DERIVE = [
    ('coop_glove_mittens_view',
     'textures/models/human/grmn_winter_glove.tga',
     'textures/models/human/germanmaps/wintertroops/mittens2.tga'),
    ('coop_glove_seaman_view',
     'textures/models/human/lthr_gloveview.tga',
     'textures/models/human/sovietmaps/seaman_gloves.tga'),
    # [bug-2082] us_winterglove was the 1P for US Winter Gloves, but it ships ONLY in
    # zzzzzz-HRRTM_Pak3_Textures.pk3 - a third-party pack this mod does not ship. Anyone without
    # HRRTM installed would have got a missing texture down the sights (TRAPS T6 / bug-2020: never
    # depend on an asset from a pack we do not ship). Derived from retail parts instead: the donor
    # is the retail German winter glove and the colour reference is handsglove.tga, the retail US
    # snow-glove 3P texture this row already uses.
    ('coop_glove_uswinter_view',
     'textures/models/human/grmn_winter_glove.tga',
     'textures/models/human/handsglove.jpg'),   # retail (mainta/maintt pak1) - it is .jpg, not .tga
]


def pak_index():
    idx = {}
    paks = []
    for r in PAK_ROOTS:
        for d in ('main', 'mainta', 'maintt'):
            paks += glob.glob(os.path.join(r, d, '*.pk3'))
    for p in sorted(paks):
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            idx.setdefault(n.lower().replace('\\', '/'), (p, n))
    return idx


def load_img(rel, idx):
    hit = idx.get(rel.lower())
    if not hit:
        return None
    data = zipfile.ZipFile(hit[0]).read(hit[1])
    return Image.open(io.BytesIO(data)).convert('RGBA')


def mean_rgb(im):
    """Mean colour over meaningfully opaque, non-black pixels.

    Hand textures carry large fully-transparent or black margins; averaging those drags every
    result toward black and makes two different gloves come out the same colour.
    """
    px = im.getdata()
    tot = [0, 0, 0]
    n = 0
    for r, g, b, a in px:
        if a < 128:
            continue
        if r + g + b < 24:
            continue
        tot[0] += r
        tot[1] += g
        tot[2] += b
        n += 1
    if not n:
        return (128, 128, 128)
    return (tot[0] // n, tot[1] // n, tot[2] // n)


def recolour(donor, target_rgb):
    """Scale each channel of the donor so its mean lands on target_rgb, preserving its own detail."""
    src = mean_rgb(donor)
    scale = []
    for i in range(3):
        s = src[i] if src[i] > 0 else 1
        scale.append(target_rgb[i] / float(s))
    out = donor.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            px[x, y] = (
                min(255, int(r * scale[0])),
                min(255, int(g * scale[1])),
                min(255, int(b * scale[2])),
                a,
            )
    return out


SHADER_TMPL = """textures/models/human/%(name)s
{
	qer_editorimage textures/models/human/%(name)s.tga
	{
		map textures/models/human/%(name)s.tga
		rgbGen lightingSpherical
	}
}

%(name)s
{
	qer_editorimage textures/models/human/%(name)s.tga
	{
		map textures/models/human/%(name)s.tga
		rgbGen lightingSpherical
	}
}
"""


def main():
    write = '--write' in sys.argv
    idx = pak_index()
    blocks = []
    print('DERIVE FIRST-PERSON GLOVE TEXTURES  (%s)' % ('WRITE' if write else 'dry run'))
    for name, donor_rel, target_rel in DERIVE:
        donor = load_img(donor_rel, idx)
        target = load_img(target_rel, idx)
        if donor is None or target is None:
            print('  SKIP %-28s donor=%s target=%s'
                  % (name, donor is not None, target is not None))
            continue
        tgt = mean_rgb(target)
        src = mean_rgb(donor)
        print('  %-28s donor %-46s mean%s -> mean%s' % (name, os.path.basename(donor_rel), src, tgt))
        if write:
            out = recolour(donor, tgt)
            if not os.path.isdir(OUT_TEX):
                os.makedirs(OUT_TEX)
            p = os.path.join(OUT_TEX, name + '.tga')
            out.convert('RGB').save(p)
            print('       wrote %s  (%dx%d)' % (p, out.size[0], out.size[1]))
        blocks.append(SHADER_TMPL % {'name': name})

    if write and blocks:
        hdr = (
            '// GENERATED by docs/tools/gen_glove_views.py - DO NOT HAND-EDIT\n'
            '//\n'
            '// First-person glove textures for the armory glove row (bug-2080). The 3P and 1P hands\n'
            '// are different meshes with different UV layouts - shipped content shares ZERO hand\n'
            '// shaders between them - so a 3P glove texture cannot be shown in first person. Each\n'
            '// texture here is an existing 1P glove (already correct for the 1P UVs) recoloured to\n'
            '// the mean colour of its 3P counterpart, so the same glove reads the same in both views.\n'
            '\n'
        )
        if not os.path.isdir(os.path.dirname(OUT_SHADER)):
            os.makedirs(os.path.dirname(OUT_SHADER))
        io.open(OUT_SHADER, 'w', encoding='ascii', newline='\n').write(hdr + '\n'.join(blocks))
        print('  wrote %s (%d shader blocks)' % (OUT_SHADER, len(blocks) * 2))
    if not write:
        print('  (dry run - pass --write)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
