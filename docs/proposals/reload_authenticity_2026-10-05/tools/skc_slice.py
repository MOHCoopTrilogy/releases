"""skc_slice.py - cut / re-time a v13 .skc by frame list (no re-keying): the per-frame block and the channel
values of the chosen frames are copied verbatim, channel names unchanged.
    python skc_slice.py <in.skc|vfs path> <out.skc> <frames: a-b,c,d-e ...> [--ft seconds]
"""
import sys, os, struct
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import vfs


def slice_skc(data, frames, ft=None):
    assert data[0:4] == b'SKAN' and struct.unpack_from('<i', data, 4)[0] == 13, 'v13 only'
    ver, flags, nbytes, oft = struct.unpack_from('<3if', data, 4)
    td = struct.unpack_from('<3f', data, 20); tad = struct.unpack_from('<f', data, 32)[0]
    nch, ofs_names, nfr = struct.unpack_from('<3i', data, 36)
    names = data[ofs_names: ofs_names + 32 * nch]
    n = len(frames)
    hdr = 48; ofs_vals = hdr + 48 * n; ofs_ch = ofs_vals + n * nch * 16; end = ofs_ch + 32 * nch
    out = bytearray(end)
    struct.pack_into('<4s3if3ff3i', out, 0, b'SKAN', 13, flags, end, ft if ft else oft, *td, tad, nch, ofs_ch, n)
    for k, f in enumerate(frames):
        blk = bytearray(data[hdr + 48 * f: hdr + 48 * f + 48])
        src = struct.unpack_from('<i', blk, 44)[0]
        struct.pack_into('<i', blk, 44, ofs_vals + k * nch * 16)
        out[hdr + 48 * k: hdr + 48 * k + 48] = blk
        out[ofs_vals + k * nch * 16: ofs_vals + (k + 1) * nch * 16] = data[src: src + nch * 16]
    out[ofs_ch:end] = names
    return bytes(out)


def parse_frames(spec):
    fr = []
    for part in spec.split(','):
        if '-' in part:
            a, b = (int(x) for x in part.split('-'))
            fr += list(range(a, b + 1)) if b >= a else list(range(a, b - 1, -1))
        else:
            fr.append(int(part))
    return fr


if __name__ == '__main__':
    src, dst, spec = sys.argv[1:4]
    ft = float(sys.argv[sys.argv.index('--ft') + 1]) if '--ft' in sys.argv else None
    data = open(src, 'rb').read() if os.path.isfile(src) else vfs.read(src)
    out = slice_skc(data, parse_frames(spec), ft)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out)
    print('wrote', dst, len(parse_frames(spec)), 'frames')


def add_to_channel(data, chan, vec):
    """add vec (x, y, z) to every frame of a 'pos' channel (model units) - e.g. shift a whole prop with 'origin pos'"""
    out = bytearray(data)
    nch, ofs_names, nfr = struct.unpack_from('<3i', out, 36)
    names = [out[ofs_names + 32 * i: ofs_names + 32 * i + 32].split(b'\0')[0].decode('latin1') for i in range(nch)]
    ci = names.index(chan)
    for f in range(nfr):
        vo = struct.unpack_from('<i', out, 48 + 48 * f + 44)[0] + 16 * ci
        x, y, z, w = struct.unpack_from('<4f', out, vo)
        struct.pack_into('<4f', out, vo, x + vec[0], y + vec[1], z + vec[2], w)
    return bytes(out)
