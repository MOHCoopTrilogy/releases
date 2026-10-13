"""ed5.py - (a) paradrop.scr: the landing-point ground test looks UP for the sky from the ground instead of down from a
guessed height (the first version started above the sky brush and refused every point: 'lz plan n=0 tests=0');
(b) parasquad.scr: the medic's leash is tethered behind the players again (runto is not leash-bound: Think_Runner
uses a plain SetPath); the planner falls back to a field of fire down the line toward the enemy when no site can see
the enemy himself."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/paradrop.scr")
E.func("coop_para_lzGround", r'''
coop_para_lzGround local.c local.topz local.ref:{
	local.r = NIL
	// the ground at the squad's level under local.c (looked for from 100u over the smoke's ground: a point inside a
	// wall or a hill starts in solid and is refused; a roof is above that and is never found)
	local.s = local.c
	local.s[2] = local.ref[2] + 100
	local.e = local.c
	local.e[2] = local.ref[2] - 200
	local.tr = traced local.s local.e 1023 ( 0 0 0 ) ( 0 0 0 ) 1
	if( local.tr["startSolid"] == 1 || local.tr["allSolid"] == 1 ){ end local.r }
	if( local.tr["fraction"] >= 1.0 ){ end local.r }
	local.g = local.tr["endpos"]
	// OPEN SKY over it and 44u round it (his canopy): nothing for 4000u, or the first thing up there is sky
	for( local.j = 0; local.j < 5; local.j++ ){
		local.p = local.g + ( 0 0 60 )
		if( local.j > 0 ){ local.p = local.p + ( vector_scale ( angles_toforward ( 0 ( local.j * 90 ) 0 ) ) 44 ) }
		local.t2 = traced local.p ( local.p + ( 0 0 4000 ) ) 1023 ( 0 0 0 ) ( 0 0 0 ) 1
		if( local.t2["startSolid"] == 1 ){ end local.r }
		if( local.t2["fraction"] < 1.0 ){
			if( local.t2["surfaceFlags"] == NIL ){ end local.r }
			local.fq = int( local.t2["surfaceFlags"] / 4 )
			if( local.fq - int( local.fq / 2 ) * 2 != 1 ){ end local.r }		// a roof, a ceiling, a tree: not sky
		}
	}
	// level: four points 22u round it within 20u
	for( local.j = 0; local.j < 4; local.j++ ){
		local.p = local.g + ( vector_scale ( angles_toforward ( 0 ( local.j * 90 ) 0 ) ) 22 )
		local.t2 = traced ( local.p + ( 0 0 40 ) ) ( local.p - ( 0 0 40 ) ) 1023 ( 0 0 0 ) ( 0 0 0 ) 1
		if( local.t2["fraction"] >= 1.0 || local.t2["startSolid"] == 1 ){ end local.r }
		local.d2 = local.t2["endpos"][2] - local.g[2]
		if( local.d2 < 0 ){ local.d2 = 0 - local.d2 }
		if( local.d2 > 20 ){ end local.r }
	}
	// room for his hull (solid, fence, every clip), and dry
	local.q = local.g + ( 0 0 2 )
	local.t2 = traced local.q ( local.q + ( 0 0 1 ) ) 1023 ( -16 -16 0 ) ( 16 16 92 ) 466945
	if( local.t2["startSolid"] == 1 || local.t2["allSolid"] == 1 || local.t2["fraction"] < 1.0 ){ end local.r }
	local.t2 = traced ( local.g + ( 0 0 80 ) ) ( local.g + ( 0 0 1 ) ) 1023 ( 0 0 0 ) ( 0 0 0 ) 32
	if( local.t2["fraction"] < 1.0 || local.t2["startSolid"] == 1 ){ end local.r }
	local.r = local.g
}end local.r
''')
E.sub("""//   - the FIRST thing under the open sky in its column (a man can only come down where the sky is open), traced
//     from the map's lowest sky; a column that starts in solid is outside the map;
//   - the ground the squad will fight on: within 96u up / 200u down of the smoke's ground - not a roof, not a pit;
""", """//   - ground at the squad's level: looked for from 100u over the smoke's ground down to 200u under it - a roof
//     is above that and is never found, a point inside a wall or a hill starts in solid;
//   - OPEN SKY over it and 44u round it (a man can only come down where the sky is open): nothing for 4000u up,
//     or the first thing up there is a sky surface - not a roof, a ceiling, a tree;
""")
E.sub("""	waitthread coop_mod/parasquad.scr::dbg ( "lz plan n=" + local.n + " tests=" + local.tests + " secs=" + ( level.time - local.t0 ) + " ref=" + local.ref + " top=" + local.topz )""",
      """	waitthread coop_mod/parasquad.scr::dbg ( "lz plan n=" + local.n + " tests=" + local.tests + " secs=" + ( level.time - local.t0 ) + " ref=" + local.ref )""")
E.save()

E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""	// (the medic keeps the engine's own leash: his loop in paradrop.scr runs him to a patient up to 2000u away)
	if( local.k != 5 ){ waitthread post self self.origin 240 }
""", """	waitthread post self self.origin 240
""")
E.sub("""		// ---- out of the players' line of fire: in a fight, or while the player is firing ----
""", """		// ---- the medic's leash is tethered behind the players: he fights from there and does not run at the enemy.
		// (His own loop in paradrop.scr still runs him to a patient - a move order is not leash-bound.)
		local.a = level.coop_psqM[local.sid][5]
		if( local.a != NIL && local.a != NULL ){
			if( isAlive local.a ){
				local.mp = local.apos - ( vector_scale local.cfw 220 )
				waitthread post local.a local.mp 400
			}
		}

		// ---- out of the players' line of fire: in a fight, or while the player is firing ----
""")
# the planner: no site sees the enemy himself -> a field of fire down the line toward him
E.sub("""	// best first, and the first he can reach
	local.found = 0""", """	if( level.coop_psqCn == 0 && local.kind != "advance" ){
		// no place round him from which the gun sees the enemy himself: a place that covers the ground TOWARD him
		// (800u clear down that line) is the next best thing - the gun is up when he shows
		local.v = local.aim - local.apos
		local.v[2] = 0
		if( vector_length local.v > 200 ){
			local.kind = "advance"
			local.aim = local.apos + ( vector_scale ( vector_normalize local.v ) 1200 )
			local.aim[2] = local.apos[2]
			local.n = 0
			for( local.r = 0; local.r <= 432; local.r = local.r + 72 ){
				for( local.j = 0; local.j < 12; local.j++ ){
					if( local.r == 0 && local.j > 0 ){ break }
					local.c = local.ctr + ( vector_scale ( angles_toforward ( 0 ( ( local.j * 30 ) + ( local.r * 0.2 ) ) 0 ) ) local.r )
					local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.c + ( 0 0 48 ) )
					if( local.g == NIL ){ continue }
					local.dz = local.g[2] - local.ctr[2]
					if( local.dz < 0 ){ local.dz = 0 - local.dz }
					if( local.dz > 120 ){ continue }
					if( ( waitthread flatDist local.g local.apos ) > 520 ){ continue }
					local.b = local.bags
					if( local.r > 300 ){ local.b = 0 }
					waitthread mgTry local.a local.sid local.g local.aim local.kind local.b local.tripod
					local.n++
					if( local.n >= 4 ){
						local.n = 0
						waitframe
						if( local.a == NULL ){ level.coop_psqPlanBusy = 0; end 0 }
						if( !isAlive local.a ){ level.coop_psqPlanBusy = 0; end 0 }
					}
				}
			}
		}
	}
	// best first, and the first he can reach
	local.found = 0""")
E.save()
