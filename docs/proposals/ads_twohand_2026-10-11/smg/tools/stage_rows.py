"""SMG lane: the staged models/player/base/fps_anims_smg.txt = the RELEASED fixes-pak copy (v1.10.21, the file the game
loads) with this lane's rows applied on top. The file is this lane's alone; it is still GENERATED so the hunks are
explicit and re-appliable after a release changes the base.

    python stage_rows.py            -> ../assets/models/player/base/fps_anims_smg.txt, prints every changed / added row
ROWS: (row, clip, crossblend or None) - an existing row is repointed (asserted), a new one is appended after `after`.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FX = r"C:\mohaa-coop-dev\docs\tools\assets\fixes\models\player\base\fps_anims_smg.txt"
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets', 'models', 'player', 'base', 'fps_anims_smg.txt'))

# aim poses with the support hand where the hip pose has it (smgpose.py; Sten = the pistol lane's magpose.py)
REPOINT = [
    ('sten_charge', 'viewmodel/sten/coop_sten_ads_mag.skc'),
    ('type100_charge', 'viewmodel/sten/coop_type100_ads_mag.skc'),
    ('mp40_charge', 'viewmodel/mp40/coop_mp40_ads_mag.skc'),
    ('ppsh_charge', 'viewmodel/ppsh/coop_ppsh_ads_mag.skc'),
    ('moschetto_charge', 'viewmodel/moschetto/coop_moschetto_ads_mag.skc'),
]
# (new row, clip, crossblend, after which row) - filled by the reload work
ADD = []
EXTRA = os.path.join(HERE, 'rows_extra.json')      # written by the bake tools: {"repoint": [[row, clip]], "add": [[row, clip, xb, after]]}


def main():
    import json
    rep, add = list(REPOINT), list(ADD)
    if os.path.isfile(EXTRA):
        e = json.load(open(EXTRA))
        rep += [tuple(x) for x in e.get('repoint', [])]
        add += [tuple(x) for x in e.get('add', [])]
    txt = open(FX, 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in txt else '\n'
    for row, clip in rep:
        rx = re.compile(r'(?m)^(\s*%s\s+)(\S+)([^\r\n]*)' % re.escape(row))
        ms = [m for m in rx.finditer(txt) if not m.group(0).lstrip().startswith('//')]
        assert len(ms) == 1, (row, len(ms))
        m = ms[0]
        if m.group(2) != clip:
            print('repoint  %-22s %s -> %s' % (row, m.group(2), clip))
        txt = txt[:m.start()] + m.group(1) + clip + m.group(3) + txt[m.end():]
    for row, clip, xb, after in add:
        rx0 = re.compile(r'(?m)^\s*%s\s+\S+[^\r\n]*' % re.escape(row))
        m0 = [m for m in rx0.finditer(txt) if not m.group(0).lstrip().startswith('//')]
        line = '\t%s\t\t%s\t\tcrossblend %s\t// HZM coop [ads-smg] staged' % (row, clip, xb)
        if m0:                                   # the row exists already (a released aimed row): repoint it
            assert len(m0) == 1, row
            print('replace  %s' % line.strip())
            txt = txt[:m0[0].start()] + line + txt[m0[0].end():]
            continue
        rx = re.compile(r'(?m)^\s*%s\s+\S+[^\r\n]*(\r?\n)' % re.escape(after))
        ms = [m for m in rx.finditer(txt) if not m.group(0).lstrip().startswith('//')]
        assert len(ms) == 1, (after, len(ms))
        # after the row's own { } block when it has one
        k = ms[0].end()
        rest = txt[k:]
        mb = re.match(r'\s*\{', rest)
        if mb:
            k += rest.index('}') + 1
            k = txt.index('\n', k) + 1
        txt = txt[:k] + line + nl + txt[k:]
        print('add      %s' % line.strip())
    # sanity: braces balance, no row twice
    body = '\n'.join(l.split('//')[0] for l in txt.splitlines())
    assert body.count('{') == body.count('}'), 'braces'
    seen = {}
    for l in body.splitlines():
        t = l.split()
        if len(t) >= 2 and t[1].lower().endswith('.skc'):
            assert t[0] not in seen, ('row twice', t[0])
            seen[t[0]] = t[1]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(txt.encode('latin-1'))
    print('wrote', OUT, len(seen), 'rows')


if __name__ == '__main__':
    main()
