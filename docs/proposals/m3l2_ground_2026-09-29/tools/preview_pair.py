# -*- coding: utf-8 -*-
"""Headless before/after pairs: LIVE stack vs the proposal (patched m3l2.bsp + new textures), same cameras.
    python preview_pair.py GENDIR OUTDIR [--only cams] [--barnyard]
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene as SC, views as VW, bsp_patch as BP   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gen")
    ap.add_argument("out")
    ap.add_argument("--only")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fy = np.asarray(Image.open(os.path.join(a.gen, "farmyard.png")).convert("RGB"))
    rd = np.asarray(Image.open(os.path.join(a.gen, "road.png")).convert("RGB"))
    live = SC.TexCache()
    prop = SC.TexCache({"textures/hzm_m3l2/farmyard": fy, "textures/hzm_m3l2/farmyard_b": fy, "textures/hzm_m3l2/road": rd})
    orig = SC.bsp("maps/m3l2.bsp")
    new, info = BP.patch(orig)
    print(BP.verify(orig, new))
    cams = a.only.split(",") if a.only else [c for c in VW.CAMS if c.startswith("m3l2")]
    for cam in cams:
        VW.BSP_OVERRIDE.clear()
        before = VW.render(cam, live)
        VW.BSP_OVERRIDE["maps/m3l2.bsp"] = new
        after = VW.render(cam, prop)
        h, w = before.shape[:2]
        pair = Image.new("RGB", (w, h * 2 + 4), (0, 0, 0))
        pair.paste(Image.fromarray(before), (0, 0))
        pair.paste(Image.fromarray(after), (0, h + 4))
        d = ImageDraw.Draw(pair)
        d.text((8, 8), cam + "  BEFORE (live stack)  - headless ground preview, no models", fill=(255, 255, 0))
        d.text((8, h + 12), cam + "  AFTER (proposal)", fill=(255, 255, 0))
        pair.save(os.path.join(a.out, cam + ".jpg"), quality=90)
        print(cam)


if __name__ == "__main__":
    main()
