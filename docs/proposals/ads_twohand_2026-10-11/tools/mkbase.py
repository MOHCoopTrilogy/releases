"""Harness plumbing for the ADS test overlay, rebuilt on the RELEASED weather.scr (read from the live pak, read-only):
the marker shader + coop_mod/weather.scr with the coop_isPoll test thread spliced in. -> ovbase_1021.pk3"""
import zipfile, glob, os, re, sys
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
HERE = os.path.dirname(os.path.abspath(__file__))
old = zipfile.ZipFile(r"G:\mohaa-adsanim\ov_rel2.pk3")
shader = old.read('scripts/zz_ironsight_test.shader')
ow = old.read('coop_mod/weather.scr').decode('latin-1')
# newest released weather.scr: the pak that sorts last and has it
cur = None
for p in sorted(glob.glob(os.path.join(GOG, '*.pk3'))):
    try:
        z = zipfile.ZipFile(p)
    except Exception:
        continue
    for n in z.namelist():
        if n.lower() == 'coop_mod/weather.scr':
            cur = (p, z.read(n).decode('latin-1'))
print('released weather.scr from', cur[0], len(cur[1]))
cw = cur[1]
hook = [l for l in ow.splitlines(True) if 'coop_isPoll' in l]
assert len(hook) == 1, hook
lines = ow.splitlines(True)
hi = lines.index(hook[0])
anchor = lines[hi - 1]
assert cw.count(anchor) == 1, ('anchor', anchor, cw.count(anchor))
# the test thread body: from its label to the end of the old file, minus anything the released file already has
m = re.search(r'(?m)^coop_is_test:', ow)
assert m
start = ow.rfind('//TEST OVERLAY ONLY', 0, m.start())
assert start > 0
body = chr(13) + chr(10) + ow[start:]
print('labels in spliced body:', re.findall('(?m)^([A-Za-z_][A-Za-z0-9_]*):', body))
assert 'coop_is_test:' not in cw
new = cw.replace(anchor, anchor + hook[0], 1)
if not new.endswith('\n'):
    new += '\r\n'
new += body
# running-depth brace scan (TRAPS: depth never negative, 0 at every column-0 label)
d = 0
for i, l in enumerate(new.splitlines()):
    c = l.split('//')[0]
    if re.match(r'^[A-Za-z_][A-Za-z0-9_ ]*:', c) and d != 0:
        print('DEPTH', d, 'at label line', i + 1, l[:60]); sys.exit(1)
    d += c.count('{') - c.count('}')
    assert d >= 0, (i + 1, l)
assert d == 0, d
assert '\u2014' not in new and not new.startswith('\ufeff')
out = os.path.join(HERE, 'ovbase_1021.pk3')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('scripts/zz_ironsight_test.shader', shader)
    z.writestr('coop_mod/weather.scr', new.encode('latin-1'))
print('wrote', out, 'weather.scr', len(new))
