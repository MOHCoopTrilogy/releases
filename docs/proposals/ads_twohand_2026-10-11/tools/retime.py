"""Resample a view / torso / gun clip to N frames (same frame time, so it simply lasts longer), or cut a frame range out
of it. v14 sources are converted to v13 (the format our baked clips already ship in). The file is laid out afresh:
skc_io.write keeps the SOURCE layout (per-frame value offsets), which is wrong once the frame count changes (the first
slow loop drew an exploded arm in the engine).

    python retime.py <game path or file> <out.skc> <frames>
    python retime.py <game path or file> <out.skc> slice <first> <last>
"""
import sys, os, copy, struct
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R
src, out = sys.argv[1], sys.argv[2]
a = R.load(src)                      # vmcam's loader: v14 -> v13, .V = [frame, channel, 4]
m = a.numFrames
if sys.argv[3] == 'slice':
    f0, f1 = int(sys.argv[4]), int(sys.argv[5])
    assert 0 <= f0 <= f1 < m, (f0, f1, m)
    n = f1 - f0 + 1
    Vn = a.V[f0:f1 + 1].copy()
    fr = [copy.deepcopy(a.frames[k]) for k in range(f0, f1 + 1)]
    what = 'sliced %d..%d of %d' % (f0, f1, m)
else:
    n = int(sys.argv[3])
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
    fr = [copy.deepcopy(a.frames[min(m - 1, int(round(f * (m - 1) / float(n - 1))))]) for f in range(n)]
    what = 'resampled (was %d)' % m
nch = a.numChannels
ofs_vals = 48 + 48 * n
ofs_ch = ofs_vals + n * nch * 16
end = ofs_ch + 32 * nch
buf = bytearray(end)
struct.pack_into('<4s3if3ff3i', buf, 0, b'SKAN', 13, a.flags, end, a.frameTime, *a.totalDelta, a.totalAngleDelta, nch, ofs_ch, n)
for f in range(n):
    frm = fr[f]
    struct.pack_into('<6ff3ffi', buf, 48 + 48 * f, *frm['bounds'], frm['radius'], *frm['delta'], frm['unknown'], ofs_vals + f * nch * 16)
    for c in range(nch):
        struct.pack_into('<4f', buf, ofs_vals + f * nch * 16 + 16 * c, *[float(np.float32(x)) for x in Vn[f, c]])
for i, raw in enumerate(a.channels):
    buf[ofs_ch + 32 * i: ofs_ch + 32 * i + 32] = raw
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, 'wb').write(bytes(buf))
b = R.skc_io.read(open(out, 'rb').read())
print('wrote', out, b.numFrames, 'frames x', round(b.frameTime, 4), 's =', round(b.numFrames * b.frameTime, 2), 's;', what)
