"""fix_drv5.py - driver: 'behind' stands the player 62u back on the ground under the gun (a gun at rest has its stock where
52u back was); 'others' hides / shows the squad members who are not the gunner (test set-up for stills)."""
import io
p = "p3_drv.scr"
s = io.open(p, encoding="latin-1", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)


rep("""			local.b = local.gg.origin - ( vector_scale local.dir 52 )
			local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.b + ( 0 0 8 ) )""",
    """			local.b = local.gg.origin - ( vector_scale local.dir 62 )
			local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.b - ( 0 0 22 ) )""")
rep("""	if( local.c == "paim" ){""", """	if( local.c == "others" ){
		// TEST SET-UP for stills: the squad members who are not on the gun are hidden (p3_n 1) or shown again (0)
		for( local.k = 1; local.k <= 5; local.k++ ){
			local.m = level.coop_psqM[level.coop_psqN][local.k]
			if( local.m == NIL || local.m == NULL ){ continue }
			if( local.k1 != NIL ){ if( local.m == local.k1 ){ continue } }
			if( int( getcvar( "p3_n" ) ) == 1 ){ local.m hide } else { local.m show }
		}
	}
	if( local.c == "paim" ){""")
io.open(p, "w", encoding="latin-1", newline="").write(s.replace("\n", nl))
print("driver patched")
