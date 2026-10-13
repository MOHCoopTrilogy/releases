"""ed17.py - fourth pass, edit 1: the gun under pitch (mgPivot), the unmanned rest (mgRest), the mount as a routine of
its own (mgMount / mgOff), the mounted gunner and a grenade (mgNade / mgFlee), pitch up to 25 degrees."""
import sys
sys.path.insert(0, ".")
from edlib import Ed

MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/"

# ---------------------------------------------------------------- parasquad_gun.scr
g = Ed(MOD + "parasquad_gun.scr")
g.sub("""// the M1919's heat (40 a second of fire, 8 bleed, 25 cooling, 2s lock) and the rest: muzzle 3 degrees down
belt local.gun local.n:{""", """// the M1919's heat (40 a second of fire, 8 bleed, 25 cooling, 2s lock)
belt local.gun local.n:{""")
g.sub("""	local.gun coopheatrates 40 8 25 2
	local.gun cooprestpitch 3
}end 1
""", """	local.gun coopheatrates 40 8 25 2
}end 1


// with nobody on it the gun eases to this pitch (negative = muzzle up; parasquad.scr::mgRest works it out)
rest local.gun local.p:{
	local.gun cooprestpitch local.p
}end 1
""")
g.save()

# ---------------------------------------------------------------- parasquad.scr
e = Ed(MOD + "parasquad.scr")

# 1. the planner: 25 degrees up, 12 down
e.sub("""		// the gun's pitch stops at 12 degrees (pitchCaps in mgSetup)
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz > ( local.dist * 0.21 ) ){ end 0 }""", """		// the gun's pitch stops at 25 degrees up and 12 down (pitchCaps in mgSetup); planned to 22 up
		if( local.dz > ( local.dist * 0.40 ) ){ end 0 }
		if( local.dz < ( 0 - ( local.dist * 0.21 ) ) ){ end 0 }""")

e.sub("""		// (a man more than 110u under or over the muzzle is not in front of it: the gun's pitch is 12 degrees)
		local.hz = local.v[2] + 40
		if( local.hz < 0 ){ local.hz = 0 - local.hz }
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 1500 ){ continue }
		if( local.hz > 110 && local.hz > ( local.along * 0.25 ) ){ continue }""", """		// (a man more than 110u under or over the muzzle is not in front of it: the gun's pitch is 12 degrees down,
		// 25 up)
		local.hz = local.v[2] + 40
		local.hs = 0.5
		if( local.hz < 0 ){ local.hz = 0 - local.hz; local.hs = 0.25 }
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 1500 ){ continue }
		if( local.hz > 110 && local.hz > ( local.along * local.hs ) ){ continue }""")

e.sub("""		local.hz = local.v[2] + 40
		if( local.hz < 0 ){ local.hz = 0 - local.hz }
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 900 ){ continue }
		if( local.hz > 110 && local.hz > ( local.along * 0.25 ) ){ continue }""", """		local.hz = local.v[2] + 40
		local.hs = 0.5
		if( local.hz < 0 ){ local.hz = 0 - local.hz; local.hs = 0.25 }
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 900 ){ continue }
		if( local.hz > 110 && local.hz > ( local.along * local.hs ) ){ continue }""")

# 2. the gunner loop: what he has set up is read from him every pass (mgFlee can give the gun away)
e.sub("""	while( local.a != NULL ){
		if( !isAlive local.a ){ break }
		wait 1
		if( local.a == NULL ){ break }
		if( local.a.coop_psqMounted != 1 ){
			local.near = 1""", """	while( local.a != NULL ){
		// what he has set up (mgSetup writes it, mgPackup and mgGiveUp clear it)
		local.gun = local.a.coop_psqGun
		local.crate = local.a.coop_psqCrate
		local.sup = local.a.coop_psqSup
		local.bag = local.a.coop_psqBag
		if( !isAlive local.a ){ break }
		wait 1
		if( local.a == NULL ){ break }
		if( local.a.coop_psqMounted != 1 ){
			local.near = 1""")

