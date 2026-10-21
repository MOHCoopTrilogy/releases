import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
MOD = r"C:\mohaa-coop-dev\hzm-mod-objectives2"
f = F(MOD + r"\coop_mod\carry.scr")
if "carry_relief_set" in f.b:
    print("already patched"); sys.exit(0)

f.rep('''// factor on a wave GAP / cooldown: 1, 0.8 or 0.64
carry_gap:{
	if( level.coop_carryPen == 1 ){ end 0.8 }
	if( level.coop_carryPen == 2 ){ end 0.64 }
}end 1
''', '''// factor on a wave GAP / cooldown: 1, 0.8 or 0.64; with RELIEF (destroyed radio sets, net pen below 0) 1.25 or 1.5 - slower
carry_gap:{
	local.m1 = 0 - 1
	local.m2 = 0 - 2
	if( level.coop_carryPen == 1 ){ end 0.8 }
	if( level.coop_carryPen == 2 ){ end 0.64 }
	if( level.coop_carryPen == local.m1 ){ end 1.25 }
	if( level.coop_carryPen == local.m2 ){ end 1.5 }
}end 1
''')

f.rep('''carry_clear:{
	setcvar "coop_carryReinf" "0"
	setcvar "coop_carryFrom" ""
	setcvar "coop_carryPlace" ""
}end
''', '''// [objectives2 2026-10-20] RELIEF: radio sets destroyed on a map make the NEXT map of the same chapter lighter (the reverse of a lost zone).
//   coop_carryRelief <0-2>      steps carried (1 = one or two sets down, 2 = three or more); read + cleared by the next map's init
//   coop_carryReliefFrom <map>  the map the sets fell on (same chapter rule and same-map-reload rule as the penalty)
// While it applies the NET penalty (level.coop_carryPen = penalty - relief) is 0, -1 or -2: waves are that many men smaller (cap lower,
// officer MG chance lower) and the gaps between waves 25 / 50 percent longer. A lost zone and silenced radios on the same trip cancel.
carry_relief_set local.down:{
	if( ( waitthread carry_on ) != 1 ){ end }
	if( level.coop_mpRun == 1 ){ end }
	local.r = 0
	if( local.down >= 1 ){ local.r = 1 }
	if( local.down >= 3 ){ local.r = 2 }
	setcvar "coop_carryRelief" ( "" + local.r )
	setcvar "coop_carryReliefFrom" level.coop_mapname
	waitthread carry_log ( "relief set " + local.r + " (" + local.down + " radio sets down) from " + level.coop_mapname )
}end


// one more radio set silenced on this map
carry_radio_down:{
	if( level.coop_radiosDown == NIL ){ level.coop_radiosDown = 0 }
	level.coop_radiosDown++
	waitthread carry_relief_set level.coop_radiosDown
}end


carry_clear:{
	setcvar "coop_carryReinf" "0"
	setcvar "coop_carryFrom" ""
	setcvar "coop_carryPlace" ""
	setcvar "coop_carryRelief" "0"
	setcvar "coop_carryReliefFrom" ""
}end


// 1 when a state recorded on local.from still applies to THIS map: not a reload of that map, and the same mission (chapter)
carry_valid local.from:{
	if( local.from == "" ){ end 0 }
	if( local.from == level.coop_mapname ){ end 0 }
	local.cf = waitthread carry_chapter local.from
	local.cc = waitthread carry_chapter level.coop_mapname
	if( local.cf == "" || local.cf != local.cc ){ end 0 }
}end 1
''')

i = f.b.index("// every map: read + clear the state")
head = f.b[:i]
tail = '''// every map: read + clear the state, arm the penalty / relief for this map, announce it
carry_init:{
	if( level.coop_carryInit == 1 ){ end }
	level.coop_carryInit = 1
	level.coop_carryPen = 0
	local.n = 0
	if( getcvar( "coop_carryReinf" ) != "" ){ local.n = int( getcvar( "coop_carryReinf" ) ) }
	local.r = 0
	if( getcvar( "coop_carryRelief" ) != "" ){ local.r = int( getcvar( "coop_carryRelief" ) ) }
	if( local.n < 1 && local.r < 1 ){ end }
	if( level.coop_mpRun == 1 ){ end }
	if( level.coop_lobbyMap == 1 ){ end }
	if( waitthread coop_mod/main.scr::containsText level.coop_mapname "briefing" 0 ){ end }
	if( waitthread coop_mod/main.scr::containsText level.coop_mapname "lobby" 0 ){ end }
	if( ( waitthread carry_on ) != 1 ){
		waitthread carry_clear
		end
	}
	// each state is judged on its own: a clean restart of the SAME mission is not progress; only levels of the SAME mission inherit it
	if( local.n > 0 && ( waitthread carry_valid ( getcvar( "coop_carryFrom" ) ) ) != 1 ){
		waitthread carry_log ( "penalty cleared: " + getcvar( "coop_carryFrom" ) + " -> " + level.coop_mapname + " is a reload or a chapter boundary" )
		setcvar "coop_carryReinf" "0"
		setcvar "coop_carryFrom" ""
		setcvar "coop_carryPlace" ""
		local.n = 0
	}
	if( local.r > 0 && ( waitthread carry_valid ( getcvar( "coop_carryReliefFrom" ) ) ) != 1 ){
		waitthread carry_log ( "relief cleared: " + getcvar( "coop_carryReliefFrom" ) + " -> " + level.coop_mapname + " is a reload or a chapter boundary" )
		setcvar "coop_carryRelief" "0"
		setcvar "coop_carryReliefFrom" ""
		local.r = 0
	}
	if( local.n < 1 && local.r < 1 ){ end }
	// stealth / disguise maps: the map scripts set their flags a little after main.scr::main - look again, and carry the state on
	wait 3
	if( level.coop_stealthMap == 1 || level.coop_enableDisguises ){
		waitthread carry_log ( "carried past stealth map " + level.coop_mapname )
		end
	}
	local.place = getcvar( "coop_carryPlace" )
	waitthread carry_clear
	level.coop_carryPen = local.n - local.r
	waitthread carry_log ( "ACTIVE pen=" + level.coop_carryPen + " (losses " + local.n + " relief " + local.r + ") on " + level.coop_mapname + " (state cleared)" )
	// the message, once the squad is in
	local.w = 0
	while( ( waitthread coop_mod/coop_counter.scr::counter_players ) < 1 && local.w < 40 ){
		wait 1
		local.w++
	}
	wait 4
	if( level.coop_carryPen > 0 ){
		local.msg = "The Germans regrouped after you lost " + local.place + " - expect heavier resistance"
		if( level.coop_carryPen >= 2 ){ local.msg = "The Germans regrouped again after you lost " + local.place + " twice - expect much heavier resistance" }
		waitthread coop_mod/feed.scr::feed_all 0 "carry" local.msg
		waitthread carry_log ( "message sent: " + local.msg )
		if( ( waitthread carry_alarm_ok level.coop_mapname ) == 1 ){ thread carry_alarm }
	}
	if( level.coop_carryPen < 0 ){
		local.msg = "The radio sets you silenced are slowing the German reinforcements"
		if( local.r >= 2 ){ local.msg = "The radio sets you silenced have cut the German reinforcements off - they will arrive slowly and in small groups" }
		waitthread coop_mod/feed.scr::feed_all 0 "carry" local.msg
		waitthread carry_log ( "message sent: " + local.msg )
	}
}end
'''
f.b = head + f.cv(tail)
f.save()
