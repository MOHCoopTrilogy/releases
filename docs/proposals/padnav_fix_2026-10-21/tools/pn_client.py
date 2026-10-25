"""pn_client.py - padnav-fix proof harness (private client G:\\mohaa-padnav, queue ticket via docs/tools/harness_turn.py).

    python pn_client.py run <exe> <page> [tag]     exe = live (v1.10.35 2cee0ef6) | i133 (v1.10.33/34 c8cb8d5c) | path to an exe
                                                    page = any menu name (pushmenu <page>), e.g. coop_padaim
    python pn_client.py keys <exe> <page> [tag]    same page, but driven by the KEYBOARD (arrows / Tab / Enter) via post_key

Virtual pad (in_padTestScript): D-pad Down x N / Up x N with a PADNAV log line each, Right/Left on the focused row (slider
value read back with a bare-cvar @cmd), left-stick pushes (the stick is a CURSOR in menus), A, B.  Built on mr_client.py
(DISPLAY2, never focused, muted, mouse off, BELOW_NORMAL, job-killed).  Output: runs/<tag>/ (shots + qconsole.log + pad.txt).
"""
import json, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
INGAME = r"C:\mohaa-coop-dev\docs\proposals\menu_redesign_2026-09-28\remaster_test\ingame"
sys.path.insert(0, INGAME)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import mr_client as mr  # noqa: E402

hg, hw = mr.hg, mr.hw
CLIENT = r"G:\mohaa-padnav"
mr.CLIENT = CLIENT
mr.EXE = os.path.join(CLIENT, "openmohaa.exe")
mr.HOME = os.path.join(CLIENT, "home")
mr.MAINTT = os.path.join(mr.HOME, "maintt")
mr.LOG = os.path.join(mr.MAINTT, "qconsole.log")
mr.SHOTS = os.path.join(mr.MAINTT, "screenshots")
mr.OWNER = "padnav"
mr.RUNS = os.path.join(HERE, "runs")
mr.build_overlay = lambda: None
EXES = {"pn": r"C:\mohaa-coop-dev\openmohaa-hzm-padnav\.cmake-pn\Release\openmohaa.exe", "live": r"G:\mohaa-gl2\openmohaa.exe", "i133": os.path.join(CLIENT, "openmohaa_i133.exe")}
DP = {"U": 0x800, "D": 0x1000, "L": 0x2000, "R": 0x4000}
A, B = 0x1, 0x2


def log(*a):
    mr.log(*a)


class Script:
    def __init__(self):
        self.S = ["@hold", "@attach 0"]
        self.t = 1500
        self.shots = 0

    def cmd(self, c):
        self.S.append("@cmd %d %s" % (self.t, c))

    def state(self, btn=0, lx=0, ly=0, rx=0, ry=0):
        self.S.append("%d %d %d %d %d 0 0 %d" % (self.t, lx, ly, rx, ry, btn))

    def press(self, btn, hold=160, gap=700):
        self.state(btn); self.t += hold; self.state(0); self.t += gap

    def shot(self, name):
        self.cmd("screenshot " + name); self.shots += 1; self.t += 500

    def mark(self, s):
        self.cmd("echo ^~^~^ STEP " + s); self.t += 40

    def stick(self, lx, ly, ms):
        self.state(0, lx, ly); self.t += ms; self.state(0); self.t += 500

    def text(self):
        return "\n".join(self.S) + "\n"


