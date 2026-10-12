"""SMG lane runner = ..\\tools\\run_2h.py taken over by takeover.py (GENERATED - edit takeover.py): harness runs on
G:\\mohaa-adsanim3 (owner adsanim3, net_port 12578), run_adsbolt's own boot / steps.

    python run_2h.py <session> --overlay <pk3> [--cgame cgame_1022d] [--guns colt45] [--parts demo,stills,reloads,yaw,fire]

parts
  demo     ONE continuous capture per gun, standing: hip idle, raise, two aimed shots, aimed reload, lower.
  stills   settled aim in every stance (stand, crouch, prone, lean L/R, crouch-lean L/R), 4 frames each, ADSFRAME on.
  reloads  aimed reload (NEW only) in crouch and prone.
  fire     run_adsbolt's per-shot capture, aimed, 3 shots.
  yaw      settled-aim stills at other view yaws (looking for a light backdrop).
Frames are one engine `screenshotJPEG` per 16 ms of game time (coop_isFixed 16), as every adsbolt run.
"""
import os, sys, time, argparse
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
os.chdir(T)
import run_adsbolt as A
S, R = A.S, A.R
# ---- SMG lane repoint (takeover.py): the lane's own test game, never G:\\mohaa-adsanim ----
R.OWNER = 'adsanim3'
R.CLIENT = 'G:' + chr(92) + 'mohaa-adsanim3'
R.EXE = os.path.join(R.CLIENT, 'openmohaa_ironsight.exe')
R.HOME = os.path.join(R.CLIENT, 'home')
R.MAINTT = os.path.join(R.HOME, 'maintt')
R.LOG = os.path.join(R.MAINTT, 'qconsole.log')
R.SHOTS = os.path.join(R.MAINTT, 'screenshots')
R.PRISTINE = os.path.join(R.CLIENT, 'pristine')
R.RUNS = 'G:/mohaa-adsanim3/runs'
R.PORT = 12578
A.LOGF = os.path.join(A.SCR, 'adssmg', 'run.log')
A.GUNS.update(mp40s='models/weapons/mp40silenced.tik', pps43='models/weapons/ppsh43silenced.tik',
              greasegun='models/weapons/greasegun.tik', greaseguns='models/weapons/greasegun_silenced.tik',
              m38='models/weapons/moschetto.tik', mp18='models/weapons/mp40_mp18.tik', mp40r='models/weapons/mp40_mp40r2.tik',
              thompson50='models/weapons/thompson50.tik', thompsongold='models/weapons/thompsonsmg_gold.tik',
              thompsonm1a1='models/weapons/thompsonsmg_m1a1dk.tik', thompson1928d='models/weapons/thompsonsmg_tommy1928d.tik',
              thompson28='models/weapons/thompsonsmg_tommy28.tik')

STANCES = ("stand", "crouch", "prone", "standL", "standR", "crouchL", "crouchR")
DEMO_RELOAD = [170]
SHOTS = [2]
EMPTY = [False]
GAP = [27]          # frames between shots in the demo (a slow gun needs more: Hi-Standard fire delay 1.0 s)
INTR = [4, 95, 170]      # shots before the reload, capture frame of the interruption, frames captured
KINDS = ["fire", "switch", "sprint"]


