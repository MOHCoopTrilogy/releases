"""mpprog_test.py - in-game proof for the MP unlock-progress persistence fix (mpprog, 2026-11-10).

    python -I mpprog_test.py run <runname> --mod <mod worktree> [--kills1 20] [--kills2 5]
    python -I mpprog_test.py coop <runname> --mod <mod worktree>       (the coop control)

MP: a dedicated server on dm/mohdm1 with 3 bots and ONE private client (fresh fake identity). The shipped dev hook
mp_progression.scr::selftest_human (coop_mpProgHumanTest 1, seeded nowhere) makes the human the attacker of N real
Player kills on bots, through the engine's player_killed delegate - the same path a trigger pull takes. Session 1
earns, the client quits (its omconfig is written), both processes stop; session 2 is a NEW server process (so the
in-process high-water game.coop_mpProgLW cannot carry anything) and the same client home. The record must come back
from the client's own carried blob: server prints MPPROG load VERIFIED and the totals continue.

COOP control: a dedicated m1l1 coop server + the same client; a test-pak devprobe makes the human kill AI actors,
flushes, restarts the server, checks the per-weapon challenge stat came back.

Rules honoured: harness_window launch (guard on, DISPLAY = the 1920x1080 screen, muted, watch_audio), in_mouse 0,
in_nograb 1, in_gamepad 0, in_joystick 0, coop_tinnitusBaseVol/Muffle/woundMuffleVol 0 on the SERVER after autoexec,
dedicated servers CREATE_NO_WINDOW, private ports 12961-12963, only PIDs this script started are stopped. The user's
live home is only READ (autoexec/coop_defaults/omconfig copied once into the test homes). Everything lives on G:.
"""
import hashlib, os, re, shutil, subprocess, sys, time, zipfile

os.environ.setdefault("HZM_TEST_RES", "1920x1080")   # the 1080p screen only (the user may be playing)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LIVE = r"G:\mohaa-gl2\home\maintt"           # READ ONLY
H = r"G:\mohaa-mpprog"
BIN = os.path.join(H, "bin")
OWNER = "mpprog"
CPORT, SPORT = 12961, 12962
RCON = "mpprog11"
CODEPAK = "zzzzzz_co-op_hzm_mod_code.pk3"
TESTPAK = "zzzzzzzzzzzz_mpprogtest.pk3"
ST = {"run": None, "client": None, "server": None, "step": 0}
RES = []
HERE = os.path.dirname(os.path.abspath(__file__))


def log(*a):
    line = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(line, flush=True)
    if ST["run"]:
        with open(os.path.join(H, ST["run"] + ".log"), "a") as f:
            f.write(line + "\n")


