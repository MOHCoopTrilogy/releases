"""run_joinflood.py - reproduce / prove the remote-join flood (bug-3909, bug-3903) on the private harness copy
G:\\mohaa-hudfeed5 (slot owner "hudfeed5"; client 2 uses G:\\mohaa-hudfeed4, owner "hudfeed4"). Sub-folders
joinflood\\<variant>\\ hold the binaries, so the lanes' root files are untouched. DISPLAY2 through harness_window only,
net_enabled 1 + net_ip 127.0.0.1, ports 12791 (server) 12792/12793 (clients). Never touches G:\\mohaa-gl2, the
user's saves or key, or the public servers (their lobby.scr override is only READ for the "patched" variant).

    python -I run_joinflood.py run <name> [--srv new|old|fix] [--cl new|old|fix] [--clients 1|2]
                                   [--lobby stock|patched|fix] [--lobbysec 300] [--missionsec 200]
                                   [--delay 0] [--noready]

Binary variants: new = the released v1.10.23 game.dll/cgame.dll (GOG root), old = v1.10.22 (progsync_old copy),
fix = the joinflood-next build. The server exe is always the joinflood build of omohaaded (v1.10.23 source + the
sv_netProbe instrument); the client exe is the released openmohaa.exe.

The internet path: sv_lanForceRate 0 (a 127.0.0.1 client is otherwise exempt from the rate gate) and the user's
client settings rate 90000 / snaps 40 / cl_maxpackets 100. The client is a FAKE identity (random qkey) carrying a
veteran-sized record (sizes of a real long-time player: chal ~3.3 KB, unlocks ~2.5 KB, pend ~1.5 KB); the server
starts with no record for it - a first join of a public server.
"""
import hashlib, json, os, random, re, shutil, subprocess, sys, time

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

ROOT = r"C:\mohaa-coop-dev"
HERE = os.path.dirname(os.path.abspath(__file__))
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
ENG = os.path.join(ROOT, "openmohaa-hzm-joinflood", ".cmake")
MODWT = os.path.join(ROOT, "hzm-mod-joinflood")
SLOTS = [("hudfeed5", r"G:\mohaa-hudfeed5"), ("hudfeed4", r"G:\mohaa-hudfeed4")]
H = SLOTS[0][1]
PRISTINE = os.path.join(H, "pristine")
OLD_DLLS = os.path.join(H, "progsync_old")
SPORT, CPORTS = 12791, [12792, 12793]
RCON = "jf14"
SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\joinflood"
ARCHIVE = r"H:\hzm_archive\joinflood"
CODEPAK = "zzzzzz_co-op_hzm_mod_code.pk3"
# --usercfg: a READ-ONLY copy of the user's own client config (never his saves or key), so the harness client
# carries the same userinfo (pins, kit, cosmetics, MP blob...) as the real one; name and identity are fake
USERCFG = r"G:\mohaa-gl2\home\maintt\configs\omconfig.cfg"
PATCHED_LOBBY = os.path.join(ROOT, "public_servers", "srv1", "maintt", "coop_mod", "lobby.scr")
TYPES = ("xp", "chal", "unlocks", "pins", "pend", "medals", "bpfound")
RES = []
ST = {"run": None, "clients": [], "server": None}


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
        time.sleep(0.5)
    return None


def guard():
    for c in ST["clients"]:
        if c["bg"].watcher.violations:
            raise RuntimeError("window policy violation: %s" % (c["bg"].watcher.violations[:3],))


