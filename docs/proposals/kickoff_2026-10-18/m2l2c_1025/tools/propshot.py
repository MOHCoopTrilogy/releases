"""propshot.py <map> <name> <px> <py> <pz> <tx> <ty> <tz> - activate the objectives, stand at p looking at t, take a still"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
mp, name = sys.argv[1:3]
px, py, pz, tx, ty, tz = [float(v) for v in sys.argv[3:9]]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_psh_" + name, mp, extra=["set coop_objxFailsafe 900"])
    G.cmd("god"); time.sleep(40)
    G.cmd("objact", timeout=60); time.sleep(8)
    G.cmd("tp", x=px, y=py, z=pz, yaw=0, pitch=0); G.cmd("aim", x=tx, y=ty, z=tz); time.sleep(1.0)
    G.still("m2_psh_" + name)
finally:
    if rundir: G.end(rundir, notes)
