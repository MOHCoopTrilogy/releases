"""ed1.py - third pass, first edits of coop_mod/parasquad.scr (the .30 cal proof gaps):
 - the planner owns its man from the start (a bound / room-clearing order started during the search pulled him off)
 - the gun rests LEVEL when nobody aims it (ThinkIdle tipped it barrel-up during the 0.3s set-down and nothing levelled
   it again: the grips sank 10u below the crouched gunner's hands), pitch held to +-20 degrees
 - mgHold: with no enemy in his sight for 9s he WATCHES - the gun level down his arc - instead of the engine's default
   position, whose pitch follows client 0 (TurretGun::AI_MoveToDefaultPosition)
 - room clearing: the man with the gun on his back goes in last"""
import io, sys
P = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr"
s = io.open(P, encoding="latin-1", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def sub(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)


sub("""	if( level.coop_psqPlanBusy == 1 ){ end 0 }
	level.coop_psqPlanBusy = 1
	local.t0 = level.time
""", """	if( level.coop_psqPlanBusy == 1 ){ end 0 }
	level.coop_psqPlanBusy = 1
	// he is the planner's from here on: the brain gives a busy man no order. (A bound or a room-clearing order
	// that started during the search took him off the walk-up - 2026-10-12, m3l2: "mg walk how=2 left=42 ok=0".)
	local.a.coop_psqBusy = 1
	local.t0 = level.time
""")
sub("""	local.gun aibulletspread 300 300
	local.gun maxYawOffset local.a.coop_psqMgArc
""", """	local.gun aibulletspread 300 300
	local.gun maxYawOffset local.a.coop_psqMgArc
	// level when nobody aims it. The engine lets an unmanned gun tip back to maxIdlePitch (-80 = barrel up,
	// TurretGun::ThinkIdle); in the 0.3s of the set-down it tipped 13 degrees and, with no enemy, nothing ever
	// levelled it: the grips sank 10u under the hands of a crouched gunner. 0 = it rests level, manned or left.
	local.gun maxIdlePitch 0
	local.gun pitchCaps ( -20 20 0 )
""")
# mgHold: the watch
sub("""	local.held = 0
	local.next = level.time + 2
	local.tgt = spawn script_origin
""", """	local.held = 0
	local.next = level.time + 2
	local.tgt = spawn script_origin
	local.watch = 0
	local.lastSee = level.time - 100
""")
sub("""			local.gun targettype "none"
			local.gun stopFiring
			local.gun clearAimTarget
			local.held = 1
			waitthread dbg "mg hold fire=friend_in_front"
		}
		if( local.blk != 1 && local.held == 1 ){
			local.gun targettype "auto"
			local.held = 0
			local.next = level.time + 1
			waitthread dbg "mg hold fire=clear"
		}""", """			local.gun targettype "none"
			local.gun stopFiring
			local.gun clearAimTarget
			local.held = 1
			local.watch = 0
			waitthread dbg "mg hold fire=friend_in_front"
		}
		if( local.blk != 1 && local.held == 1 ){
			local.gun targettype "auto"
			local.held = 0
			local.next = level.time + 1
			waitthread dbg "mg hold fire=clear"
		}""")
sub("""		if( local.held != 1 && local.own == 1 ){
			// a target of his own in sight: the turret's burst cycle is firing about 58% of the time
			if( local.a cansee local.e ){ local.a.coop_psqMgFired = local.a.coop_psqMgFired + 1.6 }
		}
""", """		local.sees = 0
		if( local.own == 1 ){
			if( local.a cansee local.e ){ local.sees = 1 }
		}
		if( local.sees == 1 ){ local.lastSee = level.time }
		if( local.held != 1 && local.sees == 1 ){
			// a target of his own in sight: the turret's own cycle tracks and fires (about 58% of the time)
			if( local.watch == 1 ){
				local.gun clearAimTarget
				local.gun targettype "auto"
				local.watch = 0
				waitthread dbg "mg track"
			}
			local.a.coop_psqMgFired = local.a.coop_psqMgFired + 1.6
		}
		if( local.held != 1 && local.watch != 1 && ( level.time - local.lastSee ) > 9 ){
			// nobody in his sight for 9s (the turret has fired its 5s at where he lost him and waited its 3):
			// he WATCHES - the gun level, down the middle of his arc. Left to itself the engine now turns the gun
			// to a "default position" whose pitch points at the first player, wherever he is
			// (TurretGun::AI_MoveToDefaultPosition), and the grips leave the gunner's hands.
			local.wp = local.gun.origin + ( vector_scale ( angles_toforward ( 0 local.a.coop_psqMgYaw 0 ) ) 600 )
			local.tgt.origin = local.wp
			local.gun targettype "none"
			local.gun stopFiring
			local.gun setAimTarget local.tgt
			local.watch = 1
			waitthread dbg "mg watch"
		}
""")
sub("""						if( local.gun == NULL ){ break }
						local.gun stopFiring
						local.gun clearAimTarget
						local.gun targettype "auto"
					}""", """						if( local.gun == NULL ){ break }
						// the burst is over: he keeps the gun on that place (the watch), until he sees a man himself
						local.gun stopFiring
						local.watch = 1
					}""")
sub("""	if( local.gun != NULL && local.held == 1 ){ local.gun targettype "auto" }
}end""", """	if( local.gun != NULL ){
		if( local.held == 1 || local.watch == 1 ){
			local.gun stopFiring
			local.gun clearAimTarget
			local.gun targettype "auto"
		}
	}
}end""")
# room clearing: the gunner last
sub("""	// entry pair: Thompson and Garand first, then the others (the gunner last)
	local.ord[1] = 2
	local.ord[2] = 3
	local.ord[3] = 4
	local.ord[4] = 1""", """	// entry pair: the Thompson and the BAR first; the man with the .30 cal on his back and the sniper last
	local.ord[1] = 2
	local.ord[2] = 1
	local.ord[3] = 3
	local.ord[4] = 4""")
io.open(P, "w", encoding="latin-1", newline="").write(s.replace("\n", nl))
print("ok", len(s.splitlines()), "lines", repr(nl))
