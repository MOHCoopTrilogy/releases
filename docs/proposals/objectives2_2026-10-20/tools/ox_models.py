"""ox_models.py <label> <map> <x> <y> <z> <yaw> model1 model2 ... - spawn each model 170 u in front of a god player and take a still."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
label, mp, x, y, z, yaw = sys.argv[1], sys.argv[2], *[float(a) for a in sys.argv[3:7]]
models = sys.argv[7:]
rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + label, mp, extra=["set coop_objx 0", "set g_ai 0"])
    G.cmd("god")
    print("active:", G.wait_active())
    for n, m in enumerate(models):
        G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=8)
        G.cmd("spawnprop", s=m)
        time.sleep(1.2)
        G.still("model_%02d_%s" % (n, m.split("/")[-1].replace(".tik", "")))
finally:
    G.end(rundir, notes)
