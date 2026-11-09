#!/usr/bin/env python3
"""Format-probing helpers for undocumented Frontline chunks (our own code).

  probe.py floats <file> [stride ...]  - find runs of plausible float vectors
                                         (vertex-buffer candidates) per stride
  probe.py strings <file> [minlen]     - printable ASCII strings with offsets
  probe.py words <file> <off> <n>      - dump n u32 words from off as int/float
"""
import struct, sys


def plausible(v):
    return v == 0.0 or (1e-4 < abs(v) < 6e4)


def float_runs(data, stride, min_run=24):
    """Yield (offset, count) of runs where the first 3 floats of each
    stride-sized record are all plausible coordinates."""
    n = len(data)
    best = []
    for phase in range(0, stride, 4):
        run_start, run = None, 0
        for off in range(phase, n - 12, stride):
            x, y, z = struct.unpack_from("<3f", data, off)
            ok = plausible(x) and plausible(y) and plausible(z) and not (x == y == z == 0.0)
            if ok:
                if run == 0:
                    run_start = off
                run += 1
            else:
                if run >= min_run:
                    best.append((run_start, run))
                run = 0
        if run >= min_run:
            best.append((run_start, run))
    return sorted(best)


def main(a):
    data = open(a[2], "rb").read()
    if a[1] == "floats":
        strides = [int(s) for s in a[3:]] or [12, 16, 20, 24, 28, 32, 36, 40]
        for st in strides:
            runs = float_runs(data, st)
            cov = sum(c * st for _, c in runs)
            print(f"stride {st}: {len(runs)} runs, {cov} bytes ({100*cov/len(data):.1f}%)",
                  "first:", [(hex(o), c) for o, c in runs[:6]])
    elif a[1] == "strings":
        ml = int(a[3]) if len(a) > 3 else 5
        cur, start = bytearray(), 0
        for i, b in enumerate(data):
            if 32 <= b < 127:
                if not cur:
                    start = i
                cur.append(b)
            else:
                if len(cur) >= ml:
                    print(hex(start), cur.decode())
                cur = bytearray()
    elif a[1] == "words":
        off, n = int(a[3], 0), int(a[4])
        for i in range(n):
            o = off + 4 * i
            u, = struct.unpack_from("<I", data, o)
            f, = struct.unpack_from("<f", data, o)
            print(hex(o), f"{u:10d} 0x{u:08x} {f: .5g}")


if __name__ == "__main__":
    main(sys.argv)
