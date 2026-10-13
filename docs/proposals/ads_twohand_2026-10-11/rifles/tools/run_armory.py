"""Iron-sight G43 as its own armory entry (wire/stage_armory_g43irons.py), run ONCE in the private test install:
the tile, locked / unlocked, the pick spawns the rifle, a finish applies, a map restart keeps the pick.
ONE engine screenshot per step; every menu action is the cfg the menu's own button execs.

    python run_armory.py <session> --overlay <abs pk3 built with mkov_rifle.py --armory> [--cgame cgame_rifle7] [--id 78]
Stills: <runs>/<session>/arm__<session>__<n>_<name>.jpg ; the log lines of interest are printed at the end.
"""
import os, sys, time, argparse, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_rifle as RR      # repoints the shared harness to G:\mohaa-adsanim2 (owner adsanim2, port 12558)
A, S, R = RR.A, RR.S, RR.R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_rifle7")
    ap.add_argument("--id", default="78"); ap.add_argument("--menuonly", action="store_true")
    a = ap.parse_args()
    i = a.id
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "armory")
    k = [0]

    def shot(name):
        k[0] += 1
        return ["screenshotJPEG arm__%s__%d_%s" % (a.session, k[0], name), "wait 1", "wait 1", "wait 1", "wait 1"]
    # the menu's own way in: open.cfg sends the ",w0o" token (the server then exports the lock cvars), init.cfg sets the
    # view state, lktab0.cfg applies the locks of the rifle tab (run rb34: a bare pushmenu showed stale locks)
    menu = ["exec ui/loadout/open.cfg", "wait 4000", "pushmenu coop_loadout", "wait 500", "exec ui/loadout/init.cfg", "wait 500",
            "exec ui/loadout/lktab0.cfg", "wait 1500"]
    rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, ["set cg_drawviewmodel 2", "set ui_hud 1"], a.overlay)

    def restart(name):
        """the map again (the recipe the menu's Apply uses), join, spawn: what does the spawn inventory hand out?"""
        t1 = len(R.read_log())
        R.step(["popmenu 0", "wait 300", "exec coop_mod/start_server.cfg"], timeout=60)
        if not R.wait_log(r"Detected Coop for", 300, t1):
            raise RuntimeError("the map did not come back")
        time.sleep(10)
        R.join()
        time.sleep(22)
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 6000", "useweaponclass rifle", "wait 3000"] + shot(name), timeout=120)
        R.step(["echo ^~^~^ ARMORY %s:" % name, "coop_lo1", "coop_loS1", "coop_loS1F", "coop_lockLoadout", "wait 200"], timeout=60)
    try:
        t0 = len(R.read_log())
        # 1 the rifle tab as the test player finds it (locks armed), the new tile's requirement text shown
        R.step(menu + ["exec ui/loadout/req%s.cfg" % i, "wait 400"] + shot("tab_locks_armed"), timeout=90)
        # 2 a click on the tile while locked: the inspect page; the commit is the server's deny
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800"] + shot("pick_locks_armed"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ ARMORY locked:", "coop_lo1", "coop_loLkA%s" % i, "coop_loCmt%s" % i, "wait 200"], timeout=60)
        # 3 the gate off = every weapon unlocked (the unlocked state of the tile)
        R.step(["set coop_lockLoadout 0", "wait 1500"] + menu + shot("tab_unlocked"), timeout=90)
        # 4 pick it into slot 1
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800"] + shot("pick_unlocked"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ ARMORY unlocked:", "coop_lo1", "coop_loS1", "coop_loA1", "coop_loLkA%s" % i, "coop_loCmt%s" % i, "wait 200"], timeout=60)
        if '--menuonly' in sys.argv:
            raise KeyboardInterrupt('menu stills only')
        # 5 the map again: the pick must come back by itself and be in the hands
        restart("spawned_with_pick_after_map_restart")
        # 6 a finish (6 = Winter) on slot 1, the map again
        R.step(["set coop_lockLoadout 0", "wait 1500"] + menu + ["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/p%s.cfg" % i, "wait 600", "exec ui/loadout/fin6_s1.cfg", "wait 1800"] + shot("finish_winter_menu"), timeout=90)
        restart("spawned_with_finish_after_map_restart")
        log = R.read_log()[t0:]
        for ln in log.splitlines():
            if re.search(r'ARMORY|"coop_lo(1|S1|A1|S1F|LkA%s|Cmt%s)" is|"coop_lockLoadout" is|KITGIVE|coop_g43_irons|Script Error|not on list' % (i, i), ln):
                print(ln[-200:])
    except (Exception, KeyboardInterrupt) as e:
        A.log("FAILED", repr(e))
        print("FAILED", repr(e))
    finally:
        S.end_session(rundir, notes)
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        A.log("armory run ended")


if __name__ == "__main__":
    main()
