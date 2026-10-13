"""FG 42 Irons: THE UNLOCK PATH, tested in the lane's private test install with the mod's own XP grant and the mod's
own challenge counter (the rifle lane's run_unlock.py recipe; harness G:\\mohaa-adsanim4, owner adsanim4, port 12598).

    python run_unlock_h.py ov  <in.pk3 (mkov_h.py + the state patch)> <out.pk3>
          adds ../armory_ov/ (wire/stage_armory_fg42irons.py) and the MEASURE-ONLY probe coop_mod/coop_xt.scr
          (+ one line in the harness copy of coop_mod/weather.scr that starts it when coop_rtPoll is 1)
    python run_unlock_h.py run <session> --overlay <abs out.pk3> [--cgame cgame_heavy9] [--id 79]

Steps (ONE engine screenshot each; every menu action is the cfg the menu's own button execs):
  1 rank as found            heavy tab: the new tile locked, its requirement text; a click is refused
  2 one award under rank 18  (rank flag 17) - still locked
  3 a REAL xp_award          the game promotes to rank 18 and grants rank 18's rewards: unlocked; picked into slot 1
  4 the map again            spawns with the gun
  5 the WINTER finish        refused while its challenge is open; then 150 kills on the snow-map counter the kill hook
                             bumps (chal_bump "kill_snow" - challenge fin_winter, reward finish_camo_winter: the SAME
                             global unlock every gun's Winter finish has) and the finish applies; the map again
  6 after the game has quit  the test player's save files are put back as found (the run's own are MOVED to the run folder)
Log lines: `^~^~^ XT ...` (probe), `^~^~^ UNLOCK <step>:` + the cvars echoed after it.
"""
import os, sys, time, argparse, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hv
TIK = 'models/weapons/coop_fg42_irons.tik'
RANK = 18

SCR = '''// MEASURE ONLY (heavy/tools/run_unlock_h.py) - unlock path probe: console cvar coop_xtCmd = one word, run once on the host
//   state    rank, total, is the FG 42 Irons unlocked, is the Winter finish unlocked, the unlock record
//   under    put the player 2 XP past rank %(rank)d's threshold MINUS one award (rank flag %(rank1)d)
//   award    a REAL xp_award of 10 "kills" (crosses the threshold: the game's own promotion + rank unlock grant)
//   snow     150 kills on the snow-map counter, by the call the kill hook makes (completes fin_winter)
xpprobe:
	println "^~^~^ XT probe started"
	while( 1 ){
		local.c = getcvar( "coop_xtCmd" )
		if( local.c != "" ){
			setcvar "coop_xtCmd" ""
			local.p = $player[1]
			if( local.p == NULL ){
				println "^~^~^ XT no player"
			} else {
				if( local.p.flags["coop_xp_id"] == NIL ){ waitthread coop_mod/xp.scr::xp_identify local.p }
				waitthread coop_mod/challenges.scr::chal_ensure local.p
				if( local.c == "under" ){
					local.thr = level.coop_xp_rankXP[%(rank)d]
					local.gain = int( 10 * level.coop_xp_scale )
					local.pre = local.thr + 2 - local.gain
					local.p.flags["coop_xp_total"] = local.pre
					local.p.flags["coop_xp_rank"] = %(rank1)d
					local.p.flags["coop_xp_barMark"] = int( local.pre / 100 )
					local.p.flags["coop_xp_popupOn"] = NIL
					local.p.flags["coop_xp_ceremony"] = NIL
					thread coop_mod/loadoutpick.scr::loadout_ui_exportUnlocks local.p
					println ( "^~^~^ XT under thr=" + local.thr + " gain=" + local.gain + " pre=" + local.pre )
				}
				if( local.c == "award" ){
					println "^~^~^ XT award 10 kills"
					thread coop_mod/xp.scr::xp_award local.p 10 "kills" "Rank probe"
				}
				if( local.c == "snow" ){
					waitthread coop_mod/challenges.scr::chal_bump local.p "kill_snow" 150
					thread coop_mod/loadoutpick.scr::loadout_ui_exportUnlocks local.p
					println "^~^~^ XT snow 150 bumped"
				}
				if( local.c == "state" || local.c == "snow" ){
					local.u = local.p.flags["coop_chal_unlocks"]
					if( local.u == NIL ){ local.u = "" }
					local.k = waitthread coop_mod/loadoutpick.scr::loadout_isUnlocked local.p "%(tik)s"
					local.s = waitthread coop_mod/loadoutpick.scr::loadout_isUnlocked local.p "models/weapons/fg42.tik"
					local.w = waitthread coop_mod/loadoutpick.scr::loadout_finUnlocked local.p 6
					println ( "^~^~^ XT state rank=" + local.p.flags["coop_xp_rank"] + " total=" + local.p.flags["coop_xp_total"] + " irons=" + local.k + " scoped=" + local.s + " winter=" + local.w )
					println ( "^~^~^ XT record=" + local.u )
				}
			}
		}
		wait 0.2
	}
end
''' % dict(rank=RANK, rank1=RANK - 1, tik=TIK)
HOOK = '\tif( getcvar( "coop_rtPoll" ) == "1" ){ thread coop_mod/coop_xt.scr::xpprobe }\t//MEASURE ONLY\n'


