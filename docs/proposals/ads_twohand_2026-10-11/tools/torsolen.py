"""Lengths that decide a pistol reload: the torso alias (= the server's reload duration, the state leaves on
ANIMDONE_TORSO) against the first-person rows cgame plays (hip and aimed). Mod tree first, then the installed paks,
staged rows (../stage or the proposal's assets) last-wins when STAGED=1.

    python torsolen.py [alias ...]
"""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
vfs = R.vfs
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
STG = os.environ.get('STAGE_TREE', '')


def rows(fn):
    out = {}
    txt = ''
    d = vfs.read('models/player/base/' + fn)
    if d:
        txt += d.decode('latin-1')
    f = os.path.join(MOD, 'models', 'player', 'base', fn)
    if os.path.isfile(f):
        txt = open(f, encoding='latin-1').read() + '\n' + txt
    if STG and os.path.isfile(os.path.join(STG, 'models', 'player', 'base', fn)):
        txt = open(os.path.join(STG, 'models', 'player', 'base', fn), encoding='latin-1').read() + '\n' + txt
    for ln in txt.replace('\r', '').splitlines():
        t = ln.split('//')[0].split()
        if len(t) >= 2 and t[1].lower().endswith('.skc') and t[0].lower() not in out:
            out[t[0].lower()] = t[1]
    return out


def length(clip):
    for base in ([STG] if STG else []) + [MOD]:
        f = os.path.join(base, 'models', 'human', 'animation', clip.replace('/', os.sep))
        if os.path.isfile(f):
            a = R.load(f)
            return a.numFrames, a.frameTime
    a = R.load('models/human/animation/' + clip)
    return a.numFrames, a.frameTime


allrows = {}
for fn in ('anims_shared.txt', 'fps_anims_pistol.txt', 'anims_pistol.txt', 'anims.txt'):
    for k, v in rows(fn).items():
        allrows.setdefault(k, v)
want = [a.lower() for a in sys.argv[1:]] or sorted(k for k in allrows if 'reload' in k and ('pistol' in k or 'colt' in k or 'p38' in k or 'histandard' in k or 'beretta' in k or 'webley' in k or 'nagant' in k or 'm10' in k or 'c96' in k))
for k in want:
    if k not in allrows:
        print('%-40s -' % k); continue
    try:
        n, ft = length(allrows[k])
        print('%-40s %-58s %3d f x %.4f = %.2f s' % (k, allrows[k], n, ft, n * ft))
    except Exception as e:
        print('%-40s %-58s load failed: %s' % (k, allrows[k], e))
