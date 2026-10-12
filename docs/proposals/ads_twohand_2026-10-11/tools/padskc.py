"""Hold a clip's last frame for N more frames (a weapon's own reload-start clip that ends a frame or two before the
next part starts lets the gun mesh fall back to its idle pose for those frames - the Webley snapped shut for ~60 ms
between `reload` and `reload_single`). v14 clips are converted to v13 on the way.

    python padskc.py <game path of the clip> <out file> <extra frames>
"""
import sys, os, copy, struct
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
import skc14to13
os.chdir(_c)
R = V.R
src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
raw = R.vfs.read(src) if not os.path.isfile(src) else open(src, 'rb').read()
if struct.unpack_from('<i', raw, 4)[0] == 14:
    raw = skc14to13.convert(raw)
a = R.skc_io.read(raw)
print('attrs', [k for k in vars(a) if not k.startswith('_')])
print(src, 'frames', a.numFrames, 'ft', a.frameTime, 'channels', a.numChannels)
b0 = R.skc_io.write(a)
assert R.skc_io.read(b0).numFrames == a.numFrames
for k, v in list(vars(a).items()):
    if isinstance(v, list) and len(v) == a.numFrames and k != 'names':
        v.extend(copy.deepcopy(v[-1]) for _ in range(n))
        print('  extended', k)
a.numFrames += n
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, 'wb').write(R.skc_io.write(a))
c = R.skc_io.read(open(out, 'rb').read())
print('wrote', out, c.numFrames, 'frames', os.path.getsize(out))
