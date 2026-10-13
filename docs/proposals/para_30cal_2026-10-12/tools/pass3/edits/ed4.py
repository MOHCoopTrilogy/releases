"""ed4.py - third pass, paradrop.scr: LANDING POINTS chosen and path-tested before the jump, the descent steered onto
them, and the stuck / off-map teleport cut down to a vetted last resort that the squad brain has to ask for."""
import io, re
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/paradrop.scr")
sub, func = E.sub, E.func


sub("""	local.sid_pending = local.sid
	local.bailK = 0
""", """	local.sid_pending = local.sid
	local.bailK = 0
	//[user 2026-10-12] "they teleport if they get stuck or fall off map... Which tends to happen if they land in a bad
	//spot": every man's landing point is chosen and tested NOW, while the aircraft are on their way in (coop_para_lz).
	thread coop_para_lz local.smoke_pos local.base_z local.sid
""")
sub("""					if( local.lostPlane == 2 ){
						thread coop_paradrop_actor local.bail 3 local.base_z local.sid_pending local.bvel local.run["s"]
						local.bailK = 3
					}""", """					if( local.lostPlane == 2 ){
						local.lz = waitthread coop_para_lzOf local.sid_pending 3
						thread coop_paradrop_actor local.bail 3 local.base_z local.sid_pending local.bvel local.run["s"] local.lz
						local.bailK = 3
					}""")
sub("""			thread coop_paradrop_actor local.drop_pos local.i local.base_z local.sid local.vel local.sc
""", """			local.lz = waitthread coop_para_lzOf local.sid local.i
			thread coop_paradrop_actor local.drop_pos local.i local.base_z local.sid local.vel local.sc local.lz
""")
sub("""coop_paradrop_actor local.drop_pos local.wtype local.base_z local.sid local.vel local.s:{""",
    """coop_paradrop_actor local.drop_pos local.wtype local.base_z local.sid local.vel local.s local.lz:{""")
sub("""	if( level.coop_c47Chute == NIL ){ level.coop_c47Chute = 280 }
	// the floor under the man, traced as he drifts (not the smoke's height: he can come down on a roof or a slope)
	local.floor = local.base_z
""", """	if( level.coop_c47Chute == NIL ){ level.coop_c47Chute = 280 }
	// the floor under the man, traced as he drifts (not the smoke's height: he can come down on a roof or a slope)
	local.floor = local.base_z
	local.hov = 0
	if( local.lz != NIL ){ waitthread coop_mod/parasquad.scr::dbg ( "lz steer k=" + local.wtype + " to=" + local.lz + " door=" + local.drop_pos ) }
""")
sub("""		local.h = vector_scale local.h ( 1 - 1.2 * local.dt )
		if( local.age < 1.0 ){""", """		if( local.age >= 1.0 && local.lz != NIL ){
			// under canopy he STEERS for his landing point: over it by the time he is 450u above it (clear of the
			// roofs), then straight down the open column that was traced for it
			local.tl = ( local.pos[2] - ( local.lz[2] + 450 ) ) / ( level.coop_c47Chute * local.sc )
			if( local.tl < 0.5 ){ local.tl = 0.5 }
			local.w = local.lz - local.pos
			local.w[2] = 0
			local.wv = vector_scale local.w ( 1.0 / local.tl )
			local.sk = 2.5 * local.dt
			if( local.sk > 1 ){ local.sk = 1 }
			local.h = local.h + ( vector_scale ( local.wv - local.h ) local.sk )
		} else {
			local.h = vector_scale local.h ( 1 - 1.2 * local.dt )
		}
		if( local.age < 1.0 ){""")
sub("""		if( local.pos[2] < local.floor + 4 ){ local.pos[2] = local.floor + 4 }
		local.actor.origin = local.pos""", """		if( local.lz != NIL ){
			local.w = local.lz - local.pos
			local.w[2] = 0
			if( vector_length local.w <= 40 ){
				local.floor = local.lz[2]		// over his point: that ground, which was looked at
			} else if( local.pos[2] < local.floor + 90 ){
				// nearly down and not over it yet (a roof under him on the way): he holds his height and glides
				// on - for 5s at most, then he lands where he is, as before
				local.pos[2] = local.floor + 90
				local.vz = 0
				local.hov = local.hov + local.dt
				if( local.hov > 5 ){ local.lz = NIL }
			}
		}
		if( local.pos[2] < local.floor + 4 ){ local.pos[2] = local.floor + 4 }
		local.actor.origin = local.pos""")
