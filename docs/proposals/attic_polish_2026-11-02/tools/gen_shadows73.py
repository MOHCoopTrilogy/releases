"""gen_shadows73.py <base menus3d pk3> <add dir> - v1.10.73: the rack's (MP room) and the projector screen's (attic) soft wall
shadows become visible.

Both were multiply decals (blendFunc GL_DST_COLOR GL_ZERO), which draw nothing in the menu Scene3D (bug-10768; the posters'
shadows were moved off it in v1.10.69). A sweep of every shader in the v1.10.72 pak (3343a976) found exactly two SINGLE-stage
multiplies - these two. The other GL_DST_COLOR GL_ZERO / filter stages in the pak are the second stage of a two-stage
texture * lightmap shader (hzm_atc_floor, hzm_hub_floor, the board / plaque faces) and draw (the dst is the shader's own first
stage); they are left alone.

Writes into <add dir> (for polish_pak.py): textures/menu/hzm_hub_rackshade.tga, textures/menu/hzm_proj_screenshade.tga
(shade73.py, the same images gen_attic68_props.py now writes) and scripts/hzm_attic68.shader = the base pak's file with ONLY
those two shader bodies replaced (asserted). The models are untouched: their surfaces already name these shaders; the halo
images are painted in those models' decal quads (asserted against the base pak) - see shade73.py for why a plain blend alone
changed no pixel.
"""
import os, re, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shade73 import RACK, SCREEN, shade_halo, shade_shader  # noqa: E402

base, add = sys.argv[1:3]
SHP = "scripts/hzm_attic68.shader"
ZB = zipfile.ZipFile(base)
txt = ZB.read(SHP).decode("latin1")
# the halo is painted in the decal quad's own world rectangle: it must still be the quad in the base pak's models
import numpy as np  # noqa: E402
import skd_read as R  # noqa: E402
for mdl, surf, spec in (("hzm_hub_rackshadow", 0, RACK), ("hzm_proj_screen", 1, SCREEN)):
    s = R.read_skd(ZB.read("models/menu/%s.skd" % mdl))["surfaces"][surf]
    P = np.array([v[3] for v in s["verts"]])
    got = (P[:, 0].min(), P[:, 0].max(), P[:, 2].min(), P[:, 2].max())
    assert np.allclose(got, spec["quad"], atol=0.15), (mdl, got, spec["quad"])
os.makedirs(os.path.join(add, "scripts"), exist_ok=True)
os.makedirs(os.path.join(add, "textures", "menu"), exist_ok=True)
for name, tex, spec in (("hzm_hub_rackshadow", "hzm_hub_rackshade", RACK),
                        ("hzm_proj_screenshadow", "hzm_proj_screenshade", SCREEN)):
    pat = re.compile(r"(?m)^%s\n\{\n.*?\n\}" % re.escape(name), re.S)
    m = pat.findall(txt)
    assert len(m) == 1 and "GL_DST_COLOR GL_ZERO" in m[0], (name, m)
    txt = pat.sub(lambda _: shade_shader(name, tex), txt)
    shade_halo(os.path.join(add, "textures", "menu", tex + ".tga"), spec)
assert "GL_DST_COLOR GL_ZERO" not in txt
open(os.path.join(add, SHP), "w", newline="\n", encoding="latin1").write(txt)
print("shadows73: 2 shaders -> blendFunc blend, 2 tgas ->", add)
