"""Dedicated server + one client of the lane's build: server-side weapon timing, released vs staged (bug-3736).

    python run_ded.py <session> --arm <name>=<overlay.pk3> [--arm ...] [--cgame cgame_adsnext12] [--guns welrod,tt33,...]

Per arm: a dedicated server (G:\\mohaa-adsanim\\omohaaded_brtest.exe + the install's game.dll, own home on C:, the
arm's overlay in its maintt, net_ip 127.0.0.1, net_port 12539) and ONE client (the lane's private copy, port 12538,
the same overlay, the given cgame) that connects to it. The harness plumbing of the overlay (coop_is_test in
weather.scr) runs on the SERVER; the client sets its cvars by rcon. Per gun, at the hip and aimed: the trigger is
pulsed 50 ms down / 50 ms up (`wait` is milliseconds) for 18 s with one `reload` typed 1.6 s in after a 1.2 s rest - so the log holds strings of shots, a
loaded reload, the emptied gun's automatic reload and the shots after each. The client runs coop_vmSrvProbe 1: one
line per snapshot in which the server's clip / reserve / hands id / weapon-entity animation changed, with the
snapshot's server time. dedcmp.py reads the lines. No screenshots, no fixed time: real server frames (sv_fps as set
by the mod's defaults).
"""
import os, sys, time, argparse, subprocess, shutil, re
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import run_adsbolt as A
os.chdir(_c)
S, R = A.S, A.R
hg, hw = R.hg, R.hw
DED_EXE = os.path.join(R.CLIENT, "omohaaded_brtest.exe")
DED_HOME = os.path.join(R.SCRATCH, "pistols", "home_ded")
DED_MAINTT = os.path.join(DED_HOME, "maintt")
DED_LOG = os.path.join(DED_MAINTT, "qconsole.log")
DPORT = 12539
RCON = "pa21ded"
OUT = os.path.join(R.SCRATCH, "pistols", "ded")
GUNS = {"welrod": "models/weapons/welrod.tik", "tt33": "models/weapons/tt33.tik", "tt33silenced": "models/weapons/tt33silenced.tik",
        "colt45": "models/weapons/colt45.tik", "p38": "models/weapons/p38.tik", "ppk": "models/weapons/ppk.tik",
        "histandard": "models/weapons/silencedpistol.tik", "luger": "models/weapons/lugerp08.tik", "c96": "models/weapons/mauser_c96.tik",
        "beretta": "models/weapons/it_w_beretta.tik", "nambu": "models/weapons/nambu.tik", "m10": "models/weapons/m10_revolver.tik"}
SRV = {"p": None}


