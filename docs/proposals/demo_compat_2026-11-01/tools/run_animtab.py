"""Demo anim-table test (bug-10330) on the registered harness G:/mohaa-animtab (owner "animtab", net_port 12931).

    python run_animtab.py rec      host m2l1, record demos/animtab_a (+ .animtab sidecar), fight a little, stop
    python run_animtab.py shift    build home/maintt/zz..._animtab_shift.pk3: one alias that sorts FIRST added to the
                                   player and AI anim lists -> every recorded anim number is off by one
    python run_animtab.py unshift  remove that pk3
    python run_animtab.py play TAG play the demo paused at fixed moments, demo_animRemap 0 then 1, screenshots

Every launch: the shared slot (harness_guard), refused while the user's own game runs (the RAW check, not the
ALLOW_WHILE_PLAYING override), DISPLAY2 through harness_window.launch_background, muted, mouse off.
"""
import json, os, re, shutil, sys, time, zipfile

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_guard as hg
import harness_window as hw

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-animtab"
EXE = os.path.join(CLIENT, "openmohaa.exe")
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
RUNS = os.path.join(CLIENT, "runs")
SHIFT_PK3 = os.path.join(MAINTT, "zzzzzzzzzzzzzzzzzzzzzzzz_animtab_shift.pk3")
PORT = "12931"
SHIFT_N = 60
W, H = 1280, 720
MAP = "m2l1"
DEMO = "animtab_a"
SHOT_TIMES = (5.0, 13.0)
# m2l1 soldiers 69 + 70 (about -1882 -3213 484) and 53 + 55 (-1796 -3135 584..776), seen from 220 u away
CAMS = ("-1662 -3173 560 9 190 0", "-1600 -2980 700 8 215 0")


def log(*a):
    print(*a, flush=True)


class Script:
    def __init__(self):
        self.S = ["@hold", "@attach 0"]
        self.t = 1500

    def cmd(self, c, dt=150):
        self.S.append("@cmd %d %s" % (self.t, c))
        self.t += dt

    def pad(self, lx, ly, rx, ry, btn, dt):
        self.S.append("%d %d %d %d %d 0 0 %d" % (self.t, lx, ly, rx, ry, btn))
        self.t += dt

    def shot(self, name, dt=700):
        self.cmd("screenshotJPEG %s" % name, dt)

    def write(self, name):
        os.makedirs(RUNS, exist_ok=True)
        p = os.path.join(RUNS, name)
        open(p, "w", newline="\n").write("\n".join(self.S) + "\n")
        return p


def _args(script, extra=()):
    return [EXE, "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", HOME,
            "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", str(W),
            "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0", "+set", "cl_memorial", "0",
            "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "net_port", PORT,
            "+set", "in_padTestScript", script.replace("\\", "/"), "+exec", "at_run.cfg"] + list(extra)


def launch(tag, script, lines, limit=600, extra=()):
    if hg.user_game_running_raw():
        raise SystemExit("the user's game is running - not launching")
    hg.acquire_slot("animtab", EXE, HOME, [int(PORT)], minutes=20)
    try:
        shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
        for fn in os.listdir(MAINTT):
            if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
                os.remove(os.path.join(MAINTT, fn))
        if os.path.exists(LOG):
            os.remove(LOG)
        shutil.rmtree(SHOTS, ignore_errors=True)
        os.makedirs(SHOTS, exist_ok=True)
        args, late = hw.apply_policy(_args(script, extra), width=W, height=H)
        open(os.path.join(MAINTT, "at_run.cfg"), "w", newline="\n").write("\n".join(late + lines) + "\n")
        c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
        hg.set_slot_pid("animtab", c.proc.pid)
        t0 = time.time()
        try:
            while time.time() - t0 < limit:
                if c.watcher.violations:
                    log("VIOLATION", c.watcher.violations[:3])
                    break
                if c.proc.poll() is not None:
                    break
                time.sleep(1)
        finally:
            if c.proc.poll() is None:
                c.proc.kill()
            c.close()
        out = os.path.join(RUNS, tag)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        if os.path.exists(LOG):
            shutil.copy(LOG, os.path.join(out, "qconsole.log"))
        if os.path.isdir(SHOTS):
            for fn in os.listdir(SHOTS):
                shutil.copy(os.path.join(SHOTS, fn), out)
        log("run %s done in %.0f s -> %s" % (tag, time.time() - t0, out))
    finally:
        hg.release_slot("animtab")


