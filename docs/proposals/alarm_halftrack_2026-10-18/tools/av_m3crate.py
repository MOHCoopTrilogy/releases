import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
rundir = notes = None
try:
    rundir, notes = G.boot("av_m3crate", "m3l3", extra=["set g_ai 0"])
    G.cmd("pin", x="1601", y="-2420", z="-277", lx="-2837", ly="-3005", lz="-215")
    time.sleep(1.5)
    G.still("m3crate_to_stop_a")
    G.cmd("pin", x="1601", y="-2420", z="-277", lx="-1500", ly="-2800", lz="-215")
    time.sleep(1)
    G.still("m3crate_to_stop_b")
except Exception as e:
    G.log("m3crate", "FAILED", repr(e))
finally:
    G.end(rundir, notes)
