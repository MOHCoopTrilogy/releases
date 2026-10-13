"""Revolver reload BREAK-OFF measured on a SECOND client (list item B, 2026-10-12).

The host (listen server, our harness copy G:\\mohaa-adsanim, small window) only serves; a second client of the same
install (its own home `home_j1`, port +1, 1280x720, the same test overlay and cgame) joins on 127.0.0.1 and is the one
driven and captured: aim, fire `shots`, reload, and after `at` ms a fire press (held 100 ms). Then the gun is emptied
one press at a time so the rounds that were really in can be counted (the joiner's HUD is ON: the ammo counter is in
every screenshot; the ADSFRAME probe gives the view-animation sequence).

The overlay must be built on ovbase_1021_p2.pk3 (MKOV_BASE): its harness poll gives / places player `coop_isPlayer`.
The joiner runs in REAL time (fixedtime is the host's): screenshots every ~50 ms, times in the log are wall clock.

    python run_break2.py <session> --overlay <pk3> --cgame cgame_adsnext7 --plan webley:4:2250,webley:4:2600,...
plan item = gun : shots fired before the reload : ms after `reload` at which fire is pressed
"""
import os, sys, time, re, shutil, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
os.chdir(T)
import run_adsbolt as A        # noqa: E402
S, R = A.S, A.R
hw = R.hw
JHOME = os.path.join(R.CLIENT, "home_j1")
JMT = os.path.join(JHOME, "maintt")
JLOG = os.path.join(JMT, "qconsole.log")
JSHOTS = os.path.join(JMT, "screenshots")
J = {"c": None, "n": 0}