# ---------------------------------------------------------------------------------------------- binaries
def prep_bins(variant, slotdir):
    d = os.path.join(slotdir, "joinflood", variant)
    os.makedirs(d, exist_ok=True)
    for src, dst in (("openmohaa.exe", "openmohaa_jf.exe"), ("OpenAL64.dll", None), ("SDL2.dll", None),
                     ("libcurl.dll", None), ("renderer_opengl1.dll", None), ("renderer_opengl2.dll", None)):
        s, t = os.path.join(GOG, src), os.path.join(d, dst or src)
        if not os.path.isfile(t) or md5f(t) != md5f(s):
            shutil.copyfile(s, t)
    if variant == "rel":
        # the RELEASED install as it is in the GOG root (v1.10.24+): exe, dedicated exe, dlls - nothing of ours
        shutil.copyfile(os.path.join(GOG, "omohaaded.exe"), os.path.join(d, "omohaaded_jf.exe"))
    else:
        shutil.copyfile(os.path.join(ENG, "Release", "omohaaded.exe"), os.path.join(d, "omohaaded_jf.exe"))
    if ST.get("clprobe") and variant != "rel":
        # the same exe source as the release (unchanged since v1.10.22) + the cl_netProbe instrument
        shutil.copyfile(os.path.join(ENG, "Release", "openmohaa.exe"), os.path.join(d, "openmohaa_jf.exe"))
    if variant in ("new", "rel"):
        game, cgame = os.path.join(GOG, "game.dll"), os.path.join(GOG, "cgame.dll")
    elif variant == "old":
        game, cgame = os.path.join(OLD_DLLS, "game.dll"), os.path.join(OLD_DLLS, "cgame.dll")
    else:
        # fix: the joinflood-next exes; game.dll/cgame.dll are unchanged from v1.10.23 (same source, e8838a89)
        game, cgame = os.path.join(GOG, "game.dll"), os.path.join(GOG, "cgame.dll")
        shutil.copyfile(os.path.join(ENG, "Release", "openmohaa.exe"), os.path.join(d, "openmohaa_jf.exe"))
    shutil.copyfile(game, os.path.join(d, "game.dll"))
    shutil.copyfile(cgame, os.path.join(d, "cgame.dll"))
    log("bins", variant, d, "game", md5f(os.path.join(d, "game.dll"))[:8], "cgame",
        md5f(os.path.join(d, "cgame.dll"))[:8], "ded", md5f(os.path.join(d, "omohaaded_jf.exe"))[:8])
    return d


def fix_codepak():
    """the joinflood-next mod tree, packed like the release code pak (scripts/ui/cfg, no assets)"""
    os.makedirs(SCR, exist_ok=True)
    full = subprocess.run(["git", "-C", MODWT, "rev-parse", "HEAD"], capture_output=True, check=True).stdout.decode().strip()
    dirty = subprocess.run(["git", "-C", MODWT, "status", "--porcelain"], capture_output=True, check=True).stdout.decode().strip()
    if dirty:
        raise RuntimeError("mod worktree has uncommitted changes - commit first so the run names its revision")
    code = os.path.join(SCR, "code_%s.pk3" % full[:10])
    if not os.path.isfile(code):
        tops = [t for t in subprocess.run(["git", "-C", MODWT, "ls-tree", "--name-only", full], capture_output=True,
                                          check=True).stdout.decode().splitlines()
                if t not in ("sound", "textures", "models", "gfx", "env") and not t.lower().endswith(".pk3")
                and not t.startswith(".git")]
        subprocess.run(["git", "-C", MODWT, "archive", "--format=zip", "-1", "-o", code, full, "--"] + tops, check=True)
    log("fix code pak", full[:10], os.path.getsize(code))
    return code, full


# ---------------------------------------------------------------------------------------------- the veteran record
def veteran_record(seed):
    rnd = random.Random(seed)
    src = read(os.path.join(MODWT, "coop_mod", "challenges.scr"))
    defs = re.findall(r'waitthread chal_def "([^"]+)"\s+"[^"]*"\s+"([^"]*)"\s+"[^"]*"\s+"[^"]*"\s+(\d+)\s+"([^"]*)"', src)
    rnd.shuffle(defs)
    chal, unlocks, pend = [], [], []
    for cid, title, target, reward in defs:
        if len("|".join(chal)) > 3250:
            break
        n = int(target)
        done = rnd.random() < 0.55
        chal.append("%s:%d" % (cid, n if done else rnd.randint(1, max(1, n - 1))))
        if done and reward and len("|".join(unlocks)) < 2500:
            unlocks.append(reward)
        if done and len("~".join(pend)) < 1480:
            pend.append(title)
    bp = "|".join("m%dl%d_%d" % (rnd.randint(1, 6), rnd.randint(1, 3), rnd.randint(1, 4)) for _ in range(10)) + "|"
    return {"xp": "8750", "chal": "|".join(chal), "unlocks": "|".join(unlocks), "pins": "", "pend": "~".join(pend),
            "medals": "", "bpfound": bp}


