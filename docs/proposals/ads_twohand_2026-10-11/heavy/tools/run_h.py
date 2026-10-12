"""Heavy lane harness runs on OUR test copy (G:\\mohaa-adsanim4, owner "adsanim4", net_port 12598, DISPLAY2, never
focused). The pistol lane's run_2h.py is used as a library and repointed - its parts, flags and capture format are
unchanged (see its docstring):

    python run_h.py <session> --overlay <abs pk3> --cgame cgame_heavy0 --guns bar,dp28 --parts yaw,stills --yaws 165
The session log goes to SCRATCH/adsheavy/run.log, the frames to G:/mohaa-adsanim4/runs/<session>/.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
sys.path.insert(0, hv.SHARED)
import run_2h as T2                       # imports run_adsbolt (A) -> run_sweep (S) -> run_ironsights (R); chdirs to BOLT
A, S, R = T2.A, T2.S, T2.R
R.OWNER = hv.OWNER
R.CLIENT = hv.CLIENT
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = hv.RUNS
R.PORT = hv.PORT
A.LOGF = os.path.join(hv.SCR, "run.log")
A.GUNS.update({"30cal": "models/weapons/30calportable.tik", "mg42": "models/weapons/mg42portable.tik",
               "mp44scope": "models/weapons/mp44_scoped.tik"})

if __name__ == "__main__":
    assert R.CLIENT.lower().endswith("adsanim4") and R.PORT == 12598
    # lane extras (taken out before the shared parser sees them):  --map <name> --spot x,y,z,yaw   another map / spot,
    # e.g. the night map m4l1 at its player start: --map m4l1 --spot -3904,-6120,-456,45
    # --pitch <deg, + = down>: the view pitch every `give` sets. 20 rounds of automatic fire walk the view up 8.5 deg
    # (run hb4: the centre box ended on the dark timber beam, where a dark gun cannot be told from the background and
    # the box measure is void) - start that much lower and the emptied gun reloads on the light wall.
    for opt in ("--map", "--spot", "--pitch"):
        if opt in sys.argv:
            k = sys.argv.index(opt)
            val = sys.argv[k + 1]
            del sys.argv[k:k + 2]
            if opt == "--map":
                R.MAP = val
            elif opt == "--spot":
                R.SPOT = tuple(float(x) for x in val.split(","))
            else:
                _give, _p = R.give, float(val)
                R.give = lambda tik, pitch=0.0: _give(tik, _p if pitch == 0.0 else pitch)
    T2.main()
