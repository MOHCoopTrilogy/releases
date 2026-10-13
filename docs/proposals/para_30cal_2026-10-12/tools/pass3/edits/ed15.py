"""ed15.py - (a) parasquad.scr: the gun does not pack up for 'enemy masked / out of arc' while it is doing work (it
fired within the last 20s), and waits 25s instead of 15 (m4l3: five set-ups in 110s, each left 12s after its last
burst); (b) paradrop.scr: the medic is only 'stuck' when he has no path to a squad mate either (m4l3: the test's
player was 5700u away with no path between; the medic stood with the squad and was teleported)."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""	if( local.bad == "" ){
		local.a.coop_psqMgBad = 0
		end "stay"
	}
	local.a.coop_psqMgBad++
	if( local.a.coop_psqMgBad >= 15 ){ end local.bad }""", """	if( local.bad == "" ){
		local.a.coop_psqMgBad = 0
		end "stay"
	}
	// (a gun that has fired in the last 20s is doing its work where it is: the squad's NEAREST enemy can be masked
	// from it while it keeps another one's head down)
	if( local.a.coop_psqMgFireT != NIL ){
		if( ( level.time - local.a.coop_psqMgFireT ) < 20 ){
			local.a.coop_psqMgBad = 0
			end "stay"
		}
	}
	local.a.coop_psqMgBad++
	if( local.a.coop_psqMgBad >= 25 ){ end local.bad }""")
E.sub("""		if( local.sees == 1 ){ local.lastSee = level.time }""", """		if( local.sees == 1 ){
			local.lastSee = level.time
			local.a.coop_psqMgFireT = level.time
		}""")
E.sub("""						local.gun startFiring
						waitthread dbg ( "mg suppress at=" """, """						local.gun startFiring
						local.a.coop_psqMgFireT = level.time
						waitthread dbg ( "mg suppress at=" """)
E.sub("""// moves on, when the support is gone, or when the enemy has been out of his arc or masked for 15s
// (the next search then re-sites him).""", """// moves on, when the support is gone, or when the enemy has been out of his arc or masked for 25s
// and the gun has not fired for 20 (the next search then re-sites him).""")
E.save()

E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/paradrop.scr")
E.sub("""				if( local.actor.pathdist == 0 ){ local.stuck = local.stuck + 1 } else { local.stuck = 0 }""", """				local.np2 = 0
				if( local.actor.pathdist > 0 ){ local.np2 = 1 }
				// ...and no path to a squad mate either (with one, he is with his squad: he stays)
				for( local.si = 1; local.si <= 4; local.si++ ){
					if( local.np2 == 1 ){ break }
					local.sm = level.coop_paradrop_squad[local.si]
					if( local.sm == NIL || local.sm == NULL ){ continue }
					if( !isAlive local.sm ){ continue }
					if( vector_length( local.sm.origin - local.actor.origin ) < 400 ){ local.np2 = 1; break }
					local.actor runto local.sm.origin
					wait 0.3
					if( local.actor == NULL ){ end }
					if( local.actor.pathdist > 0 ){ local.np2 = 1 }
				}
				if( local.np2 == 0 ){ local.stuck = local.stuck + 1 } else { local.stuck = 0 }""")
E.save()