sub("""	thread coop_paradrop_landing_check local.actor	// relocate near a player if it landed off-map / inaccessible
""", """	local.ld = "none"
	if( local.lz != NIL ){ local.ld = vector_length( local.actor.origin - local.lz ) }
	waitthread coop_mod/parasquad.scr::dbg ( "land k=" + local.wtype + " at=" + local.actor.origin + " lzoff=" + local.ld )
	thread coop_paradrop_landing_check local.actor local.wtype	// the last resort: out of the world, or the brain could not get him out
""")
func("coop_paradrop_landing_check", r'''
coop_paradrop_landing_check local.actor local.wtype:{
	//[user 2026-10-12] "how can we refine that without them teleporting at all or as much". Until now this moved any
	//trooper who was 700u from the players, not fighting and not closing for 8s - a man holding his post was enough -
	//and it put him on ground nobody had looked at (2026-10-12, m3l2: two men teleported onto a spot with no pathnode,
	//where they stood for the rest of the fight). Now: landing points are tested before the jump (coop_para_lz), a man
	//who cannot path walks out in a straight line (parasquad.scr::walkOut), and this is the LAST RESORT, for three
	//cases only - he fell out of the world; the squad brain gave up on him (coop_psqLost: two orders and two straight
	//walks went nowhere); or, for the medic (who has no brain orders), far + idle + not closing + no path, twice.
	if( local.actor == NULL ){ end }
	wait 4
	local.last_nd = 999999
	local.stuck = 0
	while( local.actor != NULL && isAlive local.actor ){
		local.np = NIL
		local.nd = 999999
		local.pi = 1
		while( local.pi <= $player.size ){
			local.pp = $player[local.pi]
			if( local.pp != NULL && local.pp.health > 0 ){
				local.d = vector_length( local.actor.origin - local.pp.origin )
				if( local.d < local.nd ){ local.nd = local.d; local.np = local.pp }
			}
			local.pi++
		}
		if( local.np == NIL ){ wait 4; continue }
		//[user 2026-10-04] never yank a trooper the squad brain is driving (a mounted .30 cal gunner has physics_off)
		if( local.actor.coop_psqMounted == 1 || local.actor.coop_psqBusy == 1 ){ local.stuck = 0; wait 4; continue }
		local.why = ""
		if( local.actor.origin[2] < ( local.np.origin[2] - 1200 ) ){ local.why = "fell" }
		if( local.why == "" && local.actor.coop_psqLost == 1 ){ local.why = "lost" }
		if( local.why == "" && local.wtype == 5 ){
			if( local.nd > 700 && local.actor.thinkstate != "attack" && local.nd >= ( local.last_nd - 64 ) && local.actor.pathdist == 0 ){
				local.stuck = local.stuck + 1
			} else {
				local.stuck = 0
			}
			if( local.stuck >= 2 ){ local.why = "medic_stuck" }
		}
		local.last_nd = local.nd
		if( local.why != "" ){
			waitthread coop_paradrop_rescue local.actor local.np local.wtype local.why
			local.stuck = 0
			local.last_nd = 999999
		}
		wait 4
	}
}end


// The last resort: the man is put near the player - on ground that is looked at first (level with the player,
// room for his hull) and from which HE finds a path to the player (runto + his pathdist: a real path test).
// Counted in level.coop_paraRescues; one debug line each.
coop_paradrop_rescue local.actor local.np local.wtype local.why:{
	local.from = local.actor.origin
	local.done = 0
	local.a0 = randomint 360
	for( local.i = 0; local.i < 10; local.i++ ){
		local.dir = angles_toforward ( 0 ( local.a0 + ( local.i * 36 ) ) 0 )
		local.r = 200 + ( ( local.i - ( int( local.i / 3 ) * 3 ) ) * 70 )
		local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.np.origin + ( vector_scale local.dir local.r ) + ( 0 0 48 ) )
		if( local.g == NIL ){ continue }
		local.dz = local.g[2] - local.np.origin[2]
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz > 90 ){ continue }
		local.q = local.g + ( 0 0 2 )
		local.tr = traced local.q ( local.q + ( 0 0 1 ) ) 1023 ( -16 -16 0 ) ( 16 16 92 ) 466945
		if( local.tr["startSolid"] == 1 || local.tr["allSolid"] == 1 || local.tr["fraction"] < 1.0 ){ continue }
		local.actor.origin = local.g
		local.actor runto local.np.origin
		wait 0.3
		if( local.actor == NULL ){ end }
		if( !isAlive local.actor ){ end }
		if( local.actor.pathdist > 0 ){ local.done = 1; break }
	}
	if( local.done != 1 ){
		// nothing passed: beside the player, as it always was
		local.actor.origin = local.np.origin + ( vector_scale ( angles_toforward ( 0 local.a0 0 ) ) 120 )
		local.actor droptofloor
	}
	local.actor forceactivate
	local.actor.coop_psqLost = 0
	local.actor.coop_psqWoFail = 0
	local.actor.coop_psqNoPath = 0
	local.actor.coop_psqNoGo = 0
	if( local.wtype != 5 ){ waitthread coop_mod/parasquad.scr::post local.actor local.actor.origin 240 }
	if( level.coop_paraRescues == NIL ){ level.coop_paraRescues = 0 }
	level.coop_paraRescues++
	waitthread coop_mod/parasquad.scr::dbg ( "rescue k=" + local.wtype + " why=" + local.why + " from=" + local.from + " to=" + local.actor.origin + " vetted=" + local.done + " n=" + level.coop_paraRescues )
}end
''')
sub("""// Sync visual model to 70 units below chute during descent
""", """//=========================================================================
// LANDING POINTS (user 2026-10-12: "they teleport if they get stuck or fall off map.... Which tends to happen if they
// land in a bad spot, how can we refine that without them teleporting at all or as much").
// The stick used to come down wherever the aircraft's speed left each man: on roofs (m5l1a), in a sunken lane with
// no pathnodes (m3l2), thousands of units off (m4l3) - and the failsafe then teleported him. Now five points are
// chosen while the C-47s are still inbound, nearest the smoke first, each one:
//   - the FIRST thing under the open sky in its column (a man can only come down where the sky is open), traced
//     from the map's lowest sky; a column that starts in solid is outside the map;
//   - the ground the squad will fight on: within 96u up / 200u down of the smoke's ground - not a roof, not a pit;
//   - level (four points round it within 20u), with room for his hull, and dry;
//   - 110u from the other points;
//   - INSIDE THE PATH NETWORK AND CONNECTED: a scout - an actor nobody sees, not solid, ignored by the enemy,
//     physics off - is stood on the point and ordered to the smoke's ground (and, if that fails, to the caller);
//     his pathdist after 0.3s is the engine's own answer (PathSearch only starts and ends in a 256u map cell
//     that holds a pathnode: a point in a cell with none has no path, for ever).
// coop_paradrop_actor steers each man's canopy onto his point. No point (none passed, or the search ran out of time)
// = he comes down as he always did.
//=========================================================================
coop_para_lz local.smoke local.base_z local.sid:{
	level.coop_paraLzN[local.sid] = 0
	local.t0 = level.time
	local.ref = local.smoke
	local.ref[2] = local.base_z
	local.rg = waitthread coop_mod/officer.scr::coop_find_ground ( local.ref + ( 0 0 48 ) )
	if( local.rg != NIL ){ local.ref = local.rg }
	local.topz = local.ref[2] + 2400
	if( level.ac_env != NIL ){
		if( level.ac_env["sky"] != NIL ){ local.topz = level.ac_env["sky"] - 24 }
	}
	local.ref2 = NIL
	local.cp = level.coop_smoke_player
	if( local.cp != NIL && local.cp != NULL ){ local.ref2 = local.cp.origin }
	local.sc = spawn "models/human/allied_airborne_soldier.tik"
	if( local.sc == NIL || local.sc == NULL ){ end }
	local.sc hide
	local.sc notsolid
	local.sc nodamage
	local.sc.enableEnemy = 0
	local.sc threatbias ignoreme
	local.sc.team = "american"
	local.sc.flags["coop_sceneActor"] = 1
	local.sc.flags["coop_personality_set"] = 1
	local.sc physics_off
	local.sc.origin = local.ref
	local.sc forceactivate
	local.n = 0
	local.tests = 0
	local.geo = 0
	// which man gets which point: the gunner and the BAR man nearest the smoke
	local.who[1] = 3
	local.who[2] = 1
	local.who[3] = 2
	local.who[4] = 4
	local.who[5] = 5
	for( local.r = 120; local.r <= 840; local.r = local.r + 120 ){
		for( local.j = 0; local.j < 10; local.j++ ){
			if( local.n >= 5 || local.tests >= 22 ){ break }
			local.c = local.smoke + ( vector_scale ( angles_toforward ( 0 ( ( local.j * 36 ) + ( local.r * 0.17 ) ) 0 ) ) local.r )
			local.g = waitthread coop_para_lzGround local.c local.topz local.ref
			if( local.g == NIL ){ continue }
			local.far = 1
			for( local.k = 1; local.k <= local.n; local.k++ ){
				if( vector_length( local.g - local.pt[local.k] ) < 110 ){ local.far = 0; break }
			}
			if( local.far != 1 ){ continue }
			local.geo++
			local.tests++
			local.sc.origin = local.g
			local.sc runto local.ref
			wait 0.3
			if( local.sc == NULL ){ end }
			local.pd = local.sc.pathdist
			local.fd = vector_length( local.g - local.ref )
			local.ok = 0
			if( local.pd > 0 && local.pd < ( ( local.fd * 3 ) + 600 ) ){ local.ok = 1 }
			if( local.ok != 1 && local.ref2 != NIL ){
				local.sc runto local.ref2
				wait 0.3
				if( local.sc == NULL ){ end }
				local.pd = local.sc.pathdist
				local.fd = vector_length( local.g - local.ref2 )
				if( local.pd > 0 && local.pd < ( ( local.fd * 3 ) + 600 ) ){ local.ok = 1 }
			}
			if( local.ok != 1 ){ continue }
			local.n++
			local.pt[local.n] = local.g
			local.wk = local.who[local.n]
			level.coop_paraLz[local.sid][local.wk] = local.g
			level.coop_paraLzN[local.sid] = local.n
		}
		if( local.n >= 5 || local.tests >= 22 ){ break }
		waitframe
	}
	if( local.sc != NULL ){ local.sc remove }
	waitthread coop_mod/parasquad.scr::dbg ( "lz plan n=" + local.n + " tests=" + local.tests + " secs=" + ( level.time - local.t0 ) + " ref=" + local.ref + " top=" + local.topz )
}end


// the landing point of man local.k of squad local.sid, or NIL
coop_para_lzOf local.sid local.k:{
	local.r = NIL
	if( level.coop_paraLzN[local.sid] != NIL ){
		local.r = level.coop_paraLz[local.sid][local.k]
	}
}end local.r


// the ground under the open sky at local.c, if it is a place to land (see above); else NIL
coop_para_lzGround local.c local.topz local.ref:{
	local.r = NIL
	local.s = local.c
	local.s[2] = local.topz
	local.e = local.c
	local.e[2] = local.ref[2] - 400
	if( local.topz < ( local.ref[2] + 200 ) ){ end local.r }
	local.tr = traced local.s local.e 1023 ( 0 0 0 ) ( 0 0 0 ) 1
	if( local.tr["startSolid"] == 1 || local.tr["allSolid"] == 1 ){ end local.r }
	if( local.tr["fraction"] >= 1.0 ){ end local.r }
	if( local.tr["surfaceFlags"] != NIL ){
		local.fq = int( local.tr["surfaceFlags"] / 4 )
		if( local.fq - int( local.fq / 2 ) * 2 == 1 ){ end local.r }		// a sky surface is not ground
	}
	local.g = local.tr["endpos"]
	local.dz = local.g[2] - local.ref[2]
	if( local.dz > 96 || local.dz < ( 0 - 200 ) ){ end local.r }
	for( local.j = 0; local.j < 4; local.j++ ){
		local.p = local.g + ( vector_scale ( angles_toforward ( 0 ( local.j * 90 ) 0 ) ) 22 )
		local.t2 = traced ( local.p + ( 0 0 40 ) ) ( local.p - ( 0 0 40 ) ) 1023 ( 0 0 0 ) ( 0 0 0 ) 1
		if( local.t2["fraction"] >= 1.0 || local.t2["startSolid"] == 1 ){ end local.r }
		local.d2 = local.t2["endpos"][2] - local.g[2]
		if( local.d2 < 0 ){ local.d2 = 0 - local.d2 }
		if( local.d2 > 20 ){ end local.r }
	}
	local.q = local.g + ( 0 0 2 )
	local.t2 = traced local.q ( local.q + ( 0 0 1 ) ) 1023 ( -16 -16 0 ) ( 16 16 92 ) 466945
	if( local.t2["startSolid"] == 1 || local.t2["allSolid"] == 1 || local.t2["fraction"] < 1.0 ){ end local.r }
	local.t2 = traced ( local.g + ( 0 0 80 ) ) ( local.g + ( 0 0 1 ) ) 1023 ( 0 0 0 ) ( 0 0 0 ) 32
	if( local.t2["fraction"] < 1.0 || local.t2["startSolid"] == 1 ){ end local.r }	// water
	local.r = local.g
}end local.r


// Sync visual model to 70 units below chute during descent
""")
E.save()
