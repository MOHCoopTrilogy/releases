# -*- coding: utf-8 -*-
"""Shared loader for the previews: the player stack, m3l2's BSP, the shader -> first-stage image table, and the
LIVE winning image for each base in engine order (.dds first - r_ext_compressed_textures 1 - then .jpg, .tga).
Overrides (candidate textures) are passed as {image base: HxWx3 uint8}."""
import io, os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "tools")))
import gen_terrain_pak_v3 as V3          # noqa: E402
import gen_terrain_pak_v2 as V2          # noqa: E402
import analyze_m3l2 as A                 # noqa: E402
import groundview as G                   # noqa: E402

_ST = None
_DEFS = None


def stack():
    global _ST
    if _ST is None:
        _ST = V3.Stack(A.GOG)
    return _ST


def defs():
    global _DEFS
    if _DEFS is None:
        _DEFS = A.winning_shader_defs(stack())
    return _DEFS


def first_image(shader):
    d = defs().get(shader)
    if d is None:
        return shader
    for ln in d[2].split("\n"):
        t = re.sub(r"//.*", "", ln).split()
        if len(t) >= 2 and t[0].lower() in ("map", "clampmap") and not t[1].startswith("$"):
            return V3.strip_ext(t[1].lower().replace("\\", "/"))
        if len(t) >= 3 and t[0].lower() == "animmap":
            return V3.strip_ext(t[2].lower())
    return shader


def decode(b, ext):
    if ext == ".dds" and b[84:88] == b"DX10":
        return np.asarray(Image.open(io.BytesIO(b)).convert("RGB"))
    if ext == ".dds":
        info = V2.dds_parse(b)
        return np.asarray(V2.dds_decode_level(b, info, 0)[..., :3], np.uint8)
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGB"))


def live_image(base, skip=()):
    """-> (rgb, 'pak member') of the image the engine loads, or (None, None)."""
    st = stack()
    for ext in (".dds", ".jpg", ".tga", ".png"):
        w = st.winner(base + ext, skip=skip)
        if w:
            i, m = w
            return decode(st.read(i, m), ext), "%s:%s" % (st.name(i), m)
    return None, None


class TexCache:
    def __init__(self, overrides=None, skip=()):
        self.over = {k: G.pyramid(v) for k, v in (overrides or {}).items()}
        self.cache, self.skip, self.src = {}, skip, {}

    def __call__(self, shader):
        im = first_image(shader)
        if im in self.over:
            return self.over[im]
        if im not in self.cache:
            rgb, src = live_image(im, self.skip)
            self.cache[im] = G.pyramid(rgb) if rgb is not None else None
            self.src[im] = src
        return self.cache[im]


def bsp(name="maps/m3l2.bsp"):
    st = stack()
    i, m = st.winner(name)
    return st.read(i, m)
