import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
SP = [(4020,-3160),(4020,-3400),(4020,-3656),(4020,-2936),(4244,-3400),(4244,-2936),(3796,-2936),(4020,-4136),(4244,-4376),(4020,-4888)]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=["set coop_objx 0"])
    G.cmd("god"); time.sleep(2)
    # objx off: no $mesh_gate level vars; drive the gate directly
    for x, y in SP:
        G.cmd("tp", x=3440, y=-3300, z=-505, yaw=0, pitch=0)
        for k in (0, 1):
            pass
        p0 = G.cmd("rgset", k=1)
        p1 = G.cmd("aitest", x=x, y=y, z=-490, yaw=3560, pitch=-3300, k=-496)
        t0 = time.time(); last = None
        for i in range(10):
            time.sleep(2.0)
            p2 = G.cmd("aipos"); r = G.since(p2, r"\^~\^~\^ OX aipos \( ([-\d.]+) ([-\d.]+)")
            if r:
                last = (float(r[0][0]), float(r[0][1]))
                if last[0] < 3600: break
        log("SPOT", (x, y), "after %.0fs" % (time.time() - t0), "pos", last, "REACHED gate side" if last and last[0] < 3640 else "NOT through")
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