def demo(sess, gun, tagst="stand"):
    tag = "ab__%s__%s__%s__demo__after" % (sess, gun, tagst)
    i = [0]
    L = S.RELEASE + S.TO_STAND + A.MODE["after"] + ["wait 600", "set cg_adsSightDebug 2",
                                                    "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 8, i)
    L += ["+button13", "echo ^~^~^ DEMO raise %d" % i[0]] + A.frames(tag, 50, i)
    REF = ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",
           "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]
    if EMPTY[0]:
        # fired EMPTY: the gun reloads by itself after the last shot; the reference is taken after the reload
        L += A.frames(tag, 6, i) + ["echo ^~^~^ DEMO empty %d" % i[0]]
    for k in range(SHOTS[0]):
        last = EMPTY[0] and k == SHOTS[0] - 1
        L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, 3, i) + ["-attackprimary"] + A.frames(tag, 11 if last else GAP[0], i)
    if EMPTY[0]:
        L += ["echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, DEMO_RELOAD[0], i)
        L += REF           # at the END: many shots walk the view up (run te4, 15 shots), a reference from before them no longer fits
    else:
        L += A.frames(tag, 50, i)          # the muzzle smoke clears (it polluted the centre-box measure: run tc1)
        # the same view WITHOUT the first-person model: the reference for the centre-box measure (centrebox.py)
        L += REF
        if DEMO_RELOAD[0] > 0:             # --demoreload 0: raise - fire - lower only (aim pose checks)
            L += ["reload", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, DEMO_RELOAD[0], i)
        else:
            L += A.frames(tag, 20, i)
    L += ["-button13", "echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 50, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE
    R.step(L, timeout=1800)


def demohip(sess, gun, tagst="hip", shots=None):
    """ONE continuous HIP capture: idle, `shots` hip shots, the hip reload, idle"""
    tag = "ab__%s__%s__%s__demohip__after" % (sess, gun, tagst)
    i = [0]
    L = S.RELEASE + S.TO_STAND + A.MODE["after"] + ["wait 600", "set cg_adsSightDebug 2",
                                                    "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 8, i)
    for _ in range(shots or SHOTS[0]):
        L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, 3, i) + ["-attackprimary"] + A.frames(tag, 27, i)
    L += ["reload", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, DEMO_RELOAD[0], i)
    L += ["echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 20, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE
    R.step(L, timeout=1800)


def interrupt(sess, gun, kind, ads=True, shots=None, at=None, n=None):
    """a reload broken off mid-loop: `shots` fired, reload, after `at` capture frames the interruption
    (fire = a trigger press, switch = next weapon, sprint = run forward), every 2nd frame captured"""
    tag = "ab__%s__%s__%s__intr__after" % (sess, gun, kind + ("A" if ads else "H"))
    shots = shots or INTR[0]; at = at or INTR[1]; n = n or INTR[2]
    L = S.RELEASE + S.TO_STAND + A.MODE["after"] + ["wait 600"] + (["+button13", "wait 1500"] if ads else [])
    for _ in range(shots):
        L += ["+attackprimary", "wait 60", "-attackprimary", "wait 420"]
    L += ["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag, "reload"]
    act = {"fire": ["+attackprimary"], "switch": ["weapnext"], "sprint": ["+speed", "+forward"]}[kind]
    for k in range(n):
        if k == at:
            L += act + ["echo ^~^~^ DEMO intr %d" % (k // 2)]
        if k == at + 6 and kind == "fire":
            L += ["-attackprimary"]
        L += (["screenshotJPEG %s__%04d" % (tag, k // 2)] if k % 2 == 0 else []) + ["wait 1", "wait 1"]
    if kind == "fire":          # then empty the gun one press at a time: the trace shows how many rounds were really in
        for j in range(4):
            L += ["+attackprimary", "echo ^~^~^ DEMO press %d" % j]
            for k in range(45):
                L += (["-attackprimary"] if k == 4 else []) + (["screenshotJPEG %s__%04d" % (tag, n // 2 + j * 23 + k // 2)] if k % 2 == 0 else []) + ["wait 1", "wait 1"]
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1", "-forward", "-speed"] + S.RELEASE
    if kind == "switch":
        L += ["wait 1200", "weapprev", "wait 2500"]
    if kind == "sprint":
        L += ["+back", "wait 1300", "-back", "wait 400"]
    R.step(L, timeout=1800)


def still(sess, gun, st, name=None):
    tag = "ab__%s__%s__%s__aim__after" % (sess, gun, name or st)
    i = [0]
    L = S.RELEASE + S.TO_STAND + S.APPLY[st] + A.MODE["after"] + ["wait 400", "+button13", "wait 1900",
                                                                 "set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 4, i) + ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",
                                "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE + A.UNAPPLY[st]
    R.step(L, timeout=600)


def reload_sparse(sess, gun, st, n=190, every=4, ads=True, shots=1):
    """aimed reload in a stance for the NUMBERS: the ADSFRAME probe on every frame, a screenshot every `every` frames"""
    tag = "ab__%s__%s__%s__%s__after" % (sess, gun, st, "reload" if ads else "hipreload")
    L = S.RELEASE + S.TO_STAND + S.APPLY[st] + A.MODE["after"] + ["wait 400"] + (["+button13", "wait 1700"] if ads else ["wait 600"])
    for _ in range(shots):
        L += ["+attackprimary", "wait 90", "-attackprimary", "wait 2200" if _ == shots - 1 else "wait 1300"]
    L += ["coop_braceView"] if st == "braced" else []
    L += ["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    for k in range(6):
        L += ["wait 1", "wait 1"]
    L += ["reload"]
    for k in range(n):
        L += (["screenshotJPEG %s__%04d" % (tag, k)] if k % every == 0 else []) + ["wait 1", "wait 1"]
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"]
    L += ["coop_braceView"] if st == "braced" else []
    L += S.RELEASE + A.UNAPPLY[st]
    R.step(L, timeout=1800)


def yawstill(sess, gun, yaw):
    x, y, z, w = R.SPOT
    R.SPOT = (x, y, z, yaw)
    tag = "ab__%s__%s__yaw%d__aim__after" % (sess, gun, yaw)
    i = [0]
    try:
        L = S.RELEASE + S.TO_STAND + R.face(0.0) + ["wait 900"] + A.MODE["after"] + ["+button13", "wait 1900"]
        L += A.frames(tag, 2, i) + S.RELEASE + ["wait 500"]
        R.step(L, timeout=600)
    finally:
        R.SPOT = (x, y, z, w)
        R.step(R.face(0.0) + ["wait 600"], timeout=120)


# ---- SMG lane block (inserted into run_smg.py by takeover.py before `def run`; edit HERE, then run takeover.py) ----
# sdemo: ONE continuous capture per gun and case - settled, [raise], fire, reload, [lower].
#   case L = rounds left (three short presses, then `reload`), E = emptied (the trigger held until the gun is dry; an
#   emptied gun starts its reload by itself). Aimed tags end in __demo__after (the shared measure tools read them),
#   hip tags in __demohip__after. A reference frame without the first-person model is taken before the lower.
SMG_HOLD = [175]        # frames the trigger is held to empty the gun (MP40: 32 rounds at 0.08 s = 160 frames of 16 ms)
SMG_REL = [200]         # frames captured from the reload mark


def sdemo(sess, gun, case, ads=True, stance="stand"):
    tag = "ab__%s__%s__%s%s__%s__after" % (sess, gun, ("" if stance == "stand" else stance) + ("ads" if ads else "hip"), case, "demo" if ads else "demohip")
    i = [0]
    L = S.RELEASE + S.TO_STAND + S.APPLY[stance] + A.MODE["after"] + ["wait 600"]
    L += ["coop_braceView"] if stance == "braced" else []
    L += ["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 8, i)
    if ads:
        L += ["+button13", "echo ^~^~^ DEMO raise %d" % i[0]] + A.frames(tag, 50, i)
    REF = ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",
           "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]
    if case == "E":
        L += ["echo ^~^~^ DEMO empty %d" % i[0], "+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, SMG_HOLD[0], i)
        L += ["-attackprimary", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, SMG_REL[0], i)
    else:
        for k in range(3):
            L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, 3, i) + ["-attackprimary"] + A.frames(tag, 22, i)
        L += A.frames(tag, 40, i)
        L += ["reload", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, SMG_REL[0], i)
    L += REF
    if ads:
        L += ["-button13", "echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 40, i)
    else:
        L += ["echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 10, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"]
    L += ["coop_braceView"] if stance == "braced" else []
    L += S.RELEASE + A.UNAPPLY[stance]
    R.step(L, timeout=2400)


def third_person(sess, gun):
    """the held gun from outside while it fires a burst and reloads: every 2nd frame"""
    tag = "ab__%s__%s__stand__tp__after" % (sess, gun)
    L = S.RELEASE + S.TO_STAND + ["wait 400", "set cg_3rd_person 1", "set cg_cameradist 62", "set cg_cameraheight 6", "set cg_camerasideoffset -34", "wait 600",
                                  "echo ^~^~^ ABSCEN begin %s" % tag]
    k = 0
    for n, pre in ((10, []), (60, ["+attackprimary"]), (20, ["-attackprimary"]), (60, ["reload"])):
        L += pre
        for _ in range(n):
            L += ["screenshotJPEG %s__%04d" % (tag, k), "wait 1", "wait 1", "wait 1", "wait 1"]
            k += 1
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_3rd_person 0", "set cg_camerasideoffset 18", "set cg_cameradist 120", "set cg_cameraheight 18", "wait 400"] + S.RELEASE
    R.step(L, timeout=900)


def ai_fire(sess, tik):
    """an AI spawned in front of the player by the test overlay's own thread (cvar coop_isAi; the dev `spawn` needs
    cheats, which the mod's server start switches off), AI switched on, the player visible and invulnerable: does its
    gun fire, cycle and reload without errors? every 3rd frame for about 12 s"""
    tag = "ab__%s__ai__stand__ai__after" % sess
    L = S.RELEASE + S.TO_STAND + ["wait 400", "echo ^~^~^ ABSCEN begin %s" % tag, "set g_ai 1", "set coop_isAi %s" % tik, "wait 800"]
    for k in range(240):
        L += ["screenshotJPEG %s__%04d" % (tag, k), "wait 1", "wait 1", "wait 1", "wait 1", "wait 1", "wait 1"]
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set g_ai 0", "wait 300"] + S.RELEASE
    R.step(L, timeout=900)


def smg_parts(a, gun):
    for part in a.parts:
        if part.startswith("sdemo"):                 # sdemo | sdemoL | sdemoE  (aimed);  shipdemo... (hip)
            cases = part[5:] or "LE"
            for c in cases:
                for st in (a.sstances if c == "E" else ["stand"]):      # every stance is run on the EMPTY case (magazine + cock)
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                    sdemo(a.session, gun, c, ads=True, stance=st)
        elif part.startswith("shipdemo"):
            for c in (part[8:] or "LE"):
                R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                sdemo(a.session, gun, c, ads=False)
        elif part == "tp":
            R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
            third_person(a.session, gun)
        elif part == "ai":
            ai_fire(a.session, a.aitik)


def cheats_on():
    """test-only: `spawn` (an AI to look at) needs the server started with cheats - put `+set cheats 1` on the command
    line of THIS harness's own client (the shared launcher builds the argument list; its window policy hook is wrapped)"""
    orig = R.hw.apply_policy

    def wrapped(args, **kw):
        a2, late = orig(args, **kw)
        return [a2[0], "+set", "cheats", "1"] + list(a2[1:]), late
    R.hw.apply_policy = wrapped
# ---- end of the SMG lane block ----


def run(a):
    extra = ["set cg_drawviewmodel 2", "set cg_weaponBreath 1", "set cg_adsSway 0.1"] + a.set
    rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, extra, a.overlay)
    try:
        R.step(["set coop_isFixed 16", "wait 300"], timeout=30)
        for gun in a.guns:
            A.GUNS.setdefault(gun, "models/weapons/%s.tik" % gun)
            A.log("[%s] 2h %s" % (a.session, gun))
            R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
            if "demo" in a.parts:
                demo(a.session, gun)
            if "demoy" in a.parts:                      # the same demo against a lighter backdrop (other view yaw)
                x, y, z, w = R.SPOT
                R.SPOT = (x, y, z, a.demoyaw)
                try:
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                    demo(a.session, gun, tagst="yaw%d" % a.demoyaw)
                    if "demohip" in a.parts:
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        demohip(a.session, gun, tagst="yaw%d" % a.demoyaw)
                finally:
                    R.SPOT = (x, y, z, w)
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
            if "interrupt" in a.parts:
                x, y, z, w = R.SPOT
                R.SPOT = (x, y, z, a.demoyaw)
                try:
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS["colt45"]) + S.give(A.GUNS[gun]), timeout=120)
                    for kind in KINDS:
                        interrupt(a.session, gun, kind.rstrip("H"), ads=(kind not in ("sprint", "fireH")))
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                finally:
                    R.SPOT = (x, y, z, w)
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
            smg_parts(a, gun)
            if "fire" in a.parts:
                A.firecap(a.session, gun, "stand", ads=True)
            if "stills" in a.parts:
                for st in STANCES + (("braced",) if a.braced else ()):
                    still(a.session, gun, st)
            if "reloads" in a.parts:
                for st in a.rstances:
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                    reload_sparse(a.session, gun, st, n=a.rframes, every=a.revery, shots=a.rshots)
                    if a.rhip:
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        reload_sparse(a.session, gun, st, n=a.rframes, every=a.revery, ads=False, shots=a.rshots)
            if "yaw" in a.parts:
                for yw in a.yaws:
                    yawstill(a.session, gun, yw)
        R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
    finally:
        S.end_session(rundir, notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_1022d")
    ap.add_argument("--guns", default="colt45"); ap.add_argument("--parts", default="demo,stills,reloads,yaw")
    ap.add_argument("--rstances", default="crouch,prone"); ap.add_argument("--rframes", type=int, default=190)
    ap.add_argument("--yaws", default="185,265,135,315"); ap.add_argument("--demoyaw", type=int, default=160); ap.add_argument("--demoreload", type=int, default=170); ap.add_argument("--braced", action="store_true"); ap.add_argument("--shots", type=int, default=2); ap.add_argument("--demoempty", action="store_true"); ap.add_argument("--shotgap", type=int, default=27); ap.add_argument("--intr", default="4,95,170"); ap.add_argument("--kinds", default="fire,switch,sprint"); ap.add_argument("--set", action="append", default=[]); ap.add_argument("--yaw", type=int, default=None); ap.add_argument("--stances", default=None); ap.add_argument("--sstances", default="stand"); ap.add_argument("--aitik", default="models/human/german_wehrmact_nco.tik"); ap.add_argument("--hold", type=int, default=175); ap.add_argument("--rel", type=int, default=200); ap.add_argument("--cheats", action="store_true"); ap.add_argument("--revery", type=int, default=4); ap.add_argument("--rhip", action="store_true"); ap.add_argument("--rshots", type=int, default=1)
    a = ap.parse_args()
    if a.yaw is not None:
        R.SPOT = R.SPOT[:3] + (a.yaw,)
    a.sstances = [x for x in a.sstances.split(',') if x]
    SMG_HOLD[0] = a.hold; SMG_REL[0] = a.rel
    if a.cheats:
        cheats_on()
    if a.stances:
        globals()['STANCES'] = tuple(x for x in a.stances.split(',') if x)
    DEMO_RELOAD[0] = a.demoreload
    SHOTS[0] = a.shots
    EMPTY[0] = a.demoempty
    GAP[0] = a.shotgap
    INTR[:] = [int(x) for x in a.intr.split(",")]; KINDS[:] = a.kinds.split(",")
    a.guns = [g for g in a.guns.split(",") if g]; a.parts = a.parts.split(",")
    a.rstances = [s for s in a.rstances.split(",") if s]; a.yaws = [int(v) for v in a.yaws.split(",") if v]
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    # 2026-10-12 (coordinator): this harness no longer takes the shared heavy lock or the shared test slot - the
    # install and its home are ours alone; other harnesses run their own games beside it.
    A.log("start", a.session, "2h")
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
