"""The heavy lane's rows: fps_anims_mg.txt / fps_anims_shotgun.txt = the RELEASED fixes-pak copy + the edits below.

Both files are this lane's (no other lane stages them), so the full patched copy is written into heavy/assets; the
edits stay declarative here so the copy can be rebuilt on a newer released file (apply-on-top).

    python stage_rows.py [--without row,row]     -> assets/models/player/base/fps_anims_{mg,shotgun}.txt
`--without` leaves those rows as released (a BEFORE overlay for a still pair).
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv

# class -> [(row, clip, crossblend or None = keep / default 0.1, comment)]: an existing row is repointed, a new one is
# appended before the file's closing brace
EDITS = {
    'mg': [
        # step 1 (2026-10-12): aim pose with the support hand where the hip pose has it (handpose.py)
        ('bar_charge', 'viewmodel/mg/coop_bar_ads_hand.skc', None, 'support hand on the forearm as at the hip'),
        ('dp28_charge', 'viewmodel/coop_dp28/coop_dp28_ads_hand.skc', None, 'support hand on the forend as at the hip'),
        ('vickers_charge', 'viewmodel/Vickers/coop_vickers_ads_hand.skc', None, 'support hand on the forend as at the hip'),
        ('breda_charge', 'viewmodel/breda/coop_breda_ads_hand.skc', None, 'support hand under the receiver as at the hip'),
        # step 2: BAR aimed reload to the three rules (heavybake.py); an EMPTY gun gets the handle work
        ('bar_reload_ads', 'viewmodel/mg/bar_reload_ads.skc', None, 'aimed, rounds left: magazine only'),
        ('bar_reload_empty', 'viewmodel/mg/reload_bar.skc', 0.3, 'retail: hip reload of an empty gun (the retail clip; the row lets cgame find _empty_ads)'),
        ('bar_reload_empty_ads', 'viewmodel/mg/bar_reload_empty_ads.skc', 0.1, 'aimed, empty: magazine, then the left hand works the operating handle'),
        # 2b: braced variants (cgame ads-heavy-next picks <row>_adsb when the brace envelope is up): half the sag
        ('bar_reload_adsb', 'viewmodel/mg/bar_reload_adsb.skc', 0.1, 'aimed + braced, rounds left'),
        ('bar_reload_empty_adsb', 'viewmodel/mg/bar_reload_empty_adsb.skc', 0.1, 'aimed + braced, empty'),
    ],
    'shotgun': [],
}


def build(cls, without=()):
    rel = 'models/player/base/fps_anims_%s.txt' % cls
    txt = open(os.path.join(hv.FIXES, rel.replace('/', os.sep)), 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in txt else '\n'
    new = []
    for row, clip, xb, why in EDITS[cls]:
        if row in without:
            continue
        rx = re.compile(r'(?m)^(\s*%s\s+)(\S+)([^\r\n]*)' % re.escape(row))
        ms = [m for m in rx.finditer(txt) if not m.group(0).lstrip().startswith('//')]
        if ms:
            assert len(ms) == 1, (row, len(ms))
            m = ms[0]
            rest = m.group(3)
            if xb is not None:
                rest = re.sub(r'crossblend\s+[\d.]+', 'crossblend %s' % xb, rest) if 'crossblend' in rest else rest + '\tcrossblend %s' % xb
            txt = txt[:m.start()] + m.group(1) + clip + rest + txt[m.end():]
        else:
            new.append('\t%s\t\t%s\t\tcrossblend %s\t// HZM coop [ads heavy] %s' % (row, clip, xb if xb is not None else 0.1, why))
        chk = [l for l in (txt.splitlines() + new) if l.split('//')[0].split()[:1] == [row]]
        assert len(chk) == 1 and clip in chk[0], (row, chk)
    if new:
        k = txt.rstrip().rfind('}')
        txt = txt[:k] + '\t//===================== HZM coop ADS heavy lane (staged 2026-10-12) =====================' + nl + nl.join(new) + nl + txt[k:]
    # every clip a row of ours names must exist in the staging tree
    for row, clip, xb, why in EDITS[cls]:
        if row not in without and not why.startswith('retail:'):
            assert os.path.isfile(hv.staged('models/human/animation/' + clip)), 'missing staged clip ' + clip
    dst = hv.staged(rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(txt.encode('latin-1'))
    print('%s: %d edits (%d skipped) -> %s' % (cls, len(EDITS[cls]), len([e for e in EDITS[cls] if e[0] in without]), rel))


if __name__ == '__main__':
    wo = ()
    if '--without' in sys.argv:
        wo = tuple(sys.argv[sys.argv.index('--without') + 1].split(','))
    for c in EDITS:
        build(c, wo)
