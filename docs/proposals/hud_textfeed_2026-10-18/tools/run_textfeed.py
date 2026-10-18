"""run_textfeed.py - private-harness proof for the text-feed batch (bugs 4005-4007); reuses run_joinflood.py plumbing.
Dedicated server straight on m1l1 (RELEASED exe + game.dll from the GOG root; the textfeed-next mod worktree packed as
a code pak; a test-only overlay pk3 holding tools/overlay/coop_mod/coop_selftest_xp.scr) and one fake-identity client
on 127.0.0.1 (G:\\mohaa-hudfeed5 slot, DISPLAY2 window only, never activated).
    python -I run_textfeed.py <runname> --res 1280x720 [--cgame <cgame.dll>] [--scen 1,2,3,5]
Scenarios (rcon tf_go N, see the overlay): 1 full feed + client-side subtitles, 2 real m1l1 hint, 3 banner, 4 old route,
5 long wording. Shots land in the client's screenshots dir and are copied to <archive>\\<run>.
"""
import importlib.util, os, re, shutil, sys, time, zipfile

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
jf.MODWT = r"C:\mohaa-coop-dev\hzm-mod-textfeed"
jf.ARCHIVE = r"G:\mohaa-hudfeed5\runs_textfeed"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad\textfeed"
log, check, read, wait_for, step = jf.log, jf.check, jf.read, jf.wait_for, jf.step
ST = jf.ST

SUBS = ["Lieutenant, get your men across the bridge before the Germans bring up their armour and cut us off from the beach!",
        "Sir, the sniper in the church tower has us pinned down, we need smoke on the square right now!",
        "Cover me, I'm going for the machine gun nest on the left, keep their heads down for ten seconds."]


def start_server2(bins, hm, mt):
    """jf.start_server, but ready = the map script chain ran (m1l1 prints none of the lobby's ready lines)"""
    args = [os.path.join(bins, "omohaaded_jf.exe")]
    for k, v in (("com_target_game", "2"), ("dedicated", "1"), ("fs_basepath", jf.GOG), ("fs_homepath", hm),
                 ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", str(jf.SPORT)), ("sv_maxclients", "4"),
                 ("g_gametype", "2"), ("logfile", "2"), ("coop_campaign", "1"), ("com_abnormalExit", "0")):
        args += ["+set", k, v]
    args += ["+exec", "jf_start.cfg"]
    p = jf.subprocess.Popen(args, cwd=bins, creationflags=0x08000000, stdin=jf.subprocess.DEVNULL,
                            stdout=jf.subprocess.DEVNULL, stderr=jf.subprocess.DEVNULL)
    ST["server"] = p
    lg = os.path.join(mt, "qconsole.log")
    log("server pid", p.pid)
    if not wait_for(lg, r"execing coop_mod/cfg/mapgrade\.cfg", 300):
        raise RuntimeError("server: map never became ready")
    time.sleep(8)
    return lg


def pick_slot():
    """the first harness copy whose harness_guard slot is free (2 games may run at once, each in its own copy)"""
    for _try in range(40):
      for owner, d in (("hudfeed5", r"G:\mohaa-hudfeed5"), ("hudfeed4", r"G:\mohaa-hudfeed4"), ("hudfeed2", r"G:\mohaa-hudfeed2")):
          try:
              jf.hg.acquire_slot(owner, os.path.join(d, "x.exe"), os.path.join(d, "home_probe"), [12832], 1)
              jf.hg.release_slot(owner)
          except Exception as e:
              log("slot", owner, "busy:", str(e)[:80])
              continue
          jf.SLOTS[:] = [(owner, d)]
          jf.H = d
          jf.PRISTINE = os.path.join(d, "pristine")
          jf.SPORT, jf.CPORTS[:] = 12831, [12832, 12833]
          log("using slot", owner)
          return

      time.sleep(15)
    raise RuntimeError("no free harness slot")


def overlay_pak():
    p = os.path.join(jf.SCR, "zzzzzzz_tf_overlay.pk3")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, "overlay", "coop_mod", "coop_selftest_xp.scr"), "coop_mod/coop_selftest_xp.scr")
    return p


def burst(c, name, n, gap):
    sd = os.path.join(c["mt"], "screenshots")
    lines = []
    for i in range(n):
        lines += ["screenshotJPEG %s_%02d" % (name, i), "wait %d" % gap]
    step(c, lines, timeout=120)
    time.sleep(2)
    out = [os.path.join(sd, f) for f in sorted(os.listdir(sd)) if f.startswith(name + "_")]
    log("burst", name, len(out))
    return out


def join(c, tries=3):
    for _ in range(tries):
        step(c, ["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20",
                 "popmenu 0", "wait 20", "+attackprimary", "wait 30", "-attackprimary", "wait 60"])
        time.sleep(3)


