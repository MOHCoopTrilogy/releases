"""ox_dedcheck.py [--map m1l3c] [--seconds 70] - headless dedicated compile check of the objx scripts against the WORKING copy of
the objectives worktree (overlay pk3 in a PRIVATE home, nothing deployed, GOG tree read-only).
Prints the script errors and the ^~^~^ OXPROBE lines. Exit 1 on any compile/script error."""
import os, re, sys, time, zipfile, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mod-objectives"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
HOME = r"C:\mohaa-coop-dev\objx_ded_home"
EXE = os.path.join(GOG, "omohaaded.exe")
LOG = os.path.join(HOME, "maintt", "qconsole.log")
FILES = ["coop_mod/alarm.scr", "coop_mod/alarmpoints.scr", "coop_mod/carry.scr", "coop_mod/coop_counter.scr",
         "coop_mod/coop_counter_zones.scr", "coop_mod/main.scr", "coop_mod/officer.scr", "coop_mod/reinf_mg.scr",
         "coop_mod/missioncomplete.scr", "coop_mod/objx.scr", "coop_mod/objx_points.scr"]


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m1l3c"
    secs = int(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else 70
    driver = sys.argv[sys.argv.index("--driver") + 1] if "--driver" in sys.argv else "ox_probe.scr"
    os.makedirs(os.path.join(HOME, "maintt"), exist_ok=True)
    for fn in os.listdir(os.path.join(HOME, "maintt")):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(HOME, "maintt", fn))
    ov = os.path.join(HOME, "maintt", "zzzzzzzzzzzz_oxprobe.pk3")
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/coop_selftest_xp.scr", open(os.path.join(HERE, driver), "rb").read())
        for rel in FILES:
            z.write(os.path.join(MOD, rel), rel)
    try:
        open(LOG, "w").close()
    except Exception:
        pass
    args = [EXE, "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "dedicated", "1",
            "+set", "fs_homepath", HOME, "+set", "net_port", "12203", "+set", "sv_maxclients", "8",
            "+set", "g_gametype", "2", "+set", "logfile", "2", "+set", "developer", "1", "+set", "com_abnormalExit", "0",
            "+set", "coop_st_xp", "1", "+set", "coop_objx", "1", "+map", mapname]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    t0 = time.time()
    txt = ""
    while time.time() - t0 < secs:
        time.sleep(3)
        try:
            txt = open(LOG, encoding="latin-1", errors="replace").read()
        except Exception:
            continue
        if "OXPROBE end" in txt:
            break
    crashed = p.poll()
    try:
        p.kill()
    except Exception:
        pass
    bad = [l.strip()[:200] for l in txt.splitlines() if "not properly loaded" in l or "Couldn't compile" in l or "parse error" in l.lower()]
    errs = [l.strip()[:200] for l in txt.splitlines() if "Script Error" in l]
    probe = [l.strip()[:200] for l in txt.splitlines() if "OXPROBE" in l or "OBJX" in l]
    print("map", mapname, "elapsed %.0fs" % (time.time() - t0), "crashed", crashed)
    for l in probe:
        print("  ", l)
    for l in (bad + errs)[:12]:
        print("  ERR", l)
    return 1 if (bad or errs or (crashed not in (None, 0))) else 0


sys.exit(main())
