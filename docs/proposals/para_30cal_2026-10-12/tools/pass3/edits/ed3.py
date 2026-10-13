"""ed3.py - third pass, parasquad.scr: (a) the medic is not tethered (his own loop runs him to a patient 2000u off);
(b) a man whose orders get him nowhere: walkOut, then LOST (the last-resort rescue in paradrop.scr reads it);
(c) the .30 cal on the engine keys of game.dll 1.10.22 (belt, heat, true rate of fire) through the helper file
coop_mod/parasquad_gun.scr: short bursts, he lets the barrel cool before it cooks, a second belt, belt out = pack up."""
import io, re
P = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr"
s = io.open(P, encoding="latin-1", newline="").read().replace("\r\n", "\n")


def sub(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)


# (a)
sub("""		// ---- the medic keeps behind the players (his own loop tends and follows; this is only his leash) ----
		local.a = level.coop_psqM[local.sid][5]
		if( local.a != NIL && local.a != NULL ){
			if( isAlive local.a ){
				local.mp = local.apos - ( vector_scale local.cfw 260 )
				waitthread post local.a local.mp 320
			}
		}

""", "")
sub("""	waitthread post self self.origin 240
	if( local.sid != NIL ){""", """	// (the medic keeps the engine's own leash: his loop in paradrop.scr runs him to a patient up to 2000u away)
	if( local.k != 5 ){ waitthread post self self.origin 240 }
	if( local.sid != NIL ){""")
sub("""				if( !isAlive local.a || local.a.coop_psqMounted == 1 ){ continue }
				local.a.coop_psqHp = local.a.health
				waitthread post local.a local.a.origin 180""", """				if( !isAlive local.a || local.a.coop_psqMounted == 1 || local.k == 5 ){ continue }
				local.a.coop_psqHp = local.a.health
				waitthread post local.a local.a.origin 180""")
# (b) moveTo: an order that got him nowhere
sub("""	local.a.movedoneradius = 40
	waitthread post local.a local.pos 240
	if( local.crouch == 1 ){ local.a crouchto local.pos } else { local.a runto local.pos }
	local.t = 0""", """	local.a.movedoneradius = 40
	local.d0 = vector_length( local.a.origin - local.pos )
	waitthread post local.a local.pos 240
	if( local.crouch == 1 ){ local.a crouchto local.pos } else { local.a runto local.pos }
	local.t = 0""")
sub("""	// his post is where he got to (the leash holds him there; see the header)
	waitthread post local.a local.a.origin 170
	local.a.enableEnemy = 1
	local.a forceactivate
	local.a.coop_psqBusy = 0
""", """	// his post is where he got to (the leash holds him there; see the header)
	waitthread post local.a local.a.origin 170
	local.a.enableEnemy = 1
	local.a forceactivate
	local.a.coop_psqBusy = 0
	// an order that got him nowhere and found no path (no pathnode in his 256u cell): the second one in a row
	// and he walks out in a straight line (walkOut); if that fails too he is LOST (see walkOut)
	if( local.d0 > 100 && vector_length( local.a.origin - local.pos ) > ( local.d0 - 24 ) && local.a.pathdist == 0 ){
		local.a.coop_psqNoGo++
		if( local.a.coop_psqNoGo >= 2 ){
			local.a.coop_psqNoGo = 0
			thread walkOut local.a local.pos
		}
	} else {
		local.a.coop_psqNoGo = 0
		local.a.coop_psqWoFail = 0
		local.a.coop_psqLost = 0
	}
""")
sub("""	self.coop_psqNoPath = 0
	self.coop_psqPinT = 0""", """	self.coop_psqNoPath = 0
	self.coop_psqNoGo = 0
	self.coop_psqWoFail = 0
	self.coop_psqLost = 0
	self.coop_psqPinT = 0""")
