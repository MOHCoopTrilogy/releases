#!/usr/bin/env python3
"""nav A/B breakdown: for given maps, report the two navmesh-quality stuck causes from a soak dir.
  - bare_geom = BOTBLOCK world=1 count (bot pathed into raw world geometry: mesh-vs-collision mismatch)
  - nopath_pct = %% of 'wants to move' probe frames with pth=0 AND spd<12 (no usable path -> stuck in place)
  - stuck_pct  = %% of 'wants to move' frames with spd<12 (any stuck)
  - reach cols come from bot_soak_report; here we isolate nav causes.
  python docs/tools/nav_breakdown.py <soakdir> m4l2 m5l1a m3l3 t2l1
"""
import re, sys, os
FIELD = re.compile(r'\b([a-z]+)=(-?\d+(?:\.\d+)?)')
def analyze(path):
    wants=stuck=nopath=0
    bare=0
    for line in open(path,'r',encoding='latin-1',errors='replace'):
        if 'BOTBLOCK' in line:
            m=re.search(r'\bworld=(\d)', line)
            if m and m.group(1)=='1': bare+=1
            continue
        if 'BOTPROBE' not in line: continue
        kv=dict((k,float(v)) for k,v in FIELD.findall(line))
        if kv.get('al',1)<0.5: continue
        if abs(kv.get('fm',0))>20 or abs(kv.get('rm',0))>20:
            wants+=1
            if kv.get('spd',99)<12:
                stuck+=1
                if kv.get('pth',1)==0: nopath+=1
    return dict(wants=wants,stuck=stuck,nopath=nopath,bare=bare,
               stuck_pct=round(100*stuck/wants) if wants else 0,
               nopath_pct=round(100*nopath/wants) if wants else 0)
sd=sys.argv[1]; maps=sys.argv[2:]
print('%-7s %8s %8s %9s %9s'%('MAP','stuck%','nopath%','bareGeom','wantFrms'))
for m in maps:
    p=os.path.join(sd,m+'.log')
    if not os.path.isfile(p): print('%-7s  (no log)'%m); continue
    r=analyze(p)
    print('%-7s %7d%% %7d%% %9d %9d'%(m,r['stuck_pct'],r['nopath_pct'],r['bare'],r['wants']))
