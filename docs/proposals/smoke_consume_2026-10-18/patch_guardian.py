import io
p = "C:/mohaa-coop-dev/hzm-mod-smokec/coop_mod/keyitems.scr"
t = io.open(p, "r", encoding="utf-8", newline="").read()
crlf = "\r\n" in t
def f(s):
    return s.replace("\n", "\r\n") if crlf else s

old = f("""			if( level.coop_smoke_player == local.player && level.coop_paradrop_armed == 1 && local.player.flags["coop_smokeUsed"] != 1 ){	//[bug-4005] a THROWN smoke is gone for good
				if( !( waitthread coop_mod/itemhandler.scr::playerHasWeapon local.player "models/weapons/coop_smoke_grenade.tik" ) ){
					local.player item models/weapons/coop_smoke_grenade.tik
				}
			}
""")
new = f("""			//[bug-4005] the SIGNAL SMOKE is NOT re-given on a plain "owner without a smoke in hand" test any more. That test
			//fired the moment the grenade left the hand (coop_smoke_player stays set through the whole call-in), so a thrown
			//smoke came straight back - armed was 0 by then and the second throw called nothing. It is re-given only at
			//the revive below, and only while it is still unused and armed.
""")
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)

old2 = f("""				if( isAlive local.player && local.player.flags["coop_dbno_active"] != 1 ){
					local.player thread coop_mod/main.scr::itemGetAll
				}
""")
new2 = f("""				if( isAlive local.player && local.player.flags["coop_dbno_active"] != 1 ){
					local.player thread coop_mod/main.scr::itemGetAll
					//[bug-4005] revive: an UNUSED smoke that the DBNO takeall stripped comes back; a thrown one never does
					if( level.coop_smoke_player == local.player && level.coop_paradrop_armed == 1 && local.player.flags["coop_smokeUsed"] != 1 ){
						if( !( waitthread coop_mod/itemhandler.scr::playerHasWeapon local.player "models/weapons/coop_smoke_grenade.tik" ) ){
							local.player item models/weapons/coop_smoke_grenade.tik
							println( "^~^~^ SMOKE_REGIVE revive p=" + local.player.netname )
						}
					}
				}
""")
assert t.count(old2) == 1, t.count(old2)
t = t.replace(old2, new2)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("ok")
