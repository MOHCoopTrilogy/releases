"""Iron-sight G43: the staged tiks. assets/models/weapons/coop_g43_irons.tik + one per finish of the scoped G43
(coop_g43_irons_<finish>.tik) - each is the mod tree's own G43 tik of that finish with ONLY these changes:

  * skelmodel coop_g43_irons.skd (tools/g43irons.py: scope, mount, rings, turrets, lens removed; the two sights
    rebuilt as the surface coop_sight); the `surface svt_lens` line becomes `surface coop_sight shader coop_g43_sight`
  * name "G 43 Irons" / "G 43 Irons (<Finish>)" - a NEW base name: the cgame's scope table lists "G 43", so a
    finish-style name "G 43 (Irons)" would be stripped to "G 43" and get the ZF4 scope picture
  * no `zoom` (the tik's zoom 30 is the scope; an iron-sighted gun has none - M1 Garand, Kar98) and no zoomspreadmult /
    zoommovement
  * ACCURACY and MOVEMENT = the M1 Garand's rows (the scoped G43's 59..300 hip spread is a sniper's hip penalty that
    only its 0.055 zoom multiplier takes back; without the zoom it would never hit). Damage, fire delay, magazine
    (10), ammo, sounds, recoil kick, reload: the G43's own, untouched.   <- A DECISION FOR THE USER (README)
  * airange long (the Garand's; was sniper)
Rank: 271 (270 = the scoped G43; no tik of the mod tree uses 271).

    python g43tik.py            writes the tiks, prints one line per tik
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\models\weapons"
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets', 'models', 'weapons'))
# source tik -> finish key of the new file name
SRC = [('G43.tik', ''), ('g43_gold.tik', 'gold'), ('g43_chrome.tik', 'chrome'), ('g43_blued.tik', 'blued'), ('g43_bloody.tik', 'bloody'),
       ('g43_camo_woodland.tik', 'camo_woodland'), ('g43_camo_winter.tik', 'camo_winter'), ('g43_camo_desert.tik', 'camo_desert'),
       ('G43_dhg43fleck.tik', 'dhg43fleck'), ('G43_hobbsg43urb.tik', 'hobbsg43urb'), ('G43_hobbsg43wood.tik', 'hobbsg43wood'),
       ('G43_lv_ttg43.tik', 'lv_ttg43')]
ACC = """		//HZM coop [g43 irons 2026-10-12] iron-sighted G43: the M1 Garand's accuracy rows (no zoom, no zoom multiplier)
		sp bulletrange			4000
		sp bulletspread			10 10 60 60
		sp firespreadmult		0.7 0.6 200 0.8

		dm bulletrange			4000
		dm bulletspread			10 10 80 80
		dm firespreadmult		0.75 0.6 200 0.8

		realism bulletrange		4000
		realism bulletspread		4 4 60 60
		realism firespreadmult		0.75 0.6 200 0.8
"""
MOVE = """		sp movementspeed		1.0
		dm movementspeed		1.05
		realism movementspeed		1.05
"""


def block(txt, head, nxt, new, nl):
    """replace the body between the `//   <head>   //` banner and the next banner"""
    a = re.search(r'//\s*%s\s*//[^\n]*\n[^\n]*=+//[^\n]*\n' % head, txt)
    assert a, head
    b = txt.index('//====', a.end())
    assert nxt in txt[b:b + 200], (head, txt[b:b + 200])
    return txt[:a.end()] + new.replace('\n', nl) + nl + '\t' + txt[b:]


def make(src, fin):
    raw = open(os.path.join(MOD, src), 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in raw else '\n'
    t = raw
    t, n = re.subn(r'skelmodel\s+g43\.skd', 'skelmodel coop_g43_irons.skd', t); assert n == 1
    # the lens surface is gone; the two sights are a surface of their own, dark steel on every finish
    t, n = re.subn(r'([ \t]*)surface\s+svt_lens\s+shader\s+svt_lens[^\n]*\n', lambda m: m.group(1) + 'surface coop_sight \tshader coop_g43_sight' + nl, t); assert n == 1
    m = re.search(r'(\n\s*name\s+)"G 43( \([^"]*\))?"', t); assert m, src
    name = 'G 43 Irons' + (m.group(2) or '')
    t = t[:m.start()] + m.group(1) + '"%s"' % name + t[m.end():]
    t, n = re.subn(r'(\n\s*rank\s+)\d+\s+\d+', r'\g<1>271 271', t); assert n == 1
    t = block(t, 'WEAPON ACCURACY', 'DAMAGE', ACC, nl)
    t = block(t, 'PLAYER MOVEMENT', 'RIFLE BUTT', MOVE, nl)
    t, n = re.subn(r'(\n\s*crosshair\s+1[^\n]*\n)\s*zoom\s+30[^\n]*\n', r'\g<1>', t); assert n == 1
    t, n = re.subn(r'(airange\s+)sniper', r'\g<1>long', t); assert n == 1
    t, n = re.subn(r'addon_playerweapon_german_g43\b', 'addon_playerweapon_german_g43_irons', t)
    t = t.replace('German sniper rifle - G43.', 'German semi-automatic rifle - G43 with iron sights (no scope).')
    assert 'zoom' not in re.sub(r'//[^\n]*', '', t).lower().replace('zoomspreadmult', '').replace('zoommovement', '') or True
    code = re.sub(r'//[^\n]*', '', t)
    assert not re.search(r'\bzoom\b|zoomspreadmult|zoommovement|svt_lens', code) and 'coop_sight' in code, src
    d = 0
    for ln in code.splitlines():
        d += ln.count('{') - ln.count('}')
    assert d == 0, src
    out = 'coop_g43_irons%s.tik' % (('_' + fin) if fin else '')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, out), 'wb').write(t.encode('latin-1'))
    return out, name


def main():
    rows = []
    for src, fin in SRC:
        out, name = make(src, fin)
        rows.append((out, name))
        print('%-24s -> %-36s "%s"' % (src, out, name))
    return rows


if __name__ == '__main__':
    main()
