"""one-off: the timing probe of tools/dbs_world.scr prints EVERY server frame while coop_rtOn is 1 (the harness keeps
the changes); a shot's FIREDBG SHOOT line then falls between two frames of known time."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dbs_world.scr')
s = open(p, encoding='latin-1').read()
i = s.index('//server timing probe')
new = '''//server timing probe: while coop_rtOn is 1, one line per server frame (time, torso state, shell pool)
dbsw_probe:{
	println "^~^~^ DBST probe started"
	while( 1 ){
		if( getcvar( "coop_rtOn" ) == "1" && $player != NULL && $player.size >= 1 ){
			local.p = $player[1]
			local.s = local.p gettorsostate
			local.a = local.p getammo "shotgun"
			println ( "^~^~^ DBST t=" + level.time + " st=" + local.s + " am=" + local.a )
		}
		waitframe
	}
}end
'''
s = s[:i] + new
open(p, 'w', encoding='latin-1', newline='\n').write(s)
print('probe replaced')
