"""one-off repair of wiring/patch_torso_dbs.py (a Git-Bash heredoc turned \\t / \\n into real characters)"""
import re
p = r'C:\mohaa-coop-dev\docs\proposals\dbshotgun_2026-10-12\wiring\patch_torso_dbs.py'
L = open(p, encoding='utf-8').read().split('\n')
i = [k for k, l in enumerate(L) if l.startswith('QUICK_ROW = (')][0]
j = [k for k, l in enumerate(L) if l.startswith('REFIRE_STATE = (')][0]
new = [
    "QUICK_ROW = ('\\t\\t// HZM coop %s an open double barrel is shut before the owed shot: the full end row, not the quick hand-back\\n'",
    "             '\\t\\tRELOAD_SHOTGUN_BREAK_END\\t: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP \"mainhand\" %s\\n') % (MARK, NAME)",
]
L[i:j] = new
k = [n for n, l in enumerate(L) if l.strip().startswith('rx_q = re.compile(')][0]
e = [n for n, l in enumerate(L) if l.strip().startswith('assert len(rx_q.findall(s))')][0]
L[k:e] = ["    rx_q = re.compile(r'^[ \\t]*RELOAD_SHOTGUN_BREAK_QUICK[ \\t]+: \\+ATTACK_PRIMARY HAS_AMMO_IN_CLIP \"mainhand\"[^\\n]*\\n', re.M)"]
k = [n for n, l in enumerate(L) if l.strip().startswith("print('%s: %s' % (p, 'already patched'")][0]
L[k] = ("    print('%s: %s' % (p, 'already patched' if out == raw else '%d torso rows, 1 aimed-refire exit row + the routing state "
        "COOP_DBS_REFIRE_AIM, %d break-off routing rows' % (len(re.findall(r'(?m)^\\t\\tcoop_dbs_', out)), out.count('an open double barrel is shut'))))")
open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
print('repaired')
