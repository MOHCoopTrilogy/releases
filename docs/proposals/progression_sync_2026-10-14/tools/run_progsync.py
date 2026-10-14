"""run_progsync.py - in-game proof of bug-3903 (progression follows the player) on the private harness copy
G:\\mohaa-hudfeed5 (slot owner "hudfeed5"; its own sub-folder progsync\\ for binaries, so the lane's root files are
untouched). DISPLAY2 through harness_window only, net_ip 127.0.0.1, ports 12781 (client) 12782/12783 (servers).
Never touches G:\\mohaa-gl2, the user's saves or the public servers; the GOG root is only the read-only basepath
(and the source of the RELEASED binaries that are copied, never modified).

    python -I run_progsync.py run <runname> [--phases 1,2,3,4,5]

A FAKE identity: a random 2048-byte qkey in the test PC home, so cl_guid = MD5(qkey) is known in advance and the
PC's save files are seeded for it before the first launch. Each phase prints PASS/FAIL lines; everything (logs, the
three homes, screenshots) is MOVED to H:\\hzm_archive\\progression_sync\\<run>\\ at the end.

Phases
  1 remote client, dedicated server A (fresh: no record) - join, award+flush, unlock, award then disconnect
    (XP fold-in), reconnect mid-mission
  2 the same client straight on to dedicated server B, which already holds an OLDER/different record (merge case)
  3 OLD client (released cgame.dll) on server B - today's behaviour, no upload, no download
  4 OLD server (released game.dll) with the NEW client - nothing breaks, nothing written on the PC
  5 listen host (new client hosts the map itself) - no upload, unchanged
"""
import hashlib, json, os, re, shutil, subprocess, sys, time, zipfile

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

ROOT = r"C:\mohaa-coop-dev"
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(ROOT, "hzm-mod-progsync")
ENGINE = os.path.join(ROOT, "openmohaa-hzm-progsync", ".cmake", "code")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
H = r"G:\mohaa-hudfeed5"
BIN = os.path.join(H, "progsync")          # new game.dll + cgame.dll
BIN_OLD = os.path.join(H, "progsync_old")  # released game.dll + cgame.dll (old server / old client)
OWNER = "hudfeed5"
CPORT = 12781
SPORT = {"A": 12782, "B": 12783, "OLD": 12784}
RCON = "psync14"
MAP = "m3l2"
SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\progsync"
ARCHIVE = r"H:\hzm_archive\progression_sync"
CODEPAK = "zzzzzz_co-op_hzm_mod_code.pk3"
TESTPAK = "zzzzzzzzzzzz_progsynctest.pk3"
TYPES = ("xp", "chal", "unlocks", "pins", "pend", "medals", "bpfound")
RES = []
ST = {"run": None, "client": None, "servers": {}, "step": 0}


def log(*a):
    line = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(line, flush=True)
    if ST["run"]:
        with open(os.path.join(SCR, ST["run"] + ".log"), "a") as f:
            f.write(line + "\n")