def main():
    name = sys.argv[1]
    a = sys.argv[2:]

    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    W, HH = [int(x) for x in opt("--res", "1280x720").split("x")]
    scen = [int(x) for x in opt("--scen", "1,2,3,5").split(",")]
    ST["run"] = name
    pick_slot()
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 60})
    os.makedirs(jf.SCR, exist_ok=True)
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 0, "parkbytes": None, "mx": {}, "ufps": 60,
            "listen": False, "clprobe": False, "usercfg": False}
    code, rev = jf.fix_codepak()
    sbins = jf.prep_bins("rel", jf.H)
    cbin = jf.prep_bins("rel", jf.SLOTS[0][1])
    if "--cgame" in a:
        cg = opt("--cgame", "")
        shutil.copyfile(cg, os.path.join(cbin, "cgame.dll"))   # client only: the dedicated server keeps the released game.dll
        log("client cgame.dll replaced by", cg, jf.md5f(cg)[:8])
    shm, smt = jf.seed_server(opts, code)
    shutil.copyfile(overlay_pak(), os.path.join(smt, "zzzzzzz_tf_overlay.pk3"))
    pc = jf.seed_client(1, jf.SLOTS[0][1], code, jf.veteran_record(1000))
    cfgp = os.path.join(smt, "jf_start.cfg")
    txt = jf.read(cfgp).replace("map co_lobby1", "seta coop_st_xp 1\nmap m1l1")
    txt = txt.replace("seta developer 0", "seta developer 1")   # script println / errors are developer-gated
    open(cfgp, "w", newline="\n").write(txt)
    shots = {}
    slog = os.path.join(smt, "qconsole.log")
    sd = None
    try:
        slog = start_server2(sbins, shm, smt)
        c = jf.launch_client(1, cbin, pc[0], W=W, Hh=HH)
        sd = os.path.join(c["mt"], "screenshots")
        m = wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240)
        check("client entered the server", m)
        step(c, ["set ui_gmbox 1", "set coop_hudFadeTime 600", "set coop_feedDebug 1", "set g_subtitle 1", "set cg_huddraw_force 1", "ui_hud 1",
                 "set rconPassword " + jf.RCON])
        time.sleep(30)
        join(c, 3)
        time.sleep(40)
        join(c, 2)
        step(c, ["+attackprimary", "wait 6", "-attackprimary", "wait 20"])
        shots["a_hud"] = jf.shot(c, "a_hud")
        def sc(tag, go, n, gap, pre=100, extra=None, post=None):
            """ONE console step: trigger, wait, then n shots `gap` frames apart (>= 50: closer ones are dropped by the exe)"""
            lines = (extra or []) + ["rcon set tf_go %d" % go, "wait %d" % pre] + (post or [])
            for i in range(n):
                lines += ["screenshotJPEG %s_%02d" % (tag, i), "wait %d" % gap]
            step(c, lines, timeout=150)
            time.sleep(2)
            shots[tag] = [os.path.join(sd, f) for f in sorted(os.listdir(sd)) if f.startswith(tag + "_")]
            log("shots", tag, len(shots[tag]))
        if 1 in scen:
            sc("b_sub_feed", 1, 4, 45, 330, None, ["set subtitle0 \"%s\"" % SUBS[0], "set subtitle1 \"%s\"" % SUBS[1], "set subtitle2 \"%s\"" % SUBS[2], "wait 70"])
            step(c, ["set subtitle0 \"\"", "set subtitle1 \"\"", "set subtitle2 \"\"", "wait 300"])
            time.sleep(8)
        if 5 in scen:
            sc("e_longwording", 5, 3, 120, 100)
            time.sleep(10)
        if 2 in scen:
            sc("c_m1l1_hint", 2, 6, 120, 1000)
            time.sleep(8)
        if 4 in scen:
            sc("f_oldroute", 4, 2, 60, 120)
            time.sleep(8)
        if 3 in scen:
            sc("d_banner", 3, 6, 50, 40, ["set cg_hud 1", "set cg_huddraw_force 1", "echo ^~^~^ HUDCV1", "cg_hud", "cg_huddraw_force", "ui_hud", "coop_cineHud", "echo ^~^~^ HUDCV2", "+attackprimary", "wait 6", "-attackprimary", "wait 10"])
            time.sleep(6)
        errs = re.findall(r"[^\r\n]*Script Error[^\r\n]*", read(slog))
        check("0 Script Error lines in the server log", not errs, "; ".join(errs[:3]))
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        try:
            jf.stop_client(jf.ST["clients"][0])
        except Exception as e:
            log("client stop note", e)
        jf.stop_server()
        time.sleep(2)
    dst = os.path.join(jf.ARCHIVE, name)
    os.makedirs(dst, exist_ok=True)
    if sd and os.path.isdir(sd):
        shutil.copytree(sd, os.path.join(dst, "shots"), dirs_exist_ok=True)
    for tag, hm in (("srv", jf.home(jf.H, "srv")), ("pc1", pc[0])):
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(dst, tag))
    lf = os.path.join(jf.SCR, name + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(dst, "harness.log"))
    for r in jf.RES:
        log("CHECK", r)
    log("DONE ->", dst, "rev", rev[:12], "shots", {k: v for k, v in shots.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
