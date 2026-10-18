import io
p = "C:/mohaa-coop-dev/hzm-mod-smokec/coop_mod/officer.scr"
t = io.open(p, encoding="utf-8", newline="").read()
t = t.replace(chr(13) + chr(10), chr(10))

old = """	local.sp = exec coop_mod/officer.scr::coop_reward_validate local.dead_pos
	if( local.sp == NIL ){ local.sp = local.dead_pos }
	local.trig = spawn trigger_multiple
	if( local.trig == NULL ){ end }	// entity pool exhausted
	local.trig.origin = local.sp
	local.trig setsize ( -56 -56 0) (56 56 72)
	local.crate = spawn script_model
	if( local.crate != NULL ){
		local.crate model "models/static/50cal_crate.tik"
		local.crate scale 3.4
		local.crate.origin = local.sp
		local.crate notsolid
	}
	local.kit = spawn script_model
	if( local.kit != NULL ){
		local.kit model "models/items/item_50_healthbox.tik"
		local.kit scale 2.2
		local.kit.origin = local.sp + (0 0 46)
		local.kit notsolid
		local.kit rendereffects "+fullbright"
	}
"""
new = """	local.sp = exec coop_mod/officer.scr::coop_reward_validate local.dead_pos
	if( local.sp == NIL ){ local.sp = local.dead_pos }
	local.sp = exec coop_mod/officer.scr::coop_cache_clearspot local.sp
	local.trig = spawn trigger_multiple
	if( local.trig == NULL ){ end }	// entity pool exhausted
	local.trig.origin = local.sp
	local.trig setsize ( -56 -56 0) (56 56 72)
	local.top = 40
	local.crate = spawn script_model
	if( local.crate != NULL ){
		local.crate model "models/static/50cal_crate.tik"
		local.m0 = local.crate.maxs
		local.crate scale 3.4
		local.crate.origin = local.sp
		local.crate notsolid
		// the lid = the crate's real top: its bounds maxs z (scaled: if the engine did not rescale the bounds, scale them here)
		local.m1 = local.crate.maxs
		local.top = local.m1[2]
		if( local.top == local.m0[2] ){ local.top = local.m0[2] * 3.4 }
		println( "^~^~^ INDOOR_CACHE crate maxs before=" + local.m0 + " after=" + local.m1 + " top=" + local.top )
	}
	local.kit = spawn script_model
	if( local.kit != NULL ){
		local.kit model "models/items/item_50_healthbox.tik"
		local.k0 = local.kit.mins
		local.kit scale 2.2
		local.k1 = local.kit.mins
		local.kb = local.k1[2]
		if( local.kb == local.k0[2] ){ local.kb = local.k0[2] * 2.2 }
		// seat the kit's underside (its bounds mins z) on the lid
		local.kz = local.top - local.kb
		local.kit.origin = local.sp + ( 0 0 local.kz )
		local.kit notsolid
		local.kit rendereffects "+fullbright"
		println( "^~^~^ INDOOR_CACHE kit mins before=" + local.k0 + " after=" + local.k1 + " baseOffset=" + local.kb )
	}
"""
assert t.count(old) == 1
t = t.replace(old, new)

fn = """// Nearest clear floor spot for the cache: rings of 8 directions (0..360 u) round the drop point, each candidate must pass the
// reward drop's own ground + headroom rule (coop_reward_validate) and a crate-sized box trace must not touch a wall / rail.
coop_cache_clearspot local.sp:{
	local.r = 0
	while( local.r <= 360 ){
		local.k = 0
		while( local.k < 8 ){
			local.d = angles_toforward ( 0 ( local.k * 45 ) 0 )
			local.q = local.sp + ( vector_scale local.d local.r )
			local.v = exec coop_mod/officer.scr::coop_reward_validate local.q
			if( local.v != NIL ){
				local.a = local.v + ( 0 0 6 )
				local.b = local.v + ( 0 0 7 )
				local.tr = traced ( local.a ) ( local.b ) 0 ( -62 -62 0 ) ( 62 62 100 )
				if( local.tr["startSolid"] != 1 && local.tr["allSolid"] != 1 && local.tr["fraction"] >= 1.0 ){
					if( local.r > 0 ){ println( "^~^~^ INDOOR_CACHE nudged " + local.sp + " -> " + local.v ) }
					end local.v
				}
			}
			if( local.r == 0 ){ break }
			local.k++
		}
		if( local.r == 0 ){ local.r = 60 } else { local.r = local.r + 60 }
	}
	println( "^~^~^ INDOOR_CACHE no clear spot, kept " + local.sp )
}end local.sp

"""
anchor = "indoorReward local.dead_pos:{"
i = t.index(anchor)
# keep the comment block above indoorReward attached: insert the new function before that comment block
j = t.rindex("// === INDOOR REWARD", 0, i)
t = t[:j] + fn + t[j:]
io.open(p, "w", encoding="utf-8", newline="").write(t.replace(chr(10), chr(13) + chr(10)))
print("ok")
