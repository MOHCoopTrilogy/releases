#!/usr/bin/env python3
"""ea_sheetiter - curate ea_levels.json "clip_keep" with the walk audit (the Frontline polish sheetiter recipe).
Our code; writes only triangle INDEXES (no disc data) into ea_levels.json.

Loop: convert -> geoaudit -> every dropped clip sheet within R of a void fall (the walker left the world there)
joins clip_keep -> repeat until no void falls or nothing changes.

  python ea_sheetiter.py <iso> <workdir> [--rounds 4] [--radius 320]
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BYO = os.environ.get("BYOAUDIT", r"C:\hzm-root-flpolish\docs\tools\byoaudit")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"


def main():
    iso, work = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 4
    rad = float(sys.argv[sys.argv.index("--radius") + 1]) if "--radius" in sys.argv else 320.0
    os.makedirs(work, exist_ok=True)
    spec_p = os.path.join(HERE, "ea_levels.json")
    for it in range(rounds):
        pk = os.path.join(work, "it%d.pk3" % it)
        rp = os.path.join(work, "it%d.json" % it)
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "run_isolated.py"), "flconvert.py", iso, "1_11", pk,
                        "--game", "ea", "--mohaa", GOG, "--report", rp], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        od = os.path.join(work, "geo%d" % it)
        subprocess.run([sys.executable, os.path.join(BYO, "geoaudit.py"), pk, "coop_ea_1_11", od], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        g = json.load(open(os.path.join(od, "geoaudit.json")))
        r = json.load(open(rp))
        voids = [c for c, _n in g["void_clusters"]]
        dropped = r["stats"].get("sheets_dropped", [])
        add = set()
        for ident, cen in dropped:
            if any(math.hypot(cen[0] - v[0], cen[1] - v[1]) < rad and abs(cen[2] - v[2]) < 600 for v in voids):
                add.add(ident[0])
        spec = json.load(open(spec_p))
        keep = set(spec["1_11"].get("clip_keep", []))
        print("round", it, "void_falls", g["summary"]["void_falls"], "invisible", g["summary"]["blocked_moves"].get("invisible"),
              "dropped", len(dropped), "keep", len(keep), "+", len(add - keep), flush=True)
        if not voids or not (add - keep):
            break
        spec["1_11"]["clip_keep"] = sorted(keep | add)
        spec["1_11"]["_clip_keep_doc"] = ("collision triangle indexes (level .cdb order) of floating clip sheets that hold a "
                                          "level edge: kept, drawn as a barbed-wire edge (docs/tools/ea/ea_sheetiter.py)")
        json.dump(spec, open(spec_p, "w"), indent=1)


if __name__ == "__main__":
    main()
