"""run_reloadauth.py - reload authenticity phase A, ONE batched in-engine run (queue slot "reloadauth").

    python run_reloadauth.py <session> --overlay <pk3> [--guns a,b]

Install G:\\mohaa-reloadauth (byte copies of the LIVE exe/cgame/game/renderers, fresh home from G:\\mohaa-adsanim\\pristine,
no qkey/saves, coop_loA* blanked by seed_home). Reuses the ironsights harness (run_sweep / run_ironsights): DISPLAY2 via
harness_window.launch_background, basepath = GOG read-only, net_ip 127.0.0.1, g_ai 0, com_maxfps 60.
Per gun: give, spend rounds (a reload only plays when the magazine is not full), `reload`, one screenshotJPEG every
3rd game frame (coop_isFixed 16) with the HUD on so the ammo counter shows when the clip fills.
"""
import os, sys, time, argparse, math
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28"
sys.path.insert(0, os.path.join(IS, "tools"))
import run_sweep as S          # noqa: E402
R = S.R
SCR = R.SCRATCH
R.OWNER = "reloadauth"
R.CLIENT = r"G:\mohaa-reloadauth"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")   # boot_session md5s this exact name
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-reloadauth/runs"
R.PORT = 12571
QNAME = "reloadauth"
CGAME = ["cgame_live"]
SLOT = os.path.join(SCR, "test_slot.txt")
LOGF = os.path.join(SCR, "reloadauth", "run.log")
# key: (tik, rounds to spend, expected reload seconds)
GUNS = {
    "fg42": ("models/weapons/FG42.tik", 4, 2.34), "johnson": ("models/weapons/johnson_m1941.tik", 2, 2.03),
    "dp28": ("models/weapons/dp28.tik", 4, 3.27), "m10": ("models/weapons/m10_revolver.tik", 2, 2.43),
    "breda": ("models/weapons/It_W_Breda.tik", 4, 5.73), "arisaka": ("models/weapons/arisaka.tik", 1, 3.37),
    "arisakasniper": ("models/weapons/arisakasniper.tik", 1, 3.37),
    "mosinsniper": ("models/weapons/nagant_sniper.tik", 1, 3.07),
    "mosinsnipersil": ("models/weapons/nagant_snipersilenced.tik", 1, 3.07),
    "enfieldsniper": ("models/weapons/enfieldsniper.tik", 1, 3.87), "g43sniper": ("models/weapons/g43sniper.tik", 2, 2.93),
    "carcanosniper": ("models/weapons/carcanosniper.tik", 1, 3.33), "mp44scoped": ("models/weapons/mp44scoped.tik", 4, 2.77),
    "m1903": ("models/weapons/springfield_unscoped.tik", 1, 3.4),
    "kar98snsil": ("models/weapons/kar98snipersilenced.tik", 1, 3.4),
    "mp40silenced": ("models/weapons/mp40silenced.tik", 4, 2.53), "greasegun": ("models/weapons/greasegun.tik", 4, 2.53),
    "greasegunsil": ("models/weapons/greasegun_silenced.tik", 4, 2.53),
    "pps43": ("models/weapons/ppsh43silenced.tik", 4, 2.53), "berettam38": ("models/weapons/moschetto.tik", 4, 2.30),
    "lewis": ("models/weapons/bar_bar1918.tik", 4, 3.27), "webley6": ("models/weapons/colt45_colt1911w.tik", 2, 2.43),
    # phase B group 1-3
    "b_arisakasn": ("models/weapons/arisakasniper.tik", 2, 4.3), "b_mosinsn": ("models/weapons/nagant_sniper.tik", 2, 4.3),
    "b_mosinsnsil": ("models/weapons/nagant_snipersilenced.tik", 2, 4.3),
    "b_enfieldsn": ("models/weapons/enfieldsniper.tik", 2, 4.3), "b_webley6": ("models/weapons/colt45_colt1911w.tik", 2, 2.7),
    "b_carbine": ("models/weapons/carbine.tik", 3, 2.93), "b_m38": ("models/weapons/moschetto.tik", 4, 2.30),
    "b_moschetto": ("models/weapons/It_W_Moschetto.tik", 4, 2.30), "b_mp40": ("models/weapons/mp40.tik", 4, 2.53),
    "b_lewis": ("models/weapons/bar_bar1918.tik", 4, 3.27), "b_dp28": ("models/weapons/dp28.tik", 4, 3.27),
}
PRE = {}      # gun -> console lines before its give (A/B cvars)
POST = {}     # gun -> extra lines after its reload capture


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


