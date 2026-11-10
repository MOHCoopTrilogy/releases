#!/usr/bin/env python3
"""catalogue EAGL4 stream records in an EA .cpt: header {a, size, type, 1, b} with b + 0xC0 == data start."""
import struct, sys, collections
d = open(sys.argv[1], "rb").read()
PB = 0xC0
recs = []
for h in range(0, len(d) - 20, 4):
    a, size, typ, one, b = struct.unpack_from("<5I", d, h)
    if one == 1 and b + PB == h + 20 and 0 < size < 0x400000 and a + PB == h + 20 + size + 4 * 0 + ((-size) % 4) + 4:
        recs.append((h + 20, size, typ))
    elif one == 1 and b + PB == h + 20 and 0 < size < 0x400000:
        recs.append((h + 20, size, typ | 0x1000))
c = collections.Counter(t for _, _, t in recs)
print(len(recs), "streams; types", dict(c))
sz = collections.defaultdict(list)
for o, s, t in recs: sz[t].append(s)
for t, v in sorted(sz.items()): print(hex(t), len(v), "sum", sum(v), "min", min(v), "max", max(v))
for r in recs[:12]: print(hex(r[0]), r[1], hex(r[2]), d[r[0]:r[0]+16].hex(" "))
