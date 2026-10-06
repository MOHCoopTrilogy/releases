"""run_weaponhd.py - weapon HD pilot, ONE batched in-engine run (queue slot "weaponhd").

    python run_weaponhd.py            wait for test_slot == "weaponhd", run BEFORE then AFTER, write "free"

Install G:\\mohaa-weaponhd: byte copies of the LIVE G:\\mohaa-gl2 exe/cgame/game/renderers (md5s in notes.json),
fresh home from G:\\mohaa-adsanim\\pristine (no qkey/saves; coop_loA* blanked by seed_home). Reuses the ironsights
harness (run_sweep / run_ironsights): DISPLAY2 via harness_window.launch_background, basepath = GOG read-only,
net_ip 127.0.0.1, g_ai 0, com_maxfps 60, map m3l2 at the ironsights spot (open, level, daylight).
BEFORE = today's shipped textures. AFTER = the same plus ../stage packed as zzzzzzzzzz_coop_hd_weapons.pk3 in the
home maintt (homepath outranks basepath, so it wins exactly as it would in the shipped pak order).
Per gun: 1P idle, 1P ADS (+button13), 3P over the right shoulder (close), 3P wider. Engine `screenshot` only.
"""
import os, sys, time, json, zipfile, shutil
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28"
sys.path.insert(0, os.path.join(IS, "tools"))
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = R.SCRATCH
R.OWNER = "weaponhd"
R.CLIENT = r"G:\mohaa-weaponhd"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")   # boot_session md5s this exact name
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-weaponhd/runs"
R.PORT = 12597
QNAME = "weaponhd"
SLOT = os.path.join(SCR, "test_slot.txt")
LOGF = os.path.join(SCR, "weaponhd", "run.log")
OVERLAY = os.path.join(SCR, "weaponhd", "zzzzzzzzzzzz_ironsighttest.pk3")
HDPAK = "zzzzzzzzzz_coop_hd_weapons.pk3"
STAGE = os.path.join(HERE, "..", "stage")
# run 2 (2026-10-05): run 1's 3P shots hid the gun; add the heavy-wear option (WHD_WEAR=1.8 -> ../stage_heavy)
RUN2 = [("before2", False, None), ("after2", True, None),
        ("heavy2", True, os.path.join(HERE, "..", "stage_heavy"))]
GUNS = [("kar98", "models/weapons/kar98.tik"), ("thompson", "models/weapons/thompsonsmg.tik"),
        ("colt45", "models/weapons/colt45.tik")]


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def make_overlay():
    """the ironsights polling weather.scr (teleport + give by cvar) and nothing else"""
    src = zipfile.ZipFile(r"G:\mohaa-adsanim\home\maintt\zzzzzzzzzzzz_ironsighttest.pk3")
    with zipfile.ZipFile(OVERLAY, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/weather.scr", src.read("coop_mod/weather.scr"))


def pack_stage(dst, stage):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(stage):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, stage).replace(os.sep, "/"))


def shot(name):
    return ["screenshot %s" % name, "wait 1", "wait 1", "wait 200", "echo ^~^~^ WHDSHOT %s" % name]


def session(sess, with_hd, stage=None):
    hd = os.path.join(R.MAINTT, HDPAK)
    if os.path.exists(hd):
        os.remove(hd)
    if with_hd:
        pack_stage(hd, stage or STAGE)
        log("hd pak", os.path.getsize(hd))
    extra = ["set cg_drawviewmodel 2", "set ui_hud 0", "set cg_adsSway 0", "set cg_weaponBreath 0", "fov 80",
             "set cg_3rd_person 0"]
    rundir, notes = S.boot_session(sess, "cgame_live", 1920, 1080, extra, OVERLAY)
    notes["hdpak"] = with_hd
    log("booted", notes)
    try:
        for g, tik in GUNS:
            log("[%s] %s" % (sess, g))
            R.step(S.RELEASE + S.TO_STAND + S.give(tik), timeout=90)
            L = ["wait 1500"] + shot("whd__%s__%s__1p_idle" % (sess, g))
            L += ["+button13", "wait 1800"] + shot("whd__%s__%s__1p_ads" % (sess, g)) + ["-button13", "wait 900"]
            R.step(L, timeout=240)
            # 3P: run 1's behind-the-shoulder camera hid the gun behind the body. Put the camera to the RIGHT of the
            # player and pitch the view down so the camera looks onto the gun in the hands (three framings).
            L = ["set cg_3rd_person 1"]
            for tag, (pitch, dist, hgt, side) in (("3p_a", (35, 30, 14, 26)), ("3p_b", (10, 10, 0, 40)),
                                                   ("3p_c", (55, 45, 30, 10))):
                L += R.face(pitch) + ["set cg_cameradist %d" % dist, "set cg_cameraheight %d" % hgt,
                                      "set cg_camerasideoffset %d" % side, "wait 1200"]
                L += shot("whd__%s__%s__%s" % (sess, g, tag))
            L += ["set cg_3rd_person 0", "set cg_cameradist 120", "set cg_cameraheight 18", "set cg_camerasideoffset 18"]
            L += R.face(0) + ["wait 600"]
            R.step(L, timeout=240)
        # texture memory + which file loaded, for the report
        R.step(["imagelist", "wait 200"], timeout=60)
    finally:
        S.end_session(rundir, notes)


def main():
    os.makedirs(os.path.dirname(LOGF), exist_ok=True)
    make_overlay()
    log("preflight: waiting for slot ==", QNAME)
    while open(SLOT).read().strip() != QNAME:
        time.sleep(5)
    log("slot is ours")
    try:
        for sess, hd, st in RUN2:
            try:
                session(sess, hd, st)
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
