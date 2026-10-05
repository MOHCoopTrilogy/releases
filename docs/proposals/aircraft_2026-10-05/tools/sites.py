"""sites.py <map...> - pick a strike target T and a camera spot C for the in-engine captures (offline, BSP only).
T = outdoor pathnode near the play centroid with full sky clearance; C = an outdoor node 1100-1500u away with a
clear eye-height line to T (every sample in a valid leaf) and open sky above. Prints  map Tx Ty Tz Cx Cy Cz yaw."""
import math, struct, sys
import sky_envelope as E

def pick(m):
    b, _ = E.find_bsp(m); s = E.BSP(b)
    ents = E.parse_ents(s.ents)
    nodes = [tuple(float(v) for v in e["origin"].split()[:3]) for e in ents
             if e.get("classname", "").lower() == "info_pathnode" and "origin" in e]
    def clear(x, y, z):
        zz = z + 48
        while zz < z + 4000 and s.valid(x, y, zz):
            zz += 64
        return zz - z, s.is_sky_leaf(s.leaf(x, y, zz + 1))
    # static models: trees block the sky but are not in the BSP leaves
    off, ln = struct.unpack_from("<ii", b, 12 + 25 * 8)
    trees = []
    for i in range(ln // 164):
        o = off + i * 164
        name = b[o:o + 128].split(bytes(1))[0].decode("latin-1").lower()
        if any(k in name for k in ("tree", "bush", "foliage", "pine", "oak", "birch", "hedge")):
            trees.append(struct.unpack_from("<3f", b, o + 128))
    def treefree(p, r=700):
        return all(math.hypot(p[0] - t[0], p[1] - t[1]) > r for t in trees)
    out = []
    for n in nodes[::max(1, len(nodes) // 500)]:
        c, sky = clear(*n)
        if sky and c > 700:
            out.append((n, c))
    cx = sorted(p[0][0] for p in out)[len(out) // 2]; cy = sorted(p[0][1] for p in out)[len(out) // 2]
    out.sort(key=lambda p: math.hypot(p[0][0] - cx, p[0][1] - cy) - 0.5 * p[1])
    for (t, ct) in out[:40]:
        for (c, cc) in out:
            d = math.hypot(c[0] - t[0], c[1] - t[1])
            if not (1100 < d < 1500) or abs(c[2] - t[2]) > 200 or not treefree(c):
                continue
            ok = all(s.valid(c[0] + (t[0] - c[0]) * k / 20, c[1] + (t[1] - c[1]) * k / 20,
                             c[2] + 60 + (t[2] - c[2]) * k / 20) for k in range(21))
            if ok:
                yaw = math.degrees(math.atan2(t[1] - c[1], t[0] - c[0]))
                return t, c, yaw
    return None

for m in sys.argv[1:]:
    r = pick(m)
    if r:
        t, c, yaw = r
        print(m, "%d %d %d" % t, "%d %d %d" % c, "%d" % yaw)
    else:
        print(m, "none")
