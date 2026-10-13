"""ed19.py - grenades for the whole squad (nadeWatch replaces mgNade: the engine's own grenade think did not move a man
on foot in the harness either), the gun level while it is set down (its butt would come down where he stands), the
walk back to a gun that lies on its butt."""
import sys
sys.path.insert(0, ".")
from edlib import Ed
e = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")

e.sub("""	waitthread dbg ( "brain start sid=" + local.sid )
	while( 1 ){""", """	waitthread dbg ( "brain start sid=" + local.sid )
	thread nadeWatch local.sid
	while( 1 ){""")
e.sub("""			waitthread dbg ( "brain end sid=" + local.sid )
			end""", """			waitthread dbg ( "brain end sid=" + local.sid )
			level.coop_psqEnd[local.sid] = 1
			end""")
e.sub("""	local.a.coop_psqBusy = 1
	local.a.coop_psqNadeT = level.time
	local.a.enableEnemy = 0""", """	local.a.coop_psqBusy = 1
	local.a.coop_psqNadeT = level.time
	level.coop_psqNadeOwn[local.a.coop_psqSid] = level.time		// nadeWatch: this one is ours
	local.a.enableEnemy = 0""")
e.sub("""	// set down, it lies back on its butt until he is behind it
	local.rp = waitthread mgRest local.a.coop_psqMgGun local.yaw
	local.gun.coop_psqRest = local.rp
	waitthread mgRestSet local.gun local.rp""", """	// where it will lie when nobody holds it (mgRest). Level while it is set down: he stands where its butt
	// would come down
	local.rp = waitthread mgRest local.a.coop_psqMgGun local.yaw
	local.gun.coop_psqRest = local.rp
	waitthread mgRestSet local.gun 0""")
e.sub("""	thread mgHold local.a local.gun local.sid
	thread mgNade local.a local.gun local.sid
""", """	thread mgHold local.a local.gun local.sid
""")

e.func("mgNade", r'''
nadeWatch local.sid:{
	local.i = 0
	while( level.coop_psqEnd[local.sid] != 1 ){
		for( local.n = 0; local.n < 64; local.n++ ){
			local.i++
			if( local.i >= 1024 ){ local.i = 1 }
			local.e = getentbyentnum local.i
			if( local.e == NULL ){ continue }
			if( local.e.classname != "Projectile" ){ continue }
			if( ( vector_length local.e.velocity ) > 200 ){ continue }
			// one of ours, thrown in the last 6s: only a man it has come back to within 150u moves
			local.own = 0
			if( level.coop_psqNadeOwn[local.sid] != NIL ){
				if( ( level.time - level.coop_psqNadeOwn[local.sid] ) < 6 ){ local.own = 1 }
			}
			for( local.k = 1; local.k <= 5; local.k++ ){
				local.m = level.coop_psqM[local.sid][local.k]
				if( local.m == NIL || local.m == NULL ){ continue }
				if( !isAlive local.m ){ continue }
				if( local.m.coop_psqNadeE == local.e ){ continue }
				local.d = vector_length( local.e.origin - local.m.origin )
				if( local.d > 300 ){ continue }
				if( local.own == 1 && local.d > 150 ){ continue }
				local.m.coop_psqNadeE = local.e
				if( local.m.coop_psqMounted == 1 ){
					local.g = local.m.coop_psqGun
					if( local.g != NIL && local.g != NULL ){ thread mgFlee local.m local.g local.sid local.e }
				} else {
					thread nadeRun local.m local.e
				}
			}
		}
		waitframe
	}
}end


// a place 300u from where he is, away from a grenade at local.np: straight away from it, else round in 45 degree
// steps, over ground that was looked at (mgLine: his hull, and ground every 32u). NIL = none.
nadeAway local.from local.np:{
	local.v = local.from - local.np
	local.v[2] = 0
	if( vector_length local.v < 8 ){ local.v = ( 1 0 0 ) }
	local.va = vector_toangles local.v
	local.to = NIL
	for( local.i = 0; local.i < 5; local.i++ ){
		local.h = int( ( local.i + 1 ) / 2 ) * 45
		if( ( local.i - ( int( local.i / 2 ) * 2 ) ) == 0 ){ local.h = 0 - local.h }
		local.c = local.from + ( vector_scale ( angles_toforward ( 0 ( local.va[1] + local.h ) 0 ) ) 300 )
		local.cz = waitthread mgSurf local.c 40 60
		if( local.cz == NIL ){ continue }
		local.c[2] = local.cz
		if( !( waitthread mgLine local.from local.c ) ){ continue }
		local.to = local.c
		break
	}
}end local.to


// a man on foot: he runs
nadeRun local.a local.nade:{
	if( !( waitthread usable local.a ) ){ end }
	local.np = local.nade.origin
	local.to = waitthread nadeAway local.a.origin local.np
	if( local.a == NULL ){ end }
	if( local.to == NIL ){
		waitthread dbg ( "nade run k=" + local.a.coop_psqK + " nowhere_to_go" )
		end
	}
	waitthread dbg ( "nade run k=" + local.a.coop_psqK + " d=" + ( vector_length( local.np - local.a.origin ) ) )
	waitthread moveTo local.a local.to 3.5 0 "nade"
}end
''')

