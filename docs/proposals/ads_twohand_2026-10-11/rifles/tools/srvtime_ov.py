"""MEASURE-ONLY overlay for the SERVER reload timing check (run_srvtime.py). NEVER shipped.

    python srvtime_ov.py <in.pk3 from mkov_rifle.py> <out.pk3> <weapon tik> [<weapon tik> ...]

Adds to a copy of the overlay:
* coop_mod/coop_rt.scr - a server script: while cvar coop_rtOn is 1 it prints, every server frame, level.time and the
  player's RESERVE rifle ammo (`getammo`: the reserve drops in the frame the magazine is filled); two labels the weapon
  tik calls when its own `reload` row starts / reaches its last frame / is left (= Weapon::DoneReloading's side);
* coop_mod/weather.scr - the harness copy + one line that starts the probe when coop_rtPoll is 1 at map load;
* each named weapon tik (the STAGED one if there is one, else the RELEASED one) with three server commands added to its
  `reload` row: entry / last / exit -> the labels above. The row's clip is NOT changed.
"""
import sys, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged                       # noqa: E402
vfs = staged.vfs

SCR = '''// MEASURE ONLY (rifles/tools/srvtime_ov.py) - server reload timing probe
probe:
	println "^~^~^ RT probe started"
	while( 1 ){
		if( getcvar( "coop_rtOn" ) == "1" ){
			local.p = $player[1]
			if( local.p != NULL ){
				local.a = local.p getammo "rifle"
				println ( "^~^~^ RT tick t=" + level.time + " reserve=" + local.a )
			}
		}
		waitframe
	}
end

// ---- UNLOCK PATH probe (run_unlock.py): console cvar coop_xtCmd = one word, run once on the host player.
//   state    print rank, total, is the iron-sight G43 unlocked, is its Flecktarn variant unlocked, the unlock record
//   seed     grant two unrelated items through the mod's own chal_add_unlock (so the record is not empty)
//   under2   put the player 2 XP past rank 2's threshold MINUS one award (rank flag 1) - coop_selftest_xp.scr's promo recipe
//   award    a REAL xp_award of 10 "kills" (crosses the threshold: the game's own promotion + rank unlock grant)
//   backfill the connect-time path: xp_rank_unlock 0..rank
//   g43kills 225 kills on the scoped G43's counter (chal_bump "wpn_g43"): completes its Flecktarn variant challenge
//            wpn_g43_mv9 - the gate the iron-sight G43's Flecktarn SHARES
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
				if( local.c == "seed" ){
					waitthread coop_mod/challenges.scr::chal_add_unlock local.p "models/weapons/bar.tik"
					waitthread coop_mod/challenges.scr::chal_add_unlock local.p "models/weapons/kar98sniper.tik"
					println "^~^~^ XT seed done"
				}
				if( local.c == "under2" ){
					local.thr = level.coop_xp_rankXP[2]
					local.gain = int( 10 * level.coop_xp_scale )
					local.pre = local.thr + 2 - local.gain
					local.p.flags["coop_xp_total"] = local.pre
					local.p.flags["coop_xp_rank"] = 1
					local.p.flags["coop_xp_barMark"] = int( local.pre / 100 )
					local.p.flags["coop_xp_popupOn"] = NIL
					local.p.flags["coop_xp_ceremony"] = NIL
					thread coop_mod/loadoutpick.scr::loadout_ui_exportUnlocks local.p
					println ( "^~^~^ XT under2 thr=" + local.thr + " gain=" + local.gain + " pre=" + local.pre )
				}
				if( local.c == "award" ){
					println "^~^~^ XT award 10 kills"
					thread coop_mod/xp.scr::xp_award local.p 10 "kills" "Rank probe"
				}
				if( local.c == "backfill" ){
					waitthread coop_mod/xp.scr::xp_rank_unlock local.p 0 local.p.flags["coop_xp_rank"]
					println "^~^~^ XT backfill done"
				}
				if( local.c == "g43kills" ){
					// the scoped G43's kill counter, by the call the kill hook makes: 225 = the Flecktarn variant's target
					waitthread coop_mod/challenges.scr::chal_bump local.p "wpn_g43" 225
					thread coop_mod/loadoutpick.scr::loadout_ui_exportUnlocks local.p
					println "^~^~^ XT g43kills 225 (wpn_g43)"
				}
				// (no `restore` here: level variables do not survive a map restart - run rb44 wrote "NIL" into the test
				// player's save files. run_unlock.py puts the save FILES back from outside the game.)
				if( local.c == "state" || local.c == "seed" || local.c == "backfill" || local.c == "g43kills" ){
					local.u = local.p.flags["coop_chal_unlocks"]
					if( local.u == NIL ){ local.u = "" }
					local.k = waitthread coop_mod/loadoutpick.scr::loadout_isUnlocked local.p "models/weapons/coop_g43_irons.tik"
					local.v = waitthread coop_mod/loadoutpick.scr::loadout_mvUnlocked local.p "models/weapons/coop_g43_irons.tik" 8
					println ( "^~^~^ XT state rank=" + local.p.flags["coop_xp_rank"] + " total=" + local.p.flags["coop_xp_total"] + " irons=" + local.k + " ironsFleck=" + local.v )
					println ( "^~^~^ XT record=" + local.u )
				}
			}
		}
		wait 0.2
	}
end
'''
HOOK = ('\tif( getcvar( "coop_rtPoll" ) == "1" ){ thread coop_mod/coop_rt.scr::probe }\t//MEASURE ONLY\n'
        '\tif( getcvar( "coop_rtPoll" ) == "1" ){ thread coop_mod/coop_rt.scr::xpprobe }\t//MEASURE ONLY\n')
