"""read SKC (SKAN v13) channels: python skcread.py <rel skc> [channel substring] -> frame 0 values"""
import sys, struct
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import gen_wpnfix_pak as W


def read(b):
    ident, ver, flags, size, ft = struct.unpack_from('<4s3if', b, 0)
    nc, o_ch, nf = struct.unpack_from('<3i', b, 36)
    chans = [b[o_ch + 32 * i:o_ch + 32 * i + 32].split(b'\0')[0].decode() for i in range(nc)]
    frames = []
    for f in range(nf):
        ov = struct.unpack_from('<i', b, 48 + 48 * f + 44)[0]
        frames.append([struct.unpack_from('<4f', b, ov + 16 * c) for c in range(nc)])
    return chans, frames


if __name__ == '__main__':
    rel = sys.argv[1]
    w, b = W.carriers(rel)[-1]
    ch, fr = read(b)
    print(rel, w, 'frames', len(fr), 'channels', ch)
    for i, c in enumerate(ch):
        if len(sys.argv) < 3 or sys.argv[2] in c:
            print(' ', c, [round(v, 4) for v in fr[0][i]], '..', [round(v, 4) for v in fr[-1][i]])