def check(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    log("PASS" if ok else "FAIL", name, detail)


def read(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


def guard():
    c = ST["client"]
    if c is not None and c.watcher.violations:
        raise RuntimeError("window policy violation: %s" % (c.watcher.violations[:3],))
    if c is not None and c.proc.poll() is not None:
        raise RuntimeError("client exited")


def wait_for(path, pat, timeout, start=0):
    rx = re.compile(pat)
    t0 = time.time()
    while time.time() - t0 < timeout:
        guard()
        m = rx.search(read(path), start)
        if m:
            return m
        time.sleep(0.5)
    return None


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def prep_bins():
    os.makedirs(BIN, exist_ok=True)
    for f in ("openmohaa.exe", "omohaaded.exe", "game.dll", "cgame.dll", "OpenAL64.dll", "SDL2.dll", "libcurl.dll",
              "renderer_opengl1.dll", "renderer_opengl2.dll"):
        s, t = os.path.join(GOG, f), os.path.join(BIN, f)
        if os.path.isfile(s) and (not os.path.isfile(t) or md5f(s) != md5f(t)):
            shutil.copyfile(s, t)
    log("bins game", md5f(os.path.join(BIN, "game.dll"))[:8], "exe", md5f(os.path.join(BIN, "openmohaa.exe"))[:8])


def build_pak(mod):
    rev = sys.argv[sys.argv.index("--rev") + 1] if "--rev" in sys.argv else "HEAD"
    full = subprocess.run(["git", "-C", mod, "rev-parse", rev], capture_output=True, text=True, check=True).stdout.strip()
    code = os.path.join(H, "code_%s.pk3" % full[:10])
    if not os.path.isfile(code):
        tops = [t for t in subprocess.run(["git", "-C", mod, "ls-tree", "--name-only", full], capture_output=True,
                                          text=True, check=True).stdout.splitlines()
                if t not in ("sound", "textures", "models", "gfx", "env") and not t.lower().endswith(".pk3")
                and not t.startswith(".git")]
        subprocess.run(["git", "-C", mod, "archive", "--format=zip", "-1", "-o", code, full, "--"] + tops, check=True)
    test = os.path.join(H, TESTPAK)
    with zipfile.ZipFile(test, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/devprobe.scr", open(os.path.join(HERE, "mpprog_devprobe.scr"), "rb").read())
    log("pak", full[:10], os.path.getsize(code))
    return code, test, full


def home(tag):
    return os.path.join(H, "home_%s_%s" % (ST["run"], tag))


def seed_home(hm, code, test):
    mt = os.path.join(hm, "maintt")
    os.makedirs(os.path.join(mt, "configs"), exist_ok=True)
    os.makedirs(os.path.join(mt, "coop_mod", "save"), exist_ok=True)
    for f in ("autoexec.cfg", "coop_defaults.cfg"):
        shutil.copyfile(os.path.join(LIVE, f), os.path.join(mt, f))
    shutil.copyfile(code, os.path.join(mt, CODEPAK))
    shutil.copyfile(test, os.path.join(mt, TESTPAK))
    open(os.path.join(mt, "whatsnew_pending.cfg"), "wb").write(b"// up to date\r\n")
    return mt


MPKEYS = re.compile(r"(?im)^seta (coop_mp(ProgBlob|Total|Rank|Cnt_\w+|Uw_\w+|UnlockC_\w+|ChD\d+|B\d+|S_\w+|UP_\w+))"
                    r" \"[^\"\r\n]*\"\r?\n")


def seed_pc(code, test):
    hm = home("pc")
    mt = seed_home(hm, code, test)
    key = os.urandom(2048)
    open(os.path.join(hm, "qkey"), "wb").write(key)
    gid = hashlib.md5(key).hexdigest().upper()
    cfg = read(os.path.join(LIVE, "configs", "omconfig.cfg"))
    cfg = MPKEYS.sub("", cfg)       # a FRESH MP record: no carried blob, no stale padlock cvars
    cfg = re.sub(r'(?im)^seta name "[^"\r\n]*"', 'seta name "MPProgTester"', cfg)
    cfg = re.sub(r'(?im)^seta coop_xp_totalOwn "[^"\r\n]*"', 'seta coop_xp_totalOwn "0"', cfg)
    open(os.path.join(mt, "configs", "omconfig.cfg"), "wb").write(cfg.encode("latin-1"))
    log("PC home", hm, "fake id", gid)
    return hm, mt, gid


def start_server(tag, code, test, mapname, extra):
    hm = home("srv" + tag)
    mt = seed_home(hm, code, test)
    lines = ["set rconPassword " + RCON, "set sv_fps 20", "set sv_timeout 900", "set g_inactivespectate 0", "set g_inactivekick 0", "set fraglimit 0", "set timelimit 0", "set coop_dbno 0", "set coop_dev 1",
             "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
             "set coop_weatherPin 0"] + extra + ["map " + mapname]
    open(os.path.join(mt, "ded_mpp.cfg"), "w", newline="\n").write("\n".join(lines) + "\n")
    args = [os.path.join(BIN, "omohaaded.exe")]
    for k, v in (("com_target_game", "2"), ("dedicated", "1"), ("fs_basepath", GOG), ("fs_homepath", hm),
                 ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", str(SPORT)), ("sv_maxclients", "8"),
                 ("g_gametype", "2"), ("developer", "1"), ("logfile", "2"),
                 ("sv_maxbots", "4" if mapname.startswith("dm/") else "0"),
                 ("sv_numbots", "3" if mapname.startswith("dm/") else "0")):
        args += ["+set", k, v]
    args += ["+exec", "ded_mpp.cfg"]
    p = subprocess.Popen(args, cwd=BIN, **hw.popen_kwargs())
    ST["server"] = p
    lg = os.path.join(mt, "qconsole.log")
    log("server", tag, "pid", p.pid, mapname, hm)
    m = wait_for(lg, r"Could not load[^\r\n]*|Can't find map|MPPROG init subscribed|initialising coop weapon loadout", 300)
    if not m or not m.group(0).startswith(("MPPROG", "initialising")):
        raise RuntimeError("server %s never became ready: %s" % (tag, m.group(0) if m else "timeout"))
    time.sleep(3)
    return mt, lg


def stop_server():
    p = ST["server"]
    ST["server"] = None
    if p is not None and p.poll() is None:
        p.kill()          # only the PID this script started
        p.wait(20)
        log("server stopped pid", p.pid)


def launch_client(hm, W=960, Hh=540):
    mt = os.path.join(hm, "maintt")
    boot = ['bind F12 "exec isstep.cfg"', "set ui_gmbox 0", "ui_checkrestart", "set coop_idleInspect 0",
            "set com_maxfps 60", "set in_nograb 1", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0",
            "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "set s_volume 0"]
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", hm), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(Hh)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_enabled", "1"), ("net_ip", "127.0.0.1"),
            ("net_port", str(CPORT)), ("in_gamepad", "0"), ("in_joystick", "0")]
    args = [os.path.join(BIN, "openmohaa.exe")]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "mpp_on.cfg", "+connect", "127.0.0.1:%d" % SPORT]
    args, late = hw.apply_policy(args, width=W, height=Hh)
    boot += late
    open(os.path.join(mt, "mpp_on.cfg"), "w", newline="\n").write("\n".join(boot) + "\n")
    hg.acquire_slot(OWNER, args[0], hm, [CPORT], 60)
    c = hw.launch_background(args[0], args[1:], BIN, policy=False, log=log, watch_audio=True)
    ST["client"] = c
    try:
        hg.set_slot_pid(OWNER, c.proc.pid)
    except Exception as e:
        log("slot pid note:", e)
    log("client pid", c.proc.pid)
    return os.path.join(mt, "qconsole.log")


def step(hm, lines, timeout=120):
    ST["step"] += 1
    mt = os.path.join(hm, "maintt")
    lg = os.path.join(mt, "qconsole.log")
    mk = "^~^~^ MPPSTEP %d" % ST["step"]
    open(os.path.join(mt, "isstep.cfg"), "w", newline="\n").write("\n".join(lines + ["echo " + mk]) + "\n")
    start = len(read(lg))
    for _ in range(5):
        ST["client"].post_key(0x7B)
        if wait_for(lg, r"execing isstep\.cfg", 6, max(0, start - 10)):
            break
    else:
        raise RuntimeError("step %d: F12 never executed isstep.cfg" % ST["step"])
    if not wait_for(lg, re.escape(mk) + r"\b", timeout, max(0, start - 10)):
        raise RuntimeError("step %d timed out" % ST["step"])


def stop_client(hm):
    c = ST["client"]
    if c is None:
        return
    if c.proc.poll() is None:
        open(os.path.join(hm, "maintt", "isstep.cfg"), "w", newline="\n").write("quit\n")
        try:
            c.post_key(0x7B)
            c.proc.wait(40)
        except Exception:
            c.proc.kill()
    rep = c.report() if hasattr(c, "report") else None
    ST["client"] = None
    try:
        hg.release_slot(OWNER)
    except Exception:
        pass
    log("client stopped; window report", rep)


def shot(hm, name, menu):
    sd = os.path.join(hm, "maintt", "screenshots")
    before = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    pre = ["set coop_mpSrP%d %d" % (i, 1 if i == 0 else 0) for i in range(7)] if menu == "coop_mp_record" else []
    step(hm, pre + ["pushmenu " + menu, "wait 400", "screenshotJPEG", "wait 300", "popmenu 0", "wait 100"])
    time.sleep(1.0)
    new = sorted((set(os.listdir(sd)) if os.path.isdir(sd) else set()) - before)
    if not new:
        log("screenshot missing", name)
        return None
    dst = os.path.join(H, "%s_%s%s" % (ST["run"], name, os.path.splitext(new[-1])[1]))
    shutil.move(os.path.join(sd, new[-1]), dst)
    log("screenshot", dst)
    return dst


def cvars(mt):
    cfg = read(os.path.join(mt, "configs", "omconfig.cfg"))
    return dict(re.findall(r'(?im)^seta (coop_mp\w+) "([^"\r\n]*)"', cfg))


def wait_active(slog):
    m = wait_for(slog, r"to CS_ACTIVE", 300)
    if not m:
        raise RuntimeError("client never went CS_ACTIVE")
    time.sleep(6)


def join(hm, slog):
    wait_active(slog)
    st = len(read(slog))
    for _ in range(4):
        step(hm, ["popmenu 0", "wait 10", "join_team allies", "wait 20", "primarydmweapon rifle", "wait 20",
                  "popmenu 0", "wait 40", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if wait_for(slog, r"MPPROGTEST human found e[0-9]+ [^\r\n]*", 40, st):
            return True
    return False


def mp_session(tag, code, test, hm, mt, kills):
    smt, slog = start_server(tag, code, test, "dm/mohdm1",
                             ["set coop_mpProgHumanTest 1", "set coop_mpProgHumanKills %d" % kills,
                              "set coop_mpProgFarmCooldown 0", "set g_teamdamage 0"])
    clog = launch_client(hm)
    out = {"slog": slog, "clog": clog, "smt": smt}
    try:
        ok = join(hm, slog)
        check("%s client joined and the hook found the human" % tag, ok)
        d = wait_for(slog, r"\^~\^~\^ MPPROGTEST human done kills=[0-9]+[^\r\n]*", 120 + kills * 22, 0)
        out["done"] = d.group(0) if d else None
        check("%s %d kills credited to the human" % (tag, kills), d, out["done"])
        time.sleep(4)        # the push throttle (3 s) - the forced flush in the hook covers the last kill
        out["shot_rec"] = shot(hm, tag + "_record", "coop_mp_record")
        out["shot_arm"] = shot(hm, tag + "_armory", "coop_mpa_armory")
    finally:
        stop_client(hm)
        stop_server()
    out["srv"] = read(slog)
    out["cli"] = read(clog)
    out["cv"] = cvars(mt)
    return out


def mp_run(mod, k1, k2):
    prep_bins()
    code, test, full = build_pak(mod)
    hm, mt, gid = seed_pc(code, test)
    a = mp_session("S1", code, test, hm, mt, k1)
    blob = a["cv"].get("coop_mpProgBlob", "")
    log("S1 client omconfig blob=[%s]" % blob)
    log("S1 client cvars", {k: v for k, v in a["cv"].items() if not k.startswith(("coop_mpB", "coop_mpChD"))})
    log("S1 userinfo line", (re.findall(r"MPPROGTEST human found e[0-9]+ [^\r\n]*", a["srv"]) or [""])[-1])
    bad = re.findall(r"Can't use keys or values[^\r\n]*coop_mpProgBlob[^\r\n]*|Info string length exceeded", a["cli"])
    check("S1 client accepted the blob into userinfo (no blacklist / length refusal)", not bad, bad[:2])
    check("S1 the carried blob reached the client's archived config", blob.startswith("4") and len(blob) > 40, blob[:80])
    b = mp_session("S2", code, test, hm, mt, k2)
    ld = re.findall(r"MPPROG load (VERIFIED|REJECTED)[^\r\n]*", b["srv"])
    check("S2 a fresh server process loaded the carried record (MPPROG load VERIFIED)", ld and ld[0] == "VERIFIED",
          (re.findall(r"MPPROG load [^\r\n]*", b["srv"]) or ["no load line"])[0][:200])
    found = re.findall(r"MPPROGTEST human found e[0-9]+ [^\r\n]*", b["srv"])
    k1r = int((re.search(r"human done kills=\d+ total=(\d+)", a["srv"]) or [0, 0])[1])
    check("S2 total at join = S1 credited total (%d)" % k1r, found and (" total=%d " % k1r) in found[-1] + " ", found[-1] if found else "")
    k2r = int((re.search(r"human done kills=(\d+)", b["done"] or "") or [0, 0])[1])
    check("S2 total after more kills = S1 + S2", b["done"] and (" total=%d " % (k1r + k2r)) in b["done"] + " ",
          b["done"])
    cv = b["cv"]
    check("S2 armory unlock cvars still set from persisted counts (class unlock + wt tier 2)",
          any(v == "1" for k, v in cv.items() if k.startswith("coop_mpUnlockC_")),
          {k: v for k, v in cv.items() if k.startswith(("coop_mpUnlockC_", "coop_mpCnt_", "coop_mpTotal"))})
    for name, ok, det in RES:
        print("%-5s %s %s" % ("PASS" if ok else "FAIL", name, det if not ok else ""))
    return all(ok for _, ok, _ in RES)


def coop_run(mod):
    prep_bins()
    code, test, full = build_pak(mod)
    hm, mt, gid = seed_pc(code, test)
    res = {}
    for tag in ("C1", "C2"):
        smt, slog = start_server(tag, code, test, "m1l1", ["set g_ai 1", "set coop_mpptest 1"])
        if tag == "C2":       # the same server home restarted: the coop record is the server's save file
            pass
        clog = launch_client(hm)
        try:
            wait_active(slog)
            st = len(read(slog))
            for _ in range(4):
                step(hm, ["popmenu 0", "wait 10", "join_team allies", "wait 20", "primarydmweapon rifle", "wait 20",
                          "popmenu 0", "wait 40", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
                if wait_for(slog, r"MPPCOOP found e[0-9]+[^\r\n]*", 60, st):
                    break
            d = wait_for(slog, r"\^~\^~\^ MPPCOOP done kills=[0-9]+[^\r\n]*", 240, st)
            res[tag] = d.group(0) if d else None
            log(tag, res[tag])
            res[tag + "found"] = (re.findall(r"MPPCOOP found e[0-9]+[^\r\n]*", read(slog)) or [None])[-1]
        finally:
            stop_client(hm)
            stop_server()
        res[tag + "saves"] = {f: read(os.path.join(smt, "coop_mod", "save", f))[:200]
                              for f in os.listdir(os.path.join(smt, "coop_mod", "save"))}
        res[tag + "pc"] = {f: read(os.path.join(mt, "coop_mod", "save", f))[:200]
                           for f in os.listdir(os.path.join(mt, "coop_mod", "save"))}
        log(tag, "server saves", res[tag + "saves"])
        log(tag, "pc saves", res[tag + "pc"])
    return res


if __name__ == "__main__":
    mode, run = sys.argv[1], sys.argv[2]
    ST["run"] = run
    mod = sys.argv[sys.argv.index("--mod") + 1]
    os.makedirs(H, exist_ok=True)
    if hg.user_game_running():
        log("user game running - 1080p screen only (HZM_TEST_RES=%s)" % os.environ["HZM_TEST_RES"])
    try:
        if mode == "run":
            k1 = int(sys.argv[sys.argv.index("--kills1") + 1]) if "--kills1" in sys.argv else 20
            k2 = int(sys.argv[sys.argv.index("--kills2") + 1]) if "--kills2" in sys.argv else 5
            ok = mp_run(mod, k1, k2)
            sys.exit(0 if ok else 1)
        else:
            coop_run(mod)
    finally:
        try:
            stop_client(home("pc"))
        except Exception:
            pass
        stop_server()
