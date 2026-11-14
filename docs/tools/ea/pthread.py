"""Parse an OpenMOHAA .pth (Archiver v14, LZ77/LZO-compressed, typed) into nodes + links.
Usage: python -I pthread.py <file.pth> [xmin xmax ymin ymax zmin zmax]"""
import struct, sys


def decomp(b):
    ip = 0
    out = bytearray()

    def dl(base):
        nonlocal ip
        n = base
        while b[ip] == 0:
            n += 255
            ip += 1
        n += b[ip]
        ip += 1
        return n

    def cp(m, n):
        for _ in range(n):
            out.append(out[m[0]])
            m[0] += 1

    if b[0] > 17:
        t = b[0] - 17
        ip = 1
        out += b[ip:ip + t]
        ip += t
        t = b[ip]; ip += 1
    else:
        t = b[ip]; ip += 1
    while True:
        if t <= 15:
            if t == 0:
                t = dl(15)
            out += b[ip:ip + t + 3]
            ip += t + 3
            t = b[ip]; ip += 1
            if t <= 15:
                m = [len(out) - 2049 - (t >> 2) - 4 * b[ip]]
                ip += 1
                cp(m, 3)
                continue
        # match
        if t > 63:
            m = [len(out) - 1 - ((t >> 2) & 7) - 8 * b[ip]]
            ip += 1
            cp(m, (t >> 5) - 1 + 2)
        elif t > 31:
            t &= 31
            if t == 0:
                t = dl(31)
            s = b[ip] | (b[ip + 1] << 8)
            ip += 2
            m = [len(out) - 1 - (s >> 2)]
            cp(m, t + 2)
        elif t <= 15:
            m = [len(out) - 1 - (t >> 2) - 4 * b[ip]]
            ip += 1
            cp(m, 2)
        else:
            mp = len(out) - 2048 * (t & 8)
            t &= 7
            if t == 0:
                t = dl(7)
            s = b[ip] | (b[ip + 1] << 8)
            ip += 2
            mp -= (s >> 2)
            if mp == len(out):
                return bytes(out)
            mp -= 0x4000
            cp([mp], t + 2)
        t = b[ip - 2] & 3
        if t == 0:
            t = b[ip]; ip += 1
            continue
        out += b[ip:ip + t]
        ip += t
        t = b[ip]; ip += 1


class R:
    def __init__(s, d):
        s.d = d; s.p = 0

    def tag(s, want):
        t = struct.unpack_from('<i', s.d, s.p)[0]; s.p += 4
        assert t == want, (t, want, s.p)

    def i(s, tag=5):
        s.tag(tag); v = struct.unpack_from('<i', s.d, s.p)[0]; s.p += 4; return v

    def f(s):
        s.tag(11); v = struct.unpack_from('<f', s.d, s.p)[0]; s.p += 4; return v

    def sh(s):
        s.tag(9); v = struct.unpack_from('<h', s.d, s.p)[0]; s.p += 2; return v

    def v(s, tag, n):
        s.tag(tag); v = struct.unpack_from('<%df' % n, s.d, s.p); s.p += 4 * n; return v

    def st(s):
        s.tag(14); n = struct.unpack_from('<I', s.d, s.p)[0]; s.p += 4
        v = s.d[s.p:s.p + n]; s.p += n; return v


def load(path):
    raw = open(path, 'rb').read()
    assert raw[:4] == b'CSVG', raw[:4]
    ln = struct.unpack_from('<I', raw, 4)[0]
    d = decomp(raw[8:])
    assert len(d) == ln, (len(d), ln)
    r = R(d)
    r.i(6); r.i(6); r.st(); r.i()  # header, version, info, numclasses
    ver = r.i(); mt = r.st(); fail = r.i()
    n = r.i(); tot = r.i(); totc = r.i()
    nodes = []
    for k in range(n):
        r.i(23)
        o = r.v(1, 3); c = r.v(1, 3); fl = r.i(); nc = r.i()
        ch = []
        for _ in range(nc):
            nd = r.sh(); fh = r.sh(); di = r.f(); dr = r.v(2, 2); p1 = r.v(3, 3); p2 = r.v(3, 3)
            ch.append((nd, fh, di))
        nodes.append((o, fl, ch))
    return ver, nodes


if __name__ == '__main__':
    ver, nodes = load(sys.argv[1])
    print('version', ver, 'nodes', len(nodes))
    box = [float(x) for x in sys.argv[2:8]] if len(sys.argv) >= 8 else None
    for k, (o, fl, ch) in enumerate(nodes):
        if box and not (box[0] <= o[0] <= box[1] and box[2] <= o[1] <= box[3] and box[4] <= o[2] <= box[5]):
            continue
        links = ' '.join('%d(%.0f,%.0f,%.0f)' % (c[0], *nodes[c[0]][0]) for c in ch)
        print('%4d (%.0f,%.0f,%.0f) f%x -> %s' % (k, *o, fl, links))
