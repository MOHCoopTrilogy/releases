"""Iron-sight FG 42: the staged tiks. assets/models/weapons/coop_fg42_irons.tik + one per finish of the scoped FG 42
(coop_fg42_irons_<finish>.tik) - each is the mod tree's own FG 42 tik of that finish with ONLY these changes (the rifle
lane's G 43 Irons recipe, rifles/tools/g43tik.py):

  * skelmodel coop_fg42_irons.skd (tools/fg42irons.py); `surface fg42lens ...` becomes `surface coop_sight shader
    coop_fg42_sight`
  * name "FG 42 Irons" / "FG 42 Irons (<Finish>)" - a NEW base name: the cgame's scope table lists "FG 42", a
    finish-style name would be stripped to it and get the ZF4 scope picture (bug-3713)
  * no `zoom`, no zoomspreadmult / zoommovement
  * ACCURACY and MOVEMENT = the BAR's rows, read from the mod tree's bar.tik when this runs (the scoped FG 42's hip
    spread 59..300 is a sniper's hip penalty that only its 0.055 zoom multiplier takes back). Damage, fire delay,
    magazine (20), ammo, sounds, recoil kick, reload: the FG 42's own.            <- A DECISION FOR THE USER (README)
  * rank 231 (230 = the scoped FG 42; no tik of the mod tree uses 231)

    python fg42tik.py            writes the 8 tiks, prints one line per tik
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\models\weapons"
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets', 'models', 'weapons'))
SRC = [('FG42.tik', ''), ('fg42_gold.tik', 'gold'), ('fg42_chrome.tik', 'chrome'), ('fg42_blued.tik', 'blued'), ('fg42_bloody.tik', 'bloody'),
       ('fg42_camo_woodland.tik', 'camo_woodland'), ('fg42_camo_winter.tik', 'camo_winter'), ('fg42_camo_desert.tik', 'camo_desert')]
BANNER = r'//\s*%s[^\n]*//[^\n]*\n[^\n]*=+//[^\n]*\n'


def body(txt, head):
    a = re.search(BANNER % head, txt); assert a, head
    b = txt.index('//====', a.end())
    return a.end(), b


def donor(head):
    t = open(os.path.join(MOD, 'bar.tik'), 'rb').read().decode('latin-1')
    a, b = body(t, head)
    rows = [ln.rstrip() for ln in t[a:b].replace('\r\n', '\n').split('\n') if ln.strip() and not ln.strip().startswith('//')]
    assert rows and not any('zoom' in r.lower() for r in rows), head
    return rows


def make(src, fin, acc, mov):
    raw = open(os.path.join(MOD, src), 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in raw else '\n'
    t = raw
    t, n = re.subn(r'skelmodel\s+fg42\.skd', 'skelmodel coop_fg42_irons.skd', t); assert n == 1, src
    t, n = re.subn(r'(\n[ \t]*)surface\s+fg42lens\s+shader\s+\S+[^\n]*', lambda m: m.group(1) + 'surface coop_sight shader coop_fg42_sight', t); assert n == 1, src
    m = re.search(r'(\n\s*name\s+)"FG 42( \([^"]*\))?"', t); assert m, src
    name = 'FG 42 Irons' + (m.group(2) or '')
    t = t[:m.start()] + m.group(1) + '"%s"' % name + t[m.end():]
    t, n = re.subn(r'(\n\s*rank\s+)\d+\s+\d+', r'\g<1>231 231', t); assert n == 1, src
    for head, rows, why in (('WEAPON ACCURACY', acc, "the BAR's accuracy rows (no zoom, no zoom multiplier)"), ('PLAYER MOVEMENT', mov, "the BAR's movement rows")):
        a, b = body(t, head)
        t = t[:a] + nl + '\t\t//HZM coop [fg42 irons 2026-10-13] iron-sighted FG 42: ' + why + nl + nl.join(rows) + nl + nl + '\t' + t[b:]
    t, n = re.subn(r'\n[ \t]*zoom[ \t]+\d+[^\n]*', '', t); assert n == 1, src
    code = re.sub(r'//[^\n]*', '', t)
    assert not re.search(r'\bzoom\b|zoomspreadmult|zoommovement|fg42lens', code) and 'coop_sight' in code, src
    d = 0
    for ln in code.splitlines():
        d += ln.count('{') - ln.count('}')
        assert d >= 0, src
    assert d == 0, src
    out = 'coop_fg42_irons%s.tik' % (('_' + fin) if fin else '')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, out), 'wb').write(t.encode('latin-1'))
    return out, name


def main():
    acc, mov = donor('WEAPON ACCURACY'), donor('PLAYER MOVEMENT')
    print('accuracy rows (BAR):', ' | '.join(' '.join(r.split('//')[0].split()) for r in acc))
    print('movement rows (BAR):', ' | '.join(' '.join(r.split('//')[0].split()) for r in mov))
    used = set()
    for f in os.listdir(MOD):
        if f.lower().endswith('.tik'):
            m = re.search(r'\n\s*rank\s+(\d+)', open(os.path.join(MOD, f), 'rb').read().decode('latin-1'))
            if m:
                used.add(int(m.group(1)))
    assert 231 not in used, 'rank 231 is taken'
    rows = []
    for src, fin in SRC:
        out, name = make(src, fin, acc, mov)
        rows.append((out, name))
        print('%-24s -> %-36s "%s"' % (src, out, name))
    return rows


if __name__ == '__main__':
    main()
