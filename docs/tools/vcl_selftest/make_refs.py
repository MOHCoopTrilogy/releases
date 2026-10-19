# -*- coding: utf-8 -*-
"""make_refs.py - reference bytes from the P0 twin for vcl_selftest.c (plan 2.8 V2).

Writes into <out>:
  noise_l<k>.bin      every level of vc_render.noise_mips(make_noise(64)) as R8 bytes, in GL's layout (x fastest)
  cov_rgba.bin        the HD talonclouds TGA as RGBA8 (PIL), 2048 x 2048 - the C side converts it with R_HZM_VclGrey
  cov_grey.bin        PIL's "L" of the same (vc_assets.load_talon)
  cov_l<k>.bin        every level of vc_render.build_mips(talon, quant8=True) as R8 bytes
The twin is the P0 look-dev code in docs/proposals/volumetric_clouds_2026-09-26/p0_stills/tools; nothing here
re-implements it.
    python make_refs.py <out_dir>
"""
import io, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TW = os.path.normpath(os.path.join(HERE, "..", "..", "proposals", "volumetric_clouds_2026-09-26", "p0_stills", "tools"))
sys.path.insert(0, TW)
import vc_render as R  # noqa: E402
from vc_fs import FS  # noqa: E402


def main(out):
    os.makedirs(out, exist_ok=True)
    vol = R.make_noise(64)
    flat, offs, ns = R.noise_mips(vol)
    for k in range(len(offs)):
        n = int(ns[k])
        lv = flat[offs[k]:offs[k] + n * n * n].reshape(n, n, n)            # [i][j][k], i = u
        b = np.round(lv * 255.0).astype(np.uint8)
        np.ascontiguousarray(b.transpose(2, 1, 0)).tofile(os.path.join(out, "noise_l%d.bin" % k))   # [k][j][i]
    fs = FS()
    tag, raw = fs.read("env/hzmhd/clouds/sky/talonclouds.tga")
    im = Image.open(io.BytesIO(raw))
    np.asarray(im.convert("RGBA"), np.uint8).tofile(os.path.join(out, "cov_rgba.bin"))
    grey = np.asarray(im.convert("L"), np.uint8)
    grey.tofile(os.path.join(out, "cov_grey.bin"))
    talon = (grey.astype(np.float32) / 255.0)[..., None]
    cflat, coffs, cws, chs, _ = R.build_mips(talon)
    for k in range(len(coffs)):
        w, h = int(cws[k]), int(chs[k])
        lv = cflat[coffs[k]:coffs[k] + w * h].reshape(h, w)
        np.round(lv * 255.0).astype(np.uint8).tofile(os.path.join(out, "cov_l%d.bin" % k))
    print("refs:", out, "noise levels", len(offs), "cov levels", len(coffs), "from", tag)


if __name__ == "__main__":
    main(sys.argv[1])
