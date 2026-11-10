"""Test overlay pk3 from this worktree's wpnfix sources: every manifest entry marked new, plus any extra <rel>=<file> pairs.
    python mkov.py <out.pk3> [prefix ...]      (prefix filters the members, e.g. models/weapons/coop_bren)"""
import os, sys, json, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'tools', 'assets', 'wpnfix'))
out = sys.argv[1]
pre = sys.argv[2:]
man = json.load(open(os.path.join(SRC, 'wpnfix_manifest.json')))
n = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as z:
    for rel in sorted(man):
        if pre and not any(rel.startswith(p) for p in pre):
            continue
        p = os.path.join(SRC, *rel.split('/'))
        if os.path.isfile(p):
            z.write(p, rel); n += 1
print(out, n, 'members')
