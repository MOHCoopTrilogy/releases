"""run_scopes.py - modern scope view (bug-3462), before/after captures. Queue slot "scopes".

    python run_scopes.py <session> <mode> [--guns a,b] [--renderer opengl2|opengl1] [--fast]

mode     before = the LIVE cgame + gl2 (today's scope);  after = cgame_<--cg> + gl2_<--gl> (the modern scope)
Install  G:\\mohaa-scopes (byte copies of the live exe/game/gl1, cgames\\ and renderers\\ swapped in per session; fresh
         home, no qkey/saves; registered "scopes" in docs/tools/harness_guard.py). Harness = the ironsights
         run_sweep/run_ironsights stack (m3l2 spot, coop_isPoll overlay, F12 step files, DISPLAY2 only).
Per gun: hip idle -> scope in (every frame) -> scan right then left at a fixed yaw rate (every frame) -> settle ->
breathing (every 4th frame, ~2.5 s) -> breath held (every 4th frame) -> scope out (every frame). Frames are
screenshotJPEG under fixedtime 16 (coop_isFixed), so game time per frame is exactly 16 ms.
"""
import os, sys, time, argparse, shutil, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28"
sys.path.insert(0, os.path.join(IS, "tools"))
import run_sweep as S          # noqa: E402
R = S.R
SCR = R.SCRATCH
R.OWNER = "scopes"
R.CLIENT = r"G:\mohaa-scopes"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-scopes/runs"
R.PORT = 12561
QNAME = "scopes"
SLOT = os.path.join(SCR, "test_slot.txt")
LOGF = os.path.join(SCR, "scopes", "run.log")
BASE_OVERLAY = os.path.join(SCR, "adsbolt", "base_vis.pk3")      # coop_isPoll weather.scr (ironsights harness)
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"

GUNS = {
    "kar98s": "models/weapons/kar98sniper.tik",          # ZF39
    "g43s": "models/weapons/g43sniper.tik",              # ZF4
    "springfield": "models/weapons/springfield.tik",     # M73B1
    "garands": "models/weapons/garand_scoped.tik",       # M84
    "mosins": "models/weapons/nagant_sniper.tik",        # PU
    "enfields": "models/weapons/enfieldsniper.tik",      # No.32
    "arisakas": "models/weapons/arisakasniper.tik",      # Type 97
    "carcanos": "models/weapons/carcanosniper.tik",      # Italian
    # table coverage stills (optic shared with one above)
    "l42a1": "models/weapons/uk_w_l42a1.tik", "svt": "models/weapons/svt_rifle.tik", "fg42": "models/weapons/FG42.tik",
    "mp44s": "models/weapons/mp44scoped.tik", "g43": "models/weapons/G43.tik",
    "kar98ss": "models/weapons/kar98snipersilenced.tik", "mosinss": "models/weapons/nagant_snipersilenced.tik",
}
MAIN = ["kar98s", "g43s", "springfield", "garands", "mosins", "enfields", "arisakas", "carcanos"]

RENDERER = ["opengl2"]
_R_LAUNCH = R.launch


def launch_with_renderer(W, H, extra=()):
    """R.launch with cl_renderer taken from RENDERER[0] (R.launch hard-codes opengl2 in its +set list)"""
    orig = R.hw.apply_policy

    def policy(args, **kw):
        args = list(args)
        for k in range(len(args) - 2):
            if args[k] == "+set" and args[k + 1] == "cl_renderer":
                args[k + 2] = RENDERER[0]
        return orig(args, **kw)
    R.hw.apply_policy = policy
    try:
        return _R_LAUNCH(W, H, extra)
    finally:
        R.hw.apply_policy = orig


R.launch = launch_with_renderer


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def build_overlay(out):
    """the ironsights harness base + the staged scope textures and shader (the deployed paks do not have them yet)"""
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(BASE_OVERLAY)
        for i in b.infolist():
            z.writestr(i.filename, b.read(i.filename))
        tex = os.path.join(MOD, "textures", "hud", "coop_scope")
        for fn in sorted(os.listdir(tex)):
            z.write(os.path.join(tex, fn), "textures/hud/coop_scope/" + fn)
        z.write(os.path.join(MOD, "scripts", "coop_scope.shader"), "scripts/coop_scope.shader")
    return out


