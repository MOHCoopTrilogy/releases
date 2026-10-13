"""RIFLE lane harness runs on G:\\mohaa-adsanim2 (harness_guard owner "adsanim2", net_port 12558) - the shared
run_2h / run_adsbolt steps, repointed; nothing here touches G:\\mohaa-adsanim.

    python run_rifle.py <session> --overlay <abs pk3> --cgame cgame_rifle1 --guns kar98 --parts bolt,reload,hipreload,stills
                        [--stances stand,crouch,prone,standL,standR,braced] [--after 110] [--rframes 230]

parts (each = ONE continuous capture per gun and stance, one engine screenshot per 16 ms of game time)
  bolt       settled aim, reference frames (the same view without the first-person model, before and after), one aimed
             shot, the cycle (`--after` frames)
  bolt2      the same with TWO shots and two cycles
  reload     settled aim, one aimed shot + its cycle (not captured), reference, `reload`, `--rframes` frames
  empty      settled aim, `--shots` aimed shots `--gap` frames apart (the last one empties the gun), then `--rframes`
  hipreload  the same from the hip (no aim) - one shot, the cycle, then the reload
  breakfire / breakswitch / breaksprint   one aimed shot + cycle, `reload`, broken off --breakat frames in, --bframes more
  stills     settled aim, 4 frames;  hipstills  the hip view, 4 frames;  <part>D  the same part facing --darkyaw
             (stance tag <stance>D);  tpc  third person, close: 4 camera places, hip then the aim held
Tags: ab__<sess>__<gun>__<stance>__<part>__after ; marks `^~^~^ RIFLE <name> <capture frame>` in the log.
"""
import os, sys, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
os.chdir(T)
import run_adsbolt as A          # noqa: E402
S, R = A.S, A.R
# ---- repoint to the rifle lane's own copy of the test game
R.OWNER = "adsanim2"
R.CLIENT = r"G:\mohaa-adsanim2"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-adsanim2/runs"
R.PORT = 12558
A.LOGF = os.path.join(A.SCR, "adsrifle", "run.log")
A.GUNS.update({"kar98mortar": "models/weapons/kar98_mortar.tik", "carbine": "models/weapons/carbine.tik", "carcano": "models/weapons/it_w_carcano.tik",
               "svt": "models/weapons/svt_rifle.tik", "delisle": "models/weapons/delisle.tik",
               "garand_silenced": "models/weapons/garand_silenced.tik", "enfield_p14": "models/weapons/enfield_p14.tik",
               "springfield_scoped": "models/weapons/springfield.tik", "kar98sniper": "models/weapons/kar98sniper.tik"})
F = A.frames
REF = lambda tag, sfx: ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__%s" % (tag, sfx), "wait 1", "wait 1",
                        "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]


def pre(st, ads=True):
    L = S.RELEASE + S.TO_STAND + S.APPLY[st] + A.MODE["after"] + ["wait 400"]
    L += ["+button13", "wait 1900"] if ads else ["wait 700"]
    L += ["coop_braceView"] if st == "braced" else []
    return L


def post(st):
    return (["coop_braceView"] if st == "braced" else []) + S.RELEASE + A.UNAPPLY[st]


