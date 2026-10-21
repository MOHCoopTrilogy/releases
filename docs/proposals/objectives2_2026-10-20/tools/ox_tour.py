"""ox_tour.py <label> <map> "<name>:x,y,z,yaw,pitch" ...  - teleport the god-moded player to each spot and take a still (map scouting).
Run inside a harness_turn.py turn (runbatch.sh)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
spots = sys.argv[3:]
rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + LABEL, MAP, extra=["set coop_objx 0", "set g_ai 0"])
    G.cmd("god")
    print("active:", G.wait_active())
    for sp in spots:
        name, v = sp.split(":")
        x, y, z, yw, pt = [float(a) for a in v.split(",")]
        G.cmd("tp", x=x, y=y, z=z, yaw=yw, pitch=pt)
        time.sleep(1.2)
        G.still("tour_%s" % name)
        G.cmd("here")
    G.log(LABEL, "errors", G.errors()[:5])
finally:
    G.end(rundir, notes)
