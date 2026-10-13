"""ed13.py - (a) paradrop.scr: landing points out of the enemy's SIGHT first (m5l1a: all five came down on tested ground
- in a street 800u in front of the enemy, and in the 15s after landing they stood 24 man-seconds in his view and lost
a man); (b) parasquad.scr: on first contact every man in view looks for cover at once, not one man a second."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/paradrop.scr")
E.sub("""	for( local.r = 120; local.r <= 840; local.r = local.r + 120 ){
		for( local.j = 0; local.j < 10; local.j++ ){
			if( local.n >= 5 || local.tests >= 22 ){ break }
			local.c = local.smoke + ( vector_scale ( angles_toforward ( 0 ( ( local.j * 36 ) + ( local.r * 0.17 ) ) 0 ) ) local.r )
			local.g = waitthread coop_para_lzGround local.c local.topz local.ref
			if( local.g == NIL ){ continue }
""", """	// two rounds: first only points NO living German within 1600u has a line to (solid world between his eyes and a
	// man standing there) - nobody jumps into the enemy's view if there is anywhere else; then the rest
	for( local.rnd = 1; local.rnd <= 2; local.rnd++ ){
	for( local.r = 120; local.r <= 840; local.r = local.r + 120 ){
		for( local.j = 0; local.j < 10; local.j++ ){
			if( local.n >= 5 || local.tests >= 22 ){ break }
			local.c = local.smoke + ( vector_scale ( angles_toforward ( 0 ( ( local.j * 36 ) + ( local.r * 0.17 ) ) 0 ) ) local.r )
			local.g = waitthread coop_para_lzGround local.c local.topz local.ref
			if( local.g == NIL ){ continue }
			local.sn = waitthread coop_para_lzSeen local.g
			if( local.rnd == 1 && local.sn == 1 ){ continue }
			if( local.rnd == 2 && local.sn != 1 ){ continue }		// (looked at in the first round)
""")
E.sub("""		if( local.n >= 5 || local.tests >= 22 ){ break }
		waitframe
	}
	if( local.sc != NULL ){ local.sc remove }""", """		if( local.n >= 5 || local.tests >= 22 ){ break }
		waitframe
	}
	if( local.n >= 5 || local.tests >= 22 ){ break }
	}
	if( local.sc != NULL ){ local.sc remove }""")
E.sub("""// the landing point of man local.k of squad local.sid, or NIL""", """// 1 when a living German within 1600u has a clear line (solid world only) to a man standing at local.g
coop_para_lzSeen local.g:{
	local.arr = level.coop_actorArray["german"]
	if( local.arr == NIL ){ end 0 }
	local.t = local.g + ( 0 0 50 )
	local.n = 0
	for( local.i = 1; local.i <= local.arr.size; local.i++ ){
		local.e = local.arr[local.i]
		if( local.e == NIL || local.e == NULL ){ continue }
		if( !isAlive local.e ){ continue }
		if( vector_length( local.e.origin - local.g ) > 1600 ){ continue }
		local.tr = traced ( local.e.origin + ( 0 0 64 ) ) local.t 1023 ( 0 0 0 ) ( 0 0 0 ) 1
		if( local.tr["fraction"] >= 1.0 ){ end 1 }
		local.n++
		if( local.n >= 40 ){ break }
	}
}end 0


// the landing point of man local.k of squad local.sid, or NIL""")
E.sub("""//   - 110u from the other points;""", """//   - out of the enemy's sight where that can be had (first round), 110u from the other points;""")
E.save()

E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""			waitthread dbg ( "tac contact thr=" + local.thr )
		}""", """			waitthread dbg ( "tac contact thr=" + local.thr )
			// ...and for the next 4s every man in view looks for cover at once (one a second is the rule after that),
			// and nobody bounds
			if( level.time >= local.shaken ){ local.shaken = level.time + 4 }
		}""")
E.save()
