"""fix_drv4.py - fourth-pass commands for the overlay driver p3_drv.scr: aimp gst mbelt nade paim hurt."""
import io
p = "p3_drv.scr"
s = io.open(p, encoding="latin-1", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")
NEW = r'''	if( local.c == "aimp" ){
		// TEST'S DOING (said in the report): the manned gun is aimed p3_pitch degrees UP (negative = down), p3_yaw off
		// the middle of its arc; p3_n 1 = it fires
		if( local.k1 != NIL ){
			local.gg = local.k1.coop_psqGun
			if( local.gg != NIL && local.gg != NULL ){
				if( level.p3_ft == NIL || level.p3_ft == NULL ){ level.p3_ft = spawn script_origin }
				local.el = 0 - ( float( getcvar( "p3_pitch" ) ) )
				local.bo = local.gg.origin
				if( local.gg.coop_psqBase != NIL ){ local.bo = local.gg.coop_psqBase }
				level.p3_ft.origin = local.bo + ( vector_scale ( angles_toforward ( local.el ( local.k1.coop_psqMgYaw + local.yaw ) 0 ) ) 900 )
				local.gg targettype "none"
				local.gg setAimTarget level.p3_ft
				if( int( getcvar( "p3_n" ) ) == 1 ){ local.gg startFiring } else { local.gg stopFiring }
				println ( "^~^~^ P3 aimp el=" + local.el )
			}
		}
	}
	if( local.c == "gst" ){
		// the gun in full: the manned one, else the one left for the players
		local.gg = NIL
		local.who = "none"
		if( local.k1 != NIL ){
			local.gg = local.k1.coop_psqGun
			if( isAlive local.k1 ){ local.who = "k" + local.k1.coop_psqK + " at=" + local.k1.origin + " pos=" + local.k1.position + " mnt=" + local.k1.coop_psqMounted }
		}
		if( local.gg == NIL || local.gg == NULL ){
			if( level.coop_psqLeftN != NIL ){ local.gg = level.coop_psqLeftGun[level.coop_psqLeftN] }
		}
		if( local.gg != NIL && local.gg != NULL ){
			local.ss = "none"
			local.su = NIL
			if( local.k1 != NIL ){ local.su = local.k1.coop_psqSup }
			if( local.su != NIL && local.su != NULL ){ level.p3_sup = local.su }
			if( level.p3_sup != NIL && level.p3_sup != NULL ){ local.ss = level.p3_sup.origin + " " + level.p3_sup.angles }
			println ( "^~^~^ P3 GST at=" + local.gg.origin + " ang=" + local.gg.angles + " base=" + local.gg.coop_psqBase + " rest=" + local.gg.coop_psqRest + " sup=" + local.ss + " who=" + local.who + " pl=" + local.p.origin )
			println ( "^~^~^ P3 GSTK ammo=" + local.gg.coopammo + " heat=" + local.gg.coopheat )	//NEWDLL
		} else {
			println "^~^~^ P3 GST none"
		}
	}
	if( local.c == "mbelt" ){
		// TEST SET-UP: the belt of the MANNED gun is cut to p3_n rounds, and he has p3_z belts more
		if( local.k1 != NIL ){
			local.gg = local.k1.coop_psqGun
			if( local.gg != NIL && local.gg != NULL ){
				local.gg coopammo ( int( getcvar( "p3_n" ) ) )
				local.k1.coop_psqBelts = int( getcvar( "p3_z" ) )
				println ( "^~^~^ P3 mbelt " + getcvar( "p3_n" ) + " belts=" + local.k1.coop_psqBelts )
			}
		}
	}
	if( local.c == "nade" ){
		// TEST'S DOING: a German stick grenade is laid p3_n units from squad member p3_tag (0 = the gunner), p3_yaw
		// round from the way he faces; it tells the AI it is there twice a second and goes off after p3_z seconds
		local.m = local.k1
		local.mk = int( getcvar( "p3_tag" ) )
		if( local.mk > 0 ){ local.m = level.coop_psqM[level.coop_psqN][local.mk] }
		if( local.m != NIL && local.m != NULL ){
			local.dist = float( getcvar( "p3_n" ) )
			local.np = local.m.origin + ( vector_scale ( angles_toforward ( 0 ( local.m.angles[1] + local.yaw ) 0 ) ) local.dist )
			local.ng = waitthread coop_mod/officer.scr::coop_find_ground ( local.np + ( 0 0 40 ) )
			if( local.ng != NIL ){ local.np = local.ng }
			local.g = spawn "models/projectiles/steilhandgranate.tik"
			local.g.origin = local.np + ( 0 0 3 )
			println ( "^~^~^ P3 nade at=" + local.g.origin + " class=" + local.g.classname + " from=" + local.m.origin )
			thread p3_nadego local.g ( float( getcvar( "p3_z" ) ) )
		}
	}
	if( local.c == "paim" ){
		// the PLAYER on gun level.p3_gunEnt looks p3_pitch degrees up (negative = down), p3_yaw off its facing
		if( level.p3_gunEnt != NIL && level.p3_gunEnt != NULL ){
			local.el = 0 - ( float( getcvar( "p3_pitch" ) ) )
			level.p3_gunEnt psetviewangles ( local.el ( level.p3_gunYaw + local.yaw ) 0 )
			println ( "^~^~^ P3 paim el=" + local.el )
		}
	}
	if( local.c == "hurt" ){
		// TEST SET-UP: squad member p3_tag gets p3_n health (0 = he is killed)
		local.mk = int( getcvar( "p3_tag" ) )
		local.m = level.coop_psqM[level.coop_psqN][local.mk]
		if( local.m != NIL && local.m != NULL ){
			local.hp = float( getcvar( "p3_n" ) )
			if( local.hp <= 0 ){ local.m kill } else { local.m.health = local.hp }
		}
	}
'''
MARK = "}end\n\n// the fight in numbers"
assert s.count(MARK) == 1
s = s.replace(MARK, NEW + "}end\n\np3_nadego local.g local.fuse:{\n\tlocal.t = 0\n\twhile( local.t < local.fuse && local.g != NULL ){\n\t\tlocal.g ai_event \"grenade\" 1024\n\t\twait 0.5\n\t\tlocal.t = local.t + 0.5\n\t}\n\tif( local.g != NULL ){ local.g explode }\n\tprintln \"^~^~^ P3 nade exploded\"\n}end\n\n// the fight in numbers")
io.open(p, "w", encoding="latin-1", newline="").write(s.replace("\n", nl))
print("driver patched", len(s.splitlines()), "lines")