def frames(tag, n, idx, every=1):
    out = []
    for k in range(n):
        out += ["screenshotJPEG %s__%04d" % (tag, idx[0]), "wait 1", "wait 1"]   # one game frame
        for _ in range(every - 1):
            out += ["wait 1", "wait 1"]
        idx[0] += 1
    return out


def capture(sess, gun, mode, fast=False):
    tag = "sc__%s__%s__%s" % (sess, gun, mode)
    i = [0]
    L = S.RELEASE + S.TO_STAND + ["centerview", "set cl_yawspeed 32", "wait 400"]
    L += ["echo ^~^~^ SCSCEN begin %s" % tag] + frames(tag, 3, i)
    L += ["+button13"] + frames(tag, 30, i)                              # scope in
    if not fast:
        L += ["+right"] + frames(tag, 45, i) + ["-right"] + frames(tag, 12, i)   # scan right, stop
        L += ["+left"] + frames(tag, 45, i) + ["-left"] + frames(tag, 20, i)     # scan back left, settle
        L += frames(tag, 40, i, every=4)                                         # breathing (2.5 s)
        L += ["+speed"] + frames(tag, 30, i, every=4) + ["-speed"]               # hold breath (1.9 s)
        L += frames(tag, 10, i, every=2)                                         # exhale
    else:
        L += frames(tag, 6, i)
    # the scope is a TOGGLE on the ADS press (player.cpp ToggleZoom on BUTTON_COOPADS; s1: releasing kept it up)
    L += ["-button13", "wait 1", "wait 1", "+button13"] + frames(tag, 24, i) + ["-button13"]   # scope out
    L += ["echo ^~^~^ SCSCEN end %s" % tag, "set cl_yawspeed 140"] + S.RELEASE
    R.step(L, timeout=1500)


def run(sess, mode, guns, renderer, cg, gl, fast):
    overlay = build_overlay(os.path.join(SCR, "scopes", "overlay_%s.pk3" % sess))
    rname = {"before": "gl2_live", "after": "gl2_" + gl}[mode]
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", rname + ".dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    cgame = {"before": "cgame_live", "after": "cgame_" + cg}[mode]
    extra = ["set cg_drawviewmodel 1", "set cg_weaponBreath 1", "set cg_adsSway 0.1", "set cg_headbob 1",
             "set r_ppBloom 1", "set r_ppFXAA 1", "set r_ppSharpen 1", "set r_ppTonemap 1",
             "set cg_scopeDebug 2"]
    log("[%s] mode=%s cgame=%s gl2=%s renderer=%s" % (sess, mode, cgame, rname, renderer))
    RENDERER[0] = renderer
    rundir, notes = S.boot_session(sess, cgame, 1280, 720, extra, overlay)
    notes["mode"] = mode
    notes["renderer"] = renderer
    try:
        R.step(["set coop_isFixed 16", "wait 300"], timeout=30)
        for gun in guns:
            log("[%s] %s %s" % (sess, mode, gun))
            R.step(S.RELEASE + S.TO_STAND + S.give(GUNS[gun]), timeout=90)
            capture(sess, gun, mode, fast or gun not in MAIN)
        R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
    finally:
        S.end_session(rundir, notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("mode", choices=("before", "after"))
    ap.add_argument("--guns", default=",".join(MAIN))
    ap.add_argument("--renderer", default="opengl2")
    ap.add_argument("--cg", default="scope1"); ap.add_argument("--gl", default="scope1")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--then", default="", help="a second 'session:mode[:guns[:renderer]]' run in the same slot")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(LOGF), exist_ok=True)
    log("preflight", a.session, a.mode, "waiting for slot ==", QNAME)
    while open(SLOT).read().strip() != QNAME:
        time.sleep(5)
    log("slot is ours")
    t0 = time.time()
    try:
        jobs = [(a.session, a.mode, a.guns, a.renderer)]
        for spec in [s for s in a.then.split(";") if s]:
            p = spec.split(":")
            jobs.append((p[0], p[1], p[2] if len(p) > 2 and p[2] else a.guns, p[3] if len(p) > 3 else "opengl2"))
        for sess, mode, guns, rend in jobs:
            try:
                run(sess, mode, guns.split(","), rend, a.cg, a.gl, a.fast)
            except Exception as e:
                import traceback
                log("FAILED", sess, repr(e), traceback.format_exc()[-600:])
                try:
                    if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                        R.CL["proc"].kill()
                except Exception:
                    pass
    finally:
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        open(SLOT, "w").write("free")
        log("slot released (free) after %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
