"""joinflood (bug-3909): the public servers' lobby.scr hot patch (public_servers/patch_lobby.py) applied to the mod
SOURCE in the joinflood-next worktree. Same three edits: one lobbyHideHud loop per player, its reliable stufftexts
every 5 s instead of every 0.5 s; cg_huddraw_force once per player; dm_playermodel only when the skin changed.

    python -I patch_lobby_src.py
"""
P = r"C:\mohaa-coop-dev\hzm-mod-joinflood\coop_mod\lobby.scr"
raw = open(P, "rb").read().decode("latin-1")
nl = "\r\n" if "\r\n" in raw else "\n"
s = raw.replace("\r\n", "\n")
orig = s


def sub(old, new):
    global s
    assert s.count(old) == 1, ('anchor count', s.count(old), old[:60])
    s = s.replace(old, new)


# 1) one HUD loop per player; stufftexts every 5 s (10 x 0.5 s)
sub('''	while( level.coop_lobbyActive == 1 && self != NULL ){
		for( local.s = 20; local.s <= 90; local.s++ ){
			ihuddraw_alpha self local.s 0
		}''',
'''	//[bug-3909 2026-10-14] remote-join command flood: ONE loop per player (a new copy used to start on every lobby
	//placement), and its reliable stufftexts every 5 s instead of every 0.5 s - each one is re-sent in every
	//snapshot until the client acks it. The ihuddraw_alpha wipe is not a reliable command and keeps its 0.5 s.
	if( self.flags["coop_lobbyHudLoop"] == 1 ){
		end
	}
	self.flags["coop_lobbyHudLoop"] = 1
	local.k = 10
	while( level.coop_lobbyActive == 1 && self != NULL ){
		for( local.s = 20; local.s <= 90; local.s++ ){
			ihuddraw_alpha self local.s 0
		}''')
sub('''		self stufftext "ui_removehud hud_compass"''',
'''		local.k++
		if( local.k >= 10 ){
		local.k = 0
		self stufftext "ui_removehud hud_compass"''')
sub('''		self stufftext "ui_removehud hud_ammo"
		wait 0.5
	}''',
'''		self stufftext "ui_removehud hud_ammo"
		}
		wait 0.5
	}
	if( self != NULL ){
		self.flags["coop_lobbyHudLoop"] = NIL
	}''')
# 2) cg_huddraw_force only once per player
sub('''	local.player stufftext "set cg_huddraw_force 1"''',
'''	if( local.player.flags["coop_lobbyHudForce"] != 1 ){
		local.player.flags["coop_lobbyHudForce"] = 1
		local.player stufftext "set cg_huddraw_force 1"
	}''')
# 3) dm_playermodel only when the skin actually changed (a userinfo change = a ~600-byte client command back)
sub('''	self stufftext ( "seta dm_playermodel " + local.skin )''',
'''	if( self.flags["coop_lobbySkinSent"] != local.skin ){
		self.flags["coop_lobbySkinSent"] = local.skin
		self stufftext ( "seta dm_playermodel " + local.skin )
	}''')

assert all(ord(c) < 128 for c in s), "non-ASCII would kill the parse"


def depth_ok(t):
    d = 0
    for ch in t.replace('"{"', "").replace('"}"', ""):
        d += (ch == "{") - (ch == "}")
        if d < 0:
            return False
    return d == 0


assert depth_ok(s) and depth_ok(orig)
open(P, "wb").write(s.replace("\n", nl).encode("latin-1"))
print("lobby.scr patched, depth ok")
