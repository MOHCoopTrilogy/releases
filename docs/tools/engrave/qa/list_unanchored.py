import sys, re, glob, json, os
sys.path.insert(0, r"C:\hzm-root-benchfix\docs\tools\engrave")
import gunmesh
MOD = r"C:\mohaa-coop-dev\hzm-mod-benchfix"
uses = set(l.split()[1].lower() for l in open(MOD + r"\scripts\hzm_engrave_anchors.txt") if l.startswith("use "))
tiks = set()
for f in glob.glob(MOD + r"\ui\loadout\*.cfg"):
    for m in re.finditer(r'coop_loPrev "([^"]+)"', open(f, encoding="latin-1").read()):
        if m.group(1): tiks.add(m.group(1).lower())
miss = sorted(t for t in tiks if t not in uses)
groups = {}
for t in miss:
    tk = gunmesh.read_tik(t)
    if not tk:
        print("no tik", t); continue
    groups.setdefault((tk["path"].lower(), (tk["skelmodel"] or "").lower()), []).append(t)
def wname(t, depth=0):
    b = gunmesh.vfs.read(t)
    if not b or depth > 4: return None
    s = b.decode("latin-1", "replace")
    m = re.search(r'(?im)^\s*name\s+"([^"]+)"', s) or re.search(r'(?im)^\s*name\s+(\S+)', s)
    if m: return m.group(1)
    for inc in re.findall(r'(?im)^\s*\$include\s+(\S+)', s):
        r = wname(inc, depth + 1)
        if r: return r
    return None
out = []
for k, ts in sorted(groups.items()):
    rep = min(ts, key=len)
    out.append([rep, wname(rep), "new", len(ts)])
    print(rep, wname(rep), len(ts))
json.dump([o[:3] for o in out], open(sys.argv[1], "w"), indent=0)
