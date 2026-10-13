"""ed20.py - nobody stands on the seat of a gun that is set up and unmanned (mgSeatClear, from mgPivot): a squad mate
there made the engine refuse the player his seat and decide 'not a low gun' from the mate's head - the player stood
upright behind the sandbag gun, hands in the air (run t6)."""
import sys
sys.path.insert(0, ".")
from edlib import Ed
e = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
e.sub("""	thread mgPivot local.gun local.sup local.mode local.yaw
	local.ok = waitthread mgMount local.a local.gun local.sid""", """	local.gun.coop_psqSid = local.sid
	thread mgPivot local.gun local.sup local.mode local.yaw
	local.ok = waitthread mgMount local.a local.gun local.sid""")
e.sub("""		if( local.fz == NIL && local.cur == 0 ){ wait 0.25 } else { waitframe }
	}""", """		if( local.fz == NIL && local.cur == 0 ){
			waitthread mgSeatClear local.gun local.base local.yaw0
			wait 0.25
		} else {
			waitframe
		}
	}""")
e.sub("""// the gun stays where it is, for the players; he is a rifleman from here on
mgGiveUp local.a local.gun:{""", """// THE SEAT OF AN UNMANNED GUN IS KEPT FREE. A man standing where the gunner kneels (the medic at a dead gunner, a
// mate who took cover behind the bags) is in the way of whoever takes the gun next; for a player the engine then
// refuses the seat and reads "not a low gun" off the man's head - he stood upright behind the sandbag gun, hands in
// the air. Called four times a second by mgPivot while nobody is on the gun: a squad member within 40u of the seat
// who is nobody's at the moment steps 90u back from the gun (once in 4s a man).
mgSeatClear local.gun local.base local.yaw0:{
	local.sid = local.gun.coop_psqSid
	if( local.sid == NIL ){ end }
	local.seat = waitthread mgSeat local.base local.yaw0 ( local.base[2] - 39.3 )
	for( local.k = 1; local.k <= 5; local.k++ ){
		local.m = level.coop_psqM[local.sid][local.k]
		if( local.m == NIL || local.m == NULL ){ continue }
		if( !( waitthread usable local.m ) ){ continue }
		if( ( waitthread flatDist local.m.origin local.seat ) > 40 ){ continue }
		local.dz = local.m.origin[2] - local.seat[2]
		if( local.dz < ( 0 - 70 ) || local.dz > 70 ){ continue }
		if( local.m.coop_psqSeatT != NIL ){
			if( ( level.time - local.m.coop_psqSeatT ) < 4 ){ continue }
		}
		local.m.coop_psqSeatT = level.time
		local.v = local.m.origin - local.base
		local.v[2] = 0
		if( vector_length local.v < 4 ){ local.v = angles_toforward ( 0 ( local.yaw0 + 180 ) 0 ) }
		local.to = local.m.origin + ( vector_scale ( vector_normalize local.v ) 90 )
		local.tz = waitthread mgSurf local.to 40 60
		if( local.tz == NIL ){ continue }
		local.to[2] = local.tz
		waitthread dbg ( "mg seat clear k=" + local.k )
		thread moveTo local.m local.to 3 0 "seat"
	}
}end


// the gun stays where it is, for the players; he is a rifleman from here on
mgGiveUp local.a local.gun:{""")
e.save()
