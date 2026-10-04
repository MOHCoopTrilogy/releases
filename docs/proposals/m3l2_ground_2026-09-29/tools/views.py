# -*- coding: utf-8 -*-
"""Named preview cameras on m3l2 (and other maps) + a renderer that takes texture overrides.

    python views.py OUTDIR [--only name,name] [--over base=png ...] [--tag before]
Eye = ground under the camera + 82 (MOHAA standing view height). Single process.
"""
import argparse, os, sys, time
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene as SC, groundview as G   # noqa: E402

# name: (map, x, y, yaw, pitch, region half-size)
CAMS = {
    "m3l2_barn_front":  ("maps/m3l2.bsp", -6250, -6250, 180, 14, 1700),
    "m3l2_barn_wide":   ("maps/m3l2.bsp", -6000, -6980, 128, 9, 1900),
    "m3l2_court_front": ("maps/m3l2.bsp", -3700, 2150, 90, 14, 1700),
    "m3l2_court_wide":  ("maps/m3l2.bsp", -3620, 1640, 90, 8, 1900),
    "m3l2_road":        ("maps/m3l2.bsp", -4700, 1440, 0, 9, 2200),
    "m3l2_lane":        ("maps/m3l2.bsp", -2850, 1700, 90, 10, 1900),
}


def ground_z(w, x, y):
    gx, gy = int((x - w.region[0]) / w.res), int((y - w.region[1]) / w.res)
    z = w.Z[max(0, gy - 3):gy + 4, max(0, gx - 3):gx + 4]
    z = z[z > -1e8]
    return float(np.median(z)) if z.size else 0.0


_WORLDS = {}


BSP_OVERRIDE = {}      # map -> patched bytes (the proposal)
import bsp_patch as _BP   # noqa: E402
TCGEN = _BP.tcgen_vectors(SC.bsp("maps/m3l2.bsp"))


def world_for(cam):
    mp, x, y, yaw, pitch, R = CAMS[cam]
    b = BSP_OVERRIDE.get(mp) or SC.bsp(mp)
    key = (mp, x, y, R, hash(b[:64]) ^ len(b))
    if key not in _WORLDS:
        _WORLDS[key] = G.World(b, (x - R, y - R, x + R, y + R), res=2.0, zmax=ground_zmax(cam), tcgen=TCGEN)
    return _WORLDS[key]


ZMAX = {"m3l2_barn_front": -100.0, "m3l2_barn_wide": -100.0}


def ground_zmax(cam):
    return ZMAX.get(cam, 60.0)


def render(cam, texcache, size=(1280, 720), fov=80.0):
    mp, x, y, yaw, pitch, R = CAMS[cam]
    w = world_for(cam)
    z = ground_z(w, x, y) + 82.0
    return w.render(texcache, (x, y, z), yaw, pitch, fov=fov, size=size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--only")
    ap.add_argument("--over", nargs="*", default=[])
    ap.add_argument("--tag", default="live")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    over = {}
    for o in a.over:
        k, p = o.split("=", 1)
        over[k] = np.asarray(Image.open(p).convert("RGB"))
    tc = SC.TexCache(over)
    for cam in (a.only.split(",") if a.only else CAMS):
        t = time.time()
        img = render(cam, tc)
        im = Image.fromarray(img)
        ImageDraw.Draw(im).text((8, 8), "%s  [%s]  headless ground preview (no models/buildings)" % (cam, a.tag),
                                fill=(255, 255, 0))
        im.save(os.path.join(a.out, "%s_%s.jpg" % (cam, a.tag)), quality=90)
        print(cam, "%.1fs" % (time.time() - t))


if __name__ == "__main__":
    main()
