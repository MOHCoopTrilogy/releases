"""ed16.py - parasquad.scr: (a) the walk to the gun site stalled falsely: 'no progress' was measured as the straight
distance to the seat not shrinking, and a path that leads round a building first grows it - he stopped after 2s and
the same site was planned again every 13s (m3l3, six times). Stall = he is not MOVING. The leg's time limit follows
the length of the path. (b) a site he did not reach is not planned again for 60s."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""	local.d0 = waitthread flatDist local.a.origin local.pos
	local.t = 0
	local.stall = 0
	while( local.t < local.tmo ){
		wait 0.25
		local.t = local.t + 0.25
		if( local.a == NULL ){ break }
		if( !isAlive local.a ){ break }
		local.d = waitthread flatDist local.a.origin local.pos
		if( local.d < ( local.rad + 6 ) ){ break }
		if( local.d < ( local.d0 - 4 ) ){ local.stall = 0 } else { local.stall = local.stall + 0.25 }
		local.d0 = local.d
		if( local.stall >= 2.0 ){ break }
	}""", """	local.o0 = local.a.origin
	local.t = 0
	local.stall = 0
	while( local.t < local.tmo ){
		wait 0.25
		local.t = local.t + 0.25
		if( local.a == NULL ){ break }
		if( !isAlive local.a ){ break }
		local.d = waitthread flatDist local.a.origin local.pos
		if( local.d < ( local.rad + 6 ) ){ break }
		// stalled = he is not moving (NOT 'the straight distance is not shrinking': a path round a building grows it)
		if( vector_length( local.a.origin - local.o0 ) > 5 ){ local.stall = 0 } else { local.stall = local.stall + 0.25 }
		local.o0 = local.a.origin
		if( local.stall >= 2.0 ){ break }
	}""")
E.sub("""	} else {
		local.left = waitthread mgLeg local.a local.pos 0 28 12
	}""", """	} else {
		// by the path graph: 12s, or what the path's length needs at a run (pathdist is what mgReach read)
		local.tmo = 12
		if( level.coop_psqPd != NIL ){
			if( ( level.coop_psqPd / 140 ) + 4 > local.tmo ){ local.tmo = ( level.coop_psqPd / 140 ) + 4 }
		}
		if( local.tmo > 30 ){ local.tmo = 30 }
		local.left = waitthread mgLeg local.a local.pos 0 28 local.tmo
	}""")
E.sub("""	if( local.got != 1 ){
		local.wd = waitthread flatDist local.a.origin local.a.coop_psqMgStand
		waitthread dbg ( "mg setup abort=not_reached left=" + local.wd )
		end
	}""", """	if( local.got != 1 ){
		local.wd = waitthread flatDist local.a.origin local.a.coop_psqMgStand
		// not planned again for a minute (mgPlan)
		local.a.coop_psqMgBadSeat = local.a.coop_psqMgStand
		local.a.coop_psqMgBadSeatT = level.time + 60
		waitthread dbg ( "mg setup abort=not_reached left=" + local.wd )
		end
	}""")
E.sub("""		level.coop_psqCd[local.bi] = 1
		local.tried++""", """		level.coop_psqCd[local.bi] = 1
		// the seat he set out for and did not reach in the last minute: not again
		if( local.a.coop_psqMgBadSeatT != NIL ){
			if( level.time < local.a.coop_psqMgBadSeatT ){
				if( vector_length( level.coop_psqCt[local.bi] - local.a.coop_psqMgBadSeat ) < 48 ){ continue }
			}
		}
		local.tried++""")
E.save()
