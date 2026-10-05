"""parse models/player/base/anims_*.txt (live VFS) -> {anim: {'skc': path, 'ev': [(frametoken, cmd...)]}}"""
import re, sys
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import vfs
def parse():
    out = {}
    for k in sorted(vfs.index()):
        if not (k.startswith('models/player/base/anims') and k.endswith('.txt')):
            continue
        d = vfs.read(k).decode('latin1'); path = 'models/human/animation/'; cur = None
        for l in d.split('\n'):
            s = re.sub(r'//.*', '', l).strip()
            if not s: continue
            m = re.match(r'^\$path\s+(\S+)', s)
            if m: path = m.group(1).rstrip('/') + '/'; continue
            m = re.match(r'^([A-Za-z0-9_]+)\s+(\S+\.skc)', s)
            if m:
                cur = m.group(1).lower(); out.setdefault(cur, {'skc': path + m.group(2), 'ev': [], 'file': k}); continue
            m = re.match(r'^(\S+)\s+(attachmodel|removeattachedmodel|weaponcommand)\s+(.*)$', s, re.I)
            if m and cur:
                out[cur]['ev'].append((m.group(1).lower(), m.group(2).lower(), m.group(3).split()))
    return out
if __name__ == '__main__':
    A = parse()
    for n in sys.argv[1:]:
        a = A.get(n.lower()); print(n, a and a['skc'], a and a['file'], a and [e for e in a['ev'] if e[1] != 'weaponcommand' or 'attachtohand' in e[2]])
