"""ed10.py - parasquad.scr: 'in front of the muzzle' is not a man a floor below it (the m3l3 window sill was refused,
and the gun there would have held its fire, for squad mates standing in the street 200u under the window)."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""		local.v = local.p.origin - local.pos
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 1500 ){ continue }""", """		local.v = local.p.origin - local.pos
		// (a man more than 110u under or over the muzzle is not in front of it: the gun's pitch is 12 degrees)
		local.hz = local.v[2] + 40
		if( local.hz < 0 ){ local.hz = 0 - local.hz }
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 1500 ){ continue }
		if( local.hz > 110 && local.hz > ( local.along * 0.25 ) ){ continue }""")
E.sub("""		local.v = local.m.origin - local.pos
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 900 ){ continue }""", """		local.v = local.m.origin - local.pos
		local.hz = local.v[2] + 40
		if( local.hz < 0 ){ local.hz = 0 - local.hz }
		local.v[2] = 0
		local.along = vector_dot local.v local.dir
		if( local.along <= 0 || local.along > 900 ){ continue }
		if( local.hz > 110 && local.hz > ( local.along * 0.25 ) ){ continue }""")
E.save()
