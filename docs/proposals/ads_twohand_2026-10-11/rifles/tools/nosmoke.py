"""MEASURE-ONLY weapon tiks: the shot's lingering muzzle smoke (models/fx/snipesmoke.tik spawned on tag_barrel) hangs in
the centre box for ~0.5 s after an aimed shot - exactly while the bolt is cycled - and the engine centre-box measure
(rbox.py) counts it as cover on a dark backdrop (run ra2: 17 % with the model well under the box). For the measure
runs the overlay carries the gun's tik with that one emitter removed. NEVER staged for shipping: the output goes to
tools/measure_ov/, which mkov_rifle.py only packs with --measure.

    python nosmoke.py kar98.tik [more.tik ...]
"""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
import vfs
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
OUT = os.path.join(HERE, 'measure_ov')

for tk in sys.argv[1:]:
    rel = 'models/weapons/' + tk
    st = os.path.join(ASSETS, rel.replace('/', os.sep))
    raw = open(st, 'rb').read() if os.path.isfile(st) else vfs.read(rel)
    t = raw.decode('latin-1')
    t2, n = re.subn(r'[ \t]*entry\s+tagspawn\s+tag_barrel\s*\([^()]*?model\s+models/fx/snipesmoke\.tik[^()]*?\)[ \t]*\r?\n', '', t)
    assert n >= 1, tk + ': no snipesmoke emitter found'
    d = 0
    for ln in t2.splitlines():
        c = ln.split('//')[0]; d += c.count('{') - c.count('}') + c.count('(') - c.count(')')
    assert d == 0, tk
    dst = os.path.join(OUT, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(t2.encode('latin-1'))
    print(tk, 'smoke emitters removed:', n, '->', dst)
