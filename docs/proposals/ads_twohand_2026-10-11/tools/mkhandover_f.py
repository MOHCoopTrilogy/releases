"""mkhandover_f.py <stances.json> <bug ids text>   prepend the 2026-10-13 pistol-lane handover to the proposal README"""
import io, json, os, sys
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\README.md'
HERE = os.path.dirname(os.path.abspath(__file__))
st = json.load(open(sys.argv[1])) if os.path.isfile(sys.argv[1]) else {}
bugs = sys.argv[2] if len(sys.argv) > 2 else '?'
cb = json.load(open(os.path.join(HERE, 'centrebox.json')))
p19 = json.load(open(os.path.join(HERE, 'centrebox_pa19.json')))
NAMES = [('welrod', 'Welrod'), ('lugerp08', 'Luger P08'), ('lugerp08silenced', 'Silenced Luger P08'), ('mauser_c96', 'Mauser C96 (clip parts, UNFINISHED)'),
         ('ppk', 'Walther PPK'), ('tt33', 'TT-33'), ('tt33silenced', 'Silenced TT-33'), ('colt45_coltpa', 'Colt 45 (Pacific)'),
         ('colt_silenced', 'Silenced Colt .45'), ('berettasilenced', 'Silenced Beretta'), ('nambu', 'Nambu Type 14'),
         ('p38silenced', 'Silenced Walther P38'), ('colt45', 'Colt 45'), ('p38', 'Walther P38'), ('beretta', 'Beretta')]
STS = ['crouch', 'prone', 'standL', 'standR']


def f(d, k):
    v = d.get(k)
    return ('%.2f' % v['xmax']) if v and v.get('env') else 'n/m'


rows = []
for g, nm in NAMES:
    src = p19 if g in p19 else cb
    run = src.get(g, {}).get('run', '?')
    rows.append('| %s | %s | %s | %s | %s |' % (nm, f(src, g), f(src, g + '_empty'), ' | '.join(f(st, '%s@%s_empty' % (g, s)) for s in STS), run))
tr = '| Mauser C96 (Trench C96) | %s | %s | n/m | n/m | n/m | n/m | pa19 |' % (f(p19, 'mauser_c96_c96trench'), f(p19, 'mauser_c96_c96trench_empty'))
srun = ' '.join(sorted(set(v.get('run', '') for v in st.values()))) or 'not run'
top = io.open(os.path.join(HERE, '_handover_f.md'), encoding='utf-8').read()
top = top.replace('@@TABLE@@', '\n'.join(rows + [tr])).replace('@@SRUN@@', srun).replace('@@BUGS@@', bugs)
old = io.open(P, encoding='utf-8').read()
assert old.startswith('# HANDOVER (2026-10-12 night, PISTOL lane')
old = old.replace('# HANDOVER (2026-10-12 night, PISTOL lane, after list items D and E) - read this first; everything below the line `# HANDOVER (2026-10-12 late evening` is history',
                  '# HANDOVER (2026-10-12 night, PISTOL lane, after list items D and E) - superseded by the section above; history from here on', 1)
io.open(P, 'w', encoding='utf-8', newline='\n').write(top + '\n---\n\n' + old)
print('README: %d chars on top, %d stance figures' % (len(top), len(st)))