def dlog():
    try:
        return open(DED_LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def wait_dlog(pat, timeout, start=0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        m = re.search(pat, dlog()[start:])
        if m:
            return m
        time.sleep(0.5)
    return None


def start_server(overlay):
    os.makedirs(os.path.join(DED_MAINTT, "configs"), exist_ok=True)
    for f in ("autoexec.cfg", "coop_defaults.cfg"):
        shutil.copyfile(os.path.join(R.PRISTINE, f), os.path.join(DED_MAINTT, f))
    for fn in os.listdir(DED_MAINTT):
        if fn.lower().endswith(".pk3") or fn.lower().endswith(".pid") or fn == "qconsole.log":
            os.remove(os.path.join(DED_MAINTT, fn))
    shutil.copyfile(overlay, os.path.join(DED_MAINTT, R.OVERLAY))
    with open(os.path.join(DED_MAINTT, "ded_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(["set rconPassword %s" % RCON, "set coop_isPoll 1", "set g_ai 0", "set coop_dbno 0", "set coop_dev 1",
                           "set sv_maxbots 0", "set sv_numbots 0", "set coop_weatherPin 0", "set coop_idleInspect 0",
                           "map %s" % R.MAP]) + "\n")
    args = [DED_EXE]
    for k, v in (("dedicated", "1"), ("com_target_game", "2"), ("fs_basepath", R.GOG), ("fs_homepath", DED_HOME), ("net_ip", "127.0.0.1"),
                 ("net_port", str(DPORT)), ("sv_maxclients", "4"), ("g_gametype", "2"), ("logfile", "2"), ("developer", "1")):
        args += ["+set", k, v]
    args += ["+exec", "ded_on.cfg"]
    SRV["p"] = subprocess.Popen(args, cwd=R.CLIENT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=0x08000000)
    A.log("server pid", SRV["p"].pid)
    m = wait_dlog(r"Could not load[^\r\n]*|Detected Coop for|initialising coop weapon loadout", 240)
    if not m or m.group(0).startswith("Could not"):
        raise RuntimeError("server: map never became ready")


def stop_server():
    p = SRV["p"]
    if p is not None and p.poll() is None:
        p.kill()
        p.wait(20)
    SRV["p"] = None


def launch_client(W, H, extra):
    """R.launch, but the client CONNECTS to our dedicated server instead of starting a listen server"""
    boot = ["bind F12 \"exec isstep.cfg\"", "set rconPassword %s" % RCON, "set cg_drawviewmodel 2", "set ui_gmbox 0", "ui_checkrestart",
            "set ui_crosshair 0", "set coop_tinnitus 0", "set coop_tinnitusBlast 0", "set cg_headbob 0", "set coop_coverAuto 0",
            "set coop_coverLean 0", "set ui_hud 0", "set com_maxfps 60", "set coop_idleInspect 0"] + list(extra)
    sets = [("com_target_game", "2"), ("fs_basepath", R.GOG), ("fs_homepath", R.HOME), ("cl_renderer", "opengl2"),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"), ("r_mode", "-1"),
            ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"), ("developer", "1"),
            ("logfile", "2"), ("net_ip", "127.0.0.1"), ("net_port", str(R.PORT))]
    args = [R.EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "is_on.cfg", "+connect", "127.0.0.1:%d" % DPORT]
    args, late = hw.apply_policy(args, width=W, height=H)
    boot += late
    with open(os.path.join(R.MAINTT, "is_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(boot) + "\n")
    hg.acquire_slot(R.OWNER, R.EXE, R.HOME, [R.PORT], 40)
    c = hw.launch_background(args[0], args[1:], R.CLIENT, policy=False, log=A.log)
    R.CL["c"], R.CL["proc"] = c, c.proc
    try:
        hg.set_slot_pid(R.OWNER, c.proc.pid)
    except Exception as e:
        A.log("slot pid note:", e)


def rcon(lines):
    """ONE rcon per call (the server rate-limits rcon packets): the lines go into a cfg in the server's own home"""
    with open(os.path.join(DED_MAINTT, "isgive.cfg"), "w", newline=chr(10)) as f:
        f.write(chr(10).join(lines) + chr(10))
    return ["rcon exec isgive.cfg"]


def pulses(sec, reload_at=None):
    L = []
    n = int(sec * 10)                     # `wait` is in MILLISECONDS here (cmd.c): 50 ms down, 50 ms up
    for k in range(n):
        if reload_at is not None and k == int(reload_at * 10):
            # the trigger rests 1.2 s first (a `reload` typed inside a shot's fire delay is dropped - run pa21a)
            L += ["wait 1200", "reload", "echo ^~^~^ DED reloadcmd"]
        L += ["+attackprimary", "wait 50", "-attackprimary", "wait 50"]
    return L


def gun_run(arm, gun, secs):
    for mode in ("hip", "ads"):
        st = len(dlog())
        R.step(S.RELEASE + S.TO_STAND + rcon(S.give(GUNS[gun])), timeout=60)
        if not wait_dlog(r"ISTEST seq=\d+ tik=", 30, st):
            raise RuntimeError("server never gave %s" % gun)
        time.sleep(1.0)
        L = ["echo ^~^~^ DED begin %s %s %s" % (arm, gun, mode), "wait 500"]
        if mode == "ads":
            L += ["+button13", "wait 1500"]
        L += pulses(secs, 1.6) + ["wait 4000", "echo ^~^~^ DED end %s %s %s" % (arm, gun, mode), "-button13", "wait 800"]
        R.step(L, timeout=secs * 2 + 90)


def run_arm(arm, overlay, cgame, guns, secs):
    A.log("[ded] arm", arm, overlay)
    start_server(overlay)
    try:
        R.seed_home(cgame, overlay)
        launch_client(1280, 720, ["set coop_vmSrvProbe 1", "set coop_vmGunClipClock 2", "set cg_adsSway 0.1", "set cg_weaponBreath 1"])
        if not R.wait_log(r"Could not load[^\r\n]*|Detected Coop for|CGame.*initiali|\^~\^~\^ ", 300):
            raise RuntimeError("client never loaded the map")
        time.sleep(10)
        joined = False
        for k in range(5):
            st = len(dlog())
            R.step(["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20", "popmenu 0", "wait 40",
                    "popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
            if wait_dlog(r"\^~\^~\^ KITGIVE|has joined the", 15, st):
                joined = True
                break
        A.log("[ded] joined", joined)
        time.sleep(8)
        for k in range(3):
            st = len(dlog())
            R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
            if re.search(r"KITGIVE", dlog()):
                break
        time.sleep(6)
        for k in range(3):                      # a first give that may land before the spawn is complete: thrown away
            st = len(dlog())
            R.step(S.RELEASE + S.TO_STAND + rcon(S.give(GUNS["colt45"])), timeout=60)
            wait_dlog(r"ISTEST seq=\d+ tik=", 30, st)
            time.sleep(1.5)
        for gun in guns:
            A.log("[ded] %s %s" % (arm, gun))
            gun_run(arm, gun, secs)
    finally:
        try:
            proc = R.CL["proc"]
            if proc is not None and proc.poll() is None:
                with open(os.path.join(R.MAINTT, "isstep.cfg"), "w", newline="\n") as f:
                    f.write("quit\n")
                R.CL["c"].post_key(0x7B)
                try:
                    proc.wait(30)
                except Exception:
                    proc.kill()
        except Exception as e:
            A.log("client stop note:", e)
        stop_server()
        try:
            hg.release_slot(R.OWNER)
        except Exception:
            pass
        d = os.path.join(OUT, a_sess[0])
        os.makedirs(d, exist_ok=True)
        for src, nm in ((R.LOG, "client_%s.log" % arm), (DED_LOG, "server_%s.log" % arm)):
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(d, nm))


a_sess = [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--arm", action="append", required=True); ap.add_argument("--cgame", default="cgame_adsnext12")
    ap.add_argument("--guns", default="welrod,tt33,tt33silenced,colt45,p38"); ap.add_argument("--secs", type=float, default=18.0)
    a = ap.parse_args()
    a_sess[0] = a.session
    if os.path.isdir(os.path.join(OUT, a.session)):
        sys.exit("session %s exists" % a.session)
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    for spec in a.arm:
        arm, ov = spec.split("=", 1)
        try:
            run_arm(arm, os.path.abspath(ov), a.cgame, a.guns.split(","), a.secs)
        except Exception as e:
            A.log("[ded] arm %s FAILED: %r" % (arm, e))
        time.sleep(5)


if __name__ == "__main__":
    main()