def rec():
    s = Script()
    s.cmd("set coop_dev 1", 200)
    s.cmd("set developer 1", 100)
    s.cmd("set name Sgt.Animtab", 100)
    s.cmd("set ui_dmmap " + MAP, 200)
    s.cmd("ui_startdmmap 2", 50000)
    s.cmd("+attack", 150)
    s.cmd("-attack", 6000)
    s.cmd("echo ^~^~^ ANIMTABTEST in", 100)
    s.cmd("record " + DEMO, 1500)
    for k in range(5):                                   # look around and shoot: the AI wakes up and moves
        s.pad(0, -12000, 7000 if k % 2 else -7000, 0, 0, 1500)
        s.pad(0, 0, 0, 0, 0, 200)
        s.cmd("+attackprimary", 600)
        s.cmd("-attackprimary", 1200)
    s.cmd("wait", 4000)
    s.cmd("stoprecord", 1500)
    s.cmd("echo ^~^~^ ANIMTABTEST rec done", 300)
    s.cmd("quit", 0)
    p = s.write("rec.txt")
    launch("rec", p, ["set developer 1", "wait 9000", "set in_padTestGo 1"], limit=300)


def play(tag):
    s = Script()
    s.cmd("set developer 1", 100)
    s.cmd("set demo_startPaused 1", 100)   # the demo is ~23 s: it must not run out while it loads
    for remap in (0, 1):
        s.cmd("set demo_animRemap %d" % remap, 100)
        s.cmd("demo " + DEMO, 75000)  # cold load is ~51 s (cgame init + load cinematic)
        s.cmd("demo_hidehud 1", 300)
        for t in SHOT_TIMES:
            s.cmd("demo_pause 1", 200)
            s.cmd("demo_seek %.2f" % t, 1800)
            s.cmd("echo ^~^~^ ANIMTABTEST shot remap=%d t=%.1f" % (remap, t), 100)
            for ci, cam in enumerate(CAMS):          # fixed cameras on AI soldiers (positions from demo_probe)
                s.cmd("demo_camera set " + cam, 700)
                s.shot("%s_r%d_t%02d_c%d" % (tag, remap, int(t), ci), 700)
            s.cmd("demo_camera off", 300)
            s.cmd("demo_pause 0", 100)
        s.cmd("disconnect", 3000)
    s.cmd("echo ^~^~^ ANIMTABTEST play done", 300)
    s.cmd("quit", 0)
    p = s.write("play_%s.txt" % tag)
    launch("play_" + tag, p, ["set developer 1", "wait 9000", "set in_padTestGo 1"], limit=480)


def _insert_first(text, alias):
    """add `alias` as a copy of the first anim line of the file's first `animations {` block"""
    lines = text.splitlines(True)
    i = next(k for k, ln in enumerate(lines) if re.match(r"\s*animations\b", ln, re.I))
    j = next(k for k in range(i, len(lines)) if "{" in lines[k])
    for k in range(j + 1, len(lines)):
        body = lines[k].split("//")[0].strip()
        if not body or body.startswith("$"):
            continue
        toks = body.split()
        if len(toks) >= 2 and toks[0] not in ("{", "}"):
            nl = "\r\n" if lines[k].endswith("\r\n") else "\n"
            # SHIFT_N aliases that sort first -> every recorded number is off by SHIFT_N
            # (one lands on a near-twin, idle01 -> idle02; 60 lands in another anim family)
            for n in range(SHIFT_N):
                lines.insert(k, "\t%s%02d\t%s%s" % (alias, n, toks[1], nl))
            return "".join(lines), toks
    raise SystemExit("no anim line found")


def shift():
    import tiki_anims as T
    vfs = T.VFS(stack=T.install_stack(home=HOME))
    with zipfile.ZipFile(SHIFT_PK3, "w", zipfile.ZIP_DEFLATED) as z:
        for path in ("models/player/base/anims_shared.txt", "models/human/new_generic_human.tik"):
            k = path.lower()
            src = vfs.retail[k][0].filename if k in vfs.retail else "?"
            new, toks = _insert_first(vfs.read(path), "aaa_animtab_shift")
            z.writestr(path, new.encode("latin-1"))
            log("%s (from %s): + aaa_animtab_shift -> %s" % (path, os.path.basename(src), toks[1]))
    log("wrote", SHIFT_PK3)


def unshift():
    if os.path.exists(SHIFT_PK3):
        os.remove(SHIFT_PK3)
    log("removed", SHIFT_PK3)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"rec": rec, "shift": shift, "unshift": unshift}.get(cmd, lambda: play(sys.argv[2] if len(sys.argv) > 2 else "x"))()
