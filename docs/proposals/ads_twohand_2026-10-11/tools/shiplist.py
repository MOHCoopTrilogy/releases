"""Per pistol of the ship cut: its tiks (base, finishes, variants), the client rows they carry, the staged gun files and
the hands rows - section (b) of PISTOLS_SHIP.md.      python shiplist.py <ship dir> > out.md
"""
import sys, os, re
ship = os.path.abspath(sys.argv[1])
wd = os.path.join(ship, 'models', 'weapons')
FIN = re.compile(r'_(bloody|blued|camo_desert|camo_winter|camo_woodland|chrome|gold)$')
# base tik stem -> (name, hands prefix, per-weapon row key or None)
GUNS = [('colt45', 'Colt 45', 'colt45', None), ('colt45_coltpa', 'Colt 45 (Pacific)', 'colt45', None), ('colt_silenced', 'Silenced Colt .45', 'colt45', None),
        ('p38', 'Walther P38', 'p38', None), ('p38silenced', 'Silenced Walther P38', 'colt45', None),
        ('it_w_beretta', 'Beretta', 'beretta', None), ('berettasilenced', 'Silenced Beretta', 'colt45', None),
        ('lugerp08', 'Luger P08', 'colt45', 'luger_p08'), ('lugerp08silenced', 'Silenced Luger P08', 'colt45', 'silenced_luger_p08'),
        ('nambu', 'Nambu Type 14', 'colt45', None), ('ppk', 'Walther PPK', 'colt45', 'walther_ppk'),
        ('tt33', 'TT-33 Tokarev', 'colt45', None), ('tt33silenced', 'Silenced TT-33', 'colt45', None),
        ('welrod', 'Welrod', 'colt45', 'welrod'), ('silencedpistol', 'Hi-Standard Silenced', 'histandard', None),
        ('webley_revolver', 'Webley Revolver', 'webley', None), ('nagant_revolver', 'Nagant Revolver', 'nagantrev', None), ('colt45_colt1911w', 'Webley Mk VI', 'webley', None)]
ROWS = ('reload_ads_loaded', 'reload_ads_empty', 'reload_empty', 'idle_empty', 'fire_ads', 'reload_end_ads', 'reload_single_ads')
tiks = {fn[:-4].lower(): fn for fn in os.listdir(wd) if fn.lower().endswith('.tik')}
staged = set()
for dp, dn, fns in os.walk(ship):
    for fn in fns:
        staged.add(os.path.relpath(os.path.join(dp, fn), ship).replace(os.sep, '/').lower())
fps = open(os.path.join(ship, 'models', 'player', 'base', 'fps_anims_pistol.txt'), 'rb').read().decode('latin-1')
bases = [g[0] for g in GUNS]
used = set()
print('| pistol | tiks shipped (base; finishes; variants) | gun-side client rows | staged gun files | hands rows |')
print('|---|---|---|---|---|')
for base, name, prefix, key in GUNS:
    fam = sorted(s for s in tiks if (s == base or s.startswith(base + '_')) and not any(b != base and len(b) > len(base) and (s == b or s.startswith(b + '_')) for b in bases))
    used.update(fam)
    fins = [s for s in fam if FIN.search(s)]
    var = [s for s in fam if s != base and not FIN.search(s)]
    tx = open(os.path.join(wd, tiks[base]), 'rb').read().decode('latin-1')
    s = '\n'.join(l.split('//')[0] for l in tx.replace('\r\n', '\n').split('\n'))
    path = re.search(r'(?im)^\s*path\s+(\S+)', s).group(1).strip('/')
    skd = re.search(r'(?im)^\s*skelmodel\s+(\S+)', s).group(1)
    rows = []
    files = set()
    for r in ROWS:
        m = re.search(r'(?im)^\s*%s\s+(\S+\.skc)' % r, s)
        if m:
            rows.append(r)
            f = ('%s/%s' % (path, m.group(1))).lower()
            if f in staged:
                files.add(m.group(1))
    if ('%s/%s' % (path, skd)).lower() in staged:
        files.add(skd + ' (mesh)')
    hr = sorted(set(re.findall(r'(?m)^\s*(%s_(?:charge|idle|reload\w*|cycle\w*))\s' % re.escape(prefix), fps)))
    if key:
        hr += sorted(set(re.findall(r'(?m)^\s*(coopr_%s_\w+)\s' % re.escape(key), fps)))
    print('| %s | `%s.tik`; %d finishes%s; variants: %s | %s | `%s/`: %s | %s |' % (
        name, base, len(fins), (' (' + ' '.join(x[len(base) + 1:] for x in fins) + ')') if fins else '', ', '.join('`%s`' % v for v in var) or '-',
        ' '.join(rows) or '-', path, ', '.join(sorted(files)) or '-', ' '.join(hr)))
rest = sorted(set(tiks) - used)
print('\nOther staged tiks in the cut (same rows as their family, not listed above): ' + ', '.join('`%s`' % r for r in rest))
