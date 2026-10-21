import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
MOD = r"C:\mohaa-coop-dev\hzm-mod-objectives2"
f = F(MOD + r"\coop_mod\objx.scr")
if "ox_line_alloc" in f.b:
    print("already patched"); sys.exit(0)

# 1. when: near / after_id / delay
f.rep('''ox_arm local.i:{
	local.w = level.objx_when[local.i]
	local.arg = level.objx_arg[local.i]
	if( local.w == "trigger" ){
		local.t = $( local.arg )
		if( local.t == NULL || local.t == NIL ){
			waitthread ox_log ( "trigger " + local.arg + " is missing on " + level.coop_mapname + " - starting " + level.objx_id[local.i] + " now" )
		} else {
			local.t waittill trigger
		}
	}
	if( local.w == "after" ){
		local.j = waitthread ox_index local.arg
		while( local.j > 0 && level.objx_stat[local.j] != 3 ){ wait 0.5 }
	}
	waitthread ox_activate local.i
}end
''', '''ox_arm local.i:{
	local.w = level.objx_when[local.i]
	local.arg = level.objx_arg[local.i]
	if( local.w == "trigger" ){
		local.t = $( local.arg )
		if( local.t == NULL || local.t == NIL ){
			waitthread ox_log ( "trigger " + local.arg + " is missing on " + level.coop_mapname + " - starting " + level.objx_id[local.i] + " now" )
		} else {
			local.t waittill trigger
		}
	}
	if( local.w == "near" ){
		// the squad comes within level.objx_nr[i] of level.objx_npos[i] (any living player), or something else has forced the objective already
		while( level.objx_stat[local.i] == 1 ){
			local.cn = waitthread coop_mod/objx2.scr::ox2_near level.objx_npos[local.i] level.objx_nr[local.i]
			if( local.cn > 0 ){ break }
			wait 1
		}
	}
	if( local.w == "after" ){
		local.j = waitthread ox_index local.arg
		while( local.j > 0 && level.objx_stat[local.j] != 3 ){ wait 0.5 }
	}
	// an extra prerequisite: another objective must be done first (after_id), and an optional pause
	local.aid = level.objx_after[local.i]
	if( local.aid != NIL && local.aid != "" ){
		local.j2 = waitthread ox_index local.aid
		while( local.j2 > 0 && level.objx_stat[local.j2] != 3 && level.objx_stat[local.i] == 1 ){ wait 0.5 }
	}
	if( level.objx_delay[local.i] > 0 ){ wait level.objx_delay[local.i] }
	waitthread ox_activate local.i
}end


// the HUD side line (3..5) an objective will use: a line no RUNNING objective owns, preferring one never used, then the one used longest ago
ox_line_alloc local.i:{
	local.pick = 0
	local.pt = 999999
	for( local.ln = 3; local.ln <= 5; local.ln++ ){
		local.busy = 0
		for( local.j = 1; local.j <= level.objx_n; local.j++ ){
			if( local.j != local.i && level.objx_stat[local.j] == 2 && level.objx_line[local.j] == local.ln ){ local.busy = 1 }
		}
		if( local.busy == 1 ){ continue }
		local.lt = level.objx_lineUse[local.ln]
		if( local.lt == NIL ){ local.lt = 0 }
		if( local.lt < local.pt ){
			local.pt = local.lt
			local.pick = local.ln
		}
	}
	if( local.pick == 0 ){ local.pick = level.objx_line[local.i] }
	level.objx_line[local.i] = local.pick
	level.objx_lineUse[local.pick] = level.time
}end
''')

# 2. activate: line allocation + new types
f.rep('''	level.objx_stat[local.i] = 2
	level.objx_t0[local.i] = level.time
	level.objx_lastProg = level.time
	local.id = level.objx_id[local.i]
''', '''	level.objx_stat[local.i] = 2
	level.objx_t0[local.i] = level.time
	level.objx_lastProg = level.time
	waitthread ox_line_alloc local.i
	local.id = level.objx_id[local.i]
''')
f.rep('''	if( local.ty == "hold" ){ thread ox_hold_run local.i }
''', '''	if( local.ty == "hold" ){ thread ox_hold_run local.i }
	if( local.ty == "perform" ){ thread ox_hold_run local.i }
	if( local.ty == "charge" ){ thread coop_mod/objx2.scr::ox2_charge_run local.i }
''')