def check(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    log("PASS" if ok else "FAIL", name, detail)


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def home(tag):
    # every home path carries "G:\mohaa-hudfeed5\home" so harness_guard classifies our processes as HARNESS
    return os.path.join(H, "home_ps_%s_%s" % (ST["run"], tag))


def read(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


def wait_for(path, pat, timeout, start=0):
    rx = re.compile(pat)
    t0 = time.time()
    while time.time() - t0 < timeout:
        guard()
        m = rx.search(read(path), start)
        if m:
            return m
        time.sleep(0.4)
    return None


def guard():
    c = ST["client"]
    if c is not None and c.watcher.violations:
        raise RuntimeError("window policy violation: %s" % (c.watcher.violations[:3],))
    if c is not None and c.proc.poll() is not None:
        raise RuntimeError("client exited")


# ---------------------------------------------------------------------------------------------- binaries + paks
def prep_bins():
    for d, game, cgame in ((BIN, os.path.join(ENGINE, "server", "fgame", "Release", "game.dll"),
                            os.path.join(ENGINE, "client", "cgame", "Release", "cgame.dll")),
                           (BIN_OLD, os.path.join(GOG, "game.dll"), os.path.join(GOG, "cgame.dll"))):
        os.makedirs(d, exist_ok=True)
        for src, dst in (("openmohaa.exe", "openmohaa_progsync.exe"), ("omohaaded.exe", "omohaaded_progsync.exe"),
                         ("OpenAL64.dll", None), ("SDL2.dll", None), ("libcurl.dll", None),
                         ("renderer_opengl1.dll", None), ("renderer_opengl2.dll", None)):
            s, t = os.path.join(GOG, src), os.path.join(d, dst or src)
            if not os.path.isfile(t) or md5f(t) != md5f(s):
                shutil.copyfile(s, t)
        shutil.copyfile(game, os.path.join(d, "game.dll"))
        shutil.copyfile(cgame, os.path.join(d, "cgame.dll"))
        log("bins", d, "game", md5f(os.path.join(d, "game.dll"))[:8], "cgame", md5f(os.path.join(d, "cgame.dll"))[:8])
    # the released cgame for the OLD-client phase
    shutil.copyfile(os.path.join(GOG, "cgame.dll"), os.path.join(BIN, "cgame_release.dll"))
    shutil.copyfile(os.path.join(BIN, "cgame.dll"), os.path.join(BIN, "cgame_new.dll"))


def git_mod(*a):
    return subprocess.run(["git", "-C", MOD] + list(a), capture_output=True, check=True).stdout


def build_paks():
    os.makedirs(SCR, exist_ok=True)
    full = git_mod("rev-parse", "HEAD").decode().strip()
    code = os.path.join(SCR, "code_%s.pk3" % full[:10])
    if not os.path.isfile(code):
        tops = [t for t in git_mod("ls-tree", "--name-only", full).decode().splitlines()
                if t not in ("sound", "textures", "models", "gfx", "env") and not t.lower().endswith(".pk3")
                and not t.startswith(".git")]
        subprocess.run(["git", "-C", MOD, "archive", "--format=zip", "-1", "-o", code, full, "--"] + tops, check=True)
    test = os.path.join(SCR, TESTPAK)
    with zipfile.ZipFile(test, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/devprobe.scr", open(os.path.join(HERE, "pstest_devprobe.scr"), "rb").read())
    log("paks code", full[:10], "test overlay", os.path.getsize(test))
    return code, test, full


# ---------------------------------------------------------------------------------------------- homes
PRISTINE = os.path.join(H, "pristine")


def seed_common(hm, code, test):
    mt = os.path.join(hm, "maintt")
    os.makedirs(os.path.join(mt, "configs"), exist_ok=True)
    os.makedirs(os.path.join(mt, "coop_mod", "save"), exist_ok=True)
    for f in ("autoexec.cfg", "coop_defaults.cfg"):
        shutil.copyfile(os.path.join(PRISTINE, f), os.path.join(mt, f))
    shutil.copyfile(code, os.path.join(mt, CODEPAK))
    shutil.copyfile(test, os.path.join(mt, TESTPAK))
    return mt


def write_saves(mt, gid, recs):
    for t, v in recs.items():
        with open(os.path.join(mt, "coop_mod", "save", "%s_%s.dat" % (t, gid)), "wb") as f:
            f.write(v.encode("latin-1"))


def saves(mt, gid):
    out = {}
    for t in TYPES:
        p = os.path.join(mt, "coop_mod", "save", "%s_%s.dat" % (t, gid))
        out[t] = read(p) if os.path.isfile(p) else None
    return out


def seed_pc(code, test, recs):
    hm = home("pc")
    mt = seed_common(hm, code, test)
    key = os.urandom(2048)
    open(os.path.join(hm, "qkey"), "wb").write(key)
    gid = hashlib.md5(key).hexdigest().upper()
    cfg = read(os.path.join(PRISTINE, "omconfig.cfg"))
    cfg = re.sub(r'(?im)^seta coop_loA([1-4]) "[^"\r\n]*"', r'seta coop_loA\1 ""', cfg)
    # a stale archived total far above anything real: if the shutdown fold-in ever trusted an old value, the
    # PC's xp file would read 999999 (it must only take a total THIS server pushed this session)
    cfg = re.sub(r'(?im)^seta coop_xp_totalOwn "[^"\r\n]*"', 'seta coop_xp_totalOwn "999999"', cfg)
    cfg = re.sub(r'(?im)^seta name "[^"\r\n]*"', 'seta name "PSTester"', cfg)
    open(os.path.join(mt, "configs", "omconfig.cfg"), "wb").write(cfg.encode("latin-1"))
    open(os.path.join(mt, "whatsnew_pending.cfg"), "wb").write(b"// up to date\r\n")
    write_saves(mt, gid, recs)
    log("PC home", hm, "fake id", gid)
    return hm, mt, gid


# ---------------------------------------------------------------------------------------------- processes
def start_server(tag, bins, code, test, recs=None, gid=None):
    hm = home("srv" + tag)
    mt = seed_common(hm, code, test)
    if recs:
        write_saves(mt, gid, recs)
    open(os.path.join(mt, "ded_ps.cfg"), "w", newline="\n").write("\n".join([
        "set rconPassword " + RCON, "set sv_fps 40", "set g_ai 0", "set coop_dbno 0", "set coop_dev 1",
        "set sv_maxbots 0", "set sv_numbots 0", "set coop_weatherPin 0", "set coop_lockLoadout 0",
        "set coop_pstest 0", "map " + MAP]) + "\n")
    args = [os.path.join(bins, "omohaaded_progsync.exe")]
    for k, v in (("com_target_game", "2"), ("dedicated", "1"), ("fs_basepath", GOG), ("fs_homepath", hm),
                 ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", str(SPORT[tag])), ("sv_maxclients", "4"), ("g_gametype", "2"),
                 ("developer", "1"), ("logfile", "2")):
        args += ["+set", k, v]
    args += ["+exec", "ded_ps.cfg"]
    p = subprocess.Popen(args, cwd=bins, creationflags=0x08000000, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ST["servers"][tag] = p
    lg = os.path.join(mt, "qconsole.log")
    log("server", tag, "pid", p.pid, "port", SPORT[tag], "home", hm)
    m = wait_for(lg, r"Could not load[^\r\n]*|Detected Coop for|initialising coop weapon loadout|PSTEST", 300)
    if not m:
        m = wait_for(lg, r"Could not load[^\r\n]*|Detected Coop for|initialising coop weapon loadout", 60)
    if not m or m.group(0).startswith("Could not"):
        raise RuntimeError("server %s: map never became ready" % tag)
    time.sleep(3)
    return mt, lg


def stop_server(tag):
    p = ST["servers"].pop(tag, None)
    if p is not None and p.poll() is None:
        p.kill()   # only the PID this script started
        p.wait(20)
        log("server", tag, "stopped (pid %d)" % p.pid)


def launch_client(bins, hm, connect_port=None, listen=False, W=960, Hh=540):
    mt = os.path.join(hm, "maintt")
    boot = ['bind F12 "exec isstep.cfg"', "set rconPassword " + RCON, "set ui_gmbox 0", "ui_checkrestart",
            "set coop_idleInspect 0", "set coop_tinnitus 0", "set com_maxfps 60", "set coop_coverAuto 0"]
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", hm), ("cl_renderer", "opengl2"),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"), ("r_mode", "-1"),
            ("r_customwidth", str(W)), ("r_customheight", str(Hh)), ("r_fullscreen", "0"), ("developer", "1"),
            ("logfile", "2"), ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", str(CPORT))]
    args = [os.path.join(bins, "openmohaa_progsync.exe")]
    for k, v in sets:
        args += ["+set", k, v]
    if listen:
        boot += ["set sv_maxbots 0", "set sv_numbots 0", "set g_ai 0", "set coop_dbno 0", "set coop_dev 1",
                 "set coop_pstest 0"]
        args += ["+set", "g_gametype", "2", "+exec", "ps_on.cfg", "+set", "ui_dmmap", MAP,
                 "+exec", "coop_mod/start_server.cfg"]
    else:
        args += ["+exec", "ps_on.cfg", "+connect", "127.0.0.1:%d" % connect_port]
    args, late = hw.apply_policy(args, width=W, height=Hh)
    boot += late
    open(os.path.join(mt, "ps_on.cfg"), "w", newline="\n").write("\n".join(boot) + "\n")
    hg.acquire_slot(OWNER, args[0], hm, [CPORT], 60)
    c = hw.launch_background(args[0], args[1:], bins, policy=False, log=log)
    ST["client"] = c
    try:
        hg.set_slot_pid(OWNER, c.proc.pid)
    except Exception as e:
        log("slot pid note:", e)
    log("client pid", c.proc.pid, "bins", bins)
    return os.path.join(mt, "qconsole.log")


def stop_client(hm):
    c = ST["client"]
    if c is None:
        return
    mt = os.path.join(hm, "maintt")
    if c.proc.poll() is None:
        open(os.path.join(mt, "isstep.cfg"), "w", newline="\n").write("quit\n")
        try:
            c.post_key(0x7B)
            c.proc.wait(30)
        except Exception:
            c.proc.kill()
    ST["client"] = None
    try:
        hg.release_slot(OWNER)
    except Exception:
        pass
    log("client stopped")


def step(hm, lines, timeout=120):
    ST["step"] += 1
    mt = os.path.join(hm, "maintt")
    lg = os.path.join(mt, "qconsole.log")
    mk = "^~^~^ PSSTEP %d" % ST["step"]
    open(os.path.join(mt, "isstep.cfg"), "w", newline="\n").write("\n".join(lines + ["echo " + mk]) + "\n")
    start = len(read(lg))
    for _ in range(5):
        ST["client"].post_key(0x7B)
        if wait_for(lg, r"execing isstep\.cfg", 6, max(0, start - 10)):
            break
    else:
        raise RuntimeError("step %d: F12 never executed isstep.cfg" % ST["step"])
    if not wait_for(lg, re.escape(mk) + r"\b", timeout, max(0, start - 10)):
        raise RuntimeError("step %d timed out: %s" % (ST["step"], lines[:3]))
    return start


def join(hm, srvlog):
    st = len(read(srvlog))
    for _ in range(5):
        step(hm, ["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20", "popmenu 0",
                  "wait 40", "popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if wait_for(srvlog, r"has joined the|KITGIVE", 15, st):
            return True
    return False


def shot(hm, name):
    """engine screenshot, renamed to <name>.jpg/.tga in the PC home's screenshots folder"""
    sd = os.path.join(hm, "maintt", "screenshots")
    before = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    step(hm, ["wait 300", "screenshotJPEG", "wait 300"])
    time.sleep(1.0)
    after = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    new = sorted(after - before)
    if new:
        src = os.path.join(sd, new[-1])
        dst = os.path.join(sd, name + os.path.splitext(src)[1])
        shutil.move(src, dst)
        log("screenshot", dst)
        return dst
    log("screenshot missing", name)
    return None


def rcon(hm, srvlog, action, timeout=30, local=False):
    st = len(read(srvlog))
    if local:
        step(hm, ["set coop_pstest " + action, "wait 200"])
    else:
        open(os.path.join(os.path.dirname(srvlog), "pscmd.cfg"), "w", newline="\n").write("set coop_pstest %s\n" % action)
        step(hm, ["rcon exec pscmd.cfg", "wait 200"])
    m = wait_for(srvlog, r"\^~\^~\^ PSTEST did=%s total=(\S+) sync=(\S+) unlocks=([^\r\n]*)" % action, timeout, st)
    if m:
        log("server says", m.group(0))
    return m


def last(pattern, text):
    r = re.findall(pattern, text)
    return r[-1] if r else None


# ---------------------------------------------------------------------------------------------- phases
PC_SEED = {"xp": "5000", "chal": "wpn_garand:3|wpn_thompson:9", "unlocks": "pc_unlock_a|pc_unlock_b",
           "pins": "wpn_garand", "medals": "", "bpfound": "m3l2_1|"}
B_SEED = {"xp": "3000", "chal": "wpn_garand:7", "unlocks": "srv_unlock_old", "bpfound": "m9l9_9|", "pins": "srv_pin"}


def phase1(code, test, ctx):
    hm, mt, gid = ctx["pc"], ctx["pcmt"], ctx["gid"]
    smt, slog = start_server("A", BIN, code, test)
    ctx["srvA"] = (smt, slog)
    clog = launch_client(BIN, hm, SPORT["A"])
    m = wait_for(slog, r"\^~\^~\^ COOPSYNC merged cl=\d+ id=(\w+)\.\.[^\r\n]*", 300)
    check("1a server merged the uploaded record", m and gid.startswith(m.group(1)), m.group(0) if m else "no merge line")
    c = wait_for(clog, r"\^~\^~\^ COOPSYNC client uploading (\d+) chunks", 60)
    check("1a client was asked for its records and uploaded them", c and int(c.group(1)) >= 4,
          c.group(0) if c else "no upload line")
    sr = wait_for(slog, r"\^~\^~\^ XP Service record: [^\r\n]*", 120)
    check("1a XP from the PC shows on the dedicated server", sr and " 5000 XP" in sr.group(0), sr.group(0) if sr else "")
    w = re.search(r"COOPSYNC script waited[^\r\n]*", read(slog))
    log("script wait line:", w.group(0) if w else "(none - merge landed before identify)")
    srv = saves(smt, gid)
    check("1a server files now hold the PC record", srv["xp"] == "5000" and "pc_unlock_a" in (srv["unlocks"] or ""),
          json.dumps(srv))
    time.sleep(3)
    nw = len(re.findall(r"COOPSYNC client wrote unlocks", read(clog)))
    # a fresh id on a fresh server is re-granted every rank unlock (dozens of rewrites in one frame): coalesced
    check("1a join burst coalesced (unlocks record sent at most 3 times)", 1 <= nw <= 3, "client wrote unlocks x%d" % nw)
    joined = join(hm, slog)
    check("1a joined a team", joined)
    time.sleep(12)
    ctx["shots"].append(shot(hm, "p1_joined_dedicated"))
    step(hm, ["+scores", "wait 800"])
    ctx["shots"].append(shot(hm, "p1_scoreboard_rank"))
    step(hm, ["-scores", "wait 100"])

    # 1b award + flush -> the record comes back to the PC
    r = rcon(hm, slog, "award")
    total = r.group(1) if r else None
    st = len(read(clog))
    rcon(hm, slog, "flush")
    cw = wait_for(clog, r"\^~\^~\^ COOPSYNC client wrote xp[^\r\n]*", 20, st)
    pc = saves(mt, gid)
    check("1b award+flush: PC xp file = server total", cw and total and pc["xp"] == total,
          "server total=%s pc=%s line=%s" % (total, pc["xp"], cw.group(0) if cw else None))
    # 1c unlock
    st = len(read(clog))
    rcon(hm, slog, "unlock")
    cw = wait_for(clog, r"\^~\^~\^ COOPSYNC client wrote unlocks[^\r\n]*", 20, st)
    pc = saves(mt, gid)
    srvu = saves(smt, gid)["unlocks"] or ""
    check("1c unlock comes home, byte-identical to the server's record (paths with '/')",
          cw and "pstest_unlock" in (pc["unlocks"] or "") and "pc_unlock_a" in (pc["unlocks"] or "")
          and "models/weapons/" in (pc["unlocks"] or "") and pc["unlocks"] == srvu,
          "pc unlocks=%s" % (pc["unlocks"] or "")[:160])
    # 1d award WITHOUT a flush (1 XP: no rank-up, whose flush would send it anyway), then disconnect: the XP
    # fold-in must bring it home
    r = rcon(hm, slog, "award1")
    total2 = r.group(1) if r else None
    st = len(read(clog))
    sst_rc = len(read(slog))
    step(hm, ["wait 1500", "disconnect", "echo ^~^~^ PS disconnected", "wait 12000",
              "connect 127.0.0.1:%d" % SPORT["A"], "wait 500"], timeout=60)
    time.sleep(1)
    pc = saves(mt, gid)
    seg = read(clog)[st:]
    cut = seg.find("PS disconnected")
    fold = re.search(r"\^~\^~\^ COOPSYNC client wrote xp[^\r\n]*", seg[:cut] if cut >= 0 else "")
    check("1d disconnect: last XP folded into the PC file at the disconnect",
          fold and total2 and pc["xp"] == total2 and pc["xp"] != "999999",
          "server total=%s pc=%s line=%s" % (total2, pc["xp"], fold.group(0) if fold else None))
    ctx["after1d"] = pc
    # 1e reconnect mid-mission: the PC and the server already agree -> nothing uploaded, nothing lost
    m = wait_for(slog, r"\^~\^~\^ COOPSYNC merged[^\r\n]*", 180, sst_rc)
    sr = wait_for(slog, r"\^~\^~\^ XP Service record: [^\r\n]*", 120, sst_rc)
    check("1e reconnect: total intact", m and sr and (" %s XP" % total2) in sr.group(0),
          (m.group(0) if m else "no merge") + " | " + (sr.group(0) if sr else "no record"))
    check("1e reconnect: nothing had to be uploaded (all 7 records already the same)",
          m and "already_same=7" in m.group(0), m.group(0) if m else "")
    join(hm, slog)
    time.sleep(4)
    ctx["shots"].append(shot(hm, "p1_after_reconnect"))
    ctx["total"] = total2
    # 1f map change on the same server (the every-mission case): no upload, records intact
    sst = len(read(slog))
    open(os.path.join(os.path.dirname(slog), "pscmd.cfg"), "w", newline="\n").write("map %s\n" % MAP)
    step(hm, ["rcon exec pscmd.cfg", "wait 200"])
    m = wait_for(slog, r"\^~\^~\^ COOPSYNC merged[^\r\n]*", 300, sst)
    sr = wait_for(slog, r"\^~\^~\^ XP Service record: [^\r\n]*", 120, sst)
    check("1f map change: no upload, total intact", m and "already_same=7" in m.group(0) and sr and (" %s XP" % total2) in sr.group(0),
          (m.group(0) if m else "no merge") + " | " + (sr.group(0) if sr else "no record"))
    w = re.findall(r"COOPSYNC script waited[^\r\n]*", read(slog)[sst:])
    log("1f script waits:", w)
    join(hm, slog)
    time.sleep(3)


def phase2(code, test, ctx):
    hm, mt, gid = ctx["pc"], ctx["pcmt"], ctx["gid"]
    smt, slog = start_server("B", BIN, code, test, recs=B_SEED, gid=gid)
    clog = os.path.join(mt, "qconsole.log")
    st, sst = len(read(clog)), len(read(slog))
    step(hm, ["disconnect", "wait 2000", "connect 127.0.0.1:%d" % SPORT["B"], "wait 500"], timeout=60)
    stop_server("A")
    m = wait_for(slog, r"\^~\^~\^ COOPSYNC merged[^\r\n]*", 300, sst)
    check("2a server B merged", m, m.group(0) if m else "")
    sr = wait_for(slog, r"\^~\^~\^ XP Service record: [^\r\n]*", 120, sst)
    want = str(max(int(ctx["total"] or 0), 3000))
    check("2a progress from server A shows on server B (higher total wins)", sr and (" %s XP" % want) in sr.group(0),
          sr.group(0) if sr else "")
    time.sleep(3)
    srv, pc = saves(smt, gid), saves(mt, gid)
    ok_srv = ("srv_unlock_old" in (srv["unlocks"] or "") and "pstest_unlock" in (srv["unlocks"] or "")
              and "wpn_garand:7" in (srv["chal"] or "") and "wpn_thompson:9" in (srv["chal"] or "")
              and "m9l9_9" in (srv["bpfound"] or "") and "m3l2_1" in (srv["bpfound"] or ""))
    check("2b merge on server B: union of unlocks/blueprints, higher challenge progress", ok_srv, json.dumps(srv))
    ok_pc = ("srv_unlock_old" in (pc["unlocks"] or "") and "wpn_garand:7" in (pc["chal"] or "")
             and "m9l9_9" in (pc["bpfound"] or "") and pc["xp"] == want)
    check("2b the merged record came home to the PC", ok_pc, json.dumps(pc))
    check("2b pins: the PC's own choice won on join", srv["pins"] == "wpn_garand", "server pins=%s" % srv["pins"])
    join(hm, slog)
    time.sleep(4)
    ctx["shots"].append(shot(hm, "p2_serverB_merged"))
    ctx["pc_after2"] = pc
    stop_client(hm)


def phase3(code, test, ctx):
    hm, mt, gid = ctx["pc"], ctx["pcmt"], ctx["gid"]
    smt, slog = ctx["srvB"]
    shutil.copyfile(os.path.join(BIN, "cgame_release.dll"), os.path.join(BIN, "cgame.dll"))
    before_pc = saves(mt, gid)
    sst = len(read(slog))
    clog = launch_client(BIN, hm, SPORT["B"])
    cst = 0
    ok = wait_for(slog, r"\^~\^~\^ XP Service record: [^\r\n]*", 300, sst)
    check("3 old client: joins and gets a service record as today", ok, ok.group(0) if ok else "")
    time.sleep(3)
    check("3 old client: no upload/merge for it", not re.search(r"COOPSYNC merged", read(slog)[sst:]), "")
    after_pc = saves(mt, gid)
    check("3 old client: nothing written on the PC", before_pc == after_pc, "")
    check("3 old client: no script wait", not re.search(r"COOPSYNC script waited", read(slog)[sst:]), "")
    errs = re.findall(r"[^\r\n]*(?:Script Error|Couldn't compile|parse error)[^\r\n]*", read(slog)[sst:])
    log("server script errors during phase 3:", len(errs), errs[:3])
    stop_client(hm)
    shutil.copyfile(os.path.join(BIN, "cgame_new.dll"), os.path.join(BIN, "cgame.dll"))
    stop_server("B")


def phase4(code, test, ctx):
    hm, mt, gid = ctx["pc"], ctx["pcmt"], ctx["gid"]
    smt, slog = start_server("OLD", BIN_OLD, code, test)
    before_pc = saves(mt, gid)
    sst = len(read(slog))
    clog = launch_client(BIN, hm, SPORT["OLD"])
    c = wait_for(clog, r"\^~\^~\^ COOPSYNC client handshake[^\r\n]*", 300)
    check("4 new client on old server: handshake sent, nothing else (harmless)", c, c.group(0) if c else "")
    ok = wait_for(slog, r"\^~\^~\^ XP Service record: [^\r\n]*", 300, sst)
    check("4 new client on old server: joins and loads as today", ok, ok.group(0) if ok else "")
    joined = join(hm, slog)
    rcon(hm, slog, "award")
    rcon(hm, slog, "flush")
    time.sleep(2)
    check("4 new client on old server: no ack, nothing written on the PC",
          not re.search(r"COOPSYNC client (acked|wrote)", read(clog)) and saves(mt, gid) == before_pc, "")
    stop_client(hm)
    time.sleep(1)
    check("4 nothing written on the PC after disconnect either", saves(mt, gid) == before_pc, json.dumps(saves(mt, gid)))
    stop_server("OLD")


def phase5(code, test, ctx):
    hm, mt, gid = ctx["pc"], ctx["pcmt"], ctx["gid"]
    before_pc = saves(mt, gid)
    lg = os.path.join(mt, "qconsole.log")
    launch_client(BIN, hm, listen=True)
    time.sleep(3)
    st = 0
    sr = wait_for(lg, r"\^~\^~\^ XP Service record: [^\r\n]*", 300, st)
    check("5 listen host: own record loads as today", sr and (" %s XP" % before_pc["xp"]) in sr.group(0),
          sr.group(0) if sr else "")
    tail = read(lg)[st:]
    check("5 listen host: no upload, no merge, no wait",
          not re.search(r"COOPSYNC (client handshake|client uploading|merged|script waited)", tail), "")
    joined = join(hm, lg)
    r = rcon(hm, lg, "award", local=True)
    rcon(hm, lg, "flush", local=True)
    time.sleep(1)
    pc = saves(mt, gid)
    check("5 listen host: the host writes its own file directly", r and pc["xp"] == r.group(1),
          "total=%s file=%s" % (r.group(1) if r else None, pc["xp"]))
    ctx["shots"].append(shot(hm, "p5_listen_host"))
    stop_client(hm)


def archive(ctx):
    dst = os.path.join(ARCHIVE, ST["run"])
    os.makedirs(dst, exist_ok=True)
    for tag in ("pc", "srvA", "srvB", "srvOLD"):
        hm = home(tag)
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(dst, tag))
    with open(os.path.join(dst, "results.json"), "w") as f:
        json.dump({"results": RES, "gid": ctx.get("gid"), "shots": [s for s in ctx["shots"] if s]}, f, indent=1)
    lf = os.path.join(SCR, ST["run"] + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(dst, "harness.log"))
    log("archived to", dst)
    return dst


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print(__doc__)
        return 2
    ST["run"] = sys.argv[2]
    os.makedirs(SCR, exist_ok=True)
    phases = [1, 2, 3, 4, 5]
    if "--phases" in sys.argv:
        phases = [int(x) for x in sys.argv[sys.argv.index("--phases") + 1].split(",")]
    users = hg.user_game_running()
    if users:
        log("NOTE user game processes present (not touched):", users)
    prep_bins()
    code, test, rev = build_paks()
    hm, mt, gid = seed_pc(code, test, PC_SEED)
    ctx = {"pc": hm, "pcmt": mt, "gid": gid, "shots": [], "total": None}
    try:
        if 1 in phases:
            phase1(code, test, ctx)
        if 2 in phases:
            phase2(code, test, ctx)
            ctx["srvB"] = (os.path.join(home("srvB"), "maintt"), os.path.join(home("srvB"), "maintt", "qconsole.log"))
        if 3 in phases:
            if "B" not in ST["servers"]:
                start_server("B", BIN, code, test, recs=B_SEED, gid=gid)
                ctx["srvB"] = (os.path.join(home("srvB"), "maintt"), os.path.join(home("srvB"), "maintt", "qconsole.log"))
            phase3(code, test, ctx)
        if 4 in phases:
            phase4(code, test, ctx)
        if 5 in phases:
            phase5(code, test, ctx)
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        try:
            stop_client(ctx["pc"])
        except Exception as e:
            log("client stop note", e)
        for tag in list(ST["servers"]):
            stop_server(tag)
        try:
            shutil.copyfile(os.path.join(BIN, "cgame_new.dll"), os.path.join(BIN, "cgame.dll"))
        except Exception:
            pass
        time.sleep(2)
        dst = archive(ctx)
    n_fail = sum(1 for r in RES if not r[1])
    log("SUMMARY %d checks, %d failed -> %s" % (len(RES), n_fail, dst))
    for name, ok, detail in RES:
        print(("PASS " if ok else "FAIL ") + name)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
