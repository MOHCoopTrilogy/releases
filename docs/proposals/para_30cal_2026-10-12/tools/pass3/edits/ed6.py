"""ed6.py - parasquad.scr: the gun's pitch is held to 12 degrees either way (the engine keeps the gunner's hands 39u
behind the pivot at a fixed height: at 20 degrees the grips are 13u away from them), sites are planned for that, and
the gun sits 0.7u lower in the bipod's yoke."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""	local.gun pitchCaps ( -20 20 0 )
""", """	// pitch: 12 degrees either way. The engine holds his hands 39u behind the pivot at one height
	// (Actor::ThinkHoldGun_TurretGun); every degree the gun tips takes the grips 0.7u away from them.
	local.gun pitchCaps ( -12 12 0 )
""")
E.sub("""		// the gun's pitch stops at about 20 degrees
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz > ( local.dist * 0.36 ) ){ end 0 }""", """		// the gun's pitch stops at 12 degrees (pitchCaps in mgSetup)
		if( local.dz < 0 ){ local.dz = 0 - local.dz }
		if( local.dz > ( local.dist * 0.21 ) ){ end 0 }""")
E.sub("""			local.gun = local.c0				// the gun turns about its origin: the bipod stands under it
			local.gun[2] = local.s0 + 18.5""", """			local.gun = local.c0				// the gun turns about its origin: the bipod stands under it
			local.gun[2] = local.s0 + 17.8""")
E.sub("""		local.gun[2] = local.low + 21.5 + 18.5""", """		local.gun[2] = local.low + 21.5 + 17.8""")
E.sub("""	local.chk[2] = local.a.coop_psqMgGun[2] - 18.5""", """	local.chk[2] = local.a.coop_psqMgGun[2] - 17.8""")
E.sub("""		local.chk = local.gun.origin - ( 0 0 18.5 )""", """		local.chk = local.gun.origin - ( 0 0 17.8 )""")
E.save()
