"""ed11.py - parasquad.scr: the brain's gun-lane rule uses the same height rule as mgHold (a mate a floor under the
window the gun fires from is not in its lane)."""
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
E.sub("""					local.v = local.a.origin - local.gn.coop_psqMgGun
					local.v[2] = 0
					local.al = vector_dot local.v local.gd
					if( local.al <= 0 || local.al > 900 ){ continue }""", """					local.v = local.a.origin - local.gn.coop_psqMgGun
					local.hz = local.v[2] + 40
					if( local.hz < 0 ){ local.hz = 0 - local.hz }
					local.v[2] = 0
					local.al = vector_dot local.v local.gd
					if( local.al <= 0 || local.al > 900 ){ continue }
					if( local.hz > 110 && local.hz > ( local.al * 0.25 ) ){ continue }""")
E.save()
