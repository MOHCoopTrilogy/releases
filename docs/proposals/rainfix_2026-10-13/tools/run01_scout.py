"""run01_scout.py <sess> <map> <x> <y> <z> <yaw> - boot the downpour on a map with the measurement cgame, scan for rooms /
alleys / high spots round a point, and print the before / after numbers at that point."""
import sys, time, os
import rainlib as L
R = L.R
CG = "C:/mohaa-coop-dev/openmohaa-hzm-rainfix/.cmake/code/client/cgame/Release/cgame.dll"
sess, mp = sys.argv[1], sys.argv[2]
P = tuple(float(v) for v in sys.argv[3:6])
YAW = float(sys.argv[6])
rundir = notes = None
try:
    rundir, notes = L.boot(sess, mp, 1600, 900, CG, "rain_stats",
                           extra=["set coop_weatherPin 4", "set coop_weatherForce rain"])
    L.log(L.tp(P, YAW, 0))
    L.log("tier len", L.wait_tier(260, 100))
    seg = L.cmd("info")
    L.log([l for l in (seg or "").splitlines() if "GQ info" in l])
    seg = L.cmd("scan", P, wait=120, step=80, half=22)
    for l in (seg or "").splitlines():
        if "GQ " in l and ("room" in l or "alley" in l or "high" in l or "scan" in l):
            L.log(l.strip())
    for name, lines in (("before", ["set coop_rainToGround 0", "set coop_rainFloor 256"]),
                        ("after", ["set coop_rainToGround 1", "set coop_rainFloor 1024"])):
        L.sets(*lines)
        time.sleep(1.5)
        st, cov = L.stats(4)
        L.log(name, L.fmt(st, cov))
        L.shot(rundir, "scout_%s_level" % name)
        L.tp(P, YAW, 30)
        L.shot(rundir, "scout_%s_down30" % name)
        L.tp(P, YAW, 0)
finally:
    L.finish(rundir, notes)
    print("RUNDIR", rundir)
