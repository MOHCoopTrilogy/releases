"""Resample a view / torso clip to N frames (same frame time, so it simply lasts longer): the slower revolver loop.
v14 sources are converted to v13 (the format our baked clips already ship in).

    python retime.py <game path or file> <out.skc> <frames>
"""
import sys, os, copy, struct
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R
src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
a = R.load(src)                      # vmcam's loader: v14 -> v13, .V = [frame, channel, 4]
m = a.numFrames
Vn = np.zeros((n, a.numChannels, 4))
for f in range(n):
    x = f * (m - 1) / float(n - 1)
    i = min(m - 2, int(x)); u = x - i
    for c, name in enumerate(a.names):
        p, q = a.V[i, c], a.V[i + 1, c]
        if name.endswith(' rot'):
            if p @ q < 0:
                q = -q
            v = (1 - u) * p + u * q
            Vn[f, c] = v / np.linalg.norm(v)
        else:
            Vn[f, c] = (1 - u) * p + u * q
fr = []
for f in range(n):
    k = min(m - 1, int(round(f * (m - 1) / float(n - 1))))
    fr.append(copy.deepcopy(a.frames[k]))
a.frames = fr
a.numFrames = n
a.values = [[[float(np.float32(x)) for x in Vn[f, c]] for c in range(a.numChannels)] for f in range(n)]
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
# skc_io.write keeps the SOURCE file's layout (per-frame value offsets), which is wrong once the frame count changes
# (the first try drew an exploded arm in the engine): lay the file out again - header 48, frames 48 each, values
# 16 per channel per frame, channel names 32 each.
nch = a.numChannels
ofs_vals = 48 + 48 * n
ofs_ch = ofs_vals + n * nch * 16
end = ofs_ch + 32 * nch
buf = bytearray(end)
struct.pack_into('<4s3if3ff3i', buf, 0, b'SKAN', 13, a.flags, end, a.frameTime, *a.totalDelta, a.totalAngleDelta, nch, ofs_ch, n)
for f in range(n):
    frm = a.frames[f]
    struct.pack_into('<6ff3ffi', buf, 48 + 48 * f, *frm['bounds'], frm['radius'], *frm['delta'], frm['unknown'], ofs_vals + f * nch * 16)
    for c in range(nch):
        struct.pack_into('<4f', buf, ofs_vals + f * nch * 16 + 16 * c, *a.values[f][c])
for i, raw in enumerate(a.channels):
    buf[ofs_ch + 32 * i: ofs_ch + 32 * i + 32] = raw
open(out, 'wb').write(bytes(buf))
b = R.skc_io.read(open(out, 'rb').read())
print('wrote', out, b.numFrames, 'frames x', round(b.frameTime, 4), 's =', round(b.numFrames * b.frameTime, 2), 's (was', m, ')')
