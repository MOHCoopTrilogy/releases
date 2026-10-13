"""Two-handed pistol aim: harness runs on G:\\mohaa-adsanim (slot word "adsbolt", run_adsbolt's own boot / steps).

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
STANCES = ("stand", "crouch", "prone", "standL", "standR", "crouchL", "crouchR")
DEMO_RELOAD = [170]
SHOTS = [2]
EMPTY = [False]
GAP = [27]          # frames between shots in the demo (a slow gun needs more: Hi-Standard fire delay 1.0 s)
INTR = [4, 95, 170]      # shots before the reload, capture frame of the interruption, frames captured
KINDS = ["fire", "switch", "sprint"]
EPAUSE = [0]
TAIL = [0, 4]       # --tail N[:step]: the settled aim for N more game frames after the reload, every step-th captured


def demo(sess, gun, tagst="stand", stance=None):
    """stance (--dstances): the same demo in a stance (crouch, prone, standL, standR, crouchL, crouchR, braced) - the
    centre-box / sway-envelope measure needs the model-less reference and the settle tail, which reload_sparse has not"""
    tag = "ab__%s__%s__%s__demo__after" % (sess, gun, tagst)
    i = [0]
    L = S.RELEASE + S.TO_STAND + (S.APPLY[stance] if stance else []) + A.MODE["after"] + ["wait 600", "set cg_adsSightDebug 2",
                                                    "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 8, i)
    L += ["+button13", "echo ^~^~^ DEMO raise %d" % i[0]] + A.frames(tag, 50, i)
    if stance == "braced":
        L += ["coop_braceView"] + A.frames(tag, 20, i)
    REF = ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",
           "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]
    if EMPTY[0]:
        # fired EMPTY: the gun reloads by itself after the last shot; the reference is taken after the reload
        L += A.frames(tag, 6, i) + ["echo ^~^~^ DEMO empty %d" % i[0]]
    for k in range(SHOTS[0]):
        last = EMPTY[0] and k == SHOTS[0] - 1
        if last and EPAUSE[0]:               # --epause N: N frames before the emptying shot, so that the smoke of the others has cleared
            L += A.frames(tag, EPAUSE[0], i)
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
    if TAIL[0]:
        # one whole sway / breath period (5.7 s = 357 game frames) of the settled aim, sparsely captured, then 10 dense
        # frames (the aim mask's own): the reference of the sway-envelope measure (swayenv.py, centrebox.py)
        L += ["echo ^~^~^ DEMO settle %d" % i[0]]
        for k in range(TAIL[0] // TAIL[1]):
            L += A.frames(tag, 1, i) + ["wait 1", "wait 1"] * (TAIL[1] - 1)
        L += A.frames(tag, 10, i)
    L += ["-button13", "echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 50, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + (["coop_braceView"] if stance == "braced" else []) + S.RELEASE + (A.UNAPPLY[stance] if stance else [])
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
    L += A.frames(tag, 4, i) + ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE + A.UNAPPLY[st]
    R.step(L, timeout=600)


RIDE = [False]
SLOWGUNS = set()         # hand-cycled guns (--gungap): 1.3 s between the emptying shots, the others 0.45 s


def reload_sparse(sess, gun, st, n=190, every=4, ads=True, shots=1, empty=False):
    """aimed reload in a stance for the NUMBERS: the ADSFRAME probe on every frame, a screenshot every `every` frames.
    empty: `shots` = the clip size - the last shot is fired as the capture starts and the gun reloads by itself (tag
    stance <st>E)"""
    tag = "ab__%s__%s__%s%s__%s__after" % (sess, gun, st, "E" if empty else "", "reload" if ads else "hipreload")
    L = S.RELEASE + ([] if RIDE[0] else S.TO_STAND + S.APPLY[st]) + A.MODE["after"] + ["wait 400"] + (["+button13", "wait 1700"] if ads else ["wait 600"])
    for _ in range(shots - 1 if empty else shots):
        L += ["+attackprimary", "wait 90", "-attackprimary", "wait 2200" if (_ == shots - 1 and not empty) else ("wait 1300" if (not empty or gun in SLOWGUNS) else "wait 450")]
    L += ["coop_braceView"] if st == "braced" else []
    L += ["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    for k in range(6):
        L += ["wait 1", "wait 1"]
    L += ["+attackprimary", "wait 1", "wait 1", "wait 1", "wait 1", "-attackprimary"] if empty else ["reload"]
    for k in range(n):
        L += (["screenshotJPEG %s__%04d" % (tag, k)] if k % every == 0 else []) + ["wait 1", "wait 1"]
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"]
    L += ["coop_braceView"] if st == "braced" else []
    L += S.RELEASE + ([] if RIDE[0] else A.UNAPPLY[st])
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


def run(a):
    extra = ["set cg_drawviewmodel 2", "set cg_weaponBreath 1", "set cg_adsSway 0.1"] + a.set
    if a.ride:
        R.MAP = "t2l2"
        RIDE[0] = True
        extra += ["set coop_isNoMove 1", "set coop_dbgForceSeat %d" % a.seat]
    rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, extra, a.overlay)
    try:
        R.step(["set coop_isFixed 16", "wait 300"], timeout=30)
        for gun in a.guns:
            A.GUNS.setdefault(gun, "models/weapons/%s.tik" % gun)
            A.log("[%s] 2h %s" % (a.session, gun))
            R.step(S.RELEASE + ([] if RIDE[0] else S.TO_STAND) + S.give(A.GUNS[gun]), timeout=90)
            if "demo" in a.parts:
                demo(a.session, gun)
            if "demoy" in a.parts:                      # the same demo against a lighter backdrop (other view yaw)
                x, y, z, w = R.SPOT
                R.SPOT = (x, y, z, a.demoyaw)
                try:
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                    GAP[0] = a.gungap.get(gun, a.shotgap)
                    if not a.nostand:
                        demo(a.session, gun, tagst="yaw%d" % a.demoyaw)
                    if a.both:                      # the same gun fired EMPTY (its clip size) and reloaded: tag yaw<N>e
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        sv = (EMPTY[0], SHOTS[0], DEMO_RELOAD[0])
                        EMPTY[0] = True; SHOTS[0] = a.eshots.get(gun, 8); DEMO_RELOAD[0] = a.demoreload_e or a.demoreload
                        try:
                            demo(a.session, gun, tagst="yaw%de" % a.demoyaw)
                        finally:
                            EMPTY[0], SHOTS[0], DEMO_RELOAD[0] = sv
                    for st in a.dstances:           # the emptied demo in each stance: tag <st>_yaw<N>e
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        sv = (EMPTY[0], SHOTS[0], DEMO_RELOAD[0])
                        EMPTY[0] = True; SHOTS[0] = a.eshots.get(gun, 8); DEMO_RELOAD[0] = a.demoreload_e or a.demoreload
                        try:
                            demo(a.session, gun, tagst="%s_yaw%de" % (st, a.demoyaw), stance=st)
                        finally:
                            EMPTY[0], SHOTS[0], DEMO_RELOAD[0] = sv
                    for st in [s for s in a.lstances.split(",") if s]:   # the LOADED demo (two shots, the smoke cleared, reload) in each stance: tag <st>_yaw<N>
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        demo(a.session, gun, tagst="%s_yaw%d" % (st, a.demoyaw), stance=st)
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
            if "fire" in a.parts:
                A.firecap(a.session, gun, "stand", ads=True)
            if "stills" in a.parts:
                for st in STANCES + (("braced",) if a.braced else ()):
                    still(a.session, gun, st)
            if "reloads" in a.parts:
                for st in a.rstances:
                    R.step(S.RELEASE + ([] if RIDE[0] else S.TO_STAND) + S.give(A.GUNS[gun]), timeout=90)
                    if not a.remptyonly:
                        reload_sparse(a.session, gun, st, n=a.rframes, every=a.revery, shots=a.rshots)
                    if a.rempty:
                        R.step(S.RELEASE + ([] if RIDE[0] else S.TO_STAND) + S.give(A.GUNS[gun]), timeout=90)
                        reload_sparse(a.session, gun, st, n=a.rframes, every=a.revery, shots=a.eshots.get(gun, 8), empty=True)
                    if a.rhip:
                        R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                        reload_sparse(a.session, gun, st, n=a.rframes, every=a.revery, ads=False, shots=a.rshots)
            if "yaw" in a.parts:
                for yw in a.yaws:
                    yawstill(a.session, gun, yw)
        R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
    finally:
        S.end_session(rundir, notes)


def other_test_games():
    """test game / dedicated-server processes of OTHER harnesses (never the user's own installs, never ours)"""
    import subprocess
    try:
        o = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'openmohaa|omohaaded' } | "
                            "ForEach-Object { $_.ExecutablePath }"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    out = []
    for ln in o.splitlines():
        l = ln.strip().lower().replace("/", chr(92))
        if not l or l.startswith("g:" + chr(92) + "mohaa-adsanim") or l.startswith("g:" + chr(92) + "mohaa-gl2" + chr(92))                 or l.startswith("g:" + chr(92) + "gog" + chr(92)):
            continue
        out.append(l)
    return out