def write_saves(mt, gid, recs):
    os.makedirs(os.path.join(mt, "coop_mod", "save"), exist_ok=True)
    for t, v in recs.items():
        with open(os.path.join(mt, "coop_mod", "save", "%s_%s.dat" % (t, gid)), "wb") as f:
            f.write(v.encode("latin-1"))


def saves(mt, gid):
    out = {}
    for t in TYPES:
        p = os.path.join(mt, "coop_mod", "save", "%s_%s.dat" % (t, gid))
        out[t] = read(p) if os.path.isfile(p) else None
    return out


# ---------------------------------------------------------------------------------------------- homes
def home(slotdir, tag):
    # carries "<slot>\home" so harness_guard classifies the process as that harness
    return os.path.join(slotdir, "home_jf_%s_%s" % (ST["run"], tag))


def seed_server(opts, code):
    hm = home(H, "srv")
    mt = os.path.join(hm, "maintt")
    os.makedirs(os.path.join(mt, "coop_mod"), exist_ok=True)
    if opts["lobby"] == "patched":
        shutil.copyfile(PATCHED_LOBBY, os.path.join(mt, "coop_mod", "lobby.scr"))
    if code:
        shutil.copyfile(code, os.path.join(mt, CODEPAK))
    cfg = ["exec coop_mod/cfg/server_rules.cfg", 'seta sv_hostname "JF harness"', "seta sv_fps 40", "seta sv_maxRate 0",
           "seta sv_floodProtect 1", "seta g_inactivespectate 600", "seta g_inactivekick 0", "seta timelimit 0",
           "seta fraglimit 0", "seta roundlimit 0", "seta coop_health 750", "seta coop_dbno 1", "seta coop_lmsLives 0",
           "seta coop_dev 0", "seta coop_check 0", "seta developer 0", "seta rconpassword " + RCON,
           "seta coop_campaign 1", "set sv_lanForceRate 0", "set sv_netProbe 1", "set sv_lagProbe 1"]
    if opts["delay"]:
        cfg.append("set sv_packetdelay %d" % opts["delay"])
    if opts.get("parkbytes") is not None:
        cfg.append("set sv_cmdParkBytes %d" % opts["parkbytes"])  # 0 = the released behaviour (count window only)
    cfg.append("map co_lobby1")
    open(os.path.join(mt, "jf_start.cfg"), "w", newline="\n").write("\n".join(cfg) + "\n")
    return hm, mt


def seed_client(idx, slotdir, code, recs):
    hm = home(slotdir, "pc%d" % idx)
    mt = os.path.join(hm, "maintt")
    os.makedirs(os.path.join(mt, "configs"), exist_ok=True)
    for f in ("autoexec.cfg", "coop_defaults.cfg"):
        src = os.path.join(PRISTINE, f)
        if ST.get("usercfg"):   # read-only copies of the user's own (configs, never saves or key)
            src = os.path.join(os.path.dirname(os.path.dirname(USERCFG)), f)
        shutil.copyfile(src, os.path.join(mt, f))
    if code:
        shutil.copyfile(code, os.path.join(mt, CODEPAK))
    key = os.urandom(2048)
    open(os.path.join(hm, "qkey"), "wb").write(key)
    gid = hashlib.md5(key).hexdigest().upper()
    cfg = read(USERCFG if ST.get("usercfg") else os.path.join(PRISTINE, "omconfig.cfg"))
    mx = ST.get("mx", {}).get(idx)
    kv = [("name", "JFTester%d" % idx), ("rate", "90000"), ("snaps", "40"), ("cl_maxpackets", "100")]
    if mx:
        kv = [("name", "JFTester%d" % idx), ("com_maxfps", mx[0]), ("cl_maxpackets", mx[1]), ("cl_packetdup", mx[2]),
              ("rate", mx[3]), ("snaps", mx[4])]
    for k, v in kv:
        cfg, n = re.subn(r'(?im)^seta %s "[^"\r\n]*"' % k, 'seta %s "%s"' % (k, v), cfg)
        if not n:
            cfg += '\nseta %s "%s"\n' % (k, v)
    cfg = re.sub(r'(?im)^seta coop_loA([1-4]) "[^"\r\n]*"', r'seta coop_loA\1 ""', cfg)
    open(os.path.join(mt, "configs", "omconfig.cfg"), "wb").write(cfg.encode("latin-1"))
    open(os.path.join(mt, "whatsnew_pending.cfg"), "wb").write(b"// up to date\r\n")
    write_saves(mt, gid, recs)
    log("client %d home" % idx, hm, "fake id", gid, "record bytes", {k: len(v) for k, v in recs.items()})
    return hm, mt, gid