def cap(sess, gun, st, part, a, sfx=""):
    tag = "ab__%s__%s__%s__%s__after" % (sess, gun, st + sfx, part)
    i = [0]
    mark = lambda n: ["echo ^~^~^ RIFLE %s %d" % (n, i[0])]
    ads = part not in ("hipreload", "hipstills")
    # a bolt capture spends a round: top the magazine up first (a no-op when full) - run ra3 emptied the Kar98 on the
    # fifth stance and the capture ran into the automatic reload
    top = (S.RELEASE + ["reload", "wait 4300"]) if part in ("bolt", "bolt2") else []
    L = top + pre(st, ads) + ["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    if part in ("stills", "hipstills"):
        L += F(tag, 4, i)
    elif part == "relief":      # the settled aim at three eye reliefs (cg_adsRigReliefBias 0 / 1.5 / 3 u further back), 2 frames each
        for b in ("0", "1.5", "3"):
            L += ["set cg_adsRigReliefBias %s" % b, "wait 1200"] + F(tag, 2, i)
        L += ["set cg_adsRigReliefBias 0", "wait 300"]
    elif part == "bolt":
        L += REF(tag, "ref") + F(tag, 8, i) + mark("fire") + ["+attackprimary"] + F(tag, 4, i) + ["-attackprimary"] + F(tag, a.after, i)
        L += mark("end") + REF(tag, "ref2")
    elif part == "bolt2":       # two aimed shots, two cycles, in one capture (the GIF the user asked for)
        L += REF(tag, "ref") + F(tag, 8, i)
        for k in range(2):
            L += mark("fire") + ["+attackprimary"] + F(tag, 4, i) + ["-attackprimary"] + F(tag, a.after, i)
        L += mark("end") + REF(tag, "ref2")
    elif part in ("reload", "hipreload"):
        L += ["+attackprimary", "wait 90", "-attackprimary", "wait %d" % a.cyclems]
        L += REF(tag, "ref") + F(tag, 8, i) + mark("reload") + ["reload"] + F(tag, a.rframes, i) + mark("end") + REF(tag, "ref2")
    elif part in ("breakfire", "breakswitch", "breaksprint"):
        # the aimed reload broken off `--breakat` capture frames in (the shared run_2h recipe: fire = a trigger press,
        # switch = next weapon, sprint = run forward), every frame captured for `--bframes`
        act = {"breakfire": ["+attackprimary"], "breakswitch": ["weapnext"], "breaksprint": ["+speed", "+forward"]}[part]
        L += ["+attackprimary", "wait 90", "-attackprimary", "wait %d" % a.cyclems]
        L += F(tag, 6, i) + mark("reload") + ["reload"] + F(tag, a.breakat, i) + mark("break") + act + F(tag, 6, i)
        L += (["-attackprimary"] if part == "breakfire" else []) + F(tag, a.bframes, i) + mark("end")
        L += ["-forward", "-speed"]
        if part == "breakswitch":
            L += ["wait 1200", "weapprev", "wait 2500"]
        if part == "breaksprint":
            L += ["+back", "wait 1300", "-back", "wait 400"]
    elif part == "empty":
        L += F(tag, 6, i)
        for k in range(a.shots):
            L += mark("fire") + ["+attackprimary"] + F(tag, 4, i) + ["-attackprimary"] + F(tag, a.gap if k < a.shots - 1 else 4, i)
        L += mark("reload") + F(tag, a.rframes, i) + mark("end") + REF(tag, "ref2")
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + post(st)
    R.step(L, timeout=2400)


def tpc(sess, gun):
    """third person, close: the held gun from outside (the world model = the same mesh) - left, right, behind / above,
    further off; hip, then the aim held. ONE engine screenshot per step."""
    tag = "ab__%s__%s__stand__tpc__after" % (sess, gun)
    R.step(S.RELEASE + S.TO_STAND + ["wait 400", "set cg_3rd_person 1", "echo ^~^~^ ABSCEN begin %s" % tag], timeout=60)
    k = 0
    try:
        for aim in (0, 1):
            if aim:
                R.step(["+button13", "wait 900"], timeout=60)
            for dist, hgt, side in ((34, 2, -30), (34, 2, 30), (26, 12, -8), (46, 4, -40)):
                R.step(["set cg_cameradist %d" % dist, "set cg_cameraheight %d" % hgt, "set cg_camerasideoffset %d" % side, "wait 500",
                        "screenshotJPEG %s__%04d" % (tag, k), "wait 1", "wait 1", "wait 1", "wait 1"], timeout=60)
                k += 1
    finally:
        R.step(["-button13", "echo ^~^~^ ABSCEN end %s" % tag, "set cg_3rd_person 0", "set cg_camerasideoffset 18", "set cg_cameradist 120",
                "set cg_cameraheight 18", "wait 400"] + S.RELEASE, timeout=60)


def run(a):
    # --steady: breath and sway off - the measure then reads the clip, not the breathing aim (rbox.py)
    extra = ["set cg_drawviewmodel 2"] + (["set cg_weaponBreath 0", "set cg_adsSway 0"] if a.steady else
                                           ["set cg_weaponBreath 1", "set cg_adsSway 0.1"]) + a.set
    rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, extra, a.overlay)
    try:
        R.step(["set coop_isFixed 16", "wait 300"], timeout=30)
        for gun in a.guns:
            A.GUNS.setdefault(gun, "models/weapons/%s.tik" % gun)
            x, y, z, w = R.SPOT
            R.SPOT = (x, y, z, a.yaw)
            try:
                for part in a.parts:
                    if part == "tpc":
                        A.log("[%s] rifle %s tpc" % (a.session, gun))
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        tpc(a.session, gun)
                        continue
                    if part.endswith("D"):          # <part>D = the same part on the dark backdrop (--darkyaw)
                        part = part[:-1]
                        R.SPOT = (x, y, z, a.darkyaw)
                    else:
                        R.SPOT = (x, y, z, a.yaw)
                    for st in (a.stances if (part != "hipreload" or a.hipall) else a.stances[:1]):
                        A.log("[%s] rifle %s %s %s yaw %s" % (a.session, gun, part, st, R.SPOT[3]))
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        cap(a.session, gun, st, part, a, "D" if R.SPOT[3] == a.darkyaw and a.darkyaw != a.yaw else "")
            finally:
                R.SPOT = (x, y, z, w)
        R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
    finally:
        S.end_session(rundir, notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_rifle1")
    ap.add_argument("--guns", default="kar98"); ap.add_argument("--parts", default="bolt")
    ap.add_argument("--stances", default="stand"); ap.add_argument("--after", type=int, default=110)
    ap.add_argument("--rframes", type=int, default=230); ap.add_argument("--cyclems", type=int, default=2200)
    ap.add_argument("--shots", type=int, default=5); ap.add_argument("--gap", type=int, default=110)
    ap.add_argument("--hipall", action="store_true"); ap.add_argument("--steady", action="store_true"); ap.add_argument("--breakat", type=int, default=70); ap.add_argument("--bframes", type=int, default=150)
    ap.add_argument("--darkyaw", type=int, default=160)
    ap.add_argument("--yaw", type=int, default=160); ap.add_argument("--set", action="append", default=[])
    a = ap.parse_args()
    a.guns = [g for g in a.guns.split(",") if g]; a.parts = a.parts.split(","); a.stances = a.stances.split(",")
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "rifle")
    t0 = time.time()
    try:
        run(a)
    except Exception as e:
        A.log("FAILED", repr(e))
    finally:
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        A.log("run ended after %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