def refresh_lock():
    """keep our heavy lock fresh while we hold it (heavy_lock.sh treats a 30 min old lock as abandoned)"""
    f = os.path.join(A.SCR, "heavy_lock.d", "owner")
    try:
        if open(f).read().split()[0] == "adsanim":
            open(f, "w", newline=chr(10)).write("adsanim %d %s%s" % (int(time.time()), time.strftime("%H:%M:%S"), chr(10)))
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_1022d")
    ap.add_argument("--guns", default="colt45"); ap.add_argument("--parts", default="demo,stills,reloads,yaw")
    ap.add_argument("--rstances", default="crouch,prone"); ap.add_argument("--rframes", type=int, default=190)
    ap.add_argument("--yaws", default="185,265,135,315"); ap.add_argument("--demoyaw", type=int, default=160); ap.add_argument("--demoreload", type=int, default=170); ap.add_argument("--braced", action="store_true"); ap.add_argument("--shots", type=int, default=2); ap.add_argument("--demoempty", action="store_true"); ap.add_argument("--shotgap", type=int, default=27); ap.add_argument("--intr", default="4,95,170"); ap.add_argument("--kinds", default="fire,switch,sprint"); ap.add_argument("--set", action="append", default=[]); ap.add_argument("--revery", type=int, default=4); ap.add_argument("--rhip", action="store_true"); ap.add_argument("--rshots", type=int, default=1)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--both", action="store_true"); ap.add_argument("--eshots", default=""); ap.add_argument("--gungap", default="")
    ap.add_argument("--demoreload_e", type=int, default=0)
    ap.add_argument("--rempty", action="store_true"); ap.add_argument("--remptyonly", action="store_true")
    ap.add_argument("--tail", default="")
    ap.add_argument("--dstances", default=""); ap.add_argument("--nostand", action="store_true"); ap.add_argument("--lstances", default=""); ap.add_argument("--epause", type=int, default=0)
    ap.add_argument("--ride", action="store_true"); ap.add_argument("--seat", type=int, default=2)
    a = ap.parse_args()
    if os.path.isdir(os.path.join(R.RUNS, a.session)) and not a.force:
        sys.exit("run folder %s/%s exists - boot_session would delete it; pick an unused id or pass --force" % (R.RUNS, a.session))
    a.eshots = {k: int(v) for k, v in (x.split("=") for x in a.eshots.split(",") if x)}
    a.gungap = {k: int(v) for k, v in (x.split("=") for x in a.gungap.split(",") if x)}
    SLOWGUNS.update(a.gungap)
    DEMO_RELOAD[0] = a.demoreload
    if a.tail:
        TAIL[:] = [int(v) for v in (a.tail.split(":") + ["4"])[:2]]
    SHOTS[0] = a.shots; EPAUSE[0] = a.epause
    EMPTY[0] = a.demoempty
    GAP[0] = a.shotgap
    INTR[:] = [int(x) for x in a.intr.split(",")]; KINDS[:] = a.kinds.split(",")
    a.guns = [g for g in a.guns.split(",") if g]; a.parts = a.parts.split(",")
    a.dstances = [s for s in a.dstances.split(",") if s]
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
