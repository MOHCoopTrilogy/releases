"""bug-10724 ADS check on the PRIVATE client G:\\mohaa-finishes: no pad script - the client is launched through harness_window
(background, never focused, muted, in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0) as a listen server on its own port, and
driven over rcon (a listen server runs client commands from rcon: +button13, screenshotJPEG, use ...).
For each gun: the BASE finish aimed, then each finishes2 finish aimed - the sight picture must be identical.
    python run_ads.py <tag> [--res uw|1080] [--cgame <dll>]
"""
import argparse, os, shutil, subprocess, sys, time, zipfile
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\e5")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402
import rcon as R  # noqa: E402
import e5_run as E  # noqa: E402

CLIENT = r"G:\mohaa-finishes"
MAINTT = os.path.join(CLIENT, "home", "maintt")
RUNS = r"H:\hzm_work\finishes2\runs"
MODWT = r"H:\hzm_work\finishes2-mod"
FS2PAK = r"H:\hzm_work\finishes2_build\zzzzzzzzzz_coop_finishes_hd.pk3"
OV = "zzzzzzzzzzzzzzzzzzzzz_fs2_code.pk3"
PORT, PW = 12291, "fs2adsRcon77"
RES = {"uw": (3440, 1440), "1080": (1920, 1080)}
# (slot, armory id, base weapon name, [(fid, variant weapon name, tag)])
GUNS = [(1, "03", "Mauser KAR 98K", [(44, "Mauser KAR 98K (Splinter)", "kar98_splitter")]),
        (2, "26", "MP40", [(47, "MP40 (Amoeba)", "mp40_amoeba")]),
        (3, "48", "Colt 45", [(40, "Colt 45 (Whitewash)", "colt_whitewash")]),
        (2, "24", "Thompson", [(49, "Thompson (Battle-worn)", "thompson_battleworn")]),
        (1, "13", "KAR98 - Sniper", [(42, "KAR98 - Sniper (Kriegsmarine)", "kar98sniper_kriegsmarine")])]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def overlay():
    st = subprocess.run(["git", "-C", MODWT, "diff", "--name-only", "hotfix-1.10.53"], capture_output=True, text=True).stdout
    with zipfile.ZipFile(os.path.join(MAINTT, OV), "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(set(st.split())):
            p = os.path.join(MODWT, *rel.split("/"))
            if os.path.isfile(p) and not rel.endswith(".pk3"):
                z.write(p, rel)
    shutil.copyfile(FS2PAK, os.path.join(MAINTT, os.path.basename(FS2PAK)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("--res", default="1080"); ap.add_argument("--cgame")
    a = ap.parse_args()
    w, h = RES[a.res]
    out = os.path.join(RUNS, a.tag)
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    shots = os.path.join(MAINTT, "screenshots")
    shutil.rmtree(shots, ignore_errors=True); os.makedirs(shots)
    cg = os.path.join(CLIENT, "cgame.dll")
    keep = cg + ".rc67"
    if not os.path.exists(keep):
        shutil.copyfile(cg, keep)
    shutil.copyfile(a.cgame or keep, cg)
    overlay()
    shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):                 # a stale pid file = the engine's hidden "last run crashed" prompt: the boot hangs
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(MAINTT, fn))
    log_p = os.path.join(MAINTT, "qconsole.log")
    if os.path.exists(log_p):
        os.remove(log_p)
    boot = ["set developer 1", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0", "set in_nograb 1",
            "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set coop_hardcore 0",
            "set rcon_password %s" % PW, "set g_gametype 2", "set cheats 1", "set coop_dev 1", "set coop_lockLoadout 0",
            'seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA1 ""', 'seta coop_loFA2 ""', 'seta coop_loFA3 ""',
            "set cg_adsSightDebug 1", "set ui_dmmap m2l1", "ui_startdmmap 2"]
    open(os.path.join(MAINTT, "fs2_ads.cfg"), "w", newline="\n").write("\n".join(boot) + "\n")
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", E.GOG,
            "+set", "fs_homepath", os.path.join(CLIENT, "home"), "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
            "+set", "r_customwidth", str(w), "+set", "r_customheight", str(h), "+set", "net_port", str(PORT), "+set", "net_enabled", "1", "+set", "rcon_password", PW,
            "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "cheats", "1", "+set", "in_gamepad", "0", "+set", "in_joystick", "0",
            "+exec", "fs2_ads.cfg"]
    args, late = hw.apply_policy(args, width=w, height=h)
    if late:
        open(os.path.join(MAINTT, "fs2_ads.cfg"), "a", newline="\n").write("\n".join(late) + "\n")
    if hg.user_game_running():
        raise SystemExit("user game running")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    rc = lambda cmd, dt=0.6: (R.rcon(cmd, port=PORT, pw=PW, quiet=True), time.sleep(dt))  # noqa: E731
    try:
        t0 = time.time()
        while time.time() - t0 < 150:              # ready = the coop init line in the log
            time.sleep(2)
            if os.path.exists(log_p) and "initialising coop weapon loadout" in open(log_p, errors="ignore").read():
                break
        time.sleep(12)
        rc("+attack", 0.3); rc("-attack", 6)
        rc("+right", 0.5); rc("-right", 1)
        for slot, gid, base, fins in GUNS:
            rc("exec ui/loadout/w%s_s%d.cfg" % (gid, slot), 6)
            rc("exec ui/loadout/fin0_s%d.cfg" % slot, 6)
            if base:
                rc('use "%s"' % base, 3)
            else:
                rc("weapnext", 3)
            tagb = "base_" + fins[0][2].split("_")[0]
            rc("+button13", 2.2); rc("screenshotJPEG %s_ads" % tagb, 1.0); rc("-button13", 1.5)
            for fid, vname, tag in fins:
                rc("exec ui/loadout/fin%d_s%d.cfg" % (fid, slot), 6)
                if vname:
                    rc('use "%s"' % vname, 3)
                rc("+button13", 2.2); rc("screenshotJPEG %s_ads" % tag, 1.0); rc("-button13", 1.5)
                rc("screenshotJPEG %s_hip" % tag, 1.0)
        rc("quit", 2)
    finally:
        time.sleep(3)
        if c.proc.poll() is None:
            c.proc.kill()
        c.close()
        for f in (OV, os.path.basename(FS2PAK)):
            p = os.path.join(MAINTT, f)
            if os.path.exists(p):
                os.remove(p)
        shutil.copyfile(keep, cg)                  # the client goes back to the release cgame
    for fn in sorted(os.listdir(shots)):
        shutil.move(os.path.join(shots, fn), os.path.join(out, fn))
    shutil.copyfile(log_p, os.path.join(out, "qconsole.log"))
    log("shots", len(os.listdir(out)) - 1, "->", out)


if __name__ == "__main__":
    main()
