import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F

f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if "hold_ent" not in f.b:
    f.rep('''            if o.get("dz"):''', '''            w("\\tlevel.objx_hent[%d] = %s" % (i, s(o.get("hold_ent", ""))))
            if o.get("dz"):''')
    f.save()

g = F(r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx.scr")
if "ox2_ent_hold" not in g.b:
    g.rep('''	for( local.i = 1; local.i <= local.n; local.i++ ){
		thread ox_arm local.i''', '''	for( local.i = 1; local.i <= local.n; local.i++ ){
		if( level.objx_hent[local.i] != "" ){ thread coop_mod/objx2.scr::ox2_ent_hold local.i }
		thread ox_arm local.i''')
    g.save()

h = F(r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx2.scr")
if "ox2_ent_hold" not in h.b:
    h.rep('''		waitthread coop_mod/feed.scr::feed_all 1 ( "objx_pfgo_" + local.i ) "Engineer: Cover me while I get this running!"''',
          '''		if( level.objx_it_ref[local.k] == "bustgate" ){
			waitthread coop_mod/feed.scr::feed_all 1 ( "objx_pfgo_" + local.i ) "Engineer: Cover me - I am cutting the lock on this gate!"
		} else {
			waitthread coop_mod/feed.scr::feed_all 1 ( "objx_pfgo_" + local.i ) "Engineer: Cover me while I get this running!"
		}''')
    h.rep('''	waitthread coop_mod/feed.scr::feed_all 1 ( "objx_pfend_" + local.i ) "Engineer: That should do it - the generator is running!"''',
          '''	if( level.objx_it_ref[local.k] == "bustgate" ){
		// the m1l3c fence gate: the vanilla bust (fence falls, fx, crash sound) fired by the engineer instead of by the truck
		thread maps/m1l3c.scr::bust_gate
		waitthread coop_mod/feed.scr::feed_all 1 ( "objx_pfend_" + local.i ) "Engineer: Gate is open - the truck can come through!"
	} else {
		waitthread coop_mod/feed.scr::feed_all 1 ( "objx_pfend_" + local.i ) "Engineer: That should do it - the generator is running!"
	}''')
    # the dropped engineer hands over to the performer at the gate
    h.rep('''	level.objx_pf_k[local.i] = local.k
	level.objx_pf_alive[local.i] = 0''', '''	level.objx_pf_k[local.i] = local.k
	if( level.objx_it_ref[local.k] == "bustgate" ){
		// the engineer who dropped in walks off to the gate: the performer replaces him there
		local.de = level.coop_paradrop_squad[3]
		if( local.de != NULL && local.de != NIL ){ local.de remove }
	}
	level.objx_pf_alive[local.i] = 0''')
    h.save()
    code = '''

// keep a vanilla trigger/entity (level.objx_hent[i]) unusable until objective i is done: the m1l3c exit truck waits for the fence gate
ox2_ent_hold local.i:{
	local.nm = level.objx_hent[local.i]
	while( level.objx_stat[local.i] != 3 ){
		local.e = $( local.nm )
		if( local.e != NULL && local.e != NIL ){ local.e nottriggerable }
		wait 0.5
	}
	local.e = $( local.nm )
	if( local.e != NULL && local.e != NIL ){ local.e triggerable }
	waitthread coop_mod/objx.scr::ox_log ( "HOLD-ENT released " + local.nm + " t=" + level.time )
}end
'''
    p = h.p if hasattr(h, "p") else r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx2.scr"
    d = open(p, "rb").read().decode("latin-1")
    open(p, "wb").write((d.rstrip() + code.replace("\n", "\r\n" if "\r\n" in d else "\n")).encode("latin-1"))
