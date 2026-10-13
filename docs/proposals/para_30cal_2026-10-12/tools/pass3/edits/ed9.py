"""ed9.py - paradrop.scr: (a) the medic's 'stuck' test orders him to the player first and counts only a move order the
engine found no path for (he was 'stuck' whenever the player was more than 2000u away: his own loop gives no order
then, so pathdist read 0); (b) landing points when the smoke itself is off the path network (a room with no
pathnodes): two candidates with a path between them are on the network; ground looked for down to 320u under the
smoke's."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/paradrop.scr")
E.sub("""			if( local.nd > 700 && local.actor.thinkstate != "attack" && local.nd >= ( local.last_nd - 64 ) && local.actor.pathdist == 0 ){
				local.stuck = local.stuck + 1
			} else {
				local.stuck = 0
			}""", """			if( local.nd > 700 && local.actor.thinkstate != "attack" && local.nd >= ( local.last_nd - 64 ) ){
				// far, idle and not closing: he is ORDERED to the player (his own loop only follows inside 2000u),
				// and only an order the engine finds no path for counts
				local.actor.movedoneradius = 256
				local.actor runto local.np.origin
				wait 0.3
				if( local.actor == NULL ){ end }
				if( local.actor.pathdist == 0 ){ local.stuck = local.stuck + 1 } else { local.stuck = 0 }
			} else {
				local.stuck = 0
			}""")
E.sub("""			if( local.ok != 1 ){ continue }
			local.n++""", """			if( local.ok != 1 ){
				// neither the smoke nor the caller can be reached from here - or they are themselves off the network
				// (a room with no pathnodes). Two points with a path between them ARE on it: the first such point
				// is kept as the seed, and a later one that reaches it is taken together with it.
				if( local.seed == NIL ){
					local.seed = local.g
					continue
				}
				local.sc runto local.seed
				wait 0.3
				if( local.sc == NULL ){ end }
				if( local.sc.pathdist <= 0 ){ continue }
				if( local.seedIn != 1 ){
					local.seedIn = 1
					local.n++
					local.pt[local.n] = local.seed
					local.wk = local.who[local.n]
					level.coop_paraLz[local.sid][local.wk] = local.seed
					level.coop_paraLzN[local.sid] = local.n
					if( local.n >= 5 ){ break }
				}
			}
			local.n++""")
E.sub("""	local.e[2] = local.ref[2] - 200
	local.tr = traced local.s local.e 1023 ( 0 0 0 ) ( 0 0 0 ) 1""", """	local.e[2] = local.ref[2] - 320
	local.tr = traced local.s local.e 1023 ( 0 0 0 ) ( 0 0 0 ) 1""")
E.sub("""//   - ground at the squad's level: looked for from 100u over the smoke's ground down to 200u under it - a roof""",
      """//   - ground at the squad's level: looked for from 100u over the smoke's ground down to 320u under it - a roof""")
E.save()
