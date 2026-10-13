"""ed18.py - mgFlee: the walk back to the gun is tried twice and says what it did."""
import sys
sys.path.insert(0, ".")
from edlib import Ed
e = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/parasquad.scr")
e.sub("""			local.straight = 0
			local.rad = 28
			if( waitthread mgLine local.a.origin local.seat ){
				local.straight = 1
				local.rad = 10
			}
			local.left = waitthread mgLeg local.a local.seat local.straight local.rad 8
			if( local.a == NULL ){ end }
			if( !isAlive local.a ){ end }
			if( local.left > 14 && local.left < 110 ){""", """			local.a.enableEnemy = 0
			local.left = 99999
			for( local.n = 0; local.n < 2; local.n++ ){
				local.straight = 0
				local.rad = 28
				if( waitthread mgLine local.a.origin local.seat ){
					local.straight = 1
					local.rad = 10
				}
				local.left = waitthread mgLeg local.a local.seat local.straight local.rad 8
				if( local.a == NULL ){ end }
				if( !isAlive local.a ){ end }
				waitthread dbg ( "mg nade walkback straight=" + local.straight + " left=" + local.left )
				if( local.left < 110 ){ break }
			}
			if( local.left > 14 && local.left < 110 ){""")
e.save()
