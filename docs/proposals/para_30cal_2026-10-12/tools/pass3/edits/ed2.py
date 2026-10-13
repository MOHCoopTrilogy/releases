"""ed2.py - third pass: the TACTICAL squad brain (coop_mod/parasquad.scr). Replaces member / brain / slotPos / moveTo /
overwatch / coverCheck / findCover, adds post / cov / tight / inFire / lineTo / baseOfFire / bound / coverNear, and
takes every `resetleash` out (it clears the tether the posts are built on)."""
import io, re
P = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr"
s = io.open(P, encoding="latin-1", newline="").read().replace("\r\n", "\n")


def sub(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)


def func(name, new):
    """replace the whole function `name` (label line through its }end line) by new"""
    global s
    m = re.search(r"(?m)^%s( [^\n]*)?:\{\n" % re.escape(name), s)
    assert m, name
    e = re.compile(r"(?m)^\}end[^\n]*\n").search(s, m.end())
    s = s[:m.start()] + new.strip("\n") + "\n" + s[e.end():]


assert "tether" not in s
# ---------------------------------------------------------------- header
sub("""//   FOLLOW   no contact for 8s: wedge behind the anchor (the trooper who threw the smoke, else the
//            nearest player), the two fire teams (1+3 / 2+4) moving on alternate ticks = bounding.
//   CONTACT  engine combat (type_attack cover, own prone/crouch legs in anim/attack.scr) plus:
//            - COVER: a man with a clear line to his enemy and nothing in front of him at waist
//              height moves (crouched) to the nearest spot with a low obstacle between him and the
//              enemy that he can still shoot over;
//            - BOUND: a man left > 900u behind the anchor moves up while the other fire team
//              suppresses (suppresschance 100 for the move);
""", """//   POSTS    every man has a POST: a point his leash is tethered to (the engine's own `tether`:
//            Actor::Think puts m_vHome on the tether entity every frame). The engine's cover and
//            turret thinks path, hunt and take cover nodes only INSIDE the leash round that point
//            (SetPathWithLeash / MovePathWithLeash), so where the post is, is where he fights. The
//            brain moves posts; the man follows. (Until 2026-10-12 the leash was 640u and was reset
//            to wherever he stood - on every order here and by the engine on every new enemy - so
//            it never held anyone: that was the "brainless rush", 1000u past the players.)
//   FOLLOW   no contact for 8s: wedge behind the anchor (the trooper who threw the smoke, else the
//            nearest player), the two fire teams (1+3 / 2+4) moving on alternate ticks = bounding.
//   CONTACT  the wedge turns to face the enemy and stays BEHIND / BESIDE the players - nobody goes
//            past them toward the enemy; a man who is, comes back. Engine combat inside the leash
//            (type_attack cover: cover nodes, peeking; own prone/crouch legs in anim/attack.scr) plus:
//            - BASE OF FIRE: the .30 cal with the enemy in its arc, else the BAR man with a line to
//              him, else two riflemen with one. No base of fire = nobody moves up;
//            - BOUND: with a base of fire up, the men who are behind their place move up one fire
//              team at a time, 300u at most, to cover where there is some, while the base
//              suppresses (the gun fires bursts for the move, the others suppresschance 100);
//            - COVER: a man in plain view of the enemy goes (crouched) to the nearest cover - low
//              cover he can fire over first, else a corner - and his post goes with him; with no
//              cover in reach he gets small where he is;
//            - PINNED: a man who has just been hit stays down where he is (or crawls to cover
//              within 130u) for 4s: no orders;
//            - MAN DOWN: for 6s nobody bounds, everybody in view takes cover;
//            - LANES: a man in front of a player's muzzle steps out of it; no post in a doorway;
""")
# ---------------------------------------------------------------- member
func("member", r'''
member local.k local.sid:{
	if( self == NULL ){ end }
	self.flags["coop_personality_set"] = 1
	self.flags["coop_role"] = "para"
	self.coop_psqSid = local.sid
	self.coop_psqK = local.k
	self.coop_psqBusy = 0
	self.coop_psqMounted = 0
	self.coop_psqNadeT = 0
	self.coop_psqNoPath = 0
	self.coop_psqPinT = 0
	self.coop_psqSideT = 0
	self.coop_psqCovT = 0
	self.coop_psqHp = self.health
	self type_attack "cover"
	self.mindist = 128
	// maxdist: an American whose enemy is beyond it always CHARGES (Actor::Turret_SelectState - the "hold at
	// your leash" branch is German-only). 3000 = he fights from where he is posted.
	self.maxdist = 3000
	self.interval = 128			// spacing the engine keeps from squadmates while moving
	self.nosurprise = 1
	self.ammo_grenade = 0			// no engine-decided throws - only the checked scripted ones below
	self gren_awareness 90			// he sees a grenade land (engine default 20%): the engine's own grenade think gets him away
	self.suppresschance = 40
	self.coop_paraProne = 25		// anim/attack.scr: own prone leg at long range
	self.coop_paraCrouch = 45		// own crouch leg (raised while he holds a low-cover spot)
	self.coop_paraBrain = 1			// set LAST: attack.scr reads the two values above once this is 1
	waitthread post self self.origin 240
	if( local.sid != NIL ){
		level.coop_psqM[local.sid][local.k] = self
		// the .30 cal is the RIFLEMAN's (member 3, the M1 Garand): the BAR man (member 1) keeps his BAR
		// and stays the squad's automatic rifle. Member 3 is also the man who gets out of a C-47 that
		// is lost to flak; a squad that lands without him has no .30 cal (the sniper and the medic
		// never take it).
		if( local.k == 3 ){ thread gunner self local.sid }
	}
}end
''')
sub("""// The squad's anchor: the trooper-caller if he is alive and playing, else the nearest player.
""", """// His POST: the point his leash is tethered to (see the header). local.leash = how far from it the engine may
// take him. Never `resetleash` on a trooper - it clears the tether (Actor::EventResetLeash).
post local.a local.pos local.leash:{
	if( local.a == NIL || local.a == NULL ){ end }
	local.e = local.a.coop_psqPost
	if( local.e == NIL || local.e == NULL ){
		local.e = spawn script_origin
		local.e.origin = local.pos
		local.a.coop_psqPost = local.e
		local.a tether local.e
	}
	local.e.origin = local.pos
	local.a.leash = local.leash
}end


// The squad's anchor: the trooper-caller if he is alive and playing, else the nearest player.
""")
# ---------------------------------------------------------------- brain
func("brain", r'''
brain local.sid:{
	wait 8					// the stick is still under canopy
	local.lastContact = 0 - 100
	local.lastNade = 0 - 100
	local.lastClear = 0 - 100
	local.holdRef = NIL
	local.holdSince = level.time
	local.phase = 0
	local.boundTeam = 1
	local.boundTick = 0
	local.cc = 0
	local.wave = 0
	local.clrTick = 0
	local.wasContact = 0
	local.prevAlive = 0
	local.shaken = 0
	local.axis = NIL
	waitthread dbg ( "brain start sid=" + local.sid )
	while( 1 ){
		wait 1
		// ---- roster ----
		local.alive = 0
		for( local.k = 1; local.k <= 5; local.k++ ){
			local.a = level.coop_psqM[local.sid][local.k]
			if( local.a != NIL && local.a != NULL ){
				if( isAlive local.a ){
					local.alive++
				} else {
					// a dead man's post goes
					local.pe = local.a.coop_psqPost
					if( local.pe != NIL && local.pe != NULL ){ local.pe remove }
					local.a.coop_psqPost = NIL
				}
			}
		}
		if( local.alive == 0 && ( level.time - level.coop_psqT0[local.sid] ) > 45 ){
			waitthread dbg ( "brain end sid=" + local.sid )
			end
		}
		if( local.alive == 0 ){ continue }
		if( local.alive < local.prevAlive ){
			// MAN DOWN: six seconds in which nobody moves up and everybody in view gets behind something
			local.shaken = level.time + 6
			waitthread dbg ( "tac mandown alive=" + local.alive )
		}
		local.prevAlive = local.alive

		// ---- anchor + facing ----
		local.anc = waitthread anchor local.sid
		if( level.coop_paraHoldPos != NIL ){
			local.apos = level.coop_paraHoldPos
			local.ayaw = 0
			if( level.coop_paraHoldYaw != NIL ){ local.ayaw = level.coop_paraHoldYaw }
		} else {
			if( local.anc == NIL ){ continue }
			local.apos = local.anc.origin
			local.v = local.anc.velocity
			local.v[2] = 0
			local.vl = vector_length local.v
			if( local.vl > 60 ){
				local.va = vector_toangles local.v
				local.ayaw = local.va[1]
			} else {
				local.ayaw = local.anc.viewangles[1]
			}
		}
		level.coop_psqApos[local.sid] = local.apos
		level.coop_psqAyaw[local.sid] = local.ayaw

		// ---- holding? (anchor within 160u of one spot for 6s) ----
		if( local.holdRef == NIL ){ local.holdRef = local.apos; local.holdSince = level.time }
		local.hd = waitthread flatDist local.apos local.holdRef
		if( local.hd > 160 ){
			local.holdRef = local.apos
			local.holdSince = level.time
		}
		if( ( level.time - local.holdSince ) >= 6 ){ level.coop_psqHolding[local.sid] = 1 } else { level.coop_psqHolding[local.sid] = 0 }

		// ---- contact + nearest known threat ----
		local.thr = NIL
		local.td = 999999
		for( local.k = 1; local.k <= 5; local.k++ ){
			local.a = level.coop_psqM[local.sid][local.k]
			if( local.a == NIL || local.a == NULL ){ continue }
			if( !isAlive local.a ){ continue }
			local.e = local.a.enemy
			if( local.e == NIL || local.e == NULL ){ continue }
			if( !isAlive local.e ){ continue }
			local.lastContact = level.time
			local.d = vector_length( local.e.origin - local.apos )
			if( local.d < local.td ){ local.td = local.d; local.thr = local.e.origin }
		}
		level.coop_psqThreat[local.sid] = local.thr
		if( local.thr != NIL ){
			level.coop_psqLastThr[local.sid] = local.thr
			level.coop_psqLastThrT[local.sid] = level.time
		}
		waitthread trail
		local.inContact = 0
		if( ( level.time - local.lastContact ) < 8 ){ local.inContact = 1 }

		// ---- the way the fight faces: toward the nearest known enemy; it turns only when he is more than 55
		// degrees off it (a wedge that swung with every new target would have the men running under fire)
		if( local.thr != NIL ){
			local.v = local.thr - local.apos
			local.v[2] = 0
			if( vector_length local.v > 32 ){
				local.va = vector_toangles local.v
				if( local.axis == NIL ){ local.axis = local.va[1] }
				local.df = local.va[1] - local.axis
				while( local.df > 180 ){ local.df = local.df - 360 }
				while( local.df < ( 0 - 180 ) ){ local.df = local.df + 360 }
				if( local.df < 0 ){ local.df = 0 - local.df }
				if( local.df > 55 ){ local.axis = local.va[1] }
			}
		}
		if( local.inContact == 0 ){ local.axis = NIL }
		local.cyaw = local.ayaw
		if( local.axis != NIL ){ local.cyaw = local.axis }
		local.cfw = angles_toforward ( 0 local.cyaw 0 )

		// ---- first contact: every man's post is where he stands (nobody runs to a slot under fire) ----
		if( local.inContact == 1 && local.wasContact == 0 ){
			for( local.k = 1; local.k <= 5; local.k++ ){
				local.a = level.coop_psqM[local.sid][local.k]
				if( local.a == NIL || local.a == NULL ){ continue }
				if( !isAlive local.a || local.a.coop_psqMounted == 1 ){ continue }
				local.a.coop_psqHp = local.a.health
				waitthread post local.a local.a.origin 180
			}
			waitthread dbg ( "tac contact thr=" + local.thr )
		}
		local.wasContact = local.inContact

		// ---- who suppresses? ----
		local.base = 0
		if( local.inContact == 1 && local.thr != NIL ){ local.base = waitthread baseOfFire local.sid local.thr }
		level.coop_psqBase[local.sid] = local.base

		if( local.phase == 1 ){ local.phase = 0 } else { local.phase = 1 }
		local.boundTick++
		if( local.boundTick >= 3 ){
			local.boundTick = 0
			if( local.boundTeam == 1 ){ local.boundTeam = 0 } else { local.boundTeam = 1 }
		}
		local.cc++
		if( local.cc > 4 ){ local.cc = 1 }

		// ---- per member ----
		local.movers = 0
		for( local.k = 1; local.k <= 4; local.k++ ){
			local.a = level.coop_psqM[local.sid][local.k]
			if( !( waitthread usable local.a ) ){ continue }
			local.team = 0
			if( local.k == 1 || local.k == 3 ){ local.team = 1 }
			local.da = waitthread flatDist local.a.origin local.apos

			if( local.inContact == 0 ){
				// FOLLOW: fire teams leapfrog on alternate ticks; a straggler always moves
				local.a.coop_paraCrouch = 45
				local.a.coop_paraProne = 25
				local.a.coop_psqHp = local.a.health
				if( local.da > 240 ){
					if( local.team == local.phase || local.da > 700 ){
						local.slot = waitthread slotPos local.a local.k local.apos local.ayaw 0
						if( local.slot != NIL ){
							local.ds = waitthread flatDist local.a.origin local.slot
							if( local.ds > 120 ){
								local.a.movedoneradius = 64
								// A man standing in a map cell that holds no pathnode has no path to anywhere
								// (PathSearch::NearestStartNode looks in his own 256u cell only): that is the
								// trooper who came down in a bad spot and never moves. Two orders that got him
								// nowhere and he walks out in a straight line, as far as the ground was traced.
								local.so = local.a.coop_psqOrdO
								local.a.coop_psqOrdO = local.a.origin
								if( local.so != NIL ){
									if( vector_length( local.a.origin - local.so ) < 24 && local.a.pathdist == 0 ){
										local.a.coop_psqNoPath++
									} else {
										local.a.coop_psqNoPath = 0
									}
								}
								if( local.a.coop_psqNoPath >= 2 ){
									local.a.coop_psqNoPath = 0
									thread walkOut local.a local.slot
								} else {
									waitthread post local.a local.slot 320
									local.a runto local.slot
								}
							}
						}
					}
				}
				continue
			}

			// ---- CONTACT ----
			// hit since the last look: PINNED for 4s - he stays down, and gets no order
			if( local.a.health < ( local.a.coop_psqHp - 10 ) ){
				if( level.time >= local.a.coop_psqPinT ){ waitthread dbg ( "tac pinned k=" + local.k + " hp=" + local.a.health ) }
				local.a.coop_psqPinT = level.time + 4
			}
			local.a.coop_psqHp = local.a.health
			// what is between him and the enemy (0 = nothing: he is in plain view)
			local.c = 3
			if( local.thr != NIL ){ local.c = waitthread cov local.a.origin ( local.thr + ( 0 0 56 ) ) }
			if( level.time < local.a.coop_psqPinT ){
				local.a.coop_paraCrouch = 100
				if( local.c == 0 && level.time >= local.a.coop_psqCovT ){
					local.a.coop_psqCovT = level.time + 4
					thread coverCheck local.a 130
				}
				continue
			}
			local.slot = waitthread slotPos local.a local.k local.apos local.cyaw 1
			if( local.slot == NIL ){ continue }
			local.ds = waitthread flatDist local.a.origin local.slot
			// past the players, toward the enemy? Then he comes back.
			local.v = local.a.origin - local.apos
			local.v[2] = 0
			local.al = vector_dot local.v local.cfw
			local.back = 0
			if( local.al > 140 ){ local.back = 1 }
			local.go = 0
			if( local.back == 1 || local.ds > 340 ){
				// he is not where he belongs. Coming back, or catching up from far behind, he always may; moving UP
				// only with a base of fire, his own fire team's turn, two men at most, and nobody just hit
				if( local.back == 1 || local.da > 1100 ){ local.go = 1 }
				if( local.go == 0 && local.base >= 1 && level.time >= local.shaken && local.team == local.boundTeam && local.movers < 2 ){ local.go = 1 }
			}
			if( local.go == 1 ){
				local.movers++
				thread bound local.a local.sid local.slot local.thr local.back
				continue
			}
			if( local.c == 0 ){
				// in plain view: one man a tick looks for cover (every man, when one of them has just gone down)
				if( local.k == local.cc || level.time < local.shaken ){
					if( level.time >= local.a.coop_psqCovT ){
						local.a.coop_psqCovT = level.time + 3
						thread coverCheck local.a 200
					}
				}
			} else if( local.c == 1 ){
				local.a.coop_paraCrouch = 100		// low cover in front of him: down behind it between shots
			} else {
				local.a.coop_paraCrouch = 45
			}
		}

		// ---- the medic keeps behind the players (his own loop tends and follows; this is only his leash) ----
		local.a = level.coop_psqM[local.sid][5]
		if( local.a != NIL && local.a != NULL ){
			if( isAlive local.a ){
				local.mp = local.apos - ( vector_scale local.cfw 260 )
				waitthread post local.a local.mp 320
			}
		}

		// ---- out of the players' line of fire: in a fight, or while the player is firing ----
		for( local.k = 1; local.k <= 4; local.k++ ){
			local.a = level.coop_psqM[local.sid][local.k]
			if( !( waitthread usable local.a ) ){ continue }
			if( level.time < local.a.coop_psqSideT ){ continue }
			local.p = waitthread inFire local.a.origin
			if( local.p == NIL ){ continue }
			if( local.inContact != 1 && local.p.fireheld != 1 ){ continue }
			local.fw = angles_toforward ( 0 local.p.viewangles[1] 0 )
			local.v = local.a.origin - local.p.origin
			local.v[2] = 0
			local.al = vector_dot local.v local.fw
			local.sd = local.v - ( vector_scale local.fw local.al )
			if( vector_length local.sd < 2 ){ local.sd = angles_toforward ( 0 ( local.p.viewangles[1] - 90 ) 0 ) }
			local.sd = vector_normalize local.sd
			local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.a.origin + ( vector_scale local.sd 110 ) + ( 0 0 40 ) )
			if( local.g == NIL ){ continue }
			if( waitthread tight local.g ){ continue }
			local.a.coop_psqSideT = level.time + 5
			waitthread dbg ( "tac lane k=" + local.k + " to=" + local.g )
			thread moveTo local.a local.g 1.5 0 "lane"
		}

		// ---- officer-wave targets (they hunt players only and never notice AI on their own) ----
		local.wave++
		if( local.wave >= 3 && level.coop_wave_count != NIL ){
			local.wave = 0
			for( local.k = 1; local.k <= 4; local.k++ ){
				local.a = level.coop_psqM[local.sid][local.k]
				if( !( waitthread usable local.a ) ){ continue }
				if( local.a.enemy != NULL ){ continue }
				local.best = NULL
				local.bd = 2000
				for( local.wi = 1; local.wi <= level.coop_wave_count; local.wi++ ){
					local.w = level.coop_wave_actors[local.wi]
					if( local.w == NIL || local.w == NULL ){ continue }
					if( !isAlive local.w ){ continue }
					local.d = vector_length( local.w.origin - local.a.origin )
					if( local.d < local.bd ){
						if( local.a cansee local.w ){ local.bd = local.d; local.best = local.w }
					}
				}
				if( local.best != NULL ){ local.a attackentity local.best }
			}
		}

		// ---- grenades (one per squad per 9s) ----
		if( local.inContact == 1 && ( level.time - local.lastNade ) >= 9 ){
			if( waitthread tryGrenade local.sid ){ local.lastNade = level.time }
		}
		// ---- room clearing (one per squad per 30s): only with a base of fire, and not with a man just down ----
		local.clrTick++
		if( local.clrTick >= 3 && local.inContact == 1 && ( level.time - local.lastClear ) >= 30 && local.base >= 1 && level.time >= local.shaken ){
			local.clrTick = 0
			if( waitthread tryClear local.sid local.apos ){ local.lastClear = level.time }
		}
	}
}end
''')
# ---------------------------------------------------------------- slotPos
func("slotPos", r'''
slotPos local.a local.k local.apos local.ayaw local.fight:{
	local.back = 170
	local.side = 150
	if( local.k >= 3 ){ local.back = 320; local.side = 240 }
	if( local.fight == 1 ){
		// in a fight the wedge is flatter and wider: a firing line beside and behind the players
		local.back = 90
		local.side = 190
		if( local.k >= 3 ){ local.back = 200; local.side = 330 }
	}
	if( local.k == 1 || local.k == 3 ){ local.side = 0 - local.side }
	local.fwd = angles_toforward ( 0 local.ayaw 0 )
	local.rgt = angles_toforward ( 0 ( local.ayaw - 90 ) 0 )
	local.p = local.apos - ( vector_scale local.fwd local.back ) + ( vector_scale local.rgt local.side )
	// NOTE: never `canmoveto` here - it is a leash/mindist/interval test against the actor's HOME, not a
	// path test, so it refused nearly every slot in the 2026-10-04 run. runto paths; a dead-end order
	// simply stalls and the next tick re-plans.
	local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.p + ( 0 0 48 ) )
	if( local.g != NIL ){
		local.dz = local.g[2] - local.apos[2]
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz < 120 ){ end local.g }		// not the roof or the cellar under that point
	}
	// half-size wedge
	local.p = local.apos - ( vector_scale local.fwd ( local.back * 0.5 ) ) + ( vector_scale local.rgt ( local.side * 0.5 ) )
	local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.p + ( 0 0 48 ) )
	if( local.g != NIL ){
		local.dz = local.g[2] - local.apos[2]
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz < 120 ){ end local.g }
	}
}end NIL
''')
# ---------------------------------------------------------------- moveTo / overwatch
func("moveTo", r'''
moveTo local.a local.pos local.tmo local.crouch local.why:{
	if( local.a == NIL || local.a == NULL ){ end }
	if( !isAlive local.a ){ end }
	if( local.a.coop_psqBusy == 1 || local.a.coop_psqMounted == 1 ){ end }	// somebody else has him
	local.a.coop_psqBusy = 1
	local.a.enableEnemy = 0
	local.a.movedoneradius = 40
	waitthread post local.a local.pos 240
	if( local.crouch == 1 ){ local.a crouchto local.pos } else { local.a runto local.pos }
	local.t = 0
	while( local.t < local.tmo ){
		wait 0.25
		local.t = local.t + 0.25
		if( local.a == NULL ){ end }
		if( !isAlive local.a ){ end }
		if( vector_length( local.a.origin - local.pos ) < 56 ){ break }
		if( local.t >= 0.75 ){
			local.v = local.a.velocity
			if( ( local.v[0] * local.v[0] ) + ( local.v[1] * local.v[1] ) < 100 ){ break }
		}
	}
	// his post is where he got to (the leash holds him there; see the header)
	waitthread post local.a local.a.origin 170
	local.a.enableEnemy = 1
	local.a forceactivate
	local.a.coop_psqBusy = 0
	waitthread dbg ( "move k=" + local.a.coop_psqK + " why=" + local.why + " left=" + ( vector_length( local.a.origin - local.pos ) ) )
}end
''')
func("overwatch", r'''
overwatch local.sid local.mover local.secs:{
	for( local.k = 1; local.k <= 4; local.k++ ){
		local.a = level.coop_psqM[local.sid][local.k]
		if( local.a == NIL || local.a == NULL || local.a == local.mover ){ continue }
		if( isAlive local.a ){ local.a.suppresschance = 100 }
	}
	wait local.secs
	for( local.k = 1; local.k <= 4; local.k++ ){
		local.a = level.coop_psqM[local.sid][local.k]
		if( local.a != NIL && local.a != NULL ){
			if( isAlive local.a ){ local.a.suppresschance = 40 }
		}
	}
}end
''')
sub("""// the fire team NOT moving lays down suppressing fire for the move
""", """// a line of fire from local.p to an enemy standing at local.thr: clear to within 96u of him
lineTo local.p local.thr:{
	local.e = local.thr + ( 0 0 40 )
	local.d = vector_length( local.e - local.p )
	if( local.d < 97 ){ end 1 }
	local.tr = traced local.p local.e 1023 ( 0 0 0 ) ( 0 0 0 ) 270337
	if( ( local.tr["fraction"] * local.d ) >= ( local.d - 96 ) ){ end 1 }
}end 0


// who suppresses while the others move: 2 = the .30 cal is up with the enemy in its arc and a clear line, 1 = the
// BAR man has a line to him, or two of the others have; 0 = nobody (then nobody moves up)
baseOfFire local.sid local.thr:{
	local.g = level.coop_psqM[local.sid][3]
	if( local.g != NIL && local.g != NULL ){
		if( isAlive local.g && local.g.coop_psqMounted == 1 && local.g.coop_psqMgGun != NIL ){
			local.v = local.thr - local.g.coop_psqMgGun
			local.v[2] = 0
			local.va = vector_toangles local.v
			local.off = local.va[1] - local.g.coop_psqMgYaw
			while( local.off > 180 ){ local.off = local.off - 360 }
			while( local.off < ( 0 - 180 ) ){ local.off = local.off + 360 }
			if( local.off < 0 ){ local.off = 0 - local.off }
			if( local.off <= local.g.coop_psqMgArc ){
				if( waitthread lineTo ( local.g.coop_psqMgGun + ( 0 0 4 ) ) local.thr ){ end 2 }
			}
		}
	}
	local.n = 0
	for( local.k = 1; local.k <= 4; local.k++ ){
		local.a = level.coop_psqM[local.sid][local.k]
		if( !( waitthread usable local.a ) ){ continue }
		if( !( waitthread lineTo ( local.a.origin + ( 0 0 56 ) ) local.thr ) ){ continue }
		if( local.k == 1 ){ end 1 }
		local.n++
	}
	if( local.n >= 2 ){ end 1 }
}end 0


// ONE BOUND toward his place: 300u at most, to cover where there is some near the end of it, while the base of
// fire suppresses (the gun: bursts for the next 4s, mgHold; the others: suppresschance 100). local.back = 1: he is
// past the players and is coming back.
bound local.a local.sid local.slot local.thr local.back:{
	if( !( waitthread usable local.a ) ){ end }
	local.v = local.slot - local.a.origin
	local.v[2] = 0
	local.len = vector_length local.v
	local.to = local.slot
	if( local.len > 300 ){
		local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.a.origin + ( vector_scale local.v ( 300.0 / local.len ) ) + ( 0 0 48 ) )
		if( local.g != NIL ){ local.to = local.g }
	}
	local.cv = 0
	if( local.thr != NIL ){
		local.eye = local.thr + ( 0 0 56 )
		// never nearer the enemy than the players are, less 100u
		local.ap = level.coop_psqApos[local.sid]
		local.lim = waitthread flatDist local.ap local.thr
		local.lim = local.lim - 100
		local.c = waitthread coverNear local.to local.eye local.a 130 local.lim
		if( local.c != NIL ){ local.to = local.c; local.cv = 1 }
	}
	level.coop_psqSupT[local.sid] = level.time + 4
	thread overwatch local.sid local.a 3.5
	waitthread ev "bound" local.a
	waitthread dbg ( "tac bound k=" + local.a.coop_psqK + " back=" + local.back + " cover=" + local.cv + " base=" + level.coop_psqBase[local.sid] + " dist=" + ( vector_length( local.to - local.a.origin ) ) )
	waitthread moveTo local.a local.to 3.5 0 "bound"
	if( local.a == NULL ){ end }
	if( isAlive local.a && local.cv == 1 ){ local.a.coop_paraCrouch = 65 }
}end


// the others lay down suppressing fire while local.mover moves
""")
# ---------------------------------------------------------------- cover
func("coverCheck", r'''
coverCheck local.a local.maxr:{
	if( !( waitthread usable local.a ) ){ end }
	if( local.maxr == NIL ){ local.maxr = 200 }
	local.eye = NIL
	local.e = local.a.enemy
	if( local.e != NIL && local.e != NULL ){
		if( isAlive local.e ){ local.eye = local.e.origin + ( 0 0 56 ) }
	}
	if( local.eye == NIL ){
		local.t = level.coop_psqThreat[local.a.coop_psqSid]
		if( local.t != NIL ){ local.eye = local.t + ( 0 0 56 ) }
	}
	if( local.eye == NIL ){ end }
	if( local.a.position == "prone" ){ end }	// prone is already a small target
	local.c = waitthread cov local.a.origin local.eye
	if( local.c == 1 ){ local.a.coop_paraCrouch = 100; end }
	if( local.c >= 2 ){ end }
	local.lim = waitthread flatDist local.a.origin local.eye
	local.lim = local.lim - 64		// never more than 64u toward him to get there
	local.spot = waitthread coverNear local.a.origin local.eye local.a local.maxr local.lim
	if( local.spot == NIL ){
		// nothing to get behind in reach: he gets small where he is
		local.a.coop_paraCrouch = 100
		local.a.coop_paraProne = 60
		waitthread dbg ( "tac nocover k=" + local.a.coop_psqK )
		end
	}
	local.a.coop_paraCrouch = 65
	waitthread ev "cover" local.a
	waitthread dbg ( "cover k=" + local.a.coop_psqK + " from=" + local.a.origin + " to=" + local.spot )
	waitthread moveTo local.a local.spot 2.5 1 "cover"
	if( local.a == NULL ){ end }
	if( isAlive local.a ){ waitthread post local.a local.a.origin 120 }
}end
''')
func("findCover", r'''
// what a man standing at local.g has between him and an enemy's eye at local.eye (solid world only):
// 0 = nothing - he is in plain view; 1 = LOW cover: hidden to the waist by something within 72u that he can fire
// over; 2 = out of sight behind something within 220u (a corner, a wall); 3 = out of sight, the blocker far off
cov local.g local.eye:{
	if( waitthread lowCoverAt local.g local.eye ){ end 1 }
	local.p = local.g + ( 0 0 44 )
	local.d = vector_length( local.eye - local.p )
	if( local.d < 1 ){ end 0 }
	local.tr = traced local.p local.eye 1023 ( 0 0 0 ) ( 0 0 0 ) 1
	if( local.tr["fraction"] >= 1.0 ){ end 0 }
	local.d1 = local.tr["fraction"] * local.d
	local.q = local.g + ( 0 0 70 )
	local.tr = traced local.q local.eye 1023 ( 0 0 0 ) ( 0 0 0 ) 1
	if( local.tr["fraction"] >= 1.0 ){ end 0 }
	if( local.d1 < 220 ){ end 2 }
}end 3


// a doorway, a corridor, a gap: something within 56u on BOTH sides at chest height, along either axis
tight local.g:{
	local.c = local.g + ( 0 0 40 )
	for( local.j = 0; local.j < 2; local.j++ ){
		local.d = angles_toforward ( 0 ( local.j * 90 ) 0 )
		local.n = ( 0 0 0 ) - local.d
		local.w1 = waitthread mgFree local.c local.d 56
		local.w2 = waitthread mgFree local.c local.n 56
		if( local.w1 < 55 && local.w2 < 55 ){ end 1 }
	}
}end 0


// the player whose muzzle local.g is in front of (within 420u down his aim, 30u + 4% to the side), or NIL
inFire local.g:{
	local.r = NIL
	for( local.i = 1; local.i <= $player.size; local.i++ ){
		local.p = $player[local.i]
		if( local.p == NULL ){ continue }
		if( !isAlive local.p || local.p.dmteam == "spectator" ){ continue }
		local.fw = angles_toforward ( 0 local.p.viewangles[1] 0 )
		local.v = local.g - local.p.origin
		local.dz = local.v[2]
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz > 90 ){ continue }
		local.v[2] = 0
		local.al = vector_dot local.v local.fw
		if( local.al < 20 || local.al > 420 ){ continue }
		local.lat = vector_length( local.v - ( vector_scale local.fw local.al ) )
		if( local.lat < ( 30 + ( local.al * 0.04 ) ) ){ local.r = local.p; break }
	}
}end local.r


// the nearest cover round local.ctr (rings of 64u out to local.maxr) against an enemy's eye at local.eye: low cover
// he can fire over first, a corner second; never where a mate or a player already is, never in a doorway, never in
// front of a player's muzzle, never nearer the enemy than local.lim. NIL = none.
coverNear local.ctr local.eye local.a local.maxr local.lim:{
	local.best = NIL
	local.bs = 999999
	for( local.r = 0; local.r <= local.maxr; local.r = local.r + 64 ){
		for( local.j = 0; local.j < 8; local.j++ ){
			if( local.r == 0 && local.j > 0 ){ break }
			local.c = local.ctr + ( vector_scale ( angles_toforward ( 0 ( ( local.j * 45 ) + ( local.r * 0.3 ) ) 0 ) ) local.r )
			local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.c + ( 0 0 48 ) )
			if( local.g == NIL ){ continue }
			local.dz = local.g[2] - local.ctr[2]
			if( local.dz < 0 ){ local.dz = 0 - local.dz }
			if( local.dz > 70 ){ continue }
			local.dg = waitthread flatDist local.g local.eye
			if( local.dg < local.lim ){ continue }
			local.h = waitthread cov local.g local.eye
			if( local.h != 1 && local.h != 2 ){ continue }
			if( waitthread crowded local.g local.a 80 ){ continue }
			if( waitthread tight local.g ){ continue }
			local.p = waitthread inFire local.g
			if( local.p != NIL ){ continue }
			local.s = local.r + ( vector_length( local.g - local.a.origin ) * 0.5 )
			if( local.h == 2 ){ local.s = local.s + 90 }
			if( local.s < local.bs ){ local.bs = local.s; local.best = local.g }
		}
		if( local.best != NIL && local.r >= 64 ){ break }
	}
}end local.best
''')
# ---------------------------------------------------------------- the rest: no resetleash anywhere
s = s.replace("\t\tlocal.a resetleash\n", "\t\twaitthread post local.a local.a.origin 200\n")
s = s.replace("\t\t\tlocal.a resetleash\n", "\t\t\twaitthread post local.a local.a.origin 200\n")
s = s.replace("\t\t\t\tlocal.a resetleash\n", "\t\t\t\twaitthread post local.a local.a.origin 200\n")
s = s.replace("\tlocal.a resetleash\n", "\twaitthread post local.a local.a.origin 200\n")
assert "resetleash\n" not in s.replace("Never `resetleash`", ""), [l for l in s.splitlines() if "resetleash" in l]
# mgHold: bursts whenever he has nobody in his own sight (not only when he has no enemy at all), and quicker for a bound
sub("""			if( local.own != 1 && local.lt != NIL ){
				if( ( level.time - level.coop_psqLastThrT[local.sid] ) < 12 ){""", """			if( local.sees != 1 && local.lt != NIL ){
				if( ( level.time - level.coop_psqLastThrT[local.sid] ) < 12 ){""")
sub("""			local.next = level.time + 2 + ( randomfloat 2.5 )
		}
		wait 0.25""", """			local.next = level.time + 2 + ( randomfloat 2.5 )
			// a bound is on (bound sets this): keep their heads down, burst on burst
			local.st = level.coop_psqSupT[local.sid]
			if( local.st != NIL ){
				if( level.time < local.st ){ local.next = level.time + 0.5 }
			}
		}
		wait 0.25""")
io.open(P, "w", encoding="latin-1", newline="").write(s)
print("ok", len(s.splitlines()), "lines")
