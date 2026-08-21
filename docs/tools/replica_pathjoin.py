"""Join AI pathfinding failures back to the actors that caused them.

The engine prints one line per failed path with an entnum and a targetname, but a dynamically
spawned actor has no targetname - so a count-scaling REPLICA and a map spawner's own actor are
indistinguishable in that log. aihandler.scr::coop_spawnReplica now prints a `^~^~^ REPLICA ent=N`
line at birth (gated on coop_aggroDebug 1); this joins the two on entnum and reports who is
actually generating the spam.

Usage:
    coop_aggroDebug 1     (in the game console, before the fight)
    ... play ...
    python docs/tools/replica_pathjoin.py [path-to-qconsole.log]
"""
import re
import sys
import collections
import statistics

LOG = sys.argv[1] if len(sys.argv) > 1 else 'G:/mohaa-gl2/home/maintt/qconsole.log'

RE_FAIL = re.compile(
    r"Path not found in '(\S+)' for \(entnum (\d+), radnum (-?\d+), targetname '([^']*)'\)"
    r" from \((-?[\d.]+) (-?[\d.]+) (-?[\d.]+)\) to \((-?[\d.]+) (-?[\d.]+) (-?[\d.]+)\)")
RE_REP = re.compile(
    r"\^~\^~\^ REPLICA ent=(\d+) idx=(\d+) at (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)"
    r" anchor (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)")

replicas = {}
fails = []

for line in open(LOG, errors='replace'):
    m = RE_REP.search(line)
    if m:
        # a slot can be recycled across a long session; last spawn wins
        replicas[int(m.group(1))] = {
            'idx': int(m.group(2)),
            'pos': tuple(float(m.group(i)) for i in (3, 4, 5)),
            'anchor': tuple(float(m.group(i)) for i in (6, 7, 8)),
        }
        continue
    m = RE_FAIL.search(line)
    if m:
        fails.append({
            'fn': m.group(1),
            'ent': int(m.group(2)),
            'name': m.group(4),
            'frm': tuple(float(m.group(i)) for i in (5, 6, 7)),
            'to': tuple(float(m.group(i)) for i in (8, 9, 10)),
        })

print('=' * 84)
print('replica spawns logged : %d' % len(replicas))
print('path failures logged  : %d' % len(fails))
print('=' * 84)

if not replicas:
    print('\nNo REPLICA lines found. Either coop_aggroDebug was not 1 during the fight,')
    print('or no replicas spawned (count-scaling only duplicates with enough players).')
    print('Without them this cannot tell a replica from a map actor - run again with it set.')

byent = collections.Counter(f['ent'] for f in fails)
rep_fails = sum(c for e, c in byent.items() if e in replicas)
map_fails = sum(c for e, c in byent.items() if e not in replicas)

if fails:
    print('\nATTRIBUTION')
    print('  from replicas   : %6d  (%5.1f%%)  across %d entities'
          % (rep_fails, 100.0 * rep_fails / len(fails),
             len([e for e in byent if e in replicas])))
    print('  from map actors : %6d  (%5.1f%%)  across %d entities'
          % (map_fails, 100.0 * map_fails / len(fails),
             len([e for e in byent if e not in replicas])))

print('\nPER-ENTITY BREAKDOWN (worst first)')
print('  %-7s %-9s %-26s %6s  %s' % ('entnum', 'source', 'targetname', 'fails', 'position'))
print('  ' + '-' * 78)
for ent, cnt in byent.most_common(20):
    f = next(x for x in fails if x['ent'] == ent)
    src = 'REPLICA' if ent in replicas else 'map'
    nm = f['name'] or '<unnamed>'
    print('  %-7d %-9s %-26s %6d  (%.0f %.0f %.0f)'
          % (ent, src, nm[:26], cnt, f['frm'][0], f['frm'][1], f['frm'][2]))

# how far were they being asked to travel?
if fails:
    dist = []
    for f in fails:
        dx = f['to'][0] - f['frm'][0]
        dy = f['to'][1] - f['frm'][1]
        dist.append((dx * dx + dy * dy) ** 0.5)
    print('\nHOW FAR THE UNREACHABLE DESTINATION WAS')
    print('  median %.0f u   p90 %.0f u   max %.0f u'
          % (statistics.median(dist), sorted(dist)[int(len(dist) * .9)], max(dist)))
    print('  (a replica is placed within 360u of its parent, so anything much larger means it')
    print('   inherited a destination from a parent that could reach it, and it cannot)')

# did any replica land somewhere unreasonable?
if replicas:
    off = [(e, r) for e, r in replicas.items()
           if ((r['pos'][0] - r['anchor'][0]) ** 2
               + (r['pos'][1] - r['anchor'][1]) ** 2) ** 0.5 > 400
           or abs(r['pos'][2] - r['anchor'][2]) > 180]
    print('\nREPLICAS PLACED OUTSIDE THEIR OWN LIMITS (should be none - the scatter caps at 360u')
    print('and rejects floors more than 180u off):')
    if not off:
        print('  none - every replica landed within spec')
    for e, r in off[:10]:
        d = ((r['pos'][0] - r['anchor'][0]) ** 2 + (r['pos'][1] - r['anchor'][1]) ** 2) ** 0.5
        print('  ent %-5d %.0fu from anchor, dz %.0f  at (%.0f %.0f %.0f)'
              % (e, d, r['pos'][2] - r['anchor'][2], r['pos'][0], r['pos'][1], r['pos'][2]))
print()