# ---------------------------------------------------------------------------------------------- processes
def start_server(bins, hm, mt):
    args = [os.path.join(bins, "omohaaded_jf.exe")]
    for k, v in (("com_target_game", "2"), ("dedicated", "1"), ("fs_basepath", GOG), ("fs_homepath", hm),
                 ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", str(SPORT)), ("sv_maxclients", "4"),
                 ("g_gametype", "2"), ("logfile", "2"), ("coop_campaign", "1"), ("com_abnormalExit", "0")):
        args += ["+set", k, v]
    args += ["+exec", "jf_start.cfg"]
    p = subprocess.Popen(args, cwd=bins, creationflags=0x08000000, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ST["server"] = p
    lg = os.path.join(mt, "qconsole.log")
    log("server pid", p.pid, "port", SPORT, "home", hm)
    m = wait_for(lg, r"Could not load[^\r\n]*|Detected Coop for|initialising coop weapon loadout|lobby", 300)
    if not m or m.group(0).startswith("Could not"):
        raise RuntimeError("server: map never became ready")
    time.sleep(5)
    return lg


def stop_server():
    p = ST["server"]
    if p is not None and p.poll() is None:
        p.kill()   # only the PID this script started
        p.wait(20)
        log("server stopped (pid %d)" % p.pid)
    ST["server"] = None


def launch_client(idx, bins, hm, fps=60, W=960, Hh=540):
    owner, slotdir = SLOTS[idx - 1]
    mt = os.path.join(hm, "maintt")
    boot = ['bind F12 "exec isstep.cfg"', "set ui_gmbox 0", "ui_checkrestart", "set coop_idleInspect 0",
            "set coop_tinnitus 0", "set com_maxfps %d" % fps, "set coop_coverAuto 0", "set cl_lanForcePackets 1"]
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", hm), ("cl_renderer", "opengl2"),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"), ("r_mode", "-1"),
            ("r_customwidth", str(W)), ("r_customheight", str(Hh)), ("r_fullscreen", "0"), ("developer", "0"),
            ("logfile", "2"), ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", str(SPORT if (ST.get("listen") and idx == 1) else CPORTS[idx - 1]))]
    args = [os.path.join(bins, "openmohaa_jf.exe")]
    for k, v in sets:
        args += ["+set", k, v]
    if ST.get("clprobe"):
        boot += ["set cl_netProbe %d" % (2 if ST.get("clprobe2") else 1)]
    if ST.get("netdebug"):
        boot += ["set showdrop 1", "set cl_shownet 1"]
    if ST.get("listen") and idx == 1:
        # listen host: the client hosts co_lobby1 itself through the menu path (start_server.cfg -> ui_startdmmap 2)
        boot += ["set sv_netProbe 1", "set sv_lagProbe 1", "seta coop_campaign 1", "set net_port %d" % SPORT]
        args += ["+set", "g_gametype", "2", "+exec", "jf_on.cfg", "+set", "ui_dmmap", "co_lobby1",
                 "+exec", "coop_mod/start_server.cfg"]
    else:
        args += ["+exec", "jf_on.cfg", "+connect", "127.0.0.1:%d" % SPORT]
    mx = ST.get("mx", {}).get(idx)
    if mx:
        # the window is never focused: com_maxfpsUnfocused IS its frame cap, so it carries the matrix value
        boot = [b for b in boot if not b.startswith("set com_maxfps ")] + ["set com_maxfps " + mx[0]]
    args, late = hw.apply_policy(args, width=W, height=Hh,
                                 unfocused_fps=int(mx[0]) if mx else ST.get("ufps", 60))
    boot += late
    open(os.path.join(mt, "jf_on.cfg"), "w", newline="\n").write("\n".join(boot) + "\n")
    hg.acquire_slot(owner, args[0], hm, [CPORTS[idx - 1]], 90)
    bg = hw.launch_background(args[0], args[1:], bins, policy=False, log=log)
    try:
        hg.set_slot_pid(owner, bg.proc.pid)
    except Exception as e:
        log("slot pid note:", e)
    c = {"idx": idx, "owner": owner, "bg": bg, "hm": hm, "mt": mt, "log": os.path.join(mt, "qconsole.log"), "step": 0}
    ST["clients"].append(c)
    log("client %d pid" % idx, bg.proc.pid, "bins", bins)
    return c


