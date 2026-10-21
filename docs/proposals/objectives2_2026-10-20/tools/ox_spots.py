"""ox_spots.py <label> <map> - in-game stills of every placed item of one map (placement audit evidence).
Boots the map, waits for the intro to end, force-activates every objective (so all props stand) and takes 3 stills per item
from 230 u east / north / west of it, aimed at the item. Output runs/ox_<label>/spot_<obj>_<kind><n>_<view>.jpg"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OBJS = json.load(open("C:/mohaa-coop-dev/docs/tools/objx_points.json", encoding="utf-8"))[MAP]["objectives"]
rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + LABEL, MAP, extra=["set g_ai 0", "set coop_objxFailsafe 900"])
    G.cmd("god")
    print("active:", G.wait_active())
    for i in range(1, len(OBJS) + 1):
        G.cmd("force", k=i)
    time.sleep(8)
    for i, o in enumerate(OBJS, 1):
        for n, it in enumerate(o.get("items", []), 1):
            pos = it.get("prop_pos") if it["kind"] == "actor" and it.get("prop_pos") else it["pos"]
            cams = {}
            if it.get("spot_cams"):
                for ci, c in enumerate(it["spot_cams"]):
                    cams["C%d" % ci] = (c[0] - pos[0], c[1] - pos[1], 0, c[2] - pos[2] - 28)
            else:
                cams = {"E": (230, 0, 180, 0), "N": (0, 230, 270, 0), "W": (-230, 0, 0, 0)}
            for view, (dx, dy, yw, dz) in cams.items():
                G.cmd("tp", x=pos[0] + dx, y=pos[1] + dy, z=pos[2] + 28 + dz, yaw=yw, pitch=3)
                G.cmd("aim", x=pos[0], y=pos[1], z=pos[2] + 50)
                time.sleep(0.9)
                G.still("spot_%s_%s%d_%s" % (o["id"], it["kind"], n, view))
    G.cmd("props")
except Exception as e:
    import traceback
    print("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)
