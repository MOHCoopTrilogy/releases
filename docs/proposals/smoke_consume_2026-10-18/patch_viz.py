import io
p="C:/mohaa-coop-dev/hzm-mod-smokec/coop_mod/officer.scr"
t=io.open(p,encoding="utf-8",newline="").read()
t=t.replace(chr(13)+chr(10),chr(10))
old='''	if( getcvar "coop_binoc_skyCheck" != "0" && (exec coop_mod/officer.scr::coop_hasOpenSky local.target) != 1 ){
		thread coop_radio_all "coop_radio_standby"
'''
new='''	if( getcvar "coop_binoc_skyCheck" != "0" && (exec coop_mod/officer.scr::coop_hasOpenSky local.target) != 1 ){
		//[bug-4012] under cover (a roof, a doorway): move the fire mission to the nearest open-sky point instead of denying it
		local.alt = exec coop_mod/officer.scr::coop_binoc_opensky local.target
		if( local.alt != NIL ){
			println( "^~^~^ BINOC retarget " + local.target + " -> " + local.alt )
			local.target = local.alt
			waitthread coop_mod/feed.scr::feed_player local.player 0 "strike_move" "Target is under cover - fire mission moved to the nearest open sky."
		}
	}
	if( getcvar "coop_binoc_skyCheck" != "0" && (exec coop_mod/officer.scr::coop_hasOpenSky local.target) != 1 ){
		thread coop_radio_all "coop_radio_standby"
'''
assert t.count(old)==1
t=t.replace(old,new)
fn='''// [bug-4012] Nearest point with open sky overhead, searched in rings (150..750 u, 8 directions) round a covered target, or NIL.
coop_binoc_opensky local.pos:{
	local.r = 150
	while( local.r <= 750 ){
		local.k = 0
		while( local.k < 8 ){
			local.d = angles_toforward ( 0 ( local.k * 45 ) 0 )
			local.q = local.pos + ( vector_scale local.d local.r )
			if( (exec coop_mod/officer.scr::coop_hasOpenSky local.q) == 1 ){
				local.g = exec coop_mod/officer.scr::coop_find_ground local.q
				if( local.g == NIL ){ local.g = local.q }
				if( (exec coop_mod/officer.scr::coop_hasOpenSky local.g) == 1 ){ end local.g }
			}
			local.k++
		}
		local.r = local.r + 150
	}
}end NIL

'''
anchor="// Returns a player the officer can SEE *and* who is OUTDOORS"
assert t.count(anchor)==1
t=t.replace(anchor,fn+anchor)
# bigger cache
old2='''		local.crate model "models/static/50cal_crate.tik"
		local.crate scale 1.5
'''
new2='''		local.crate model "models/static/50cal_crate.tik"
		local.crate scale 3.4
'''
assert t.count(old2)==1
t=t.replace(old2,new2)
t=t.replace('''		local.kit scale 0.8
		local.kit.origin = local.sp + (0 0 30)''','''		local.kit scale 2.2
		local.kit.origin = local.sp + (0 0 46)''')
t=t.replace('local.glow lightRadius 160','local.glow lightRadius 240')
io.open(p,"w",encoding="utf-8",newline="").write(t.replace(chr(10),chr(13)+chr(10)))
