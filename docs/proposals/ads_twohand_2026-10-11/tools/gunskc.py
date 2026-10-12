"""Write a gun (weapon mesh) clip: the template clip's channels held at its frame 0, plus keyed channels.

    import gunskc; gunskc.write(out, template_bytes, nframes, {channel name: [vec4 per frame]}, frame_time=None)
A channel not in the template is appended. v13 layout written afresh (header 48, frames 48, values 16/channel, names 32).
"""
import os, sys, struct
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
if T not in sys.path:
    sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
import skc14to13
os.chdir(_c)
R = V.R


def write(out, tmpl, n, keyed, frame_time=None):
    if struct.unpack_from('<i', tmpl, 4)[0] == 14:
        tmpl = skc14to13.convert(tmpl)
    a = R.skc_io.read(tmpl)
    names = list(a.names)
    base = [list(v) for v in a.values[0]]
    chans = [bytes(c) for c in a.channels]
    for k in keyed:
        if k not in names:
            names.append(k); base.append([0.0, 0.0, 0.0, 1.0] if k.endswith(' rot') else [0.0, 0.0, 0.0, 0.0])
            b = k.encode('latin-1'); chans.append(b + b'\0' * (32 - len(b)))
    nch = len(names)
    ofs_vals = 48 + 48 * n
    ofs_ch = ofs_vals + n * nch * 16
    end = ofs_ch + 32 * nch
    buf = bytearray(end)
    struct.pack_into('<4s3if3ff3i', buf, 0, b'SKAN', 13, a.flags, end, frame_time or a.frameTime, *a.totalDelta, a.totalAngleDelta, nch, ofs_ch, n)
    fr0 = a.frames[0]
    for f in range(n):
        struct.pack_into('<6ff3ffi', buf, 48 + 48 * f, *fr0['bounds'], fr0['radius'], *fr0['delta'], fr0['unknown'], ofs_vals + f * nch * 16)
        for c, nm in enumerate(names):
            v = keyed[nm][f] if nm in keyed else base[c]
            struct.pack_into('<4f', buf, ofs_vals + f * nch * 16 + 16 * c, *[float(x) for x in v])
    for i, raw in enumerate(chans):
        buf[ofs_ch + 32 * i: ofs_ch + 32 * i + 32] = raw
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'wb').write(bytes(buf))
    return names
