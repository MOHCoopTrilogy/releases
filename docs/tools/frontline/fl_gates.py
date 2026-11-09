#!/usr/bin/env python3
"""Pilot go/no-go measurements from logs. Our own code.

  fl_gates.py soak <soak.log> <converted.pk3> <mapname>
      bot reach = share of the walkable area (256u cells holding a pathnode from the BSP entity lump)
                  that some bot entered; stuck = share of bot samples flagged why=stu* or at speed < 12
                  while the bot wants to move.
  fl_gates.py log <qconsole.log>
      counts ^~^~^ Script Error lines, FLOBJ / FLCUE / FLTEST markers.
"""
import re
import sys
import zipfile

CELL = 256.0


def pathnodes(pk3, mapname):
    z = zipfile.ZipFile(pk3)
    b = z.read(f"maps/{mapname}.bsp")
    import struct
    off, ln = struct.unpack_from("<ii", b, 12 + 8 * 14)
    ent = b[off:off + ln].decode("latin-1")
    out = []
    for blk in ent.split("}"):
        if '"info_pathnode"' in blk:
            m = re.search(r'"origin" "(\S+) (\S+) (\S+)"', blk)
            out.append(tuple(float(v) for v in m.groups()))
    return out


def cell(x, y):
    return (int(x // CELL), int(y // CELL))


def soak(log, pk3, mapname):
    nodes = pathnodes(pk3, mapname)
    want = {cell(x, y) for x, y, _ in nodes}
    seen, n, stuck = set(), 0, 0
    rx = re.compile(r"BOTPROBE .*?px=(-?\d+) py=(-?\d+) pz=(-?\d+) spd=(\d+).*?why=(\S+)")
    for line in open(log, encoding="latin-1"):
        m = rx.search(line)
        if not m:
            continue
        x, y, z, spd, why = int(m[1]), int(m[2]), int(m[3]), int(m[4]), m[5]
        n += 1
        c = cell(x, y)
        for dx in (-1, 0, 1):          # a bot passing a cell covers its neighbours' nodes too
            for dy in (-1, 0, 1):
                seen.add((c[0] + dx, c[1] + dy))
        if why.startswith("stu") or spd < 12:
            stuck += 1
    reach = len(want & seen) / max(1, len(want))
    print(f"samples={n} nodes={len(nodes)} cells={len(want)} reached={len(want & seen)} "
          f"reach={100 * reach:.1f}% stuck={100 * stuck / max(1, n):.1f}%")


def logcheck(path):
    t = open(path, encoding="latin-1").read()
    se = re.findall(r"\^~\^~\^ Script Error[^\n]*", t)
    print("script_errors", len(se))
    for e in sorted(set(se))[:15]:
        print("  ", e[:160])
    for tag in ("FLOBJ", "FLCUE", "FLTEST", "FLAI", "FLMISSION"):
        hits = re.findall(r"\^~\^~\^ " + tag + r"[^\n]*", t)
        print(tag, len(hits), hits[-6:])


if __name__ == "__main__":
    if sys.argv[1] == "soak":
        soak(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        logcheck(sys.argv[2])


def navreach(dump, pk3, mapname, start):
    """Directed reach on the engine's own navmesh dump (nav_dump 1): share of pathnodes whose nearest
    walkable poly (within 96u horizontally, 72u vertically) is reachable from the player start."""
    import collections
    polys, out = {}, collections.defaultdict(set)
    for line in open(dump):
        p = line.split()
        if not p:
            continue
        if p[0] == "P":
            nv = int(p[5])
            vs = [tuple(float(a) for a in p[6 + 3 * k:9 + 3 * k]) for k in range(nv)]
            polys[int(p[1])] = tuple(sum(v[i] for v in vs) / nv for i in range(3))
        elif p[0] == "L":
            out[int(p[1])].add(int(p[2]))
    grid = collections.defaultdict(list)
    for i, c in polys.items():
        grid[cell(c[0], c[1])].append(i)

    def near(pt, rh=96, rv=72):
        best, bd = None, 1e18
        cx, cy = cell(pt[0], pt[1])
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in grid[(cx + dx, cy + dy)]:
                    c = polys[i]
                    d = (c[0] - pt[0]) ** 2 + (c[1] - pt[1]) ** 2
                    if d < bd and d < (rh * 3) ** 2 and abs(c[2] - pt[2]) < rv * 2:
                        best, bd = i, d
        return best
    s = near(start)
    seen, q = {s}, [s]
    while q:
        a = q.pop()
        for b in out[a]:
            if b not in seen:
                seen.add(b)
                q.append(b)
    nodes = pathnodes(pk3, mapname)
    onmesh = reach = 0
    miss = collections.Counter()
    for n in nodes:
        i = near((n[0], n[1], n[2] - 16))
        if i is None:
            miss[cell(n[0], n[1])] += 1
            continue
        onmesh += 1
        if i in seen:
            reach += 1
        else:
            miss[cell(n[0], n[1])] += 1
    print(f"polys={len(polys)} start_poly={s} region={len(seen)} pathnodes={len(nodes)} on_mesh={onmesh} "
          f"reachable={reach} reach={100 * reach / max(1, len(nodes)):.1f}%")
    print("unreached cells (x256):", miss.most_common(15))


if __name__ == "__main__" and sys.argv[1] == "navreach":
    navreach(sys.argv[2], sys.argv[3], sys.argv[4], tuple(float(v) for v in sys.argv[5].split(",")))
