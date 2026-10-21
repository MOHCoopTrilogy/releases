import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if "objx_it_br" not in f.b:
    f.rep('''                w("\\tlevel.objx_it_scl[%d] = %.2f" % (k, float(it.get("scale", 0))))''',
          '''                w("\\tlevel.objx_it_scl[%d] = %.2f" % (k, float(it.get("scale", 0))))
                w("\\tlevel.objx_it_br[%d] = %d" % (k, int(it.get("bright", 0))))''')
    f.save()
