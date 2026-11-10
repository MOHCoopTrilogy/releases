#!/usr/bin/env python3
"""find vertex-buffer runs: f32 xyz inside a bbox at a constant stride. vbscan.py <file> minx miny minz maxx maxy maxz"""
import struct, sys
d = open(sys.argv[1], "rb").read()
lo = [float(v) - 1 for v in sys.argv[2:5]]; hi = [float(v) + 1 for v in sys.argv[5:8]]
n = len(d) // 4
f = struct.unpack_from(f"<{n}f", d, 0)
def ok(i):
    if i + 2 >= n: return False
    x, y, z = f[i], f[i+1], f[i+2]
    return lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] and lo[2] <= z <= hi[2] and abs(x) > 0.05 and abs(y) > 0.05 and (z == 0 or abs(z) > 1e-3)
good = [ok(i) for i in range(n)]
res = {}
for sw in range(3, 17):
    i = 0; runs = []
    while i < n:
        if good[i]:
            j = i
            while j < n and good[j]: j += sw
            cnt = (j - i) // sw
            if cnt >= 20: runs.append((i * 4, cnt))
            i = j if cnt >= 20 else i + 1
        else:
            i += 1
    res[sw] = runs
for sw, runs in res.items():
    print(sw * 4, len(runs), sum(c for _, c in runs), [(hex(o), c) for o, c in runs[:6]])
