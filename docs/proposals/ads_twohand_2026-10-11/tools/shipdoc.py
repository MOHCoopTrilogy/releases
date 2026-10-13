"""PISTOLS_SHIP.md = PISTOLS_SHIP.tmpl.md with the generated tables filled in (ship list, dedicated table, declared rows).

    python shipdoc.py        (after shipcut.py and `srvrows.py <ship> > srvrows_ship.txt`)
"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11'
t = open(os.path.join(HERE, 'PISTOLS_SHIP.tmpl.md'), encoding='utf-8').read()
shl = subprocess.run([sys.executable, os.path.join(HERE, 'shiplist.py'), os.path.join(P, 'ship')], capture_output=True, text=True).stdout.strip()
decl = []
last = None
for l in open(os.path.join(HERE, 'srvrows_ship.txt'), encoding='latin-1').read().split('\n'):
    if l.startswith('decl  '):
        m = re.match(r'decl  (\S+): (.*)', l)
        f = m.group(1).split('/')[-1]
        last = None if re.search(r'_(bloody|blued|camo_\w+|chrome|gold|lv_ttwebley)\.tik$', f) else f
        if last:
            decl.append('| `%s` | %s |' % (f, m.group(2).replace('|', '/')[:170]))
    elif l.startswith('      = ') and last:
        decl.append('| | *%s* |' % l[8:])
dt = ('| file | row: released -> staged |\n|---|---|\n' + '\n'.join(decl)
      + '\n\nThe 14 Webley / Nagant finish tiks and `webley_revolver_lv_ttwebley.tik` carry the same rows as their base tik.')
tail = [l for l in open(os.path.join(HERE, 'srvrows_ship.txt'), encoding='latin-1').read().split('\n') if 'weapon tiks checked' in l][-1]
n = sum(len(f) for _, _, f in os.walk(os.path.join(P, 'ship')))
t = (t.replace('{{SHIPLIST}}', shl).replace('{{DEDTABLE}}', open(os.path.join(HERE, 'dedtable.md')).read().strip()).replace('{{DECL}}', dt)
      .replace('{{CHECK}}', tail.strip()).replace('{{NFILES}}', str(n)))
assert '{{' not in t, re.findall(r'\{\{\w+\}\}', t)
open(os.path.join(P, 'PISTOLS_SHIP.md'), 'w', encoding='utf-8', newline='\n').write(t)
print('PISTOLS_SHIP.md', len(t), 'chars;', tail.strip(), ';', n, 'files in ship')