# 3. mgSetup: caps, rest, mount
e.sub("""	// level when nobody aims it. The engine lets an unmanned gun tip back to maxIdlePitch (-80 = barrel up,
	// TurretGun::ThinkIdle); in the 0.3s of the set-down it tipped 13 degrees and, with no enemy, nothing ever
	// levelled it: the grips sank 10u under the hands of a crouched gunner. 0 = it rests level, manned or left.
	// pitch: 12 degrees either way. The engine holds his hands 39u behind the pivot at one height
	// (Actor::ThinkHoldGun_TurretGun); every degree the gun tips takes the grips 0.7u away from them.
	local.gun pitchCaps ( -12 12 0 )""", """	// pitch: 25 degrees up (upstairs windows), 12 down. His hands stay on the grips over all of it: mgPivot.
	// With nobody on it the gun lies back on its butt (mgRest); it is level before he takes it (mgMount).
	local.gun pitchCaps ( -25 12 0 )""")

e.sub("""	} else {
		// older game.dll: the gun at least rests level (the engine tips an unmanned gun barrel-up - ThinkIdle - and in
		// the 0.3s of the set-down it tipped 13 degrees and stayed there: the grips sank 10u under his hands)
		local.gun maxIdlePitch 0
	}
	local.a.coop_psqGun = local.gun""", """	}
	// set down, it lies back on its butt until he is behind it
	local.rp = waitthread mgRest local.a.coop_psqMgGun local.yaw
	local.gun.coop_psqRest = local.rp
	waitthread mgRestSet local.gun local.rp
	local.a.coop_psqGun = local.gun""")

e.sub("""	local.gun.origin = local.a.coop_psqMgGun
	// onto the seat the engine will hold him on: it sweeps his hull down from 18u over his FEET, so
	// a seat on ground a little higher than where he stopped would never take him
	local.a.origin = local.a.coop_psqMgStand
	// mount (global/mg42_active.scr gunner recipe); remember his own thinks for the pack-up
	local.a.coop_psqT1 = local.a.type_idle
	local.a.coop_psqT2 = local.a.type_attack
	local.a.coop_psqT3 = local.a.type_disguise
	local.a.coop_psqT4 = local.a.type_grenade
	local.a turret local.gun
	local.a type_idle "machinegunner"
	local.a type_attack "machinegunner"
	local.a type_disguise "machinegunner"
	local.a type_grenade "machinegunner"
	local.a physics_off
	local.a.enableEnemy = 1
	local.a forceactivate
	local.a.coop_psqMounted = 1
	local.a.coop_psqBusy = 0
	local.a.coop_psqMgBad = 0
	// is he AT the gun? Where the engine cannot seat him it leaves him where he stopped, hands on
	// nothing. Then there is no gun.
	wait 0.6
	if( local.a == NULL ){ end }
	if( local.gun != NULL && isAlive local.a ){
		local.seat = waitthread mgSeat local.gun.origin local.gun.angles[1] local.a.coop_psqMgStand[2]
		local.off = waitthread flatDist local.a.origin local.seat
		if( local.off > 14 ){
			waitthread dbg ( "mg setup abort=not_seated off=" + local.off )
			waitthread mgPackup local.a
			end
		}
	}
	waitthread ev "mg" local.a
	thread mgHold local.a local.gun local.sid
	local.go = local.gun.origin""", """	local.gun.origin = local.a.coop_psqMgGun
	// remember his own thinks for the pack-up, then onto the gun
	local.a.coop_psqT1 = local.a.type_idle
	local.a.coop_psqT2 = local.a.type_attack
	local.a.coop_psqT3 = local.a.type_disguise
	local.a.coop_psqT4 = local.a.type_grenade
	thread mgPivot local.gun local.sup local.mode local.yaw
	local.ok = waitthread mgMount local.a local.gun local.sid
	if( local.a == NULL ){ end }
	if( local.ok != 1 ){
		// (a man who died in these last moments leaves it where it stands: the gunner thread hands it to the players)
		if( isAlive local.a ){
			waitthread dbg "mg setup abort=not_seated"
			waitthread mgPackup local.a
		}
		end
	}
	waitthread ev "mg" local.a
	local.go = local.gun.origin""")

