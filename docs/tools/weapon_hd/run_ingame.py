"""Weapon HD in-engine before/after batch (slot "weaponhd", private install G:\\mohaa-weaponhd).

    python docs/tools/weapon_hd/run_ingame.py c1 --guns carbine,sten,... --after 1low [--before ""]

Waits for test_slot == "weaponhd", runs session <tag>before (the paks in --before) and <tag>after (the paks in
--after), writes "free". Per gun: 1P idle + 1P ADS (+button13) on m3l2 at the ironsights spot, engine `screenshot`
only. Reuses the ironsights harness (run_sweep / run_ironsights: DISPLAY2 via harness_window, basepath = GOG
read-only, net_ip 127.0.0.1, g_ai 0, com_maxfps 60, coop_loA* blanked). Binaries = byte copies of the LIVE
G:\\mohaa-gl2 set (md5s in notes.json). Paks come from hzm-mohaa-coop-mod/ and are copied into the private home.
Then `stills.py <tag>` makes the zoom sheets.
"""
import os, sys, time, argparse, shutil, zipfile
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28"
sys.path.insert(0, os.path.join(IS, "tools"))
import run_sweep as S          # noqa: E402
R = S.R
SCR = R.SCRATCH
R.OWNER = "weaponhd"
R.CLIENT = r"G:\mohaa-weaponhd"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-weaponhd/runs"
R.PORT = 12597
SLOT = os.path.join(SCR, "test_slot.txt")
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
OVERLAY = r"G:\mohaa-weaponhd\zzzzzzzzzzzz_ironsighttest.pk3"
LOGF = r"G:\mohaa-weaponhd\run.log"


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def make_overlay():
    src = zipfile.ZipFile(r"G:\mohaa-adsanim\home\maintt\zzzzzzzzzzzz_ironsighttest.pk3")
    with zipfile.ZipFile(OVERLAY, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/weather.scr", src.read("coop_mod/weather.scr"))


def shot(name):
    return ["screenshot %s" % name, "wait 1", "wait 1", "wait 200", "echo ^~^~^ WHDSHOT %s" % name]


def session(sess, paks, guns):
    for fn in os.listdir(R.MAINTT):
        if fn.startswith("zzzzzzzzzz_coop_hd_wpn_"):
            os.remove(os.path.join(R.MAINTT, fn))
    for k in paks:
        if k:
            shutil.copyfile(os.path.join(r"C:\mohaa-weaponhd\paks", "zzzzzzzzzz_coop_hd_wpn_%s.pk3" % k),   # the QA outbox
                            os.path.join(R.MAINTT, "zzzzzzzzzz_coop_hd_wpn_%s.pk3" % k))
    extra = ["set cg_drawviewmodel 2", "set ui_hud 0", "set cg_adsSway 0", "set cg_weaponBreath 0", "fov 80"]
    rundir, notes = S.boot_session(sess, "cgame_live", 1920, 1080, extra, OVERLAY)
    notes["paks"] = paks
    log("booted", notes)
    try:
        for g in guns:
            log("[%s] %s" % (sess, g))
            R.step(S.RELEASE + S.TO_STAND + S.give("models/weapons/%s.tik" % g), timeout=90)
            L = ["wait 1500"] + shot("whd__%s__%s__1p_idle" % (sess, g))
            L += ["+button13", "wait 1800"] + shot("whd__%s__%s__1p_ads" % (sess, g)) + ["-button13", "wait 700"]
            R.step(L, timeout=240)
        R.step(["imagelist", "wait 200"], timeout=60)
    finally:
        S.end_session(rundir, notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("--guns", required=True)
    ap.add_argument("--before", default=""); ap.add_argument("--after", required=True)
    ap.add_argument("--only", default="", help="'after' = skip the before session (its shots already exist)")
    a = ap.parse_args()
    make_overlay()
    log("preflight %s: waiting for slot == weaponhd" % a.tag)
    while open(SLOT).read().strip() != "weaponhd":
        time.sleep(5)
    log("slot is ours")
    try:
        for sess, paks in ((a.tag + "before", a.before.split(",")), (a.tag + "after", a.after.split(","))):
            if a.only and not sess.endswith(a.only):
                continue
            try:
                session(sess, [p for p in paks if p], a.guns.split(","))
            except Exception as e:
                import traceback
                log("SESSION %s FAILED %r %s" % (sess, e, traceback.format_exc()))
    finally:
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        try:
            R.hg.release_slot(R.OWNER)
        except Exception as e:
            log("release_slot:", e)
        with open(SLOT, "w") as f:
            f.write("free")
        log("slot released (free)")


if __name__ == "__main__":
    main()
