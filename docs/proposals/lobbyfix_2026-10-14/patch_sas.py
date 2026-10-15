import sys
p = r'C:\mohaa-coop-dev\hzm-mod-lobbyfix\maps\m1l2a.scr'
s = open(p, encoding='utf-8', newline='').read()

def rep(old, new):
    global s
    old = old.replace('\n', '\r\n'); new = new.replace('\n', '\r\n')
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)

# 1. start the failsafe thread
rep("""	if( level.gametype != 0 ){ thread coop_grilloLeadKeeper }""",
"""	if( level.gametype != 0 ){ thread coop_sasGateFailsafe }	//bug-3916 - SAS stuck short of the gate/flak: re-issue, warp, then let the charge be used without him
	if( level.gametype != 0 ){ thread coop_grilloLeadKeeper }""")

# 2. blowdoor / blowflak honour the bypass
rep("""			if (vector_length(self.origin - level.friendly1.origin) > 900){ //[202][hotfix] Smithy - increase radius - original: 270""",
"""			if (level.coop_gateNoSas != 1 && vector_length(self.origin - level.friendly1.origin) > 900){ //[202][hotfix] Smithy - increase radius - original: 270 //bug-3916 bypass""")
rep("""	if (vector_length(self.origin - level.friendly1.origin) > 659){ //[202][hotfix] Smithy - increase radius - original: 650""",
"""	if (level.coop_flakNoSas != 1 && vector_length(self.origin - level.friendly1.origin) > 659){ //[202][hotfix] Smithy - increase radius - original: 650 //bug-3916 bypass""")
rep("""	if (level.friendly1.thinkstate == "attack"){
		waitthread coop_printHintMessage local.player "Grillo needs to be outside of combat to blow up the flak" //[202][hotfix] Smithy""",
"""	if (level.coop_flakNoSas != 1 && level.friendly1.thinkstate == "attack"){
		waitthread coop_printHintMessage local.player "Grillo needs to be outside of combat to blow up the flak" //[202][hotfix] Smithy""")