# 4. mgTend: what the gun stands on is looked for under where it was set down (mgPivot moves the gun itself)
e.sub("""		local.chk = local.gun.origin - ( 0 0 13.5 )
		local.sz = waitthread mgSurf local.chk 10 14
		if( local.sz == NIL ){ end "support_gone" }""", """		local.chk = local.gun.origin - ( 0 0 13.5 )
		if( local.gun.coop_psqBase != NIL ){ local.chk = local.gun.coop_psqBase - ( 0 0 13.5 ) }
		local.sz = waitthread mgSurf local.chk 10 14
		if( local.sz == NIL ){ end "support_gone" }""")

# 5. mgPackup: mgPivot lets go of the gun first
e.sub("""mgPackup local.a:{
	if( local.a == NULL ){ end }
	local.a.coop_psqBusy = 1
	local.a type_idle local.a.coop_psqT1""", """mgPackup local.a:{
	if( local.a == NULL ){ end }
	local.a.coop_psqBusy = 1
	local.pg = local.a.coop_psqGun
	if( local.pg != NIL && local.pg != NULL ){ local.pg.coop_psqPivot = 0 }
	local.a type_idle local.a.coop_psqT1""")

# 6. the new routines, after mgPackup
NEW = r'''

// off the gun: his own thinks back (the first lines of mgPackup, for a man who will come back to it)
mgOff local.a:{
	local.a type_idle local.a.coop_psqT1
	local.a type_attack local.a.coop_psqT2
	local.a type_disguise local.a.coop_psqT3
	local.a type_grenade local.a.coop_psqT4
	local.a physics_on
	local.a.coop_psqMounted = 0
}end


// THE REST. With nobody on it a bipod gun lies back on its butt, muzzle up (user 2026-10-12: "when no one is using
// that 30 cal it should be facing upward"). How far: the underside of the gun - a line from 2u under the pivot to the
// lowest corner of the stock, 63.4u behind the pivot and 8.2u under the bore (models/statweapons/30cal at 0.52) - is
// swung down in 2 degree steps until the world is in its way: the ground behind the rest, or the near edge of the
// cover it stands on. 31 degrees on the sandbags (the bags themselves are clear of it to 46). The engine's own
// drop (TurretGun::ThinkIdle) tests a point 56u back ON the bore line and stops 13 degrees later, the stock 11u in
// the ground. With nothing in the way (a sill at chest height) it stops at 60. Returns the gun's pitch: negative =
// muzzle up.
mgRest local.gp local.yaw:{
	local.r = 60
	for( local.t = 2; local.t <= 60; local.t = local.t + 2 ){
		local.ang = ( ( 0 - local.t ) local.yaw 0 )
		local.f = angles_toforward local.ang
		local.u = angles_toup local.ang
		local.p0 = local.gp - ( vector_scale local.u 2 )
		local.p1 = local.gp - ( vector_scale local.f 63.4 ) - ( vector_scale local.u 8.2 )
		local.tr = traced local.p0 local.p1 1023 ( 0 0 0 ) ( 0 0 0 ) 1
		if( local.tr["fraction"] < 1.0 || local.tr["startSolid"] == 1 ){
			local.r = local.t - 2
			break
		}
	}
	if( local.r < 6 ){ local.r = 6 }
	local.r = 0 - local.r
}end local.r


// the pitch an unmanned gun eases to: the engine key (game.dll 1.10.22, eased), else the retail idle limit (the
// engine's own drop, stopped there)
mgRestSet local.gun local.p:{
	local.kk = waitthread coop_mod/parasquad_gun.scr::rest local.gun local.p
	if( local.kk != 1 ){ local.gun maxIdlePitch local.p }
}end


// he takes the gun (global/mg42_active.scr gunner recipe). The gun is LEVEL before his hands go on it - it tipped
// during the set-down once and stayed tipped under them, and his hand was at his face - and goes back to its rest
// only when nobody holds it. 1 = he is on it.
mgMount local.a local.gun local.sid:{
	waitthread mgRestSet local.gun 0
	local.t = 0
	while( local.t < 1.2 ){
		wait 0.05
		local.t = local.t + 0.05
		if( local.gun == NULL || local.a == NULL ){ end 0 }
		local.gp = local.gun.angles[0]
		if( local.gp > 180 ){ local.gp = local.gp - 360 }
		if( local.gp > ( 0 - 1.5 ) && local.gp < 1.5 ){ break }
	}
	if( !isAlive local.a ){ end 0 }
	// onto the seat the engine will hold him on: it sweeps his hull down from 18u over his FEET, so
	// a seat on ground a little higher than where he stopped would never take him
	local.a.origin = local.a.coop_psqMgStand
	local.a turret local.gun
	local.a type_idle "machinegunner"
	local.a type_attack "machinegunner"
	local.a type_disguise "machinegunner"
	local.a type_grenade "machinegunner"
	local.a physics_off
	local.a.enableEnemy = 1
	local.a forceactivate
	local.a.coop_psqMounted = 1
	local.a.coop_psqBusy = 0
	local.a.coop_psqMgBad = 0
	local.gun.coop_psqMan = local.a
	local.rp = local.gun.coop_psqRest
	waitthread mgRestSet local.gun local.rp
	thread mgHold local.a local.gun local.sid
	thread mgNade local.a local.gun local.sid
	// is he AT the gun? Where the engine cannot seat him it leaves him where he stopped, hands on
	// nothing. Then there is no gun.
	wait 0.6
	if( local.a == NULL || local.gun == NULL ){ end 0 }
	if( !isAlive local.a ){ end 0 }
	local.base = local.gun.origin
	if( local.gun.coop_psqBase != NIL ){ local.base = local.gun.coop_psqBase }
	local.seat = waitthread mgSeat local.base local.gun.angles[1] local.a.coop_psqMgStand[2]
	local.off = waitthread flatDist local.a.origin local.seat
	if( local.off > 14 ){
		waitthread dbg ( "mg mount not_seated off=" + local.off )
		end 0
	}
}end 1


// THE GUN UNDER PITCH. The engine holds a gunner's hands 39u behind the gun's pivot on the gun's own line
// (Actor::ThinkHoldGun_TurretGun) and blends his pose between standing and crouched to put them there. The crouched
// pose is as low as he gets: hands 38.7u over his feet. A LOW gun pitched UP takes its grips under that - 39u x the
// sine of the pitch, 8u at 12 degrees, 13u at 20: firing at an upstairs window his hand was at his helmet. So the gun
// is lifted by what is missing: he raises the muzzle with the grips where they are, and the bipod, fast to the
// barrel, comes off its rest with it. Pitched down, or on a gun high enough for the blend, the engine's pose follows
// and nothing moves. A PLAYER on a low gun has one crouched clip and no blend: on the lowest guns it follows him
// down as well (the bipod's feet press up to 9u into the bags).
// Every frame while somebody is on it, four times a second otherwise. Lives as long as the gun; mgPackup ends it.
mgPivot local.gun local.sup local.mode local.yaw0:{
	local.base = local.gun.origin
	local.gun.coop_psqBase = local.base
	local.gun.coop_psqPivot = 1
	local.sb = NIL
	if( local.mode != "B" && local.sup != NIL && local.sup != NULL ){ local.sb = local.sup.origin }
	local.cur = 0
	local.last = 0
	while( local.gun != NULL ){
		if( local.gun.coop_psqPivot != 1 ){ break }
		// whose feet: the trooper on it, else a player on it
		local.fz = NIL
		local.pl = 0
		local.a = local.gun.coop_psqMan
		if( local.a != NIL && local.a != NULL ){
			if( isAlive local.a ){
				if( local.a.coop_psqMounted == 1 && local.a.coop_psqGun == local.gun ){ local.fz = local.a.origin[2] }
			}
		}
		if( local.fz == NIL ){
			for( local.i = 1; local.i <= $player.size; local.i++ ){
				local.p = $player[local.i]
				if( local.p == NULL ){ continue }
				if( local.p.turret == local.gun ){
					local.fz = local.p.origin[2]
					local.pl = 1
					break
				}
			}
		}
		local.want = 0
		local.f = angles_toforward local.gun.angles
		if( local.fz != NIL ){
			local.sink = 39 * local.f[2]
			local.room = local.base[2] - local.fz - 38.7
			if( local.room < 0 ){ local.room = 0 }
			if( local.sink > local.room ){ local.want = local.sink - local.room }
			if( local.pl == 1 && local.sink < 0 && local.room < 3 ){
				local.want = local.sink
				if( local.want < ( 0 - 9 ) ){ local.want = 0 - 9 }
			}
			if( local.want > 18 ){ local.want = 18 }
		}
		// 3u a frame at most (a man who has just taken it)
		local.d = local.want - local.cur
		if( local.d > 3 ){ local.d = 3 }
		if( local.d < ( 0 - 3 ) ){ local.d = 0 - 3 }
		local.cur = local.cur + local.d
		if( local.cur != 0 || local.last != 0 ){
			local.k = local.cur / 4.0
			if( local.k < 0 ){ local.k = 0 - local.k }
			if( local.k > 1 ){ local.k = 1 }
			// up by what the grips sank, back by what the turn brought them forward
			local.fl = local.f
			local.fl[2] = 0
			local.back = 39 * ( 1.0 - ( vector_length local.fl ) ) * local.k
			local.o = local.base - ( vector_scale ( angles_toforward ( 0 local.gun.angles[1] 0 ) ) local.back )
			local.o[2] = local.base[2] + local.cur
			local.gun.origin = local.o
			if( local.sb != NIL && local.sup != NULL ){
				local.gp = local.gun.angles[0]
				if( local.gp > 180 ){ local.gp = local.gp - 360 }
				local.dy = local.gun.angles[1] - local.yaw0
				while( local.dy > 180 ){ local.dy = local.dy - 360 }
				while( local.dy < ( 0 - 180 ) ){ local.dy = local.dy + 360 }
				local.sup.origin = local.sb + ( local.o - local.base )
				local.sup.angles = ( ( local.gp * local.k ) ( local.yaw0 + ( local.dy * local.k ) ) 0 )
			}
			local.last = local.cur
		}
		if( local.fz == NIL && local.cur == 0 ){ wait 0.25 } else { waitframe }
	}
	// the pack-up takes everything from where it was set down
	if( local.gun != NULL ){ local.gun.origin = local.base }
	if( local.sb != NIL && local.sup != NULL ){
		local.sup.origin = local.sb
		local.sup.angles = ( 0 local.yaw0 0 )
	}
}end


// THE MOUNTED GUNNER AND A GRENADE. On the gun his grenade think is the machine gunner's (the retail recipe), and for
// an American that one does nothing: he sat through it. Script has no way to ask the engine what grenade a man has
// seen, so the entity table is looked through, 64 slots a frame (all of it in under a second): a projectile that has
// come to rest - not one in flight, his own squad throws them past him - within 300u of him.
mgNade local.a local.gun local.sid:{
	local.i = 0
	while( local.a != NULL && local.gun != NULL ){
		if( !isAlive local.a ){ break }
		if( local.a.coop_psqMounted != 1 || local.a.coop_psqGun != local.gun ){ break }
		local.hit = NIL
		for( local.n = 0; local.n < 64; local.n++ ){
			local.i++
			if( local.i >= 1024 ){ local.i = 1 }
			local.e = getentbyentnum local.i
			if( local.e == NULL ){ continue }
			if( local.e.classname != "Projectile" ){ continue }
			if( vector_length( local.e.origin - local.a.origin ) > 300 ){ continue }
			if( ( vector_length local.e.velocity ) > 200 ){ continue }
			local.hit = local.e
			break
		}
		if( local.hit != NIL ){
			thread mgFlee local.a local.gun local.sid local.hit
			break
		}
		waitframe
	}
}end


// he lets go of the gun and gets 300u away from the grenade - straight away from it, else round in 45 degree steps,
// over ground that was looked at (mgLine) -, stays there until it has gone off, walks back and takes the gun again.
// A gun he cannot get back to, or that a player took meanwhile, is the players' (mgGiveUp).
mgFlee local.a local.gun local.sid local.nade:{
	local.np = local.nade.origin
	local.seat = local.a.origin
	local.a.coop_psqBusy = 1
	waitthread dbg ( "mg nade at=" + local.np + " d=" + ( vector_length( local.np - local.seat ) ) )
	waitthread mgOff local.a
	local.a.enableEnemy = 0
	local.v = local.seat - local.np
	local.v[2] = 0
	if( vector_length local.v < 8 ){ local.v = angles_toforward ( 0 ( local.gun.angles[1] + 180 ) 0 ) }
	local.va = vector_toangles local.v
	local.to = NIL
	for( local.i = 0; local.i < 5; local.i++ ){
		local.h = int( ( local.i + 1 ) / 2 ) * 45
		if( ( local.i - ( int( local.i / 2 ) * 2 ) ) == 0 ){ local.h = 0 - local.h }
		local.c = local.seat + ( vector_scale ( angles_toforward ( 0 ( local.va[1] + local.h ) 0 ) ) 300 )
		local.cz = waitthread mgSurf local.c 40 60
		if( local.cz == NIL ){ continue }
		local.c[2] = local.cz
		if( !( waitthread mgLine local.seat local.c ) ){ continue }
		local.to = local.c
		break
	}
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
			local.straight = 0
			local.rad = 28
			if( waitthread mgLine local.a.origin local.seat ){
				local.straight = 1
				local.rad = 10
			}
			local.left = waitthread mgLeg local.a local.seat local.straight local.rad 8
			if( local.a == NULL ){ end }
			if( !isAlive local.a ){ end }
			if( local.left > 14 && local.left < 110 ){
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
	waitthread dbg ( "mg nade back=" + local.ok )
	if( local.ok != 1 ){ waitthread mgGiveUp local.a local.gun }
}end


// the gun stays where it is, for the players; he is a rifleman from here on
mgGiveUp local.a local.gun:{
	if( local.gun != NULL ){ waitthread mgLeft local.gun 0 }
	if( local.a == NULL ){ end }
	local.a.coop_psqGun = NIL
	local.a.coop_psqCrate = NIL
	local.a.coop_psqSup = NIL
	local.a.coop_psqBag = NIL
	local.a.coop_psqBeltOut = 1
	if( isAlive local.a ){
		local.a unholster
		local.a.enableEnemy = 1
		local.a forceactivate
		waitthread post local.a local.a.origin 200
	}
	local.a.coop_psqBusy = 0
	waitthread dbg "mg given up"
}end
'''
e.sub("""	local.a.coop_psqBusy = 0
	waitthread dbg "mg packup k=1"
}end
""", """	local.a.coop_psqBusy = 0
	waitthread dbg "mg packup k=1"
}end
""" + NEW)
e.save()
