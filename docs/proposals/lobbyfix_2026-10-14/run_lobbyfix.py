"""run_lobbyfix.py - private-harness proof for bug-3913/3914/3915/3916 (reuses run_joinflood.py's plumbing).
Dedicated server on co_lobby1 (released v1.10.2x exe + dlls, the lobbyfix mod worktree packed as a code pak) with
two fake-identity clients on 127.0.0.1 (G:\\mohaa-hudfeed5 / hudfeed4 slots, DISPLAY2 windows only).
    python -I run_lobbyfix.py <runname> [--skip-sas]
"""
import importlib.util, os, re, shutil, sys, time

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
sys.argv_saved = sys.argv
spec.loader.exec_module(jf)
jf.MODWT = r"C:\mohaa-coop-dev\hzm-mod-lobbyfix"
jf.ARCHIVE = r"H:\hzm_archive\lobbyfix"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\lobbyfix"
log, check, read, wait_for, step, shot = jf.log, jf.check, jf.read, jf.wait_for, jf.step, jf.shot
ST = jf.ST


def main():
    name = sys.argv[1]
    skip_sas = "--skip-sas" in sys.argv
    ST["run"] = name
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 60})
    os.makedirs(jf.SCR, exist_ok=True)
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 0, "parkbytes": None, "mx": {}, "ufps": 60,
            "listen": False, "clprobe": False, "usercfg": False}
    code, rev = jf.fix_codepak()
    sbins = jf.prep_bins("rel", jf.H)
    cbins = [jf.prep_bins("rel", jf.SLOTS[i][1]) for i in range(2)]
    shm, smt = jf.seed_server(opts, code)
    def rec(i):
        r = jf.veteran_record(1000 + i)
        # same known-unlocked uniforms for BOTH clients so a lock cannot masquerade as a per-player bug
        r["unlocks"] = "models/player/american_8thUrbanRangerSniper.tik|models/player/american_8thUrbanRanger.tik|" + r["unlocks"]
        return r
    pcs = [jf.seed_client(i + 1, jf.SLOTS[i][1], code, rec(i)) for i in range(2)]
    cfgp = os.path.join(smt, "jf_start.cfg")
    txt = read(cfgp).replace("seta developer 0", "seta developer 1")   # script println is developer-gated
    open(cfgp, "w", newline="\n").write(txt)
    shots = []
    try:
        slog = jf.start_server(sbins, shm, smt)
        c1 = jf.launch_client(1, cbins[0], pcs[0][0])
        wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240)
        c2 = jf.launch_client(2, cbins[1], pcs[1][0])
        m = wait_for(slog, r"JFTester2[^\r\n]*entered the battle", 240)
        check("client 2 entered the lobby", m)
        time.sleep(30)
        shots.append(shot(c1, "a_lobby_two_default"))      # bottom bar: LOADOUT + SERVICE RECORD
        # --- bug-3915: both clients change uniform through the armory name bus (ungated skins 06 / 100)
        st = len(read(slog))
        step(c2, ['set name "JFTester2 ,sn101"', "wait 120"])
        time.sleep(4)
        step(c1, ['set name "JFTester1 ,sn100"', "wait 120"])
        time.sleep(6)
        stxt = read(slog)[st:]
        a2 = re.search(r"ARMSKIN apply player=JFTester2[^\r\n]*", stxt)
        a1 = re.search(r"ARMSKIN apply player=JFTester1[^\r\n]*", stxt)
        log("apply c1:", a1.group(0) if a1 else None)
        log("apply c2:", a2.group(0) if a2 else None)
        check("player 2 uniform change applied (mannequin swapped)", bool(a2) and not re.search(r"mannequin=(NIL|NULL)?$", a2.group(0)), a2.group(0) if a2 else "")
        check("player 1 uniform change applied", bool(a1), a1.group(0) if a1 else "")
        shots.append(shot(c1, "b_lobby_skins_changed"))
        # --- bug-3913: client 2 leaves
        st = len(read(slog))
        jf.stop_client(c2)
        m = wait_for(slog, r"LOBBY mannequin reaped", 40, st)
        check("mannequin of the departed player was removed", m)
        time.sleep(3)
        shots.append(shot(c1, "c_lobby_after_leave"))
        # --- bug-3916: m1l2a with the dev switches (fast timers, ignore flags/proximity)
        if not skip_sas:
            st = len(read(slog))
            step(c1, ["set rconPassword " + jf.RCON, "rcon set coop_sasfs_fast 1", "rcon set coop_sasfs_test 2", "rcon map m1l2a"])
            m = wait_for(slog, r"sasfs stage1[^\r\n]*", 150, st)
            check("SAS failsafe stage 1 fired", m, m.group(0) if m else "")
            m = wait_for(slog, r"sasfs stage2[^\r\n]*", 60, st)
            check("SAS failsafe stage 2 fired", m, m.group(0) if m else "")
            m = wait_for(slog, r"sasfs stage3[^\r\n]*", 60, st)
            check("SAS failsafe stage 3 fired", m, m.group(0) if m else "")
            errs = re.findall(r"[^\r\n]*Script Error[^\r\n]*", read(slog)[st:])
            check("m1l2a loaded with 0 Script Error lines", not errs, "; ".join(errs[:3]))
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
    allerr = re.findall(r"[^\r\n]*Script Error[^\r\n]*", read(os.path.join(smt, "qconsole.log")))
    check("0 Script Error lines in the whole server log", not allerr, "; ".join(allerr[:3]))
    dst = os.path.join(jf.ARCHIVE, name)
    os.makedirs(dst, exist_ok=True)
    for tag, hm in [("srv", jf.home(jf.H, "srv"))] + [("pc%d" % (i + 1), pcs[i][0]) for i in range(2)]:
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(dst, tag))
    lf = os.path.join(jf.SCR, name + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(dst, "harness.log"))
    log("DONE ->", dst, "rev", rev[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
