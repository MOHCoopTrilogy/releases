"""One-off patcher for the smoke-consume / one-reward / indoor-cache change (mod worktree hzm-mod-smokec)."""
import io, sys
MOD = "C:/mohaa-coop-dev/hzm-mod-smokec/"


def rd(p):
    return io.open(MOD + p, "r", encoding="utf-8", newline="").read()


def wr(p, t):
    io.open(MOD + p, "w", encoding="utf-8", newline="").write(t)


def sub(t, old, new, count=1):
    n = t.count(old)
    if n != count:
        raise SystemExit("expected %d of %r, found %d" % (count, old[:70], n))
    return t.replace(old, new)


def nl(t, s):
    return s.replace("\n", "\r\n") if "\r\n" in t else s


# ---------------------------------------------------------------- officer.scr
t = rd("coop_mod/officer.scr")

# 1. coin flip + indoor
old = nl(t, """	local.do_binoc = 1
	if( level.coop_feature_binoc == 0 ){ local.do_binoc = 0 }

""")
new = nl(t, """	local.do_binoc = 1
	if( level.coop_feature_binoc == 0 ){ local.do_binoc = 0 }

	//[bug-4005 rewards] ONE reward per officer, never both: a coin flip between the binoculars (airstrike) and the
	//signal smoke (paradrop). A map with one of them switched off simply drops the other. A fully INDOOR map (no
	//usable sky for either - coop_mod/indoor_maps.scr, generated from the BSPs) drops neither: it gets the
	//indoorReward instead (one function, so the item can be swapped later).
	local.indoor = exec coop_mod/indoor_maps.scr::isIndoor level.coop_mapname
	local.pick = "none"
	if( local.indoor == 1 ){
		local.do_para = 0
		local.do_binoc = 0
		local.pick = "indoor"
	} else if( local.do_para == 1 && local.do_binoc == 1 ){
		local.coin = ( randomint 2 )
		if( local.coin == 0 ){
			local.do_binoc = 0
			local.pick = "smoke"
		} else {
			local.do_para = 0
			local.pick = "binoc"
		}
	} else if( local.do_para == 1 ){
		local.pick = "smoke"
	} else if( local.do_binoc == 1 ){
		local.pick = "binoc"
	}
	println( "^~^~^ OFFICER_DROP map=" + level.coop_mapname + " indoor=" + local.indoor + " pick=" + local.pick )
	if( local.indoor == 1 ){
		thread indoorReward local.dead_pos
		end
	}

""")
t = sub(t, old, new)

