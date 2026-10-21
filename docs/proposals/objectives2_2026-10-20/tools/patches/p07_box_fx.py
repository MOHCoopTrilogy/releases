import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if "objx_it_box" not in f.b:
    f.rep('''                w("\\tlevel.objx_it_nd[%d] = %d" % (k, int(it.get("nodrop", 0))))''',
          '''                w("\\tlevel.objx_it_nd[%d] = %d" % (k, int(it.get("nodrop", 0))))
                w("\\tlevel.objx_it_box[%d] = %d" % (k, int(it.get("box", 0))))
                w("\\tlevel.objx_it_fx[%d] = %s" % (k, s(it.get("fx", ""))))''')
    f.save()
g = F(r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx.scr")
if "objx_it_box" not in g.b:
    g.rep('''	local.rx = 14 * local.rs
	local.rz = 22 * local.rs
''', '''	local.rx = 14 * local.rs
	local.rz = 22 * local.rs
	if( level.objx_it_box[local.k] > 0 ){
		// a big shootable target (fuel tanks): the data gives the hit box half width, height = 1.3 x
		local.rx = level.objx_it_box[local.k]
		local.rz = level.objx_it_box[local.k] * 1.3
	}
''')
    g.rep('''		local.radio stoploopsound
		local.radio playsound coop_radio_blast
		local.radio remove
	}
	waitthread ox_boom local.pos''', '''		local.radio stoploopsound
		if( level.objx_it_fx[local.k] == "tank" ){
			// a fuel tank: the big blast, and the wreck model stays where it stood
			waitthread coop_mod/objx2.scr::ox2_blast local.pos 2
			if( level.objx_it_aux[local.k] != "" ){
				local.radio model level.objx_it_aux[local.k]
				waitframe
				local.radio notsolid
				local.radio anim idle
			} else {
				local.radio remove
			}
		} else {
			local.radio playsound coop_radio_blast
			local.radio remove
			waitthread ox_boom local.pos
		}
	} else {
		waitthread ox_boom local.pos
	}''')
    g.save()