MARKSCR = {'ENTRY': 0, 'LAST': 0}
# the Listener `exec` event takes a script FILE (run rb39: "Can't find 'coop_mod/coop_rt.scr::wentry'"): one file per mark
# run rb40: `last` / `exit` server commands of a weapon row never fire (the row is ended by the anim-done event); a
# NUMBERED frame does: the mark is put on frame (frames - 2) of the row's clip - the row ends 2 frames (0.067 s) later
CMDS = '\t\t\tentry exec coop_mod/coop_rt_wentry.scr\n\t\t\t%d exec coop_mod/coop_rt_wlast.scr\n'
MARK = 'main:\n\tprintln ( "^~^~^ RT weapon reload row %s t=" + level.time )\nend\n'


def tik_probe(text, name):
    m = re.search(r'(?m)^[ \t]*reload[ \t]+\S+\.skc[^\n]*\n', text)
    assert m, name + ': no reload row'
    import rowlen
    clip = [c for n, c in rowlen.rows(text).items() if n == 'reload'][0]
    nf = rowlen.clip_len(vfs.read(clip))[0]
    CMDS = globals()['CMDS'] % (nf - 2)
    print('   ', name, 'reload row', clip, nf, 'frames; end mark on frame', nf - 2)
    i = text.index('{', m.end())
    s = re.compile(r'server\s*\{[ \t]*\r?\n').search(text, i)
    j = text.index('}', i)
    if s and s.start() < text.index('client', i) + 4000 and s.start() < _block_end(text, i):
        return text[:s.end()] + CMDS + text[s.end():]
    # no server block in the row: add one
    k = text.index('\n', i) + 1
    return text[:k] + '\t\tserver\n\t\t{\n' + CMDS + '\t\t}\n' + text[k:]


def _block_end(text, i):
    d = 0
    for j in range(i, len(text)):
        d += (text[j] == '{') - (text[j] == '}')
        if d == 0:
            return j
    raise AssertionError('unbalanced')


def main():
    src, out, tiks = sys.argv[1], sys.argv[2], sys.argv[3:]
    zin = zipfile.ZipFile(src)
    rep = {'coop_mod/coop_rt.scr': SCR.replace('\n', '\r\n').encode('latin-1')}
    for k in ('ENTRY', 'LAST'):
        rep['coop_mod/coop_rt_w%s.scr' % k.lower()] = (MARK % k).replace('\n', '\r\n').encode('latin-1')
    w = zin.read('coop_mod/weather.scr').decode('latin-1')
    a = w.index('if( getcvar( "coop_isPoll" ) == "1" )')
    a = w.index('\n', a) + 1
    rep['coop_mod/weather.scr'] = (w[:a] + HOOK + w[a:]).encode('latin-1')
    names = {n.lower(): n for n in zin.namelist()}
    for tk in tiks:
        rel = 'models/weapons/' + tk
        if rel.lower() in names:
            t = zin.read(names[rel.lower()]).decode('latin-1'); frm = 'staged'
        else:
            staged.off(); t = vfs.read(rel).decode('latin-1'); staged.on(); frm = 'RELEASED'
        t2 = tik_probe(t, tk)
        assert t2.count('coop_rt_w') == 2, tk
        d = 0
        for ln in t2.splitlines():
            c = ln.split('//')[0]; d += c.count('{') - c.count('}')
        assert d == 0, tk
        rep[names.get(rel.lower(), rel)] = t2.encode('latin-1')
        print('probe commands in', tk, '(' + frm + ')')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for i in zin.infolist():
            if i.filename in rep:
                continue
            z.writestr(i.filename, zin.read(i.filename))
        for k, v in rep.items():
            z.writestr(k, v)
    print('wrote', out, '(+%d measure-only files)' % len(rep))


if __name__ == '__main__':
    main()
