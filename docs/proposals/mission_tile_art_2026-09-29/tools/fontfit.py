"""fontfit.py - text measurement for the tile captions.

engine_width(font, s): the width the ENGINE would draw s at, in 640x480 virtual units, from the retail RitualFont glyph
table (main/Pak0.pk3 fonts/<font>.ritualfont; UIFont::getCharWidth reads locations[].size[0]). Used to show which
titles an engine-drawn label could hold on a 100-unit tile.

caption_font(px, bold): the baked caption face - Bahnschrift, the face the mod's facfont-20@3x atlas was rendered from
(docs/proposals/menu_system_remaster_2026-09-29/THEME.md, licensing note), so a baked caption reads as the game's own
button lettering. Width axis at 'Condensed' for the title.
"""
import os
import re
import zipfile

from PIL import ImageFont

PAK0 = r"G:\GOG\Medal of Honor - Allied Assault War Chest\main\Pak0.pk3"
FACE = r"C:\Windows\Fonts\bahnschrift.ttf"
_RF = {}


def _ritual(font):
    if font not in _RF:
        z = zipfile.ZipFile(PAK0)
        name = next(n for n in z.namelist() if n.lower() == "fonts/%s.ritualfont" % font.lower())
        t = z.read(name).decode("latin1")
        ind = [int(x) for x in re.search(r"indirections\s*\{([^}]*)\}", t).group(1).split()]
        locs = re.findall(r"\{\s*([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s*\}", t[t.find("locations"):])
        _RF[font] = (float(re.search(r"height\s+([\d.]+)", t).group(1)), ind, [float(l[2]) for l in locs])
    return _RF[font]


def engine_width(font, s):
    h, ind, w = _ritual(font)
    return sum(w[ind[ord(c)]] for c in s if ord(c) < len(ind) and ind[ord(c)] >= 0)


def caption_font(px, weight=600, width=75):
    f = ImageFont.truetype(FACE, int(round(px)))
    f.set_variation_by_axes([weight, width])
    return f


def text_w(font, s):
    b = font.getbbox(s)
    return b[2] - b[0]


def wrap_two(font, s, maxw):
    """Best 2-line split (balanced) of s under maxw, or None."""
    words = s.split()
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        wa, wb = text_w(font, a), text_w(font, b)
        if max(wa, wb) <= maxw:
            score = abs(wa - wb)
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else None


def fit_title(s, maxw, sizes, min_one=84, max_two=72):
    """-> (px, lines). One line if it fits at >= min_one px; else the largest balanced 2-line wrap at <= max_two px
    (the band holds two lines of 72 px under the kicker); else one line at the smallest size."""
    for px in sizes:
        f = caption_font(px)
        if px >= min_one and text_w(f, s) <= maxw:
            return px, [s]
    for px in [p for p in sizes if p <= max_two]:
        f = caption_font(px)
        two = wrap_two(f, s, maxw)
        if two:
            return px, two
    px = sizes[-1]
    return px, wrap_two(caption_font(px), s, maxw * 1.2) or [s]