# 3. hold: performer hooks (spawn at start, clock pauses while he is down, finish before done)
f.rep('''	thread coop_mod/coop_counter.scr::counter_marker_start
	waitthread coop_mod/feed.scr::feed_all 1 "objx_hold_go" ( "Reach " + level.coop_czSelName + " and hold it" )
''', '''	thread coop_mod/coop_counter.scr::counter_marker_start
	if( level.objx_type[local.i] == "perform" ){ waitthread coop_mod/objx2.scr::ox2_perf_start local.i }
	waitthread coop_mod/feed.scr::feed_all 1 "objx_hold_go" ( "Reach " + level.coop_czSelName + " and hold it" )
''')
f.rep('''		local.inside = waitthread coop_mod/coop_counter.scr::counter_inside
		local.prev = local.state
		if( local.inside > 0 ){
''', '''		local.inside = waitthread coop_mod/coop_counter.scr::counter_inside
		local.prev = local.state
		local.pfok = 1
		if( level.objx_type[local.i] == "perform" && level.objx_pf_alive[local.i] != 1 ){ local.pfok = 0 }
		if( local.inside > 0 && local.pfok == 0 ){
			// the performer is down: the work (and so the clock) waits for his replacement
			local.emptyT = 0
			local.loseT = 0
			local.state = "paused"
		} else if( local.inside > 0 ){
''')
f.rep('''	waitthread ox_log ( "HOLD clock 0:00 elapsed=" + ( level.time - local.t0 ) + " waves=" + local.wave + " lost=" + local.lostN )
	waitthread ox_done local.i
''', '''	waitthread ox_log ( "HOLD clock 0:00 elapsed=" + ( level.time - local.t0 ) + " waves=" + local.wave + " lost=" + local.lostN )
	if( level.objx_type[local.i] == "perform" ){ thread coop_mod/objx2.scr::ox2_perf_finish local.i }
	waitthread ox_done local.i
''')

# 4. radios: hold-USE charge (replaces trigger_use + ox_plant), carry relief per radio
f.rep('''	// the charge option: a pulsing marker + a use trigger beside the set
	local.pulse = spawn script_model
	local.pulse model "models/items/pulse_explosive.tik"
	local.pulse.origin = local.pos + ( 0 0 4 )
	local.pulse notsolid
	local.pulse anim start
	local.tuse = spawn trigger_use
	local.tuse.origin = local.pos + ( 0 0 10 )
	local.tuse solid
	local.tuse setsize ( -30 -30 -10 ) ( 30 30 60 )
	thread ox_radio_charge local.i local.k local.tuse local.pos
''', '''	// the charge option: a pulsing marker + a hold-USE plant beside the set (objx2.scr::ox2_holduse, the HD hold ring)
	local.pulse = spawn script_model
	local.pulse model "models/items/pulse_explosive.tik"
	local.pulse.origin = local.pos + ( 0 0 4 )
	local.pulse notsolid
	local.pulse anim start
	thread coop_mod/objx2.scr::ox2_radio_charge local.i local.k local.pos
''')
f.rep('''	waitthread ox_radio_down local.i local.k local.pos "shot"
	if( local.pulse != NULL ){ local.pulse delete }
	if( local.tuse != NULL ){ local.tuse remove }
}end
''', '''	waitthread ox_radio_down local.i local.k local.pos "shot"
	if( local.pulse != NULL ){ local.pulse delete }
}end
''')
i0 = f.b.index("// planted charge on a set: use -> plant -> fuse -> the set goes up")
i1 = f.b.index("// one set silenced (by whichever path got there first)")
f.b = f.b[:i0] + f.b[i1:]
f.rep('''	if( level.objx_rd_dead[local.k] == 1 ){ end }
	level.objx_rd_dead[local.k] = 1
''', '''	if( level.objx_rd_dead[local.k] == 1 ){ end }
	level.objx_rd_dead[local.k] = 1
	level.objx_huStop["rd" + local.k] = 1
	thread coop_mod/carry.scr::carry_radio_down	//[objectives2] each silenced set slows the reinforcements of the next map (carry.scr relief, same-chapter rule)
''')
# the old plant routine is replaced by objx2.scr::ox2_holduse; drop it
i0 = f.b.index("// CHARGE: hold-in-reach plant")
i0 = f.b.rindex("//====", 0, i0)
i1 = f.b.index("// the blast + fire + smoke at a spot")
f.b = f.b[:i0] + f.b[i1:]
f.save()