def page_rows(page):
    """slider / checkbox / button names + linkcvars of the page, in file order (from the mod source ui/)."""
    fn = None
    for cand in (page + ".urc", page.replace("_", " ") + ".urc"):
        p = os.path.join(r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui", cand)
        if os.path.exists(p):
            fn = p
    if not fn:
        return []
    t = open(fn, encoding="latin-1").read().replace("\r\n", "\n")
    out = []
    for m in re.finditer(r'(?ms)^resource\s*\n\s*(\w+)\s*\n\{(.*?)\n\}', t):
        k, b = m.group(1), m.group(2)
        if k in ("Slider", "CheckBox", "Button", "PulldownMenu", "ListBox", "ComboBox"):
            nm = re.search(r'(?m)^\s*name\s+"([^"]*)"', b)
            cv = re.search(r'(?m)^\s*linkcvar\s+"([^"]*)"', b)
            out.append((k, nm.group(1) if nm else "?", cv.group(1) if cv else None))
    return out


def pad_script(page, w, h, suite="pad"):
    if suite == "stick":
        return stick_script(page, w, h)
    if suite == "sweep":
        return sweep_script(page.split(","), w, h)
    rows = page_rows(page)
    n = max(len(rows) + 2, 6)
    s = Script()
    s.cmd("pushmenu " + page); s.t += 2500
    s.shot("pn_00_open")
    # phase A: D-pad DOWN through the whole page (focus must reach every row, one row per press)
    for i in range(n):
        s.press(DP["D"]); s.mark("D %d" % i)
        if i < 3 or i == n - 1:
            s.shot("pn_D%02d" % i)
    # phase B: D-pad UP all the way back
    for i in range(n):
        s.press(DP["U"]); s.mark("U %d" % i)
        if i == n - 1:
            s.shot("pn_U%02d" % i)
    # phase C: walk down again and on every slider row press RIGHT x2 then LEFT x1, reading the cvar back
    s.mark("C start")
    for i, (k, nm, cv) in enumerate(rows):
        s.press(DP["D"]); s.mark("C row %d %s %s" % (i, k, nm))
        if k in ("Slider",) and cv:
            s.cmd(cv); s.t += 80
            s.press(DP["R"], 160, 400); s.press(DP["R"], 160, 400); s.cmd(cv); s.t += 80
            s.press(DP["L"], 160, 400); s.cmd(cv); s.t += 80
    s.shot("pn_C_end")
    # phase D: the left STICK is a cursor: push down, then right, then park
    s.mark("stick")
    s.stick(0, 32767, 500); s.shot("pn_stick_down")
    s.stick(32767, 0, 500); s.shot("pn_stick_right")
    s.press(A, 200, 900); s.shot("pn_A")
    s.press(B, 200, 1500); s.shot("pn_B")
    s.cmd("echo ^~^~^ MR done pn"); s.t += 800; s.cmd("quit")
    return s


def stick_script(page, w, h):
    """left-stick probes on a slider page: cursor parked on a slider (@cursor), then stick / A used the way a handheld player would."""
    s = Script()
    s.cmd("pushmenu " + page); s.t += 2500
    def park(x, y):
        s.S.append("@cursor %d %d %d" % (s.t, x, y)); s.t += 600
    s.cmd("joy_lookY"); s.t += 80
    # 1. cursor on the lookY slider thumb, hold A and drag right with the stick (what a mouse drag does)
    park(566, 130); s.shot("sk_1_parked")
    s.state(A); s.t += 300; s.state(A, 32767, 0); s.t += 500; s.state(A); s.t += 200; s.state(0); s.t += 600
    s.cmd("joy_lookY"); s.t += 80; s.shot("sk_1_dragged")
    # 2. cursor on the track, a plain A click (click-to-position)
    park(780, 169); s.press(A, 200, 700); s.cmd("joy_adsScale"); s.t += 80
    # 3. cursor on the slider, D-pad right/left (the widget under the cursor gets the arrow)
    park(700, 208); s.press(DP["R"], 160, 500); s.press(DP["R"], 160, 500); s.cmd("joy_threshold"); s.t += 80
    # 4. stick UP / DOWN from a slider row: does the cursor leave it? (it is a free cursor: how far per flick?)
    park(656, 208)
    s.stick(0, 20000, 120); s.cmd("echo ^~^~^ STEP flick_down"); s.t += 100
    s.stick(0, -20000, 120); s.cmd("echo ^~^~^ STEP flick_up"); s.t += 100
    s.shot("sk_4_flicks")
    # 5. right stick = wheel ticks on the list under the cursor (nothing to scroll here: must not break focus)
    s.state(0, 0, 0, 0, 25000); s.t += 400; s.state(0); s.t += 400
    s.shot("sk_5_after_rs")
    s.cmd("echo ^~^~^ MR done pn"); s.t += 800; s.cmd("quit")
    return s


def sweep_script(pages, w, h):
    """one launch, several pages: for each, a snake walk with the D-pad (D x16, R, U x16, R, D x16, L, U x16); the debug log
    (ui_clickdebug 2 for the first press = PADCAND list; 1 after = PADNAV lines incl. 'eaten by') is analysed by pn_report.py"""
    s = Script()
    for pg in pages:
        s.cmd("forcemenu main"); s.t += 1200
        s.cmd("echo ^~^~^ PAGE " + pg); s.cmd("pushmenu " + pg); s.t += 1800
        s.S.append("@cursor %d 4 4" % s.t); s.t += 400
        s.cmd("set ui_clickdebug 2"); s.t += 60
        s.press(DP["D"], 120, 330)
        s.cmd("set ui_clickdebug 1"); s.t += 60
        s.shot("sw_%s" % pg)
        for d in "D" * 15 + "R" + "U" * 16 + "R" + "D" * 16 + "L" + "U" * 16:
            s.press(DP[d], 120, 330)
    s.cmd("echo ^~^~^ MR done pn"); s.t += 800; s.cmd("quit")
    return s


def key_script_lines(page):
    """keyboard run: post_key is driven from python, not the pad script; the pad script only opens the page + quits."""
    s = Script()
    s.cmd("pushmenu " + page); s.t += 2500
    return s


def setup(exe_label):
    src = EXES.get(exe_label, exe_label)
    os.makedirs(os.path.join(CLIENT, "home", "maintt", "configs"), exist_ok=True)
    shutil.copy2(src, mr.EXE)
    for f in mr.LIVE_FILES:
        if f == "openmohaa.exe":
            continue
        s_, d_ = os.path.join(mr.LIVE, f), os.path.join(CLIENT, f)
        if os.path.exists(s_) and (not os.path.exists(d_) or os.path.getsize(s_) != os.path.getsize(d_)):
            shutil.copy2(s_, d_)
    log("setup ok exe", exe_label, src)


def run_pad(exe_label, page, tag, suite="pad"):
    w, h = 1280, 720
    if hg.user_game_running():
        raise SystemExit("the user's game is running")
    setup(exe_label)
    out = os.path.join(mr.RUNS, tag)
    os.makedirs(out, exist_ok=True)
    sc = pad_script(page, w, h, suite)
    sp = os.path.join(out, "pad.txt")
    open(sp, "w", newline="\n").write(sc.text())
    lines = ["set developer 0", "set in_padDebug 1", "set ui_clickdebug 1", "wait 9000", "echo ^~^~^ MR start pn", "set in_padTestGo 1"]
    mr.cfg_lines = lambda t, c, _l=lines: _l
    orig = hw.launch_background

    def lb(exe, args, cwd, **kw):
        return orig(exe, list(args) + ["+set", "in_padTestScript", sp.replace("\\", "/")], cwd, **kw)
    hw.launch_background = lb
    hg.acquire_slot(mr.OWNER, mr.EXE, mr.HOME, [], minutes=20)
    try:
        r = mr.one("x_" + tag, w, h, 0)
    finally:
        hw.launch_background = orig
        hg.release_slot(mr.OWNER)
    # mr.one files outputs under RUNS/x_<tag>; fold into <tag>
    src = os.path.join(mr.RUNS, "x_" + tag)
    for fn in os.listdir(src):
        shutil.move(os.path.join(src, fn), os.path.join(out, fn))
    os.rmdir(src)
    json.dump(r, open(os.path.join(out, "result.json"), "w"), indent=1)
    return r


def post_ext(c, vk, down_ms=50):
    """key press with the EXTENDED bit for the arrows (else SDL reads them as numpad 2/4/6/8)"""
    h = c.hwnd()
    if not h:
        return False
    u32 = hw.u32
    sc = u32.MapVirtualKeyW(vk, 0)
    ext = (1 << 24) if vk in (0x25, 0x26, 0x27, 0x28) else 0
    u32.PostMessageW(h, 0x0100, vk, 1 | (sc << 16) | ext)
    time.sleep(down_ms / 1000.0)
    u32.PostMessageW(h, 0x0101, vk, 1 | (sc << 16) | ext | (1 << 30) | (1 << 31))
    return True


VK = {"U": 0x26, "D": 0x28, "L": 0x25, "R": 0x27}


def run_keys(exe_label, pages, tag):
    """keyboard sweep: same snake as the pad one, but real WM_KEYDOWN arrows posted to our window; F12 runs isstep.cfg"""
    if hg.user_game_running():
        raise SystemExit("the user's game is running")
    setup(exe_label)
    out = os.path.join(mr.RUNS, tag)
    os.makedirs(out, exist_ok=True)
    mr.seed_home(0, overlay=True)
    boot = ["set developer 0", "set ui_clickdebug 1", 'bind F12 "exec isstep.cfg"', "echo ^~^~^ MR start keys"]
    args = [mr.EXE, "+set", "com_target_game", "2", "+set", "fs_basepath", mr.GOG, "+set", "fs_homepath", mr.HOME,
            "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", "1280",
            "+set", "r_customheight", "720", "+set", "r_fullscreen", "0", "+set", "cl_memorial", "0",
            "+set", "logfile", "2", "+set", "com_maxfps", "60", "+exec", "mr_run.cfg"]
    args, late = hw.apply_policy(args, width=1280, height=720)
    open(os.path.join(mr.MAINTT, "mr_run.cfg"), "w", newline="\n").write("\n".join(late + boot) + "\n")
    hg.acquire_slot(mr.OWNER, mr.EXE, mr.HOME, [], minutes=20)
    c = hw.launch_background(args[0], args[1:], mr.CLIENT, policy=False, log=log)
    hg.set_slot_pid(mr.OWNER, c.proc.pid)

    def f12(lines):
        open(os.path.join(mr.MAINTT, "isstep.cfg"), "w", newline="\n").write("\n".join(lines) + "\n")
        c.post_key(0x7B)
        time.sleep(0.8)

    try:
        t0 = time.time()
        while "MR start keys" not in (open(mr.LOG, "rb").read().decode("latin-1") if os.path.exists(mr.LOG) else ""):
            time.sleep(1)
            if time.time() - t0 > 90:
                raise RuntimeError("never booted")
        time.sleep(8)
        for pg in pages:
            f12(["forcemenu main"]); time.sleep(1.0)
            f12(["echo ^~^~^ PAGE " + pg, "pushmenu " + pg]); time.sleep(1.5)
            f12(["set ui_clickdebug 2"]); post_ext(c, VK["D"]); time.sleep(0.4)
            f12(["set ui_clickdebug 1", "screenshot kb_%s" % pg])
            for d in "D" * 15 + "R" + "U" * 16 + "R" + "D" * 16 + "L" + "U" * 16:
                post_ext(c, VK[d]); time.sleep(0.28)
        f12(["echo ^~^~^ MR done keys", "quit"])
        try:
            c.proc.wait(20)
        except Exception:
            pass
    finally:
        if c.proc.poll() is None:
            c.proc.kill()
        c.close()
        hg.release_slot(mr.OWNER)
        for fn in sorted(os.listdir(mr.SHOTS)):
            shutil.move(os.path.join(mr.SHOTS, fn), os.path.join(out, fn))
        shutil.copyfile(mr.LOG, os.path.join(out, "qconsole.log"))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "dry":
        print(pad_script(sys.argv[2], 1280, 720).text()[:3000])
    elif cmd == "keys":
        print(run_keys(sys.argv[2], sys.argv[3].split(","), sys.argv[4]))
    elif cmd == "run":
        exe, page = sys.argv[2], sys.argv[3]
        tag = sys.argv[4] if len(sys.argv) > 4 else "%s_%s" % (exe, page)
        print(run_pad(exe, page, tag, sys.argv[5] if len(sys.argv) > 5 else "pad"))