def stop_client(c):
    if c["bg"].proc.poll() is None:
        open(os.path.join(c["mt"], "isstep.cfg"), "w", newline="\n").write("quit\n")
        try:
            c["bg"].post_key(0x7B)
            c["bg"].proc.wait(30)
        except Exception:
            c["bg"].proc.kill()
    try:
        hg.release_slot(c["owner"])
    except Exception:
        pass
    log("client %d stopped" % c["idx"])


def step(c, lines, timeout=60):
    c["step"] += 1
    mk = "^~^~^ JFSTEP %d" % c["step"]
    open(os.path.join(c["mt"], "isstep.cfg"), "w", newline="\n").write("\n".join(lines + ["echo " + mk]) + "\n")
    start = len(read(c["log"]))
    for _ in range(5):
        if c["bg"].proc.poll() is not None:
            raise RuntimeError("client %d exited" % c["idx"])
        c["bg"].post_key(0x7B)
        if wait_for(c["log"], r"execing isstep\.cfg", 6, max(0, start - 10)):
            break
    else:
        log("step %d: F12 never executed isstep.cfg on client %d" % (c["step"], c["idx"]))
        return None
    if not wait_for(c["log"], re.escape(mk) + r"\b", timeout, max(0, start - 10)):
        log("step %d timed out on client %d" % (c["step"], c["idx"]))
        return None
    return start


def shot(c, name):
    sd = os.path.join(c["mt"], "screenshots")
    before = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    step(c, ["wait 100", "screenshotJPEG", "wait 100"])
    time.sleep(1.5)
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


# ---------------------------------------------------------------------------------------------- analysis
SVNET = re.compile(r"\[([\d\-: ]+) [^\]]*\] \^~\^~\^ SVNET cl=(\d+) st=(\d+) inflight=(\d+) max=(\d+) parked=(\d+) "
                   r"max=(\d+) snaps=(\d+) avg=(\d+) max=(\d+) over1300=(\d+) skipfrag=(\d+) skiprate=(\d+) in=(\d+) "
                   r"infrag=(\d+) lastin=(-?\d+) ping=(-?\d+)")


def analyze(slog, t_from=0):
    txt = read(slog)[t_from:]
    rows = [m.groups() for m in SVNET.finditer(txt)]
    per = {}
    for r in rows:
        cl = int(r[1])
        d = per.setdefault(cl, {"n": 0, "maxInflight": 0, "maxParked": 0, "snapMax": 0, "over1300": 0, "secsLastinOver1500": 0,
                                "maxLastin": 0, "infrag": 0, "secsNoIn": 0, "minSnaps": 99, "activeSecs": 0})
        d["n"] += 1
        d["maxInflight"] = max(d["maxInflight"], int(r[4]))
        d["maxParked"] = max(d["maxParked"], int(r[6]))
        d["snapMax"] = max(d["snapMax"], int(r[9]))
        d["over1300"] += int(r[10])
        d["infrag"] += int(r[14])
        if int(r[2]) == 4:
            d["activeSecs"] += 1
            d["minSnaps"] = min(d["minSnaps"], int(r[7]))
            if int(r[15]) > 1500:
                d["secsLastinOver1500"] += 1
            if int(r[13]) == 0:
                d["secsNoIn"] += 1
            d["maxLastin"] = max(d["maxLastin"], int(r[15]))
    ev = re.findall(r"[^\r\n]*(?:SVCMDQ|SVCMDPARK|COOPSYNC|timed out|overflow|Server: |WARNING: msg overflowed|"
                    r"Script Error|has entered the battle|ERROR)[^\r\n]*", txt)
    return per, ev