def ov(src, out):
    zin = zipfile.ZipFile(src)
    rep = {'coop_mod/coop_xt.scr': SCR.replace('\n', '\r\n').encode('latin-1')}
    w = zin.read('coop_mod/weather.scr').decode('latin-1')
    a = w.index('if( getcvar( "coop_isPoll" ) == "1" )')
    a = w.index('\n', a) + 1
    rep['coop_mod/weather.scr'] = (w[:a] + HOOK + w[a:]).encode('latin-1')
    d = 0
    for ln in SCR.splitlines():
        c = ln.split('//')[0]; d += c.count('{') - c.count('}')
        assert d >= 0
    assert d == 0
    arm = os.path.join(hv.LANE, 'armory_ov')
    n = 0
    for dd, _, fs in os.walk(arm):
        for f in fs:
            if f == 'MANIFEST.txt':
                continue
            p = os.path.join(dd, f)
            rel = os.path.relpath(p, arm).replace(os.sep, '/')
            assert rel != 'coop_mod/weather.scr'
            rep[rel] = open(p, 'rb').read(); n += 1
    low = {k.lower() for k in rep}
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for i in zin.infolist():
            if i.filename.lower() in low:
                continue
            z.writestr(i.filename, zin.read(i.filename))
        for k, v in rep.items():
            z.writestr(k, v)
    print('wrote', out, '(%d armory files + the probe)' % n)


def run(argv):
    import run_h
    A, S, R = run_h.A, run_h.S, run_h.R
    assert R.CLIENT == hv.CLIENT and R.PORT == hv.PORT and R.OWNER == hv.OWNER
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_heavy9")
    ap.add_argument("--id", default="79"); ap.add_argument("--short", action="store_true", help="steps 1-3 only (no map restart)")
    a = ap.parse_args(argv)
    i = a.id
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "unlock")
    k = [0]

    def shot(name):
        k[0] += 1
        return ["screenshotJPEG unl__%s__%d_%s" % (a.session, k[0], name), "wait 1", "wait 1", "wait 1", "wait 1"]

    def xt(cmd, wait=1200):
        return ["set coop_xtCmd %s" % cmd, "wait %d" % wait]
    # the menu's own way in (open.cfg -> the server exports the lock cvars; init.cfg; then the HEAVY tab button's command)
    menu = ["exec ui/loadout/open.cfg", "wait 4000", "pushmenu coop_loadout", "wait 500", "exec ui/loadout/init.cfg", "wait 500",
            "set coop_loNP0 1", "set coop_loP1 0", "set coop_loP2 0", "set coop_loP3 1", "set coop_loP4 0", "set coop_loP5 0", "append name ,w0t3",
            "exec ui/loadout/lktab3.cfg", "wait 1500"]
    cv = ["coop_lo1", "coop_loS1", "coop_loS1F", "coop_loLkA%s" % i, "coop_loCmt%s" % i, "coop_lockLoadout", "wait 200"]
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
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 6000", "useweaponclass mg", "wait 3000"] + shot(name), timeout=120)
    try:
        t0 = len(R.read_log())
        # 1 as found
        R.step(xt("state") + menu + ["exec ui/loadout/req%s.cfg" % i, "wait 400"] + shot("asfound_locked"), timeout=90)
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800"] + shot("asfound_click"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK asfound_click:"] + cv, timeout=90)
        # 2 rank 17, one award under rank 18
        R.step(xt("under", 2500) + xt("state") + menu + ["exec ui/loadout/req%s.cfg" % i, "wait 400"] + shot("rank17_locked"), timeout=90)
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800", "popmenu 0", "wait 400", "echo ^~^~^ UNLOCK rank17_click:"] + cv, timeout=90)
        # 3 the real award: promotion + grant
        R.step(xt("award", 1000) + shot("promotion_hud_1s"), timeout=60)
        R.step(["wait 9000"] + xt("state") + menu + shot("rank18_unlocked"), timeout=90)
        R.step(["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/t%s.cfg" % i, "wait 1800"] + shot("rank18_picked"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK rank18_click:"] + cv, timeout=60)
        if a.short:
            raise KeyboardInterrupt('--short: the menu steps only')
        # 4 the map again
        restart("rank18_spawned_with_it")
        R.step(xt("state") + ["echo ^~^~^ UNLOCK after_restart:"] + cv, timeout=60)
        # 5 the Winter finish: refused, then its challenge completed the game's way, applied, the map again
        fin = ["exec ui/loadout/s1sel.cfg", "wait 200", "exec ui/loadout/p%s.cfg" % i, "wait 600", "exec ui/loadout/fin6_s1.cfg", "wait 1800"]
        R.step(menu + fin + shot("winter_locked_click"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK winter_locked:"] + cv, timeout=60)
        R.step(xt("snow", 4000) + menu + fin + shot("winter_unlocked_click"), timeout=90)
        R.step(["popmenu 0", "wait 400", "echo ^~^~^ UNLOCK winter_unlocked:"] + cv, timeout=60)
        restart("spawned_with_winter")
        R.step(xt("state") + ["echo ^~^~^ UNLOCK after_winter_restart:"] + cv, timeout=60)
        log = R.read_log()[t0:]
        for ln in log.splitlines():
            if re.search(r'\^~\^~\^ (XT|UNLOCK)|"coop_lo(1|S1|S1F|LkA%s|Cmt%s)" is|"coop_lockLoadout" is|LOCKED|Script Error|not on list|rror.*coop_xt' % (i, i), ln):
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
    if sys.argv[1] == 'ov':
        ov(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'run':
        run(sys.argv[2:])
    else:
        raise SystemExit(__doc__)
