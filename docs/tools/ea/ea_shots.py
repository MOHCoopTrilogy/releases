#!/usr/bin/env python3
"""ea_shots - stills of coop_ea_1_11 at named views, for visual QA of the converted smart objects, trigger areas
and set pieces. Our code; stills contain converted disc content: LOCAL ONLY.

  python ea_shots.py <outdir> <views.json> [--sp] [--sets k=v ...]
views.json: [["name", x, y, z, pitch, yaw], ...] (z = the eye's feet position, as tele takes it)
Private client: byoaudit's byoclient (BYO_CLIENT, default G:\\mohaa-ea), launched only through harness_window, on
the 1080p screen while the user's game runs; muted, no pad, in_mouse 0; cursor clips outside our display ignored
(ea_aiaudit's rule).
"""
import json
import os
import sys
import time

BYO = os.environ.get("BYOAUDIT", r"C:\hzm-root-flpolish\docs\tools\byoaudit")
sys.path.insert(0, BYO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("BYO_CLIENT", r"G:\mohaa-ea")
import ea_aiaudit  # noqa: E402,F401  (installs the user-clip filter on byoclient.Client.check)
import byoclient   # noqa: E402


def main():
    out, vf = sys.argv[1], sys.argv[2]
    sets = [tuple(a.split("=", 1)) for a in sys.argv[3:] if "=" in a]
    views = json.load(open(vf))
    os.makedirs(out, exist_ok=True)
    with byoclient.Client("coop_ea_1_11", sets=[("coop_eatest", "0")] + sets, coop="--sp" not in sys.argv,
                          w=960, h=540, port=int(os.environ.get("BYO_PORT", "12488"))) as c:
        if not c.wait(r"EAAI |Spawning Entities Done", 300):
            raise RuntimeError("map never loaded")
        time.sleep(10)
        if "--sp" not in sys.argv:
            c.join()
        time.sleep(6)
        c.step(["noclip", "wait 5", "god", "wait 5", "notarget", "wait 5", "cg_drawviewmodel 0", "cg_hud 0",
                "ui_hud 0"])
        for name, x, y, z, p, yw in views:
            c.check()
            # the move and the still are separate steps: one cfg with both took the still a view late now and then
            c.step(["tele %.0f %.0f %.0f" % (x, y, z), "wait 12", "tele %.0f %.0f %.0f" % (x, y, z), "wait 3",
                    "face %.1f %.1f 0" % (p, yw), "wait 60"])
            time.sleep(float(os.environ.get("EA_SHOT_SETTLE", "1.5")))
            c.step(["screenshot ea_" + name, "wait 12"])
            c.grab("ea_" + name, out)
        c.keep_log(os.path.join(out, "qconsole.log"))
    print("stills:", len(views))


if __name__ == "__main__":
    main()
