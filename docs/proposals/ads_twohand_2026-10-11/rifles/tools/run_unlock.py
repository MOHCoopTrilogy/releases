"""THE UNLOCK PATH of the iron-sight G43, tested with the mod's own XP grant (private test install).
Overlay: mkov_rifle.py <pk3> --armgen, then srvtime_ov.py <pk3> <out.pk3>  (adds the coop_xtCmd probe; no tik needed).

    python run_unlock.py <session> --overlay <abs pk3> [--cgame cgame_rifle7] [--id 78]

Steps (ONE engine screenshot each; the menu actions are the cfgs the menu's own buttons exec):
  1 rank as found (0)            tile locked, requirement text; a click is refused
  2 rank 1, one award under 2    (two unrelated unlocks granted first, so the record is not empty) - still locked
  3 a REAL xp_award              the game promotes to rank 2 and grants rank 2's rewards: unlocked; the record keeps all it had
  4 pick it, restart the map     spawns with the rifle; the connect-time backfill leaves the record as it was
  5 the Flecktarn variant        locked; then 225 kills on the SCOPED G43's counter (chal_bump "wpn_g43" - the shared
                                 challenge wpn_g43_mv9) and VARIANT applies it; the map again: spawns with it
  6 after the game has quit      the test player's save files are put back as found (the run's own are moved into the run folder)
Log lines: `^~^~^ XT ...` (probe), `^~^~^ UNLOCK <step>:` + the cvars echoed after it.
"""
import os, sys, time, argparse, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_rifle as RR      # repoints the shared harness to G:\mohaa-adsanim2 (owner adsanim2, port 12558)
A, S, R = RR.A, RR.S, RR.R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_rifle7")
    ap.add_argument("--id", default="78"); ap.add_argument("--labelonly", action="store_true")
    a = ap.parse_args()
    i = a.id
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "unlock")
    k = [0]

    def shot(name):
        k[0] += 1
        return ["screenshotJPEG unl__%s__%d_%s" % (a.session, k[0], name), "wait 1", "wait 1", "wait 1", "wait 1"]

    def xt(cmd, wait=1200):
        return ["set coop_xtCmd %s" % cmd, "wait %d" % wait]
    menu = ["exec ui/loadout/open.cfg", "wait 4000", "pushmenu coop_loadout", "wait 500", "exec ui/loadout/init.cfg", "wait 500",
            "exec ui/loadout/lktab0.cfg", "wait 1500"]
    cv = ["coop_lo1", "coop_loS1", "coop_loS1F", "coop_loLkA%s" % i, "coop_loCmt%s" % i, "coop_lockLoadout", "wait 200"]
    # the test player's save files as found: put back after the game has quit (nothing is deleted - what the run wrote
    # is MOVED into the run folder)
    save = os.path.join(R.MAINTT, "coop_mod", "save")
    before = {f: open(os.path.join(save, f), "rb").read() for f in (os.listdir(save) if os.path.isdir(save) else [])}
    rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, ["set cg_drawviewmodel 2", "set ui_hud 1", "set coop_rtPoll 1"], a.overlay)

    def put_back():
        import shutil
        after = os.path.join(rundir, "save_after")
        os.makedirs(after, exist_ok=True)
        for f in (os.listdir(save) if os.path.isdir(save) else []):
            shutil.move(os.path.join(save, f), os.path.join(after, f))
        os.makedirs(save, exist_ok=True)
        for f, b in before.items():
            open(os.path.join(save, f), "wb").write(b)
        print("save files put back: %d as found; the run's own -> %s" % (len(before), after))

    def restart(name):
        t1 = len(R.read_log())
        R.step(["popmenu 0", "wait 300", "exec coop_mod/start_server.cfg"], timeout=60)
        if not R.wait_log(r"Detected Coop for", 300, t1):
            raise RuntimeError("the map did not come back")
        time.sleep(10)
        R.join()
        time.sleep(22)
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 6000", "useweaponclass rifle", "wait 3000"] + shot(name), timeout=120)
    try:
        t0 = len(R.read_log())
        if '--labelonly' in sys.argv:      # the variant's name line in the menu, nothing else
            R.step(menu + ["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/p%s.cfg" % i, "wait 600", "exec ui/loadout/fin8_s1.cfg", "wait 1800"] + shot("variant_label"), timeout=90)
            raise KeyboardInterrupt('label still only')
        # 1 as found
        R.step(xt("state") + menu + ["exec ui/loadout/req%s.cfg" % i, "wait 400"] + shot("rank0_locked"), timeout=90)
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800", "popmenu 0", "wait 400", "echo ^~^~^ UNLOCK rank0_click:"] + cv, timeout=90)
        # 2 rank 1, just under rank 2
        R.step(xt("seed", 2500) + xt("under2", 2500) + xt("state") + menu + ["exec ui/loadout/req%s.cfg" % i, "wait 400"] + shot("rank1_locked"), timeout=90)
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800", "popmenu 0", "wait 400", "echo ^~^~^ UNLOCK rank1_click:"] + cv, timeout=90)
        # 3 the real award: promotion + grant
        R.step(xt("award", 1000) + shot("promotion_hud_1s"), timeout=60)
        R.step(["wait 9000"] + xt("state") + menu + shot("rank2_unlocked"), timeout=90)
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800"] + shot("rank2_picked"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK rank2_click:"] + cv, timeout=60)
        # 4 the map again
        restart("rank2_spawned_with_it")
        R.step(xt("state") + ["echo ^~^~^ UNLOCK after_restart:"] + cv, timeout=60)
        # 5 the shared variant gate: Flecktarn locked -> the scoped G43's challenge done -> VARIANT applies it
        R.step(menu + ["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/p%s.cfg" % i, "wait 600", "exec ui/loadout/reqmv.cfg", "wait 300",
                       "exec ui/loadout/fin8_s1.cfg", "wait 1800"] + shot("variant_locked_click"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK variant_locked:"] + cv, timeout=60)
        R.step(xt("g43kills", 4000) + xt("state") + menu + ["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/p%s.cfg" % i, "wait 600",
                                                         "exec ui/loadout/fin8_s1.cfg", "wait 1800"] + shot("variant_unlocked_click"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK variant_unlocked:"] + cv, timeout=60)
        restart("spawned_with_flecktarn")
        R.step(xt("state") + ["echo ^~^~^ UNLOCK after_variant_restart:"] + cv, timeout=60)
        log = R.read_log()[t0:]
        for ln in log.splitlines():
            if re.search(r'\^~\^~\^ (XT|UNLOCK)|"coop_lo(1|S1|S1F|LkA%s|Cmt%s)" is|"coop_lockLoadout" is|LOCKED|Script Error|not on list|rror.*coop_rt' % (i, i), ln):
                print(ln[33:260])
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
        time.sleep(3)
        put_back()
        A.log("unlock run ended")


if __name__ == "__main__":
    main()
