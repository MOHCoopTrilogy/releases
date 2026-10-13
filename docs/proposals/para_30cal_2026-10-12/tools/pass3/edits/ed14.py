"""ed14.py - parasquad.scr walkOut: with no walkable line toward where he was sent, he walks back ONTO the network -
to the point he landed on (path-tested before the jump), else to a squad mate - before anybody calls him lost
(m5l1a: a man 60u from his landing point, one map cell over, in a cell with no pathnode, was teleported)."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""	local.left = 0 - 1
	if( local.goal != NIL ){ local.left = waitthread mgLeg local.a local.goal 1 40 8 }""", """	if( local.goal == NIL ){
		// no line toward where he was sent: back onto the path network on foot - the point he landed on (tested
		// before the jump), else the nearest squad mate he can walk straight to
		local.sid = local.a.coop_psqSid
		if( level.coop_paraLzN[local.sid] != NIL ){
			local.lz = level.coop_paraLz[local.sid][local.a.coop_psqK]
			if( local.lz != NIL ){
				local.ld = vector_length( local.lz - local.a.origin )
				if( local.ld > 40 && local.ld < 700 ){
					if( waitthread mgLine local.a.origin local.lz ){ local.goal = local.lz }
				}
			}
		}
		if( local.goal == NIL ){
			for( local.k = 1; local.k <= 5; local.k++ ){
				local.m = level.coop_psqM[local.sid][local.k]
				if( local.m == NIL || local.m == NULL || local.m == local.a ){ continue }
				if( !isAlive local.m ){ continue }
				local.md = vector_length( local.m.origin - local.a.origin )
				if( local.md < 80 || local.md > 600 ){ continue }
				if( waitthread mgLine local.a.origin local.m.origin ){ local.goal = local.m.origin; break }
			}
		}
	}
	local.left = 0 - 1
	if( local.goal != NIL ){ local.left = waitthread mgLeg local.a local.goal 1 40 8 }""")
E.save()
