import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if "objx_it_scl" not in f.b:
    f.rep('''                w("\\tlevel.objx_it_seq[%d] = %s" % (k, s(it.get("seq", ""))))''',
          '''                w("\\tlevel.objx_it_seq[%d] = %s" % (k, s(it.get("seq", ""))))
                w("\\tlevel.objx_it_scl[%d] = %.2f" % (k, float(it.get("scale", 0))))''')
    f.save()
g = F(r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx.scr")
if "objx_it_scl" not in g.b:
    g.rep('''	local.e.angles = ( 0 local.yw 0 )
}end local.e''', '''	local.e.angles = ( 0 local.yw 0 )
	if( level.objx_it_scl[local.k] > 0 ){ local.e.scale = level.objx_it_scl[local.k] }	//[objectives2] optional prop scale (data: scale)
}end local.e''')
    g.save()
