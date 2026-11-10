"""ritualfont.py - draw text with the game's own bitmap fonts (fonts/<name>.RitualFont + gfx/fonts/<name>.tga), so pre-rendered
art matches what the engine draws (the join card: facfont-20 titles, courier-20 lines).  Works with the mod's hi-res @3x atlases."""
import re
import numpy as np
from PIL import Image


class RitualFont:
    def __init__(self, ritual_path, tga_path):
        t = open(ritual_path, encoding="latin-1").read()
        self.height = float(re.search(r"height\s+([\d.]+)", t).group(1))
        self.aspect = float(re.search(r"aspect\s+([\d.]+)", t).group(1))
        ind = re.search(r"indirections\s*\{([^}]*)\}", t).group(1).split()
        self.ind = [int(x) for x in ind]
        locs = re.findall(r"\{\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\}", t[t.index("locations"):])
        self.loc = [tuple(float(v) for v in l) for l in locs]
        self.atlas = Image.open(tga_path).convert("RGBA")
        aw, ah = self.atlas.size
        # locations are texels of a 256-wide atlas whose height is 256 / aspect; a hi-res copy scales both
        self.sx, self.sy = aw / 256.0, ah / (256.0 / self.aspect)

    def glyph(self, ch):
        o = ord(ch)
        if o >= len(self.ind) or self.ind[o] < 0:
            return None
        return self.loc[self.ind[o]]

    def width(self, s, px):
        k = px / self.height
        return sum((g[2] if g else self.height * 0.5) * k for g in (self.glyph(c) for c in s))

    def draw(self, img, x, y, s, px, rgb, alpha=1.0):
        """draw s with its top-left at (x, y), px = the font's line height on screen (the engine's 'px' / scale)"""
        k = px / self.height
        for c in s:
            g = self.glyph(c)
            if not g:
                x += self.height * 0.5 * k
                continue
            gx, gy, gw, gh = g
            if gw <= 0 or gh <= 0:
                x += gw * k
                continue
            src = self.atlas.crop((int(round(gx * self.sx)), int(round(gy * self.sy)), int(round((gx + gw) * self.sx)), int(round((gy + gh) * self.sy))))
            w, h = max(1, int(round(gw * k))), max(1, int(round(gh * k)))
            src = src.resize((w, h), Image.LANCZOS)
            a = np.asarray(src, np.float32)
            cov = a[..., 3] * (a[..., :3].mean(axis=2) / 255.0) * alpha        # white glyphs on alpha: coverage
            tile = np.zeros((h, w, 4), np.uint8)
            tile[..., 0], tile[..., 1], tile[..., 2] = rgb
            tile[..., 3] = np.clip(cov, 0, 255).astype(np.uint8)
            img.alpha_composite(Image.fromarray(tile, "RGBA"), (int(round(x)), int(round(y))))
            x += gw * k
        return x