def rd(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


def jwait(pat, timeout, start=0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        m = re.search(pat, rd(JLOG)[start:])
        if m:
            return m
        if J["c"].proc.poll() is not None:
            raise RuntimeError("joiner exited")
        R.guard()
        time.sleep(0.25)
    return None


def launch_joiner(overlay, W, H, extra):
    os.makedirs(os.path.join(JMT, "configs"), exist_ok=True)
    shutil.copyfile(os.path.join(R.MAINTT, "configs", "omconfig.cfg"), os.path.join(JMT, "configs", "omconfig.cfg"))
    for f in ("autoexec.cfg", "coop_defaults.cfg", "whatsnew_pending.cfg"):
        shutil.copyfile(os.path.join(R.MAINTT, f), os.path.join(JMT, f))
    for fn in os.listdir(JMT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(JMT, fn))
    if os.path.exists(JLOG):
        os.remove(JLOG)
    os.makedirs(JSHOTS, exist_ok=True)
    for fn in os.listdir(JSHOTS):
        os.remove(os.path.join(JSHOTS, fn))
    shutil.copyfile(overlay, os.path.join(JMT, R.OVERLAY))          # the staged clips are client assets too
    sets = [("com_target_game", "2"), ("fs_basepath", R.GOG), ("fs_homepath", JHOME), ("cl_renderer", "opengl2"),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"), ("r_mode", "-1"),
            ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"), ("developer", "1"),
            ("logfile", "2"), ("net_ip", "127.0.0.1"), ("net_port", str(R.PORT + 1)), ("name", "Joiner1")]
    args = [R.EXE]
    for a, b in sets:
        args += ["+set", a, b]
    args += ["+exec", "is_on.cfg", "+connect", "127.0.0.1:%d" % R.PORT]
    args, late = hw.apply_policy(args, width=W, height=H)
    # the host's own boot lines (binds F12, measurement hygiene), then ours
    boot = [l for l in rd(os.path.join(R.MAINTT, "is_on.cfg")).splitlines() if l.strip() and not l.startswith("ui_checkrestart")]
    boot += ["set s_volume 0", "set s_musicvolume 0", "set com_maxfps 60", "set ui_hud 1"] + list(extra) + late
    boot += ['bind F5 "exec j_reload.cfg"', 'bind F6 "exec j_down.cfg"', 'bind F7 "exec j_up.cfg"', 'bind F8 "screenshotJPEG"']
    for fn, body in (("j_reload.cfg", "reload\necho ^~^~^ DEMO reload\n"), ("j_down.cfg", "+attackprimary\necho ^~^~^ DEMO down\n"),
                     ("j_up.cfg", "-attackprimary\necho ^~^~^ DEMO up\n")):
        with open(os.path.join(JMT, fn), "w", newline="\n") as f:
            f.write(body)
    with open(os.path.join(JMT, "is_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(boot) + "\n")
    assert sum(1 for a in args if a.startswith("+")) <= 31
    c = hw.launch_background(args[0], args[1:], R.CLIENT, policy=False, log=lambda *a: None)
    J["c"] = c
    return c


def jstep(lines, timeout=240):
    J["n"] += 1
    mk = "^~^~^ JSTEP %d" % J["n"]
    with open(os.path.join(JMT, "isstep.cfg"), "w", newline="\n") as f:
        f.write("\n".join(lines + ["echo %s" % mk]) + "\n")
    start = len(rd(JLOG))
    for attempt in range(4):
        J["c"].post_key(0x7B)                       # F12 -> exec isstep.cfg, to the JOINER's window only
        if jwait(r"execing isstep\.cfg", 6, max(0, start - 10)):
            break
    else:
        raise RuntimeError("jstep %d: F12 never executed isstep.cfg" % J["n"])
    if not jwait(re.escape(mk) + r"\b", timeout, max(0, start - 10)):
        raise RuntimeError("jstep %d timed out: %s" % (J["n"], lines[:3]))
    return start


KEY = dict(reload=0x74, down=0x75, up=0x76, shot=0x77)      # F5..F8 (binds written by launch_joiner)


def key(name, ms=8):
    J["c"].post_key(KEY[name], down_ms=ms)


def press(hold=0.16):
    key("down"); time.sleep(hold); key("up")


def breakoff(sess, gun, shots, at, k, presses=7, after=2.8, every=0.05):
    """at: seconds after the reload key at which fire is pressed. Returns (tag, frames moved)."""
    tag = "ab__%s__%s__brk%d_%dms__intr__after" % (sess, gun, k, int(at * 1000))
    for fn in os.listdir(JSHOTS):
        os.remove(os.path.join(JSHOTS, fn))
    jstep(S.RELEASE + ["wait 400", "+button13"], timeout=60)
    time.sleep(1.8)
    for _ in range(shots):
        press(); time.sleep(0.75)
    time.sleep(0.8)
    jstep(["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag], timeout=60)
    t0 = time.time()
    key("reload")
    ev = [(at, "down"), (at + 0.16, "up")]
    for j in range(presses):
        ev += [(at + after + 0.75 * j, "down"), (at + after + 0.75 * j + 0.16, "up")]
    end = at + after + 0.75 * presses + 0.3
    nxt = 0.0
    while True:
        t = time.time() - t0
        if t >= end:
            break
        while ev and t >= ev[0][0]:
            key(ev.pop(0)[1])
        if t >= nxt:
            key("shot"); nxt += every
        time.sleep(0.004)
    key("up")
    time.sleep(0.3)
    jstep(["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE, timeout=60)
    time.sleep(0.5)
    n = 0
    for fn in sorted(os.listdir(JSHOTS)):
        shutil.move(os.path.join(JSHOTS, fn), os.path.join(RUNDIR[0], "%s__%04d.jpg" % (tag, n))); n += 1
    # back to a full cylinder for the next item (the last press on an empty gun started a reload: let it finish)
    time.sleep(1.0)
    key("reload")
    time.sleep(9.0)
    return tag, n


RUNDIR = [None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_adsnext7")
    ap.add_argument("--plan", required=True); ap.add_argument("--yaw", type=int, default=160)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if os.path.isdir(os.path.join(R.RUNS, a.session)) and not a.force:
        sys.exit("run folder %s/%s exists - boot_session would delete it; pick an unused id or pass --force" % (R.RUNS, a.session))
    plan = [(g, int(s), int(t) / 1000.0) for g, s, t in (x.split(":") for x in a.plan.split(","))]
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "break2")
    t0 = time.time()
    extra = ["set cg_drawviewmodel 2", "set cg_weaponBreath 1", "set cg_adsSway 0.1"]
    rundir = None
    try:
        rundir, notes = S.boot_session(a.session, a.cgame, 640, 360, extra, a.overlay)
        RUNDIR[0] = rundir
        h0 = len(R.read_log())
        launch_joiner(a.overlay, 1280, 720, extra + A.MODE["after"])
        if not R.wait_log(r"Joiner1 has entered the battle", 240, h0):
            raise RuntimeError("joiner never entered")
        A.log("joiner entered after %.0f s" % (time.time() - t0))
        time.sleep(14)
        for k in range(4):
            jstep(["popmenu 0", "wait 200", "primarydmweapon smg", "wait 100", "join_team allies", "wait 400",
                   "popmenu 0", "wait 800", "popmenu 0", "wait 400"])
            if R.wait_log(r"Joiner1 has joined the (Allies|Axis|Free)", 20, h0):
                break
        else:
            raise RuntimeError("joiner never joined a team")
        time.sleep(18)
        for k in range(5):
            p0 = len(R.read_log())
            jstep(["popmenu 0", "wait 300", "+attackprimary", "wait 100", "-attackprimary", "wait 400"])
            if R.wait_log(r"\^~\^~\^ KITGIVE player=Joiner1", 15, h0):
                break
        else:
            raise RuntimeError("joiner never spawned")
        time.sleep(8)
        x, y, z, w = R.SPOT
        R.SPOT = (x, y, z, a.yaw)
        R.step(["set coop_isPlayer 2", "wait 300"], timeout=30)
        k = 0
        cur = None
        for gun, shots, at in plan:
            A.GUNS.setdefault(gun, "models/weapons/%s.tik" % gun)
            if gun != cur:
                s0 = R.step(S.give(A.GUNS[gun]), timeout=90)
                A.log("give:", re.findall(r"\^~\^~\^ ISTEST (?:player|seq)[^\r\n]*", R.read_log()[s0:])[-2:])
                jstep(A.MODE["after"], timeout=60)
                time.sleep(2.0); key("reload"); time.sleep(9.0)
                cur = gun
            k += 1
            tag, nf = breakoff(a.session, gun, shots, at, k)
            A.log("[%s] %s shots %d press at %.2f s -> %s (%d frames)" % (a.session, gun, shots, at, tag, nf))
    except Exception as e:
        A.log("FAILED", repr(e))
    finally:
        c = J["c"]
        try:
            if c is not None and c.proc.poll() is None:
                with open(os.path.join(JMT, "isstep.cfg"), "w", newline="\n") as f:
                    f.write("quit\n")
                c.post_key(0x7B)
                try:
                    c.proc.wait(20)
                except Exception:
                    c.proc.kill()
            if c is not None:
                c.close()
        except Exception as e:
            A.log("joiner close", repr(e))
        if rundir:
            try:
                S.end_session(rundir, notes)
            except Exception as e:
                A.log("end_session", repr(e))
            n = 0
            for fn in sorted(os.listdir(JSHOTS)):
                shutil.move(os.path.join(JSHOTS, fn), os.path.join(rundir, fn)); n += 1
            if os.path.exists(JLOG):
                shutil.copyfile(JLOG, os.path.join(rundir, "qconsole_joiner.log"))
            A.log("joiner frames:", n)
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        A.log("run ended after %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
