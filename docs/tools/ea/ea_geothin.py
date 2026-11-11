#!/usr/bin/env python3
"""ea_geothin - second look at geoaudit's 'invisible' contacts on a converted EA map. Our code; reads the local pak.

geoaudit calls a blocked move invisible when no drawn surface lies within 8u of the contact. Barbed wire, Czech
hedgehogs and dragon's teeth are drawn with thin strands and cards: their collision sits a few units off what is
drawn, so they all land in that class although a player sees them. Here every invisible cluster is re-tested with
finer rays: 24 short rays from the contact, fanned in plan and height (to 48u), against the DRAWN geometry; a contact
whose rays meet drawn surfaces within 40u is 'thin drawn' (visible), the rest stay invisible.

  python ea_geothin.py <pk3> <geoaudit.json> [--out report.json]
"""
import json
import math
import os
import sys

BYO = os.environ.get("BYOAUDIT", r"C:\hzm-root-flpolish\docs\tools\byoaudit")
sys.path.insert(0, BYO)
import mapgeo  # noqa: E402


def main():
    pk3, gj = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    g = json.load(open(gj))
    M = mapgeo.MapGeo.load(pk3, "coop_ea_1_11")
    thin, inv = [], []
    for (x, y, z), n in g["invisible_clusters"]:
        hit = M.render_near((x, y, z + 40), 20.0)
        if not hit:
            for k in range(24):
                a = 2 * math.pi * (k % 8) / 8
                h = (28, 44, 60)[k // 8]
                p = (x + 40 * math.cos(a), y + 40 * math.sin(a), z + h)
                if M.render_near(p, 12.0):
                    hit = True
                    break
        (thin if hit else inv).append(((x, y, z), n))
    rep = {"clusters": len(g["invisible_clusters"]), "contacts": sum(n for _p, n in g["invisible_clusters"]),
           "thin_drawn_clusters": len(thin), "thin_drawn_contacts": sum(n for _p, n in thin),
           "invisible_clusters": len(inv), "invisible_contacts": sum(n for _p, n in inv),
           "invisible_list": sorted(inv, key=lambda c: -c[1])[:60]}
    if out:
        json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "invisible_list"}))
    print("top invisible:", rep["invisible_list"][:12])


if __name__ == "__main__":
    main()