EVERY = [3]


def frames(tag, n, idx, every=None):
    every = every or EVERY[0]
    out = []
    for k in range(n):
        out += ["screenshotJPEG %s__%04d" % (tag, idx[0])] + ["wait 1", "wait 1"] * every
        idx[0] += 1
    return out


def reload(sess, gun):
    tik, shots, secs = GUNS[gun.split("@")[0]]
    tag = "ra__%s__%s" % (sess, gun.replace("@", "_"))
    i = [0]
    L = S.RELEASE + S.TO_STAND
    for k in range(shots):
        L += ["+attackprimary", "wait 60", "-attackprimary", "wait 450"]
    L += ["wait 2000", "echo ^~^~^ RASCEN begin %s" % tag] + frames(tag, 3, i) + ["reload"]
    L += frames(tag, int(math.ceil((secs + 0.8) / (0.016 * EVERY[0]))), i)
    L += ["echo ^~^~^ RASCEN end %s" % tag] + S.RELEASE
    R.step(L, timeout=1800)


def run(sess, overlay, guns):
    extra = ["set cg_drawviewmodel 2", "set ui_hud 1", "set cg_adsSway 0"]
    rundir, notes = S.boot_session(sess, CGAME[0], 1280, 720, extra, overlay)
    log("booted", notes)
    try:
        R.step(["set coop_isFixed 16", "wait 300"], timeout=30)
        for gun in guns:
            log("[%s] %s" % (sess, gun))
            g = gun.split("@")[0]
            R.step(S.RELEASE + S.TO_STAND + PRE.get(gun, []) + S.give(GUNS[g][0]), timeout=90)
            reload(sess, gun)
            if gun in POST:
                R.step(POST[gun], timeout=300)
        R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
    finally:
        S.end_session(rundir, notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--guns", default=",".join(GUNS))
    ap.add_argument("--cgame", default="cgame_live"); ap.add_argument("--game", default=None)
    ap.add_argument("--plan", default=None, help="python file defining GUNLIST / PRE / POST")
    a = ap.parse_args()
    CGAME[0] = a.cgame
    guns = a.guns.split(",")
    if a.plan:
        ns = {"R": R, "S": S}
        exec(open(a.plan).read(), ns)
        guns = ns["GUNLIST"]; PRE.update(ns.get("PRE", {})); POST.update(ns.get("POST", {}))
        EVERY[0] = ns.get("EVERY", 3)
    os.makedirs(os.path.dirname(LOGF), exist_ok=True)
    log("preflight", a.session, "waiting for slot ==", QNAME)
    while open(SLOT).read().strip() != QNAME:
        time.sleep(5)
    log("slot is ours")
    t0 = time.time()
    import shutil
    gdll = os.path.join(R.CLIENT, "game.dll")
    try:
        if a.game:
            shutil.copyfile(os.path.join(R.CLIENT, "games", a.game + ".dll"), gdll)
            log("game.dll <-", a.game)
        run(a.session, a.overlay, guns)
    except Exception as e:
        import traceback
        log("FAILED", repr(e), traceback.format_exc())
    finally:
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        if a.game:
            time.sleep(2)
            shutil.copyfile(os.path.join(R.CLIENT, "games", "game_live.dll"), gdll)
            log("game.dll restored")
        open(SLOT, "w").write("free")
        log("slot released (free) after %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
