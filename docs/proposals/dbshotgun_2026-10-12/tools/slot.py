"""the shared private-client slot (docs/tools/harness_guard.py):  python tools/slot.py [release]
prints the holder and every game process; `release` frees the slot ONLY when it is ours (hudfeed4) and no process of
that harness is alive"""
import sys
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\tools')
import harness_guard as hg

procs = hg.classify()
for p in procs:
    print('PROC', p)
try:
    h = hg.slot_holder()
except Exception as e:
    h = 'error %s' % e
print('SLOT', h)
if len(sys.argv) > 1 and sys.argv[1] == 'release':
    mine = [p for p in procs if p.get('owner') == 'hudfeed4']
    owner = (h or {}).get('owner') if isinstance(h, dict) else None
    if owner == 'hudfeed4' and not mine:
        hg.release_slot('hudfeed4'); print('released')
    else:
        print('not released (holder %r, own processes %d)' % (owner, len(mine)))