sub("""	local.a.coop_psqBusy = 0
	waitthread dbg ( "walkout k=" + local.a.coop_psqK + " goal=" + ( local.goal != NIL ) + " left=" + local.left )
}end""", """	local.a.coop_psqBusy = 0
	// no walkable line, or the walk went nowhere: twice in a row and he is LOST - there is no way out of where
	// he stands that this script can find. paradrop.scr's last resort (coop_paradrop_landing_check) reads this.
	if( local.goal == NIL || local.left > 200 ){
		local.a.coop_psqWoFail++
		if( local.a.coop_psqWoFail >= 2 ){ local.a.coop_psqLost = 1 }
	} else {
		local.a.coop_psqWoFail = 0
		local.a.coop_psqLost = 0
	}
	waitthread dbg ( "walkout k=" + local.a.coop_psqK + " goal=" + ( local.goal != NIL ) + " left=" + local.left + " lost=" + local.a.coop_psqLost )
}end""")
# (c) the gun
sub("""	local.gun maxIdlePitch 0
	local.gun pitchCaps ( -20 20 0 )
""", """	local.gun pitchCaps ( -20 20 0 )
""")
sub("""	local.gun suppressHeight 40
""", """	local.gun suppressHeight 40
	// the belt, the barrel and the true rate of fire: engine keys of game.dll 1.10.22 (weapturret.cpp, bug-3636..3639),
	// set in a helper file because a command an older game.dll does not know fails the WHOLE file it stands in
	// (TRAPS T1, bug-3423). He carries the belt in the gun and one more.
	if( local.a.coop_psqBelt == NIL ){
		local.a.coop_psqBelt = 250
		local.a.coop_psqBelts = 1
	}
	local.a.coop_psqMgKeys = 0
	local.a.coop_psqReload = 0
	local.kk = waitthread coop_mod/parasquad_gun.scr::belt local.gun local.a.coop_psqBelt
	if( local.kk == 1 ){
		local.a.coop_psqMgKeys = 1
		// with the keys he fires at the gun's own 10 rounds a second (without: one round a server frame, 40 a second,
		// which is what the wide cone and the long bursts above were chosen for): bursts of 5-9, a tighter cone
		local.gun burstFireSettings 0.5 0.9 1.0 2.2
		local.gun aibulletspread 150 150
	} else {
		// older game.dll: the gun at least rests level (the engine tips an unmanned gun barrel-up - ThinkIdle - and in
		// the 0.3s of the set-down it tipped 13 degrees and stayed there: the grips sank 10u under his hands)
		local.gun maxIdlePitch 0
	}
""")
sub("""mgLeft local.gun local.fired:{
	local.n = int( local.fired / 250 )
	local.left = 250 - int( local.fired - ( local.n * 250 ) )
	if( local.left < 25 ){ local.left = 25 }
""", """mgLeft local.gun local.fired:{
	// what is left of the belt he was on: the engine counts his rounds (coopaibelt). 125 on an older game.dll.
	local.left = waitthread coop_mod/parasquad_gun.scr::ammo local.gun
	if( local.left == NIL ){ local.left = 125 }
	if( local.left < 25 ){ local.left = 25 }
""")
sub("""		} else {
			local.fired = local.a.coop_psqMgFired
			local.why = waitthread mgTend local.a local.sid
			if( local.a == NULL ){ break }
			if( local.why != "stay" ){
				waitthread dbg ( "mg leave why=" + local.why )
				waitthread mgPackup local.a
""", """		} else {
			local.why = waitthread mgTend local.a local.sid
			if( local.a == NULL ){ break }
			if( local.why != "stay" ){
				waitthread dbg ( "mg leave why=" + local.why )
				if( local.why == "belt_out" ){ local.a.coop_psqBeltOut = 1 }	// no rounds left: a rifleman from here on
				waitthread mgPackup local.a
""")
sub("""if( level.coop_psqHolding[local.sid] == 1 && local.a.coop_psqBusy != 1 && level.time >= local.cool && local.near == 1 ){""",
    """if( level.coop_psqHolding[local.sid] == 1 && local.a.coop_psqBusy != 1 && level.time >= local.cool && local.near == 1 && local.a.coop_psqBeltOut != 1 ){""")