# 3. the failsafe itself, before coop_grilloLeadKeeper's header comment
marker = "//[coop] chrissstrahl/coop - keep Grillo leading through the officer fight"
new = """//bug-3916 - SAS agent stuck short of the gate / flak = soft-lock (the charge needs him in range)
//=========================================================================
// While players stand at the current charge site (gate, then flak) and Grillo is far from it
// and not closing the gap: stage 1 re-issues his move (coop_forceGrilloToFollow, as friendchoice
// does), stage 2 warps him to a friendly node near the site that no player can see, stage 3
// (still not there) lets the charge be used without him (level.coop_gateNoSas / coop_flakNoSas,
// read by blowdoor / blowflak). Does nothing while he is progressing or fighting.
// Dev: coop_sasfs_fast 1 = 3/6/9 s timers; coop_sasfs_test 1 = ignore flags + player proximity.
//=========================================================================
coop_sasGateFailsafe:{
//=========================================================================
	local.t1 = 20
	local.t2 = 40
	local.t3 = 60
	local.test = 0
	if( getcvar("coop_sasfs_fast") == "1" ){ local.t1 = 3; local.t2 = 6; local.t3 = 9 }
	if( getcvar("coop_sasfs_test") == "1" ){ local.test = 1 }
	local.t = 0
	local.best = 999999
	local.site = 0
	while( 1 ){
		wait 1
		if( level.flags["flagthread9"] ){ end }		// finale scene running -- hands off
		if( level.friendly1 == NULL || !(isalive level.friendly1) ){ local.t = 0; continue }

		// which charge site is live?
		local.which = 0
		if( local.test == 1 ){
			local.which = 100
		} else if( level.flags[explosives] == 1 ){
			if( level.flags[door] == 0 ){ local.which = 100 }
			else if( level.flags[door] == 2 && level.flags[flak] == 0 ){ local.which = 101 }
		}
		if( local.which == 0 ){ local.t = 0; local.best = 999999; continue }
		if( local.which == 100 ){ local.sitepos = $explosives100.origin } else { local.sitepos = $flak88b.origin }
		if( local.which != local.site ){ local.site = local.which; local.t = 0; local.best = 999999 }

		// bypass already granted for this site
		if( local.which == 100 && level.coop_gateNoSas == 1 ){ continue }
		if( local.which == 101 && level.coop_flakNoSas == 1 ){ continue }

		// is a living player at the site?
		local.atsite = local.test
		local.pl = NULL
		for( local.i = 1; local.i <= $player.size; local.i++ ){
			local.p = $player[local.i]
			if( local.p != NULL && isalive local.p && local.p.isSpectator != 1 ){
				if( vector_length( local.p.origin - local.sitepos ) < 800 ){ local.atsite = 1; local.pl = local.p }
				if( local.pl == NULL && local.test == 1 ){ local.pl = local.p }
			}
		}
		local.dist = vector_length( level.friendly1.origin - local.sitepos )
		if( local.atsite != 1 || local.dist < 600 || level.friendly1.thinkstate == "attack" ){ local.t = 0; local.best = 999999; continue }

		// progress = at least 60u closer than his best so far
		if( local.dist < local.best - 60 ){ local.best = local.dist; local.t = 0; continue }
		local.t++

		if( local.t == local.t1 ){
			println "^~^~^ sasfs stage1 re-issue move dist=" local.dist " site=" local.which
			if( local.pl != NULL ){ thread coop_forceGrilloToFollow local.pl 3 }
		}
		if( local.t == local.t2 ){
			if( level.thread["coop_forceGrilloToFollow"] ){ level.thread["coop_forceGrilloToFollow"] delete }
			level.thread["coop_forceGrilloToFollow"] = NULL
			level.friendly1 runto NULL
			local.node = waitthread coop_sasFsPickNode local.sitepos
			if( local.node != NULL ){
				println "^~^~^ sasfs stage2 warp to node set=" local.node.set " site=" local.which
				level.friendly1.origin = local.node.origin
				local.best = vector_length( local.node.origin - local.sitepos )
			} else {
				println "^~^~^ sasfs stage2 no hidden node"
			}
			level.friendly1.friendtype = 4
		}
		if( local.t >= local.t3 ){
			println "^~^~^ sasfs stage3 bypass site=" local.which
			if( local.which == 100 ){ level.coop_gateNoSas = 1 } else { level.coop_flakNoSas = 1 }
			iprintlnbold_noloc "Grillo is held up - you can set the charge without him."
			local.t = 0
		}
	}
}end

// nearest friendly node to the site (within 500u) that is >= 350u from every player and not in a player's line of sight
//=========================================================================
coop_sasFsPickNode local.sitepos:{
//=========================================================================
	local.bestnode = NULL
	local.bestd = 500
	for( local.i = 1; local.i < level.friendlynodes + 1; local.i++ ){
		local.n = level.friendlynode[local.i]
		local.d = vector_length( local.n.origin - local.sitepos )
		if( local.d < local.bestd ){
			local.ok = 1
			for( local.j = 1; local.j <= $player.size; local.j++ ){
				local.p = $player[local.j]
				if( local.p != NULL && isalive local.p ){
					if( vector_length( local.p.origin - local.n.origin ) < 350 ){ local.ok = 0 }
					else {
						local.tr = traced ( local.p.origin + ( 0 0 60 ) ) ( local.n.origin + ( 0 0 40 ) ) 0 ( 0 0 0 ) ( 0 0 0 ) 1
						if( local.tr["fraction"] >= 1.0 ){ local.ok = 0 }
					}
				}
			}
			if( local.ok == 1 ){ local.bestnode = local.n; local.bestd = local.d }
		}
	}
}end local.bestnode

"""
rep(marker, new + marker)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