# 2. indoorReward + cache, inserted before the smoke pickup callback comment block header
anchor = nl(t, """// Fired when a player presses Use on the smoke pickup trigger (trigger_use, like the binoculars).""")
cache = nl(t, """// === INDOOR REWARD: AMMO + HEALTH CACHE [bug-4005] ===
// What an officer drops on a map with no usable sky (indoor_maps.scr). One crate (the ammo box's 50cal crate) with the
// medkit model on top, a walk-over trigger. EACH player can use it ONCE: full ammo for every pool, health to full.
// A second walk-over by the same player is refused (feed line, throttled). Keyed by entnum like the ammo box.
indoorReward local.dead_pos:{
	local.sp = exec coop_mod/officer.scr::coop_reward_validate local.dead_pos
	if( local.sp == NIL ){ local.sp = local.dead_pos }
	local.trig = spawn trigger_multiple
	if( local.trig == NULL ){ end }	// entity pool exhausted
	local.trig.origin = local.sp
	local.trig setsize ( -56 -56 0) (56 56 72)
	local.crate = spawn script_model
	if( local.crate != NULL ){
		local.crate model "models/static/50cal_crate.tik"
		local.crate scale 1.5
		local.crate.origin = local.sp
		local.crate notsolid
	}
	local.kit = spawn script_model
	if( local.kit != NULL ){
		local.kit model "models/items/item_50_healthbox.tik"
		local.kit scale 0.8
		local.kit.origin = local.sp + (0 0 30)
		local.kit notsolid
		local.kit rendereffects "+fullbright"
	}
	local.glow = spawn script_model
	if( local.glow != NULL ){
		local.glow model "models/fx/dummy.tik"
		local.glow.origin = local.sp + (0 0 12)
		local.glow light (0.3 1 0.4)
		local.glow lightRadius 160
		local.glow lightOn
		local.glow notsolid
	}
	level.coop_cacheTrig = local.trig
	println( "^~^~^ INDOOR_CACHE spawn pos=" + local.sp )
	waitthread coop_mod/feed.scr::feed_all 1 "off_cache" "The Officer dropped an Ammo and Health Cache - everyone can use it once"
	waitthread coop_mod/feed.scr::feed_hint_all "cache" "Ammo and Health Cache: walk over it once for full ammo and full health"
	thread coop_cache_wait local.trig
}end

coop_cache_wait local.trig:{
	while( local.trig != NULL ){
		local.trig waittill trigger
		local.who = parm.other
		if( local.who == NULL ){ continue }
		if( local.who.classname != "Player" ){ continue }
		if( !isAlive local.who ){ continue }
		if( local.who.flags["coop_dbno_active"] == 1 ){ continue }
		waitthread coop_cache_use local.who
	}
}end

// One use per player. Returns 1 if it served the player, 0 if refused.
coop_cache_use local.player:{
	if( local.player == NULL ){ end 0 }
	local.key = local.player.entnum
	if( level.coop_cacheUsed[local.key] == 1 ){
		// refused - but do not spam the feed while he stands on it
		if( local.player.flags["coop_cacheNag"] == NIL || ( level.time - local.player.flags["coop_cacheNag"] ) > 4 ){
			local.player.flags["coop_cacheNag"] = level.time
			waitthread coop_mod/feed.scr::feed_player local.player 2 "cache" "You already used the Ammo and Health Cache"
		}
		println( "^~^~^ INDOOR_CACHE refused p=" + local.player.netname + " (already used)" )
		end 0
	}
	level.coop_cacheUsed[local.key] = 1
	waitthread coop_cache_restock local.player
	waitthread coop_cache_heal local.player
	waitthread coop_mod/feed.scr::feed_player local.player 2 "cache" "Ammo and health restored"
	local.ar = local.player getammo rifle
	local.as = local.player getammo smg
	local.ap = local.player getammo pistol
	println( "^~^~^ INDOOR_CACHE used p=" + local.player.netname + " hp=" + local.player.health + " rifle=" + local.ar + " smg=" + local.as + " pistol=" + local.ap )
}end 1

// Full ammo for every pool. ammo ADDS and the engine clamps each pool to its own maximum (Ammo::setAmount), so a big
// add fills it; the table below only guards a pool that has no engine maximum.
coop_cache_restock local.player:{
	local.t[1] = "pistol"
	local.t[2] = "rifle"
	local.t[3] = "smg"
	local.t[4] = "mg"
	local.t[5] = "heavy"
	local.t[6] = "grenade"
	local.t[7] = "shotgun"
	local.cap[1] = 90
	local.cap[2] = 100
	local.cap[3] = 300
	local.cap[4] = 400
	local.cap[5] = 8
	local.cap[6] = 6
	local.cap[7] = 48
	local.i = 1
	while( local.i <= 7 ){
		local.ty = local.t[local.i]
		local.player ammo local.ty 999
		local.have = local.player getammo local.ty
		local.mx = local.cap[local.i]
		if( local.have > local.mx ){ local.player setammo local.ty local.mx }
		local.i++
	}
}end

// Health to the coop maximum. healthonly (not health): health also rewrites max_health (bug-1243).
coop_cache_heal local.player:{
	local.hp = local.player.max_health
	if( level.coop_health != NIL && level.coop_health > local.hp ){ local.hp = level.coop_health }
	local.player healthonly local.hp
}end


""")
t = sub(t, anchor, cache + anchor)

# 3. binoculars: a grant with nothing left is a fresh object (a spent one is gone, never handed back with 0 strikes)
t = sub(t, nl(t, """	local.firstPickup = 0
	if( level.coop_binoc_uses == NIL ){
		local.firstPickup = 1
		level.coop_binoc_uses = 1
	}
	level.coop_binoc_given = 1
	level.coop_binoc_owner = local.player"""), nl(t, """	local.firstPickup = 0
	if( level.coop_binoc_uses == NIL || level.coop_binoc_uses <= 0 ){	//[bug-4005] 0 left = the last pair was SPENT; a grant is a fresh pair, never 0 strikes
		local.firstPickup = 1
		level.coop_binoc_uses = 1
	}
	level.coop_binoc_given = 1
	level.coop_binoc_owner = local.player"""))

wr("coop_mod/officer.scr", t)
print("officer.scr ok")
