"""ed7.py - parasquad.scr: (a) a squad mate standing in front of the .30 cal's muzzle steps out of its lane (the gun
was holding its fire for him again and again); (b) LOST is only a man who is himself off the path network - a
destination with no pathnode near it is not his fault (onNet)."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""		// ---- officer-wave targets (they hunt players only and never notice AI on their own) ----
""", """		// ---- and out of the .30 cal's: a man in front of its muzzle silences it (mgHold holds the fire for him) ----
		local.gn = level.coop_psqM[local.sid][3]
		if( local.gn != NIL && local.gn != NULL ){
			if( isAlive local.gn && local.gn.coop_psqMounted == 1 && local.gn.coop_psqMgGun != NIL ){
				local.gd = angles_toforward ( 0 local.gn.coop_psqMgYaw 0 )
				for( local.k = 1; local.k <= 4; local.k++ ){
					local.a = level.coop_psqM[local.sid][local.k]
					if( local.k == 3 ){ continue }
					if( !( waitthread usable local.a ) ){ continue }
					if( level.time < local.a.coop_psqSideT ){ continue }
					local.v = local.a.origin - local.gn.coop_psqMgGun
					local.v[2] = 0
					local.al = vector_dot local.v local.gd
					if( local.al <= 0 || local.al > 900 ){ continue }
					local.sd = local.v - ( vector_scale local.gd local.al )
					local.lat = vector_length local.sd
					// (the gun's whole traverse at his range, and a man's width)
					local.need = 80 + ( local.al * 0.25 )
					if( local.need > 260 ){ local.need = 260 }
					if( local.lat >= local.need ){ continue }
					if( local.lat < 2 ){ local.sd = angles_toforward ( 0 ( local.gn.coop_psqMgYaw - 90 ) 0 ) }
					local.sd = vector_normalize local.sd
					local.step = ( local.need - local.lat ) + 40
					if( local.step > 220 ){ local.step = 220 }
					local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.a.origin + ( vector_scale local.sd local.step ) + ( 0 0 40 ) )
					if( local.g == NIL ){ continue }
					local.a.coop_psqSideT = level.time + 4
					waitthread dbg ( "tac gunlane k=" + local.k + " lat=" + local.lat + " to=" + local.g )
					thread moveTo local.a local.g 2.0 0 "gunlane"
				}
			}
		}

		// ---- officer-wave targets (they hunt players only and never notice AI on their own) ----
""")
E.sub("""	if( local.goal == NIL || local.left > 200 ){
		local.a.coop_psqWoFail++
		if( local.a.coop_psqWoFail >= 2 ){ local.a.coop_psqLost = 1 }
	} else {""", """	if( local.goal == NIL || local.left > 200 ){
		local.a.coop_psqWoFail++
		if( local.a.coop_psqWoFail >= 2 ){
			// ...unless it is the PLACE he was sent to that is off the network, not he
			local.a.coop_psqBusy = 1
			local.net = waitthread onNet local.a
			if( local.a == NULL ){ end }
			local.a.coop_psqBusy = 0
			if( local.net == 1 ){ local.a.coop_psqWoFail = 0 } else { local.a.coop_psqLost = 1 }
		}
	} else {""")
E.sub("""// (see the brain, FOLLOW) a straight walk toward local.to for a man the path graph cannot move:""", """// Is HE on the path network? 1 when the engine finds him a path to anywhere that is known to be on it: the point he
// landed on (tested before the jump, paradrop.scr::coop_para_lz), a squad mate, the anchor. (A path search starts
// in his own 256u map cell: with no pathnode there he has no path to anywhere - that is the man to rescue. A
// destination in such a cell fails the same way and says nothing about him.)
onNet local.a:{
	local.sid = local.a.coop_psqSid
	local.n = 0
	local.t[1] = NIL
	if( level.coop_paraLzN[local.sid] != NIL ){
		local.lz = level.coop_paraLz[local.sid][local.a.coop_psqK]
		if( local.lz != NIL ){ local.n++; local.t[local.n] = local.lz }
	}
	for( local.k = 1; local.k <= 5; local.k++ ){
		local.m = level.coop_psqM[local.sid][local.k]
		if( local.m == NIL || local.m == NULL || local.m == local.a ){ continue }
		if( !isAlive local.m ){ continue }
		if( local.n < 3 ){ local.n++; local.t[local.n] = local.m.origin }
	}
	if( level.coop_psqApos[local.sid] != NIL ){ local.n++; local.t[local.n] = level.coop_psqApos[local.sid] }
	local.r = 0
	for( local.i = 1; local.i <= local.n; local.i++ ){
		if( vector_length( local.t[local.i] - local.a.origin ) < 150 ){ continue }
		local.a runto local.t[local.i]
		wait 0.3
		if( local.a == NULL ){ end 0 }
		if( !isAlive local.a ){ end 0 }
		if( local.a.pathdist > 0 ){ local.r = 1; break }
	}
	local.a runto local.a.origin
}end local.r


// (see the brain, FOLLOW) a straight walk toward local.to for a man the path graph cannot move:""")
E.save()