# ---------------------------------------------------------------------------------------------- the run
def main():
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print(__doc__)
        return 2
    ST["run"] = sys.argv[2]
    a = sys.argv[3:]

    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    opts = {"srv": opt("--srv", "new"), "cl": opt("--cl", "new"), "clients": int(opt("--clients", "1")),
            "lobby": opt("--lobby", "stock"), "lobbysec": int(opt("--lobbysec", "300")),
            "missionsec": int(opt("--missionsec", "200")), "delay": int(opt("--delay", "0")),
            "ready": "--noready" not in a, "fps": int(opt("--fps", "60")), "poke": int(opt("--poke", "0")),
            "parkbytes": int(opt("--parkbytes", "-1"))}
    if opts["parkbytes"] < 0:
        opts["parkbytes"] = None
    ST["usercfg"] = "--usercfg" in a
    ST["netdebug"] = "--netdebug" in a
    ST["clprobe2"] = "--clprobe2" in a
    ST["clprobe"] = "--clprobe" in a or ST["clprobe2"]
    ST["listen"] = "--listen" in a
    ST["mx"] = {}
    if "--mx" in a:
        for n, grp in enumerate(opt("--mx", "").split(";")):
            ST["mx"][n + 1] = grp.split(",")
    opts["mx"] = ST["mx"]
    ST["ufps"] = int(opt("--ufps", "60"))
    opts["ufps"] = ST["ufps"]
    opts["listen"] = ST["listen"]
    opts["clprobe"] = ST["clprobe"]
    opts["usercfg"] = ST["usercfg"]
    os.makedirs(SCR, exist_ok=True)
    log("RUN", ST["run"], json.dumps(opts))
    users = hg.user_game_running()
    if users:
        log("NOTE user game processes present (not touched):", users)
    code = rev = None
    if "fix" in (opts["lobby"],):
        code, rev = fix_codepak()
    sbins = prep_bins(opts["srv"], H)
    cbins = [prep_bins(opts["cl"], SLOTS[i][1]) for i in range(opts["clients"])]
    shm, smt = seed_server(opts, code)
    pcs = []
    for i in range(opts["clients"]):
        pcs.append(seed_client(i + 1, SLOTS[i][1], code, veteran_record(1000 + i)))
    ctx = {"opts": opts, "rev": rev, "shots": [], "gids": [p[2] for p in pcs], "t": {}}
    slog = os.path.join(smt, "qconsole.log")
    try:
        if ST.get("listen"):
            slog = os.path.join(pcs[0][1], "qconsole.log")
        else:
            slog = start_server(sbins, shm, smt)
        if opts["delay"]:
            for i in range(opts["clients"]):
                open(os.path.join(pcs[i][1], "jf_delay.cfg"), "w").write("set cl_packetdelay %d\n" % opts["delay"])
        cs = []
        for i in range(opts["clients"]):
            cs.append(launch_client(i + 1, cbins[i], pcs[i][0], fps=opts["fps"]))
            if i + 1 < opts["clients"]:
                time.sleep(20)
                if ST.get("listen") and i == 0:
                    wait_for(slog, r"has entered the battle", 300)  # the host is up before a remote joins it
                    time.sleep(10)
        t0 = time.time()
        ctx["t"]["launched"] = time.strftime("%H:%M:%S")
        m = wait_for(slog, r"has entered the battle", 240)
        check("client entered the lobby", m)
        # the user's own menu activity during the upload: the fov menu reports through the name (player.scr
        # manageFovSet: "append name ,1<fov>"), i.e. two userinfo commands back to back
        for k in range(opts["poke"]):
            for c in cs:
                step(c, ['set name "JFTester%d ,0203"' % c["idx"], "wait 2", 'set name "JFTester%d"' % c["idx"]])
            time.sleep(4)
        if opts["delay"]:
            for c in cs:
                step(c, ["exec jf_delay.cfg"])
        # lobby stay
        mid = None
        while time.time() - t0 < opts["lobbysec"]:
            if any(c["bg"].proc.poll() is not None for c in cs):
                break
            if mid is None and time.time() - t0 > opts["lobbysec"] * 0.5:
                mid = [shot(c, "c%d_lobby_mid" % c["idx"]) for c in cs]
                ctx["shots"] += mid
            time.sleep(5)
        for c in cs:
            step(c, ["hzm_diag"])   # the client's own hitch record (frames > 100 ms, by phase) into its log
            ctx["shots"].append(shot(c, "c%d_lobby_end" % c["idx"]))
            st = len(read(slog))
        lobby_end = len(read(slog))
        cl_lobby_end = len(read(cs[0]["log"]))
        if opts["ready"]:
            for c in cs:
                step(c, ["+use", "wait 30", "-use", "wait 30"])
            m = wait_for(slog, r"Server: (?!co_lobby)\S+", 90, lobby_end)
            check("ready-up launched the campaign", m, m.group(0) if m else "")
            # in the mission: join a team, then play
            # the briefing is skipped by the squad ready gate (coop_mod/readygate.scr): everyone presses Use
            m2 = None
            for k in range(8):
                time.sleep(15)
                if re.search(r"Server: m1l1", read(cs[0]["log"])[cl_lobby_end:]):
                    break
                if k < 4:
                    for c in cs:
                        step(c, ["popmenu 0", "wait 5", "+use", "wait 40", "-use"])
                elif k == 4 and not ST.get("listen"):
                    # fallback: the same clean "map" transition the mod's own launch uses (stuffsrv map), via rcon
                    log("briefing skip by Use did not fire - rcon map m1l1")
                    step(cs[0], ["set rconPassword " + RCON, "rcon map m1l1"])
                elif k == 4:
                    step(cs[0], ["map m1l1"])
            m2 = wait_for(cs[0]["log"], r"Server: m1l1", 120, cl_lobby_end)
            check("briefing skipped into m1l1", m2)
            log("mission map:", m2.group(0) if m2 else "(no m1l1 line)")
            t1 = time.time()
            time.sleep(20)
            # spawn in: the mission starts the player as a spectator ("Press Fire to join the battle")
            for c in cs:
                for _ in range(3):
                    st0 = len(read(slog))
                    step(c, ["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20",
                             "popmenu 0", "wait 20", "+attackprimary", "wait 30", "-attackprimary", "wait 60"])
                    if wait_for(slog, r"JFTester%d[^\r\n]*(?:has joined|has entered)|KITGIVE" % c["idx"], 10, st0):
                        break
            ctx["shots"].append(shot(cs[0], "c1_mission_spawned"))
            half = None
            while time.time() - t1 < opts["missionsec"]:
                if any(c["bg"].proc.poll() is not None for c in cs):
                    break
                if half is None and time.time() - t1 > opts["missionsec"] * 0.5:
                    half = 1
                    for c in cs:
                        step(c, ["+forward", "wait 120", "-forward", "+moveleft", "wait 60", "-moveleft"])
                time.sleep(5)
            for c in cs:
                ctx["shots"].append(shot(c, "c%d_mission_end" % c["idx"]))
                step(c, ["+scores", "wait 150"])
                ctx["shots"].append(shot(c, "c%d_scores" % c["idx"]))
                step(c, ["-scores"])
        for c in cs:
            check("client %d still running at the end" % c["idx"], c["bg"].proc.poll() is None)
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        for c in ST["clients"]:
            try:
                stop_client(c)
            except Exception as e:
                log("client stop note", e)
        stop_server()
        time.sleep(2)
    per, ev = analyze(slog)
    for line in ev[:80]:
        log("EV", line.strip()[:260])
    for cl, d in per.items():
        log("SVNET summary cl=%d" % cl, json.dumps(d))
    stxt = read(slog)
    timeouts = len(re.findall(r"timed out", stxt))
    check("no client timed out", timeouts == 0, "timed out x%d" % timeouts)
    check("progression upload completed for every client", len(re.findall(r"COOPSYNC (merged|done)", stxt)) >= opts["clients"]
          and "upload timed out" not in stxt, "")
    dst = os.path.join(ARCHIVE, ST["run"])
    os.makedirs(dst, exist_ok=True)
    for tag, hm in [("srv", home(H, "srv"))] + [("pc%d" % (i + 1), pcs[i][0]) for i in range(len(pcs))]:
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(dst, tag))
    with open(os.path.join(dst, "results.json"), "w") as f:
        json.dump({"opts": opts, "rev": rev, "results": RES, "svnet": per, "events": ev[:400], "gids": ctx["gids"],
                   "shots": [s for s in ctx["shots"] if s]}, f, indent=1)
    lf = os.path.join(SCR, ST["run"] + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(dst, "harness.log"))
    n_fail = sum(1 for r in RES if not r[1])
    log("SUMMARY %d checks, %d failed -> %s" % (len(RES), n_fail, dst))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
