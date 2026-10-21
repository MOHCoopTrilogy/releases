import sys, re
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F

# ---- generator: airdrop type + dz
f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if '"airdrop"' not in f.b:
    f.rep('TYPES = ("intel", "hold", "radio", "escort", "charge", "perform")',
          'TYPES = ("intel", "hold", "radio", "escort", "charge", "perform", "airdrop")')
    f.rep('if o["type"] in ("hold", "perform"):', 'if o["type"] in ("hold", "perform", "airdrop"):')
    f.rep('''            z = o.get("zone")
            if z:''', '''            if o.get("dz"):
                w("\\tlevel.objx_dz[%d] = %s" % (i, v(o["dz"])))
            z = o.get("zone")
            if z:''')
    f.save()

# ---- objx.scr
g = F(r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx.scr")
if "airdrop" not in g.b:
    g.rep('''	if( local.ty == "perform" ){ thread ox_hold_run local.i }''',
          '''	if( local.ty == "perform" ){ thread ox_hold_run local.i }
	if( local.ty == "airdrop" ){ thread ox_hold_run local.i }''')
    # start the drop when the clock starts
    g.rep('''	local.remaining = local.total
	local.t0 = level.time''', '''	if( level.objx_type[local.i] == "airdrop" ){ thread coop_mod/objx2.scr::ox2_airdrop_go local.i }
	local.remaining = local.total
	local.t0 = level.time''')
    # the loop condition: the clock cannot end the objective before the men are down
    g.rep('''	while( local.remaining > 0 ){
		wait 0.25
		if( level.time >= local.nextwave''', '''	while( local.remaining > 0 || ( level.objx_type[local.i] == "airdrop" && level.objx_ad_done != 1 && level.time < ( local.t0 + 300 ) ) ){
		wait 0.25
		if( level.objx_type[local.i] == "airdrop" && ( waitthread coop_mod/objx2.scr::ox2_airdrop_regrouped local.i ) == 1 ){ break }
		if( local.remaining < 0 ){ local.remaining = 0 }
		if( level.time >= local.nextwave''')
    g.save()
