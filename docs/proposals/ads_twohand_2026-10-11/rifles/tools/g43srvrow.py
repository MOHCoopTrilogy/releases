"""Iron-sight G43: the SERVER-READ `reload` row back to the released clip (run rb39-rb41, bug: the 88-frame gun clip
held the server's WEAPON_RELOADING for 2.95 s instead of the scoped G43's 1.87 s - past the end of the torso's reload).

The 12 staged tiks: `reload coop_g43_irons_reload.skc` -> `reload g43_reload.skc` (56 frames, the released row, byte for
byte the scoped G43's). The aim-only row `reload_ads_empty` (88 frames, the carrier racked at 62-69) stays: the cgame
shows it on its OWN clock after the server's row has ended (coop_vmGunClipClock, engine ads-rifle-next).
tools/g43tik.py writes the same from now on (checked here: its output must equal the edited files).

    python g43srvrow.py
"""
import os, re, sys, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.normpath(os.path.join(HERE, '..', 'assets', 'models', 'weapons'))

n = 0
for f in sorted(os.listdir(W)):
    if not (f.lower().startswith('coop_g43_irons') and f.lower().endswith('.tik')):
        continue
    p = os.path.join(W, f)
    t = open(p, 'rb').read().decode('latin-1')
    if re.search(r'(?m)^[ \t]*reload[ \t]+g43_reload\.skc', t):
        print('already:', f); n += 1; continue
    t2, k = re.subn(r'(?m)^([ \t]*reload[ \t]+)coop_g43_irons_reload\.skc', r'\g<1>g43_reload.skc', t)
    assert k == 1, (f, k)
    assert t2.count('coop_g43_irons_reload_ads_empty.skc') == 1, f
    open(p, 'wb').write(t2.encode('latin-1'))
    n += 1
    print('reload row -> g43_reload.skc:', f)
assert n == 12, n
# the tik tool must now write exactly these files
sys.path.insert(0, HERE)
import g43tik
import tempfile
tmp = tempfile.mkdtemp(prefix='g43tik_')
g43tik.OUT = tmp
bad = []
for out, name in g43tik.main():
    a = open(os.path.join(tmp, out), 'rb').read()
    b = open(os.path.join(W, out), 'rb').read()
    if a != b:
        bad.append(out)
print('g43tik.py output equals the staged tiks:', 'YES' if not bad else 'NO %s' % bad, '(scratch: %s)' % tmp)
