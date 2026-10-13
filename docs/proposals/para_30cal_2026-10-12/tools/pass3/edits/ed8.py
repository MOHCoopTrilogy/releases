"""ed8.py - parasquad.scr: the gun LOW over its rest. The retail MG42 bipod prop is 17.1u tall, and on the 21.5u bag
stack the gun body stood visibly high over the bags. The prop is drawn at 0.75 (12.8u - a real M1919A6 bipod is 12 in)
and the bag stack at 1.2 (25.8u), so the gun's height over the gunner's ground stays what his crouched pose needs
(39.3u; the engine's crouched gun pose is made for 38.7u) and the gun sits 13.5u over the top bag instead of 17.8u."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
s = E.s
for a, b in (("three bags, 21.5u, not solid", "three bags, 25.8u, not solid"),
             ("local.sup[2] = local.s0 + 17.1		// the bipod hangs 17.1u below its origin: feet on the surface",
              "local.sup[2] = local.s0 + 12.8		// the bipod (drawn at 0.75) hangs 12.8u below its origin: feet on the surface"),
             ("local.gun[2] = local.s0 + 17.8", "local.gun[2] = local.s0 + 13.5"),
             ("local.sup[2] = local.low + 21.5 + 17.1		// the bags are 21.5u high",
              "local.sup[2] = local.low + 25.8 + 12.8		// the bags (drawn at 1.2) are 25.8u high"),
             ("local.gun[2] = local.low + 21.5 + 17.8", "local.gun[2] = local.low + 25.8 + 13.5"),
             ("local.chk[2] = local.a.coop_psqMgGun[2] - 17.8", "local.chk[2] = local.a.coop_psqMgGun[2] - 13.5"),
             ("local.chk = local.gun.origin - ( 0 0 17.8 )", "local.chk = local.gun.origin - ( 0 0 13.5 )"),
             ("( vector_scale local.dir 14 ) + ( vector_scale local.rgt 16 )", "( vector_scale local.dir 17 ) + ( vector_scale local.rgt 19 )"),
             ("( vector_scale local.dir 14 ) - ( vector_scale local.rgt 16 )", "( vector_scale local.dir 17 ) - ( vector_scale local.rgt 19 )")):
    assert a in s, a
    s = s.replace(a, b)
E.s = s
E.sub("""		local.bag model "models/static/coop_mg_bags.tik"
""", """		local.bag model "models/static/coop_mg_bags.tik"
		local.bag scale 1.2				// 25.8u: the gun low over the bags (see mgTry)
""")
E.sub("""		local.sup model "models/statweapons/mg42_bipod.tik"
	}""", """		local.sup model "models/statweapons/mg42_bipod.tik"
		local.sup scale 0.75			// 12.8u, the height of the M1919's own bipod (the MG42 prop is 17.1u)
	}""")
E.save()
