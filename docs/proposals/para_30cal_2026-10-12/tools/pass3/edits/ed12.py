"""ed12.py - the GREASE GUN (user 2026-10-12: "sometimes the paratroopers should spawn in with grease guns too").
paradrop.scr: the Thompson man (member 2) carries an M3 in coop_paraGreaseChance percent of the drops (default 50).
coop_defaults.cfg: the cvar's seed. Driver: camk (camera on a squad member)."""
import io
from edlib import Ed
E = Ed("C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_mod/paradrop.scr")
E.sub("""		local.actor gun "thompson"
""", """		local.actor gun "thompson"
		//[user 2026-10-12] "sometimes the paratroopers should spawn in with grease guns too": in coop_paraGreaseChance
		//percent of the drops (default 50, 0 = never) the squad's SMG man carries an M3 instead - never the BAR man
		//or the man with the .30 cal. His body is the Thompson man's (built by the line above); the gun follows.
		local.gc = getcvar( "coop_paraGreaseChance" )
		local.gp = 50
		if( local.gc != "" ){ local.gp = int( local.gc ) }
		if( local.gp > 0 && ( randomint 100 ) < local.gp ){ thread coop_paradrop_grease local.actor }
""")
E.sub("""// Sync visual model to 70 units below chute during descent
""", """// The M3 grease gun for the squad's SMG man: models/weapons/coop_greasegun_ai.tik is the players' M3 with the
// Thompson's name stem and weapon group, so an actor has animations for it (the players' own tik has weapongroup
// xw_greasegun: no AI animation set). Given the way every AI variant is (aihandler.scr: coop_actorArm, then
// unholster; bug-3306: never `gun <tik>`); if the give leaves him with nothing he gets his Thompson back.
coop_paradrop_grease local.actor:{
	wait 0.2
	if( local.actor == NULL ){ end }
	if( !isAlive local.actor ){ end }
	local.actor waitthread coop_mod/aihandler.scr::coop_actorArm "models/weapons/coop_greasegun_ai.tik"
	wait 0.1
	if( local.actor == NULL ){ end }
	if( !isAlive local.actor ){ end }
	local.actor unholster
	wait 0.1
	if( local.actor == NULL ){ end }
	if( !isAlive local.actor ){ end }
	local.w = local.actor.weapon
	if( local.w == NIL || local.w == "" ){
		println "^~^~^ PARADROP grease gun give failed - Thompson restored"
		local.actor waitthread coop_mod/aihandler.scr::coop_actorArm "thompson"
		local.actor unholster
		local.w = "restored"
	}
	waitthread coop_mod/parasquad.scr::dbg ( "grease k=2 weapon=" + local.w )
}end


// Sync visual model to 70 units below chute during descent
""")
E.save()

p = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/coop_defaults.cfg"
raw = io.open(p, encoding="latin-1", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
lines = raw.split(nl)
i = next(k for k, l in enumerate(lines) if l.startswith("seta coop_paraShootdownChance"))
assert not any("coop_paraGreaseChance" in l for l in lines)
lines.insert(i + 1, "seta coop_paraGreaseChance 50	// [user 2026-10-12] % of paradrops in which the squad's SMG man carries an M3 grease gun instead of his Thompson; 0 = never")
io.open(p, "w", encoding="latin-1", newline="").write(nl.join(lines))
print("coop_defaults.cfg: seeded after line", i + 1)

d = "p3_drv.scr"
t = io.open(d, encoding="latin-1").read()
a = """	if( local.c == "gunpos" ){"""
assert t.count(a) == 1
t = t.replace(a, """	if( local.c == "camk" ){
		// the camera on squad member p3_tag: p3_n out, p3_yaw degrees round from the way he faces, looking at his chest
		local.mk = int( getcvar( "p3_tag" ) )
		local.m = level.coop_psqM[level.coop_psqN][local.mk]
		if( local.m != NIL && local.m != NULL ){
			local.dist = float( getcvar( "p3_n" ) )
			local.done = 0
			for( local.i = 0; local.i < 8; local.i++ ){
				local.cy = local.m.angles[1] + local.yaw + ( local.i * 45 )
				local.cp = local.m.origin + ( vector_scale ( angles_toforward ( 0 local.cy 0 ) ) local.dist )
				local.cg = waitthread coop_mod/officer.scr::coop_find_ground ( local.cp + ( 0 0 60 ) )
				if( local.cg == NIL ){ continue }
				local.eye = local.cg + ( 0 0 82 )
				local.t2 = local.m.origin + ( 0 0 48 )
				local.tr = traced local.eye local.t2 1023 ( 0 0 0 ) ( 0 0 0 ) 1
				if( local.tr["fraction"] < 0.97 ){ continue }
				local.p origin local.cg
				local.va = vector_toangles ( local.t2 - local.eye )
				local.p.viewangles = ( local.va[0] local.va[1] 0 )
				local.done = 1
				break
			}
			println ( "^~^~^ P3 camk k=" + local.mk + " ok=" + local.done + " at=" + local.m.origin + " weapon=" + local.m.weapon + " think=" + local.m.thinkstate )
		} else {
			println "^~^~^ P3 camk nobody"
		}
	}
	if( local.c == "gunpos" ){""")
io.open(d, "w", encoding="latin-1", newline="\n").write(t)
print("driver ok")
