"""[bug-2870] Directed spawn sweep: every Push spawn must reach BOTH homes on the bot navmesh, and the homes must reach each other.
usage: python docs/tools/push_spawn_sweep.py hzm-mohaa-coop-mod/coop_mod/mp_push_bsp.scr hzm-mohaa-coop-mod/coop_mod/mp_push_maps.scr
(needs nav dumps: soak with -Extra '+set,nav_dump,1'; run from the repo root)   (maps file wins for a map in both)"""
import sys, re, os
sys.path.insert(0, 'docs/tools')
import gen_push_from_bsp as G
seeds = {}
for fn in sys.argv[1:3]:
    for m in re.finditer(r'^seed_(\w+):(.*?)(?=^seed_|\Z)', open(fn, encoding='utf-8').read(), re.S | re.M):
        seeds[m.group(1)] = m.group(2)
rx = re.compile(r'spawn (info_player_\w+)\s+local\.e\.origin = \( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \)(?:\s+local\.e\.angle = [\d.]+)?\s+local\.e\.targetname = "(\w+)"')
tot = bad_tot = 0
for mp in sorted(seeds):
    if not os.path.exists(G.NAVDUMP % mp):
        print('%-6s no nav dump' % mp); continue
    sp = [(c, float(x), float(y), float(z), t) for c, x, y, z, t in rx.findall(seeds[mp])]
    floor = None
    for s in sp:  # any spawn with a (loose) floor gives us the floor() helper
        try:
            floor = G.nav_from(mp, (s[1], s[2], s[3])).floor
            break
        except SystemExit:
            continue
    if floor is None:
        print('%-6s no spawn has any floor' % mp); continue
    def firsthome(tag):
        for s in sp:
            if s[4] == tag and floor((s[1], s[2], s[3])) is not None:
                return (s[1], s[2], s[3])
        return None
    ha, hx = firsthome('alh'), firsthome('axh')
    if not ha or not hx:
        print('%-6s HOME WITHOUT FLOOR  alh %s  axh %s' % (mp, ha, hx)); continue
    ra, rxh = G.nav_reach(mp, [ha]), G.nav_reach(mp, [hx])
    uniq = sorted({(s[1], s[2], s[3]): s for s in sp}.values(), key=lambda s: s[4])
    bad = []
    for s in uniq:
        n = (s[1], s[2], s[3])
        f = floor(n)
        why = 'NO FLOOR within 400u (floats)' if f is None else ('' if (ra(n) and rxh(n)) else
              'cannot reach %s' % ('/'.join(k for k, ok in (('allied home', ra(n)), ('axis home', rxh(n))) if not ok)))
        if why: bad.append((s[4], n, why))
    homes_ok = rxh(ha) and ra(hx)
    tot += len(uniq); bad_tot += len(bad)
    print('%-6s %2d spawn points  bad %2d  homes mutually reachable: %s' % (mp, len(uniq), len(bad), 'yes' if homes_ok else 'NO'))
    for tg, n, why in bad: print('         %-4s (%d %d %d)  %s' % (tg, n[0], n[1], n[2], why))
print('TOTAL', tot, 'spawn points, bad', bad_tot)
