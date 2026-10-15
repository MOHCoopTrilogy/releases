"""run_brieffix.py - private-harness proof for bug-3917 (reuses run_joinflood.py plumbing).
Dedicated server on co_lobby1 (mod worktree hzm-mod-brieffix as code pak) + ONE remote client on 127.0.0.1
(G:\\mohaa-hudfeed5, DISPLAY2 only), 100 ms packet delay each way (~200 ms ping), then rcon map briefing/briefing1
and a burst of engine screenshots across the briefing1c slide (15 s, longer than the old 2 s forced re-add).
    python -I run_brieffix.py <runname> [modworktree]
"""
import importlib.util, os, re, shutil, sys, time

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
jf.MODWT = sys.argv[2] if len(sys.argv) > 2 else r"C:\mohaa-coop-dev\hzm-mod-brieffix"
jf.ARCHIVE = r"H:\hzm_archive\brieffix"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\brieffix"
log, check, read, wait_for, step, shot = jf.log, jf.check, jf.read, jf.wait_for, jf.step, jf.shot
ST = jf.ST


def main():
    name = sys.argv[1]
    ST["run"] = name
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 60})
    os.makedirs(jf.SCR, exist_ok=True)
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 100, "parkbytes": None, "mx": {}, "ufps": 60,
            "listen": False, "clprobe": False, "usercfg": False}
    code, rev = jf.fix_codepak()
    sbins = jf.prep_bins("rel", jf.H)
    cb = jf.prep_bins("rel", jf.SLOTS[0][1])
    shm, smt = jf.seed_server(opts, code)
    pc = jf.seed_client(1, jf.SLOTS[0][1], code, jf.veteran_record(1000))
    cfgp = os.path.join(smt, "jf_start.cfg")
    txt = read(cfgp).replace("seta developer 0", "seta developer 1")
    open(cfgp, "w", newline="\n").write(txt)
    shots = []
    try:
        slog = jf.start_server(sbins, shm, smt)
        c1 = jf.launch_client(1, cb, pc[0])
        check("client entered the lobby", wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240))
        open(os.path.join(pc[1], "jf_delay.cfg"), "w").write("set cl_packetdelay 100\n")
        step(c1, ["exec jf_delay.cfg"])
        time.sleep(15)
        st = len(read(slog))
        step(c1, ["set rconPassword " + jf.RCON, "rcon map briefing/briefing1"])
        wait_for(slog, r"waiting for you to spawn", 120, st)
        time.sleep(25)
        for _ in range(3):
            step(c1, ["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20", "popmenu 0", "wait 20", "+attackprimary", "wait 30", "-attackprimary", "wait 60"])
            if wait_for(slog, r"MENUMIRROR slide briefing1a -> entnum", 12, st):
                break
        m = wait_for(slog, r"MENUMIRROR slide briefing1a -> entnum", 240, st)
        check("briefing1a sent to the remote client", m)
        m = wait_for(slog, r"MENUMIRROR slide briefing1b -> entnum", 60, st)
        check("briefing1b sent", m)
        m = wait_for(slog, r"MENUMIRROR slide briefing1c -> entnum", 90, st)
        check("briefing1c sent (15 s slide)", m)
        for i in range(6):
            time.sleep(1.5)
            shots.append(shot(c1, "brief_c_%d" % i))
        txt = read(slog)[st:]
        sends = re.findall(r"MENUMIRROR slide (\w+) -> entnum \d+", txt)
        log("slide send sequence:", sends)
        check("each slide sent exactly once per player", len(sends) == len(set(sends)), str(sends))
        errs = re.findall(r"[^\r\n]*Script Error[^\r\n]*", txt)
        check("0 Script Error lines", not errs, "; ".join(errs[:3]))
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        for c in ST["clients"]:
            try:
                jf.stop_client(c)
            except Exception as e:
                log("stop note", e)
        jf.stop_server()
        time.sleep(2)
    dst = os.path.join(jf.ARCHIVE, name)
    os.makedirs(dst, exist_ok=True)
    for tag, hm in [("srv", jf.home(jf.H, "srv")), ("pc1", pc[0])]:
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(dst, tag))
    lf = os.path.join(jf.SCR, name + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(dst, "harness.log"))
    log("DONE ->", dst, "rev", rev[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
