#!/usr/bin/env python3
"""visaudit - SEE-THROUGH audit of a converted own-disc map (offline, our code; reads the local pak only).

From viewpoints along every walkable route (the crouch flood of geoaudit, one point per --spacing) and every AI path
point, at stand / crouch / prone eye height (82 / 48 / 16), rays are cast in a fan of directions at and below the
horizon (24 azimuths x elevations -2, -8, -20, -45, -89). A ray that meets NO drawn surface before the farplane is a
view into the void / under the map / out of the world (above the horizon the sky box is meant to be seen, so those are
not cast). Also reported: drawn surfaces whose shader is a converter fallback (untextured / missing texture).

  python visaudit.py <pk3> <map> <outdir> [--spacing 192] [--png]
Results: visaudit.json with flagged viewpoint clusters (position, height, direction) - the zero-target metric is
`flagged_rays`.
"""
import argparse
import collections
import json
import math
import os
import sys
import time
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapgeo  # noqa: E402
import geoaudit  # noqa: E402

EYES = (("stand", 82.0), ("crouch", 48.0), ("prone", 16.0))
ELEV = (-2.0, -8.0, -20.0, -45.0, -89.0)
NAZ = 24


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pk3")
    ap.add_argument("map")
    ap.add_argument("outdir")
    ap.add_argument("--spacing", type=float, default=192.0)
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(a.outdir, exist_ok=True)
    M = mapgeo.MapGeo.load(a.pk3, a.map)
    ws = next((e for e in M.entities if e.get("classname") == "worldspawn"), {})
    farplane = float(ws.get("farplane", "0") or 0) or 8000.0
    spawns = [tuple(map(float, e["origin"].split())) for e in M.entities
              if e.get("classname") in ("info_player_start", "info_player_allied", "info_player_deathmatch")]
    seeds = []
    for s in spawns:
        z, _n, _b = M.ground(s[0], s[1], s[2] + 8, s[2] - 512)
        if z is not None:
            seeds.append((s[0], s[1], z))
    seen, *_ = geoaudit.flood(M, seeds, 16.0, mapgeo.CROUCH_H)
    step = max(1, int(a.spacing // 16))
    vps = [(k[0] * 16.0, k[1] * 16.0, z) for k, z in seen.items() if k[0] % step == 0 and k[1] % step == 0]
    for e in M.entities:
        if e.get("classname") == "info_pathnode":
            p = tuple(map(float, e["origin"].split()))
            g = M.ground(p[0], p[1], p[2] + 8, p[2] - 64, mapgeo.CROUCH_H)[0]
            if g is not None:
                vps.append((p[0], p[1], g))
    dirs = []
    for el in ELEV:
        for k in range(NAZ if el > -80 else 1):
            az = 2 * math.pi * k / NAZ
            ce = math.cos(math.radians(el))
            dirs.append((ce * math.cos(az), ce * math.sin(az), math.sin(math.radians(el))))
    dirs = np.array(dirs)
    O, D, meta = [], [], []
    for i, (x, y, z) in enumerate(vps):
        for nm, h in EYES:
            for j, d in enumerate(dirs):
                O.append((x, y, z + h))
                D.append(d)
                meta.append((i, nm, j))
    O = np.array(O)
    D = np.array(D)
    dist = mapgeo.cast_many(M, O, D, farplane)
    bad = np.nonzero(dist < 0)[0]
    flagged = collections.Counter()
    pts = []
    for r in bad:
        i, nm, j = meta[r]
        flagged[nm] += 1
        x, y, z = vps[i]
        d = dirs[j]
        pts.append((x, y, z))
    cl = sorted(geoaudit.cluster(pts, 128), key=lambda c: -c[1])
    # fallback shaders drawn anywhere (untextured / missing texture)
    z = zipfile.ZipFile(a.pk3)
    fb = set()
    for nm, sf, cf in M.shaders:
        if nm.endswith("/untextured"):
            fb.add(nm)
    fb_tris = int(sum(1 for s in M.rshader if M.shaders[s][0] in fb))
    rep = {"viewpoints": len(vps), "rays": int(len(O)), "farplane": farplane, "flagged_rays": int(len(bad)),
           "flagged_by_eye": dict(flagged), "flagged_viewpoints": len(set(meta[r][0] for r in bad)),
           "flagged_clusters": len(cl), "clusters": cl[:300], "fallback_shader_tris": fb_tris,
           "seconds": round(time.time() - t0, 1)}
    json.dump(rep, open(os.path.join(a.outdir, "visaudit.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "clusters"}, indent=1))
    print("top clusters:", cl[:15])
    if a.png:
        from PIL import Image, ImageDraw
        lo, hi = M.lo, M.hi
        W = 2400
        s = W / max(hi[0] - lo[0], hi[1] - lo[1])
        H = int((hi[1] - lo[1]) * s) + 1
        im = Image.new("RGB", (W, H))
        dr = ImageDraw.Draw(im)
        for t in M.rtri[::2]:
            dr.polygon([((p[0] - lo[0]) * s, H - (p[1] - lo[1]) * s) for p in t], fill=(38, 38, 38))
        for x, y, zz in vps:
            dr.point(((x - lo[0]) * s, H - (y - lo[1]) * s), fill=(0, 120, 0))
        for (x, y, zz), n in cl:
            px, py = (x - lo[0]) * s, H - (y - lo[1]) * s
            r = 2 + min(10, n // 4)
            dr.ellipse((px - r, py - r, px + r, py + r), outline=(255, 0, 0))
        im.save(os.path.join(a.outdir, "visaudit.png"))


if __name__ == "__main__":
    main()
