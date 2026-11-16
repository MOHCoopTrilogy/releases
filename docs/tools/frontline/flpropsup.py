#!/usr/bin/env python3
"""OPTIONAL local HD pass for the converted Frontline PROP textures (flprops.py output, textures/fl_<level>_props/
<hash>.tga) - runs on the PLAYER's PC only, after the conversion, the European Assault prop recipe (eapropsup.py:
ESRGAN x4 via eacharup.upscale_one, CC0 colourless fine grain, markings resampled only). Output: its own pak
(zzzz_fl_hdprops_<level>.pk3) overriding the map pak's prop TGAs by load order.

Per texture (keyed by the md5[:8] of the disc image, the name flprops writes), chosen 2026-11-15 on a side-by-side of
disc | bicubic | ESRGAN | CC0 grain (user: "upscale the Frontline tank and everything else ... higher quality online
content where possible if it doesn't look bad"):
  * steel (hull, turret, gun, destroyed set): ESRGAN is no better than bicubic on these, so the CC0 painted-steel
    grain (ambientCG PaintedMetal005 + Metal016) over the disc picture; the Balkenkreuze resampled only
  * road wheels, sprockets, tracks: ESRGAN (the grain left a seam on the 32 px wheels)
  * cut-outs / blended cards: resampled only
usage: flpropsup.py <converted.pk3> <level> <out_pk3> <upscaler_dir>
"""
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(HERE, "..", "ea"), os.path.join(HERE, "ea")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)
import numpy as np            # noqa: E402
from PIL import Image         # noqa: E402
import eacharup               # noqa: E402
import eapropsup              # noqa: E402

ZIP_TIME = (2002, 5, 28, 0, 0, 0)
STEEL = [("PaintedMetal005", 3.5, 2.0, (1, 1)), ("Metal016", 2.5, 1.2, (1, 1))]
STEEL_KEYS = ("e1ecd680", "fee481ff", "b07b1c51", "a6c97ede", "724b58e1", "cbf1f409", "91d20a46", "3671a2f7",
              "8e1a0f98", "4a320455", "d84b48cb", "a018a4a9", "8e75b3ac")
PROTECT = {"fee481ff": [(0.6, 0.52, 0.85, 0.8)], "b07b1c51": [(0.44, 0.0, 0.64, 0.18)],
           "8e1a0f98": [(0.44, 0.0, 0.64, 0.18)]}
ESRGAN_KEYS = ("317971c7", "76f48835", "9362be6e", "aac16783", "c3961048", "dd715eff", "ff479a21", "0262ef25",
               "e1797701", "71d56509", "c32cdc11", "0262ef25")


def process(key, a, exe, tmp):
    h, w = a.shape[:2]
    bic = np.asarray(Image.fromarray(a).resize((w * 4, h * 4), Image.BICUBIC))
    if a[..., 3].min() < 250:
        return bic, "kept (cut-out, bicubic)"
    if key in STEEL_KEYS:
        b = bic.astype(np.float32)
        for name, amp, sig, reps in STEEL:
            b = eapropsup._detail(b, name, amp, sig, reps)
        b = b.clip(0, 255).astype(np.uint8)
        for x0, y0, x1, y1 in PROTECT.get(key, ()):
            X0, Y0, X1, Y1 = int(x0 * w * 4), int(y0 * h * 4), int(x1 * w * 4), int(y1 * h * 4)
            b[Y0:Y1, X0:X1] = bic[Y0:Y1, X0:X1]
        return b, "ok cc0 steel"
    if key in ESRGAN_KEYS and exe:
        up, why = eacharup.upscale_one(exe, a, [], tmp)
        return (up, "ok esrgan") if up is not None else (None, why)
    return None, "no recipe"


def main(pk3, level, out_pk3, exe_dir):
    exe = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe") if exe_dir else None
    if exe and not os.path.exists(exe):
        exe = None
    z = zipfile.ZipFile(pk3)
    pre = "textures/fl_%s_props/" % level
    tmp = tempfile.mkdtemp(prefix="flpropsup_")
    report, files = {}, {}
    for n in sorted(x for x in z.namelist() if x.startswith(pre) and x.endswith(".tga")):
        key = n.rsplit("/", 1)[-1][:-4]
        try:
            res, why = process(key, eacharup.load_tga(z.read(n)), exe, tmp)
        except Exception as e:  # never fail the conversion
            res, why = None, "error %s" % e
        report[key] = why
        if res is not None:
            files[n] = eacharup.save_tga(res)
    if files:
        with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED) as o:
            for n in sorted(files):
                zi = zipfile.ZipInfo(n, ZIP_TIME)
                zi.compress_type = zipfile.ZIP_DEFLATED
                o.writestr(zi, files[n])
    with open(out_pk3 + ".report.json", "w") as f:
        json.dump(report, f, indent=0, sort_keys=True)
    print("FL props HD", sum(1 for v in report.values() if v.startswith(("ok", "kept"))), "of", len(report), "->", out_pk3)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else None)