e.func("mgFlee", r'''
mgFlee local.a local.gun local.sid local.nade:{
	local.np = local.nade.origin
	local.seat = local.a.origin
	local.a.coop_psqBusy = 1
	waitthread dbg ( "mg nade at=" + local.np + " d=" + ( vector_length( local.np - local.seat ) ) )
	waitthread mgOff local.a
	local.a.enableEnemy = 0
	local.to = waitthread nadeAway local.seat local.np
	wait 0.25		// hands off the gun
	if( local.a == NULL ){ end }
	if( !isAlive local.a ){ end }
	local.a unholster
	if( local.to != NIL ){
		local.left = waitthread mgLeg local.a local.to 1 24 3.5
	} else {
		waitthread dbg "mg nade nowhere_to_go"
	}
	// until it has gone off
	local.t = 0
	while( local.nade != NULL && local.t < 6 ){
		wait 0.25
		local.t = local.t + 0.25
	}
	wait 0.8
	if( local.a == NULL ){ end }
	if( !isAlive local.a ){ end }
	// back to the gun, if it is still his to take
	local.ok = 0
	if( local.gun != NULL ){
		local.free = 1
		for( local.i = 1; local.i <= $player.size; local.i++ ){
			local.p = $player[local.i]
			if( local.p == NULL ){ continue }
			if( local.p.turret == local.gun ){ local.free = 0 }
		}
		if( local.free == 1 ){
			local.a.enableEnemy = 0
			local.left = 99999
			for( local.n = 0; local.n < 2; local.n++ ){
				local.straight = 0
				local.rad = 28
				if( waitthread mgLine local.a.origin local.seat ){
					local.straight = 1
					local.rad = 28
				}
				local.left = waitthread mgLeg local.a local.seat local.straight local.rad 8
				if( local.a == NULL ){ end }
				if( !isAlive local.a ){ end }
				waitthread dbg ( "mg nade walkback straight=" + local.straight + " left=" + local.left )
				if( local.left < 110 ){ break }
			}
			if( local.left < 110 && local.gun != NULL ){
				// the gun lies on its butt where he has to kneel: it comes level, then the last steps
				waitthread mgRestSet local.gun 0
				wait 0.7
				if( local.a == NULL ){ end }
				if( !isAlive local.a ){ end }
				if( local.left > 14 ){
					if( waitthread mgLine local.a.origin local.seat ){ local.left = waitthread mgLeg local.a local.seat 1 10 4 }
				}
				if( local.a == NULL ){ end }
				if( !isAlive local.a ){ end }
				if( local.left < 30 && local.gun != NULL ){
					local.ok = waitthread mgMount local.a local.gun local.sid
					if( local.a == NULL ){ end }
					if( !isAlive local.a ){ end }
					if( local.ok != 1 ){ waitthread mgOff local.a }
				}
			}
		}
	}
	waitthread dbg ( "mg nade back=" + local.ok )
	if( local.ok != 1 ){
		if( local.gun != NULL ){
			local.rp = local.gun.coop_psqRest
			waitthread mgRestSet local.gun local.rp
		}
		waitthread mgGiveUp local.a local.gun
	}
}end
''')
e.save()
s = open(e.path, encoding="latin-1").read()
assert "mgNade" not in s.replace("mgNade / mgFlee", ""), [l for l in s.splitlines() if "mgNade" in l]