sub("""	local.apos = level.coop_psqApos[local.sid]
	if( level.coop_psqHolding[local.sid] != 1 ){
		if( vector_length( local.apos - local.gun.origin ) > 560 ){ end "squad_moved_on" }
	}
""", """	local.apos = level.coop_psqApos[local.sid]
	if( level.coop_psqHolding[local.sid] != 1 ){
		if( vector_length( local.apos - local.gun.origin ) > 560 ){ end "squad_moved_on" }
	}
	// the belt: out = the second belt goes in (4s with the gun silent), and when that is gone too he packs up
	if( local.a.coop_psqMgKeys == 1 && local.a.coop_psqReload != 1 ){
		local.am = waitthread coop_mod/parasquad_gun.scr::ammo local.gun
		if( local.am != NIL ){
			local.a.coop_psqBelt = local.am
			if( local.am == 0 ){
				if( local.a.coop_psqBelts < 1 ){ end "belt_out" }
				local.a.coop_psqBelts--
				thread mgReload local.a local.gun
				end "stay"
			}
		}
	}
""")
sub("""// four times a second while he is on the gun:""", """// a new belt: the gun is silent for 4s (mgHold holds it), then it has 250 rounds again
mgReload local.a local.gun:{
	local.a.coop_psqReload = 1
	waitthread dbg ( "mg newbelt left=" + local.a.coop_psqBelts )
	wait 4
	if( local.a == NULL || local.gun == NULL ){ end }
	local.gun coopammo 250
	local.a.coop_psqBelt = 250
	local.a.coop_psqReload = 0
}end


// four times a second while he is on the gun:""")
sub("""	local.watch = 0
	local.lastSee = level.time - 100
""", """	local.watch = 0
	local.hot = 0
	local.lastSee = level.time - 100
""")
sub("""		local.blk = waitthread playerInFront local.gun.origin local.dir
		if( local.blk != 1 ){ local.blk = waitthread mateInFront local.gun.origin local.dir local.sid local.a }
		if( local.blk == 1 && local.held != 1 ){
			local.gun targettype "none"
			local.gun stopFiring
			local.gun clearAimTarget
			local.held = 1
			local.watch = 0
			waitthread dbg "mg hold fire=friend_in_front"
		}""", """		local.blk = waitthread playerInFront local.gun.origin local.dir
		if( local.blk != 1 ){ local.blk = waitthread mateInFront local.gun.origin local.dir local.sid local.a }
		local.hw = "friend_in_front"
		if( local.blk != 1 && local.a.coop_psqReload == 1 ){ local.blk = 1; local.hw = "new_belt" }
		if( local.blk != 1 && local.a.coop_psqMgKeys == 1 ){
			// the barrel: he stops at 45 of 100 and lets it bleed to 12 (the engine locks a cooked gun for 2s);
			// while the squad is bounding on his fire he takes it to 70
			local.ht = waitthread coop_mod/parasquad_gun.scr::heat local.gun
			if( local.ht != NIL ){
				local.cap = 45
				local.st = level.coop_psqSupT[local.sid]
				if( local.st != NIL ){
					if( level.time < local.st ){ local.cap = 70 }
				}
				if( local.hot == 1 ){
					if( local.ht > 12 ){ local.blk = 1; local.hw = "barrel_hot" } else { local.hot = 0 }
				} else if( local.ht >= local.cap ){
					local.hot = 1
					local.blk = 1
					local.hw = "barrel_hot"
				}
			}
		}
		if( local.blk == 1 && local.held != 1 ){
			local.gun targettype "none"
			local.gun stopFiring
			local.gun clearAimTarget
			local.held = 1
			local.watch = 0
			waitthread dbg ( "mg hold fire=" + local.hw )
		}""")
sub("""			local.a.coop_psqMgFired = local.a.coop_psqMgFired + 1.6
""", "")
sub("""							if( local.a != NULL ){ local.a.coop_psqMgFired = local.a.coop_psqMgFired + 2.8 }
""", "")
# the script's own suppression burst: 0.6-1.0s, 1.5-2.5s while the squad is bounding on it
m = re.search(r"(?m)^(\t+)local\.t = 0\.8 \+ \( randomfloat 1\.0 \)\n", s)
assert m
i = m.group(1)
rep = [i + "local.t = 0.6 + ( randomfloat 0.4 )", i + "local.st = level.coop_psqSupT[local.sid]", i + "if( local.st != NIL ){",
       i + "\tif( level.time < local.st ){ local.t = 1.5 + ( randomfloat 1.0 ) }", i + "}"]
s = s[:m.start()] + "\n".join(rep) + "\n" + s[m.end():]
io.open(P, "w", encoding="latin-1", newline="").write(s)
G = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad_gun.scr"
io.open(G, "w", encoding="latin-1", newline="").write("""//====================================================================
// parasquad_gun.scr - the paratroopers' .30 cal: the TurretGun keys that exist only in game.dll 1.10.22 and
// later (fgame/weapturret.cpp, bug-3636..3639: coopaibelt, coopnoresupply, coopdrysound, coopheatrates,
// cooprestpitch, and the getters coopammo / coopheat).
// A FILE OF ITS OWN ON PURPOSE (docs/TRAPS.md T1, bug-3423): a command the running game.dll does not know fails
// the whole file it stands in. On an older game.dll this file does not load, every call into it returns nothing,
// and parasquad.scr - which tests for that - carries on with the gun as it was before.
//====================================================================

// the belt (local.n rounds, counted for the AI gunner too, no ammo box refills it, a dry click when it is out),
// the M1919's heat (40 a second of fire, 8 bleed, 25 cooling, 2s lock) and the rest: muzzle 3 degrees down
belt local.gun local.n:{
	local.gun coopammo local.n
	local.gun coopaibelt 1
	local.gun coopnoresupply 1
	local.gun coopdrysound "bar_snd_noammo"
	local.gun coopheatrates 40 8 25 2
	local.gun cooprestpitch 3
}end 1


// rounds left on the belt
ammo local.gun:{
	local.r = local.gun.coopammo
}end local.r


// the barrel's heat, 0-100
heat local.gun:{
	local.r = local.gun.coopheat
}end local.r
""")
print("ok", len(s.splitlines()), "lines")
