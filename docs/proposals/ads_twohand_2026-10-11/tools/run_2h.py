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
        # fired EMPTY: the gun reloads by itself after the last shot, so the reference is taken before the shots
        L += REF + A.frames(tag, 6, i) + ["echo ^~^~^ DEMO empty %d" % i[0]]
    for k in range(SHOTS[0]):
        last = EMPTY[0] and k == SHOTS[0] - 1
        L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, 3, i) + ["-attackprimary"] + A.frames(tag, 11 if last else 27, i)
    if EMPTY[0]:
        L += ["echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, DEMO_RELOAD[0], i)
    else:
        L += A.frames(tag, 50, i)          # the muzzle smoke clears (it polluted the centre-box measure: run tc1)
        # the same view WITHOUT the first-person model: the reference for the centre-box measure (centrebox.py)
        L += REF
        L += ["reload", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, DEMO_RELOAD[0], i)
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
    L += A.frames(tag, 4, i) + ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE + A.UNAPPLY[st]
    R.step(L, timeout=600)


def reload_sparse(sess, gun, st, n=190, every=4):
    """aimed reload in a stance for the NUMBERS: the ADSFRAME probe on every frame, a screenshot every `every` frames"""
    tag = "ab__%s__%s__%s__reload__after" % (sess, gun, st)
    L = S.RELEASE + S.TO_STAND + S.APPLY[st] + A.MODE["after"] + ["wait 400", "+button13", "wait 1700",
                                                                 "+attackprimary", "wait 90", "-attackprimary", "wait 2200"]
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
            if "fire" in a.parts:
                A.firecap(a.session, gun, "stand", ads=True)
            if "stills" in a.parts:
                for st in STANCES + (("braced",) if a.braced else ()):
                    still(a.session, gun, st)
            if "reloads" in a.parts:
                for st in a.rstances:
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                    reload_sparse(a.session, gun, st, n=a.rframes)
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
    ap.add_argument("--yaws", default="185,265,135,315"); ap.add_argument("--demoyaw", type=int, default=160); ap.add_argument("--demoreload", type=int, default=170); ap.add_argument("--braced", action="store_true"); ap.add_argument("--shots", type=int, default=2); ap.add_argument("--demoempty", action="store_true"); ap.add_argument("--intr", default="4,95,170"); ap.add_argument("--kinds", default="fire,switch,sprint"); ap.add_argument("--set", action="append", default=[])
    a = ap.parse_args()
    DEMO_RELOAD[0] = a.demoreload
    SHOTS[0] = a.shots
    EMPTY[0] = a.demoempty
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
