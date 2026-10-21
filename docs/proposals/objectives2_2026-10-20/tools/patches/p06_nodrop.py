import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if "objx_it_nd" not in f.b:
    f.rep('''                w("\\tlevel.objx_it_br[%d] = %d" % (k, int(it.get("bright", 0))))''',
          '''                w("\\tlevel.objx_it_br[%d] = %d" % (k, int(it.get("bright", 0))))
                w("\\tlevel.objx_it_nd[%d] = %d" % (k, int(it.get("nodrop", 0))))''')
    f.save()
g = F(r"C:\mohaa-coop-dev\hzm-mod-objectives2\coop_mod\objx.scr")
if "objx_it_nd" not in g.b:
    g.rep('''	local.radio.origin = local.pos + ( 0 0 6 )
	local.radio droptofloor
''', '''	local.radio.origin = local.pos + ( 0 0 6 )
	if( level.objx_it_nd[local.k] != 1 ){ local.radio droptofloor }	//[objectives2] nodrop 1: the vanilla set stood on a table / shelf
''')
    g.rep('''	local.e.origin = level.objx_it_pos[local.k] + ( 0 0 6 )
	local.e droptofloor''', '''	local.e.origin = level.objx_it_pos[local.k] + ( 0 0 6 )
	if( level.objx_it_nd[local.k] != 1 ){ local.e droptofloor }''')
    g.save()
