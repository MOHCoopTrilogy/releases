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
               "mp44gold": "models/weapons/mp44_gold.tik",
               "mp44strap": "models/weapons/mp44_mp44strap.tik",
               # the other BAR meshes (bug-3623): retail mesh / the Pacific pack's S93 skeleton on its own path
               "sggold": "models/weapons/shotgun_gold.tik", "sgcamo": "models/weapons/shotgun_camo_winter.tik",
               "sgchrome": "models/weapons/shotgun_chrome.tik",
               "dp28": "models/weapons/dp28.tik", "fg42": "models/weapons/FG42.tik",
               "bar1918a": "models/weapons/bar_bar1918a.tik", "barpa": "models/weapons/bar_pabar.tik"})

def stdemo(sess, gun, st, shots, gap, nrel, empty):  # TAIL: see below
    """LANE part (--stdemo st,st,..): the aimed reload in a stance as a DENSE capture that boxeng.py can measure - the
    shared `reloads` part is sparse and cannot empty the gun (an emptied gun reloads by itself during its wait).
    Tag ab__<sess>__<gun>__<st>__demo__after, marks DEMO reload / lower, the model-less reference `__ref`; the
    firing phase is NOT captured (frame index = file index from the reload on)."""
    tag = "ab__%s__%s__%s%s__demo__after" % (sess, gun, st, "hip" if STHIP else "")
    i = [0]
    # --sthip: the same capture from the HIP (no aim key) - a hand-cycled gun emptied press by press (the SMG lane's
    # hip demo holds the trigger, which fires a pump gun once)
    L = S.RELEASE + S.TO_STAND + S.APPLY[st] + A.MODE["after"] + ["wait 400"] + ([] if STHIP else ["+button13"]) + ["wait 1700"]
    L += ["coop_braceView"] if st == "braced" else []
    L += ["wait 300", "set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    REF = ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",
           "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]
    L += A.frames(tag, 4, i)
    for k in range(shots):
        last = k == shots - 1
        L += ["+attackprimary", "wait 1", "wait 1", "wait 1", "wait 1", "wait 1", "wait 1", "-attackprimary"]
        # rounds left: 200 frames (3.2 s) after the last shot - the recoil of a heavy gun recovers for seconds and the
        # ADS rig solve is HELD in whatever state the reload starts in (bug-3597; run hc3: 4-7 % 'extra' at both ends)
        L += ["wait 1", "wait 1"] * ((11 if empty else 200) if last else gap)
    if not empty:
        L += REF + ["reload"]
    L += ["echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, nrel, i)
    if empty:
        L += REF
    if TAIL[0]:
        # --tail N[:step] (sway-on runs): the settled aim for N more game frames, every step-th captured, then 10 dense
        # ones (the aim mask's own frames) - one whole sway / breath period (5.7 s = 357 frames) for boxeng.py --sway
        L += ["echo ^~^~^ DEMO settle %d" % i[0]]
        for k in range(TAIL[0] // TAIL[1]):
            L += A.frames(tag, 1, i) + ["wait 1", "wait 1"] * (TAIL[1] - 1)
        L += A.frames(tag, 10, i)
    L += ["-button13", "echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 24, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"]
    L += ["coop_braceView"] if st == "braced" else []
    L += S.RELEASE + A.UNAPPLY[st]
    R.step(L, timeout=2400)


# The SMG lane's captures as they are (smg/tools/smg_block.py is source that its runner inlines; executed here it binds
# to OUR S / A / R): sbreak = an aimed reload broken off (fire / switch / sprint / drop), sdemo(ads=False) = the hip
# reload, rounds left (L) or emptied (E; SMG_HOLD = frames the trigger is held, --hold).
exec(compile(open(os.path.join(hv.LANE, '..', 'smg', 'tools', 'smg_block.py'), encoding='latin-1').read(), 'smg_block.py', 'exec'), globals())

_run0 = T2.run
STDEMO = []
TAIL = [0, 4]
BRK = []            # --brk fire+switch+sprint+drop:50+105[:E]
HIPDEMO = []        # --hipdemo L,E
WALLSTILL = []      # --wallstill stand,crouch,prone : the settled aim on the light wall (--demoyaw), tag <st>W
STHIP = []          # --sthip : --stdemo from the hip
TPC = []            # --tpc : third_close (smg_block) = the held gun from outside, close, hip + aim


def _run(a):
    if not (STDEMO or BRK or HIPDEMO or WALLSTILL or TPC):
        return _run0(a)
    # our part runs inside the shared session: hook the per-gun loop through the (otherwise unused here) "yaw" part
    def ys(sess, gun, yaw):
        x, y, z, w = R.SPOT
        R.SPOT = (x, y, z, a.demoyaw)        # the light wall: on the default yaw (fence, moving foliage) the box measure is void (run hc1)
        try:
            for st in WALLSTILL:
                R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)      # give re-faces to the wall yaw
                T2.still(sess, gun, st, name=st + "W")
            if TPC:
                third_close(sess, gun)
            for st in STDEMO:
                R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                stdemo(sess, gun, st, a.shots, a.shotgap, a.demoreload, a.demoempty)
            for c in HIPDEMO:
                R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                sdemo(sess, gun, c, ads=False)
            for spec in BRK:
                sp = spec.split(":")
                for kind in sp[0].split("+"):
                    for at in [int(x) for x in sp[1].split("+")]:
                        # a second weapon in the inventory, or `weapnext` has nowhere to go
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS["colt45"]) + S.give(A.GUNS[gun]), timeout=120)
                        sbreak(sess, gun, kind, at, case=(sp[2] if len(sp) > 2 else "L"), n=int(sp[3]) if len(sp) > 3 else 170)
        finally:
            R.SPOT = (x, y, z, w)
            R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
    T2.yawstill = ys
    a.parts = list(a.parts) + ["yaw"] if "yaw" not in a.parts else a.parts
    a.yaws = [0]
    return _run0(a)


T2.run = _run

if __name__ == "__main__":
    assert R.CLIENT.lower().endswith("adsanim4") and R.PORT == 12598
    if "--stdemo" in sys.argv:
        k = sys.argv.index("--stdemo")
        STDEMO[:] = sys.argv[k + 1].split(",")
        del sys.argv[k:k + 2]
    if "--sthip" in sys.argv:
        sys.argv.remove("--sthip"); STHIP.append(1)
    if "--tpc" in sys.argv:
        sys.argv.remove("--tpc"); TPC.append(1)
    for opt, lst in (("--brk", BRK), ("--hipdemo", HIPDEMO), ("--wallstill", WALLSTILL)):
        if opt in sys.argv:
            k = sys.argv.index(opt)
            lst[:] = sys.argv[k + 1].split(",")
            del sys.argv[k:k + 2]
    if "--hold" in sys.argv:
        k = sys.argv.index("--hold")
        SMG_HOLD[0] = int(sys.argv[k + 1])
        del sys.argv[k:k + 2]
    if "--rel" in sys.argv:
        k = sys.argv.index("--rel")
        SMG_REL[0] = int(sys.argv[k + 1])
        del sys.argv[k:k + 2]
    if "--tail" in sys.argv:
        k = sys.argv.index("--tail")
        v = sys.argv[k + 1].split(":")
        TAIL[:] = [int(v[0]), int(v[1]) if len(v) > 1 else 4]
        del sys.argv[k:k + 2]
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
