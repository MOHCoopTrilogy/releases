"""[bug-2870 round 5] Every Push map's END-ZONE CENTRES (the bots' goals: push_publishTargets sends each team to the centre of
the enemy's end zone ZA[1] / ZA[N]) must stand on navmesh that both homes can reach (directed). A band-AABB centre off the mesh
made t1l1/t3l1 bots chase unreachable goals. usage (repo root, nav dumps needed):
    python docs/tools/push_endzone_check.py hzm-mohaa-coop-mod/coop_mod/mp_push_bsp.scr [hzm-mohaa-coop-mod/coop_mod/mp_push_maps.scr]"""
import re, subprocess, sys, os
seeds = {}
for fn in sys.argv[1:]:
    for m in re.finditer(r'^seed_(\w+):(.*?)(?=^seed_|\Z)', open(fn, encoding='utf-8').read(), re.S | re.M):
        seeds[m.group(1)] = m.group(2)
here = os.path.dirname(os.path.abspath(__file__))
bad = 0
for m in sorted(seeds):
    if not os.path.exists('server_home_soak/maintt/navdump/maps/%s.bsp_mp.txt' % m):
        print('%-6s no nav dump' % m); continue
    blk = seeds[m]
    def z(k, i): return [float(v) for v in re.search(r'coop_mpPush%s\[%d\] = \( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \)' % (k, i), blk).groups()]
    n = int(re.search(r'coop_mpPushZN = (\d+)', blk).group(1))
    ca = [(a + b) / 2 for a, b in zip(z('ZAmin', 1), z('ZAmax', 1))]; cn = [(a + b) / 2 for a, b in zip(z('ZAmin', n), z('ZAmax', n))]
    home = lambda tag: re.findall(r'origin = \( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \)(?:\s+local\.e\.angle = [\d.]+)?\s+local\.e\.targetname = "%s"' % tag, blk)[0]
    env = dict(os.environ, HOMES='%s,%s,%s;%s,%s,%s' % (home('alh') + home('axh')), SNAP='1')
    pts = ['%.0f,%.0f,%.0f' % (ca[0], ca[1], z('ZAmax', 1)[2]), '%.0f,%.0f,%.0f' % (cn[0], cn[1], z('ZAmax', n)[2])]
    out = subprocess.run([sys.executable, os.path.join(here, 'nav_dirreach.py'), m] + pts, capture_output=True, text=True, env=env).stdout.strip().splitlines()
    ok = len(out) == 2 and all('AL: to yes' in l and 'AX: to yes' in l for l in out)
    bad += not ok
    print('%-6s %s' % (m, 'OK' if ok else 'PROBLEM  ' + ' | '.join(l.strip() for l in out)))
print('maps with an unreachable end-zone centre:', bad)
