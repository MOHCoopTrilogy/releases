"""M1 / Mosin aimed reload, before / after, in the engine: the rifle lane's run_rifle.py capture, repointed to a PRIVATE
client built from the v1.10.86 binaries (H:/hzm_work/m1reload/client; basepath = the GOG install, READ ONLY - nothing
is written there). before = an empty overlay (the shipped fixes pak's clips play); after = the staged clips.

    python run_m1.py <session> before|after --guns garand --stances stand,crouch,prone,standL,standR,braced

Screen slot (H:/hzm_work/screen_slot.py) held for the run; client muted, never focused (harness_window policy +
the muted pristine cfgs, mute_pristine.py); 60 fps cap. Captures: one engine screenshot per 16 ms of game time.
"""
import os, sys, zipfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.dirname(HERE)
RT = os.path.join(FIX, "..", "tools")
sys.path.insert(0, RT)
import run_rifle as RF          # noqa: E402  (chdirs into the ads_bolt tools)
R, A = RF.R, RF.A
C = r"H:\hzm_work\m1reload\client"
R.OWNER = "m1reload"
R.CLIENT = C
R.EXE = os.path.join(C, "openmohaa_ironsight.exe")    # = the live openmohaa.exe (boot_session md5s this name)
R.HOME = os.path.join(C, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(C, "pristine")
R.RUNS = "H:/hzm_work/m1reload/runs"
R.PORT = 12671
A.LOGF = os.path.join(r"H:\hzm_work\m1reload", "run.log")

CODEPK3 = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzzz_co-op_hzm_mod_code.pk3"   # read only
MUTE = ["set s_volume 0", "set s_musicvolume 0", "set coop_tinnitusBaseVol 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60"]


def overlay(mode):
    out = os.path.join(r"H:\hzm_work\m1reload", "ov_%s.pk3" % mode)
    z = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    z.writestr("m1reload_%s.txt" % mode, "m1_reload_fix harness overlay: %s\n" % mode)
    # the iron-sight harness hook (place / face / give / fixedtime on coop_isSeq), on THIS build's weather.scr
    import build_overlay as BO
    src = zipfile.ZipFile(CODEPK3).read("coop_mod/weather.scr").decode("latin-1")
    if BO.HOOK_OLD not in src:
        raise SystemExit("weather.scr hook line not found in %s" % CODEPK3)
    z.writestr("coop_mod/weather.scr", (src.replace(BO.HOOK_OLD, BO.HOOK_NEW, 1).rstrip("\n") + "\n" + BO.FUNC).encode("latin-1"))
    if mode == "after":
        st = os.path.join(FIX, "stage")
        for dp, dn, fn in os.walk(st):
            for f in fn:
                if f.endswith(".skc"):
                    p = os.path.join(dp, f)
                    z.write(p, os.path.relpath(p, st).replace("\\", "/"))
    z.close()
    return out


if __name__ == "__main__":
    sess, mode = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    ov = overlay(mode)
    sh = r"H:\hzm_work\screen_slot.py"
    subprocess.check_call([sys.executable, "-I", sh, "acquire", "m1reload", "15", "m1 reload %s %s" % (sess, mode)])
    try:
        sys.argv = ["run_rifle.py", sess, "--overlay", ov, "--cgame", "cgame_live", "--parts", "reload", "--yaw", "172",
                    "--rframes", "150", "--w", "1280", "--h", "720"] + rest
        for m in MUTE:
            sys.argv += ["--set", m]
        RF.main()
    finally:
        subprocess.call([sys.executable, "-I", sh, "release", "m1reload"])
