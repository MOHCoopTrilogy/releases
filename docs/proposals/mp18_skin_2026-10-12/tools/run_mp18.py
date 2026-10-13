"""MP18 skin, in-engine before / after. Private harness copy G:/mohaa-hudfeed4 (slot "hudfeed4", port 12761),
integration exe + game + renderer + cgame, DISPLAY2 through the harness, engine `screenshot` only.

    python run_mp18.py <tag> before|after <map> [W H]

Per spot of the map: MP18 at the hip + aiming, MP40 at the hip + aiming (yardstick), then two MP18s (right side up,
left side up) and an MP40 laid on the ground, seen from above with the view model hidden. Ends with `imagelist`:
the coop_mp18 lines (sizes) go to work/shots/<tag>_<mode>_<map>_images.txt - proof of WHICH texture was loaded.
Stills: work/shots/<tag>_<mode>_<map>_<spot>_<view>.png"""
import os, re, sys, time, shutil, subprocess
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.abspath(os.path.join(HERE, ".."))
R.OWNER = "hudfeed4"
R.CLIENT = "G:/mohaa-hudfeed4"
R.EXE = os.path.join(R.CLIENT, "openmohaa_integ.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed4/runs"
R.PORT = 12761
SPOTS = {"m3l2": [("light", (-3608, 2303, 80, 165)), ("dark", (-3608, 2303, 80, 225))],
         "m4l1": [("night", (-3904, -6120, -456, 45))]}
MP18 = "models/weapons/mp40_mp18.tik"
MP40 = "models/weapons/mp40.tik"


def grab(name, out):
    from PIL import Image
    p = os.path.join(R.SHOTS, name + ".tga")
    for _ in range(40):
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            break
        time.sleep(0.25)
    time.sleep(0.4)
    Image.open(p).convert("RGB").save(out)


def main():
    tag, mode, mp = sys.argv[1], sys.argv[2], sys.argv[3]
    W, H = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1920, 1080)
    out = os.path.join(PROP, "work", "shots"); os.makedirs(out, exist_ok=True)
    ov = os.path.join(PROP, "work", "ov_%s.pk3" % mode)
    subprocess.check_call([sys.executable, os.path.join(HERE, "mkov_mp18.py"), ov] + (["--base"] if mode == "before" else []))
    for f, d in (("games/game_integ.dll", "game.dll"), ("renderers/gl2_integ.dll", "renderer_opengl2.dll")):
        shutil.copyfile(os.path.join(R.CLIENT, f), os.path.join(R.CLIENT, d))
    R.MAP = mp
    R.SPOT = SPOTS[mp][0][1]
    pre = "%s_%s_%s" % (tag, mode, mp)
    rundir = notes = None
    try:
        extra = ["set g_ai 0", "set coop_st_xp 0", "set developer 1", "set com_maxfpsUnfocused 60"]
        rundir, notes = S.boot_session("mp18_" + pre, "cgame_integ", W, H, extra, ov)
        print("booted", notes.get("md5"), flush=True)
        n = 0
        for sname, spot in SPOTS[mp]:
            R.SPOT = spot
            for gname, tik in (("mp18", MP18), ("mp40", MP40)):
                R.step(S.RELEASE + S.TO_STAND + S.give(tik), timeout=90)
                sh = "%s_%s_%s_hip" % (pre, sname, gname)
                R.step(["screenshot " + sh, "wait 300"], timeout=30); grab(sh, os.path.join(out, sh + ".png"))
                sh = "%s_%s_%s_ads" % (pre, sname, gname)
                R.step(["+button13", "wait 1900", "screenshot " + sh, "wait 300"], timeout=30)
                grab(sh, os.path.join(out, sh + ".png"))
                R.step(["-button13", "wait 700"], timeout=30)
            n += 1
            R.step(S.RELEASE + S.TO_STAND + R.give("none", 0.0) + ["wait 800", "set coop_isProp %d" % n, "wait 1200"], timeout=60)
            R.step(R.give("none", 62.0) + ["wait 800", "set cg_drawviewmodel 0", "wait 400"], timeout=60)
            sh = "%s_%s_ground" % (pre, sname)
            R.step(["screenshot " + sh, "wait 300"], timeout=30); grab(sh, os.path.join(out, sh + ".png"))
            R.step(["set cg_drawviewmodel 1", "wait 200"] + R.give("none", 0.0) + ["wait 500"], timeout=60)
        st = R.step(["imagelist", "wait 300"], timeout=60)
        t = R.read_log()
        lines = [l for l in t[st:].splitlines() if "coop_mp18" in l.lower() or "weapons/mp40/" in l.lower()]
        open(os.path.join(out, pre + "_images.txt"), "w").write("\n".join(lines) + "\n")
        print("\n".join(lines))
        print("props:", re.findall(r"ISTEST props[^\r\n]*", t))
        print("script errors:", len([l for l in t.splitlines() if "Script Error" in l]))
    except Exception as e:
        import traceback
        print("FAILED", repr(e), traceback.format_exc()[-900:])
    finally:
        try:
            if rundir:
                S.end_session(rundir, notes or {})
        except Exception as e:
            print("end_session", repr(e))
        for f, d in (("games/game_ship.dll", "game.dll"), ("renderers/gl2_ship.dll", "renderer_opengl2.dll"),
                     ("cgames/cgame_ship.dll", "cgame.dll")):
            shutil.copyfile(os.path.join(R.CLIENT, f), os.path.join(R.CLIENT, d))


if __name__ == "__main__":
    main()
